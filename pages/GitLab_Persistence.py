# pages/GitLab_Persistence.py
import streamlit as st
import os, json, requests
import trueskill
from datetime import datetime
from urllib.parse import quote_plus

st.set_page_config(page_title="GitLab Persistence", page_icon="💾")
st.title("💾 GitLab-backed Persistence (Players & Matches)")

# ---------- Configuration: get token/project/branch ----------
def get_secret(name):
    v = os.getenv(name)
    if v:
        return v
    try:
        return st.secrets[name]
    except Exception:
        return None

GITLAB_TOKEN = get_secret("GITLAB_TOKEN")
PROJECT_ID = get_secret("PROJECT_ID")  # can be numeric id or "namespace%2Frepo"
BRANCH = get_secret("BRANCH") or "main"

if not GITLAB_TOKEN or not PROJECT_ID:
    st.error("GitLab config missing — set GITLAB_TOKEN and PROJECT_ID as environment variables or Streamlit secrets.")
    st.stop()

# If PROJECT_ID is not numeric, GitLab API expects URL-encoded path; we'll URL-encode it later when building URLs.
def project_id_for_api(pid):
    # If numeric, return as-is; otherwise URL-encode.
    try:
        int(pid)
        return str(pid)
    except Exception:
        return quote_plus(pid)

PROJ_API_ID = project_id_for_api(PROJECT_ID)
API_BASE = f"https://gitlab.com/api/v4/projects/{PROJ_API_ID}"

HEADERS = {"PRIVATE-TOKEN": GITLAB_TOKEN}

# ---------- Helper functions for GitLab file ops ----------
def gitlab_raw_get(file_path):
    """Return (status_code, parsed_json_or_text). file_path like 'leaderboards/players.json'."""
    url = f"{API_BASE}/repository/files/{quote_plus(file_path)}/raw?ref={BRANCH}"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    if resp.status_code == 200:
        try:
            return 200, resp.json()
        except Exception:
            return 200, resp.text
    return resp.status_code, resp.text

def gitlab_file_exists(file_path):
    url = f"{API_BASE}/repository/files/{quote_plus(file_path)}?ref={BRANCH}"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    return resp.status_code == 200

def gitlab_create_or_update_file(file_path, data, commit_message):
    """
    data: Python object (will be JSON dumped)
    If file exists -> PUT (update). Else -> POST (create).
    """
    content = json.dumps(data, indent=2, ensure_ascii=False)
    api_path = f"{API_BASE}/repository/files/{quote_plus(file_path)}"
    payload = {
        "branch": BRANCH,
        "content": content,
        "commit_message": commit_message,
        "encoding": "text"
    }
    # update if exists
    if gitlab_file_exists(file_path):
        resp = requests.put(api_path, headers=HEADERS, json=payload, timeout=20)
    else:
        resp = requests.post(api_path, headers=HEADERS, json=payload, timeout=20)
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"GitLab API error {resp.status_code}: {resp.text}")
    return resp.json()

def gitlab_list_leaderboards_dir():
    """Return list of file names under leaderboards/ (names only)."""
    url = f"{API_BASE}/repository/tree?path=leaderboards&ref={BRANCH}&per_page=100"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    if resp.status_code == 200:
        return [item["name"] for item in resp.json()]
    return []

# ---------- TrueSkill env ----------
env = trueskill.TrueSkill(draw_probability=0)

# ---------- Utility for leaderboard format ----------
# We'll store per-game leaderboards as: { "Alice": {"mu": 25.0, "sigma": 8.333}, ... }
def load_leaderboard_from_git(game_name):
    file_path = f"leaderboards/{game_name}_leaderboard.json"
    status, data = gitlab_raw_get(file_path)
    if status == 200 and isinstance(data, dict):
        return data
    return {}

def save_leaderboard_to_git(game_name, leaderboard_dict, commit_message=None):
    file_path = f"leaderboards/{game_name}_leaderboard.json"
    if commit_message is None:
        commit_message = f"Update {game_name} leaderboard"
    gitlab_create_or_update_file(file_path, leaderboard_dict, commit_message)

def load_history_from_git(game_name):
    file_path = f"leaderboards/{game_name}_history.json"
    status, data = gitlab_raw_get(file_path)
    if status == 200 and isinstance(data, dict):
        return data
    return {"matches": []}

def save_history_to_git(game_name, history_dict, commit_message=None):
    file_path = f"leaderboards/{game_name}_history.json"
    if commit_message is None:
        commit_message = f"Update {game_name} history"
    gitlab_create_or_update_file(file_path, history_dict, commit_message)

def load_players_from_git():
    file_path = "leaderboards/players.json"
    status, data = gitlab_raw_get(file_path)
    if status == 200:
        # players.json can be dict or list; we normalize to list of names
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return list(data.keys())
    return []

def save_players_to_git(players_list):
    file_path = "leaderboards/players.json"
    # store as list for simplicity
    gitlab_create_or_update_file(file_path, players_list, "Update players list")

# ---------- UI: Add Player ----------
st.header("👥 Add / Remove Players (persistent in GitLab)")

with st.form("add_player_form", clear_on_submit=True):
    new_player = st.text_input("Player name to add")
    submitted = st.form_submit_button("Add Player")
    if submitted:
        new_player = new_player.strip()
        if not new_player:
            st.warning("Enter a name.")
        else:
            try:
                players = load_players_from_git()
                if new_player in players:
                    st.info(f"{new_player} already exists.")
                else:
                    players.append(new_player)
                    save_players_to_git(players)
                    st.success(f"{new_player} added to players.json in GitLab.")
            except Exception as e:
                st.error(f"Failed to add player: {e}")

# Remove player UI
players_now = load_players_from_git()
if players_now:
    st.write("Current players:", ", ".join(players_now))
    remove = st.selectbox("Remove a player", options=[""] + players_now)
    if st.button("Remove Player") and remove:
        players_now.remove(remove)
        try:
            save_players_to_git(players_now)
            st.success(f"{remove} removed.")
        except Exception as e:
            st.error(f"Failed to remove player: {e}")
else:
    st.info("No players found yet. Add one above.")

st.markdown("---")

# ---------- UI: Record a game (Individual and Team) ----------
st.header("✏️ Record a Game (Individual or Team)")

# Gather existing games from leaderboards dir (extract base names)
files = gitlab_list_leaderboards_dir()
game_names = sorted(list({fn.replace("_leaderboard.json","").replace("_history.json","") for fn in files if fn.endswith(".json")}))
game_option = st.selectbox("Select game (or type a new name)", options=["<New Game>"] + game_names)

if game_option == "<New Game>":
    game_name_input = st.text_input("New game name")
    game_name = game_name_input.strip() if game_name_input else None
else:
    game_name = game_option

if not game_name:
    st.info("Pick or type a game name to record matches for.")
    st.stop()

st.subheader(f"Recording for game: {game_name}")

# Load current per-game leaderboard and history
leaderboard = load_leaderboard_from_git(game_name)  # dict name -> {mu,sigma}
history = load_history_from_git(game_name)          # dict with "matches" list

all_players = load_players_from_git()
if not all_players:
    st.warning("No global players found. Add players first.")
    st.stop()

tab1, tab2 = st.tabs(["Individual", "Team"])

# --- Individual tab ---
with tab1:
    ordered = st.multiselect("Select players in finishing order (winner first)", options=all_players)
    if st.button("Record Individual Game"):
        if len(ordered) < 2:
            st.warning("Select at least two players.")
        else:
            try:
                # prepare ratings list in order
                ratings = []
                for name in ordered:
                    p = leaderboard.get(name)
                    if p:
                        ratings.append(env.Rating(mu=p["mu"], sigma=p["sigma"]))
                    else:
                        ratings.append(env.Rating())  # default
                ranks = list(range(len(ratings)))
                new_ratings = env.rate(ratings, ranks=ranks)
                # update leaderboard dict
                for name, r in zip(ordered, new_ratings):
                    leaderboard[name] = {"mu": r.mu, "sigma": r.sigma}
                # append history
                history.setdefault("matches", []).append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "individual",
                    "results": ordered
                })
                # push
                save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record individual match for {game_name}")
                save_history_to_git(game_name, history, commit_message=f"Add match to {game_name} history")
                st.success("Individual game recorded and pushed to GitLab.")
            except Exception as e:
                st.error(f"Failed to record game: {e}")

# --- Team tab ---
with tab2:
    sel = st.multiselect("Select all players for this team match", options=all_players)
    if sel:
        team_a = st.multiselect("Team A players", options=sel)
        team_b = [p for p in sel if p not in team_a]
        st.write("Team B:", ", ".join(team_b) if team_b else "(empty)")
        winner = st.radio("Winner", options=["Team A", "Team B"])
        if st.button("Record Team Game"):
            if not team_a or not team_b:
                st.warning("Make sure both teams have at least one player.")
            else:
                try:
                    ratings_a = []
                    ratings_b = []
                    for name in team_a:
                        p = leaderboard.get(name)
                        ratings_a.append(env.Rating(mu=p["mu"], sigma=p["sigma"]) if p else env.Rating())
                    for name in team_b:
                        p = leaderboard.get(name)
                        ratings_b.append(env.Rating(mu=p["mu"], sigma=p["sigma"]) if p else env.Rating())
                    # determine ranks; winner rank 0
                    if winner == "Team A":
                        new_team_ratings = env.rate([ratings_a, ratings_b], ranks=[0,1])
                    else:
                        new_team_ratings = env.rate([ratings_a, ratings_b], ranks=[1,0])
                    # update leaderboard
                    for name, r in zip(team_a, new_team_ratings[0]):
                        leaderboard[name] = {"mu": r.mu, "sigma": r.sigma}
                    for name, r in zip(team_b, new_team_ratings[1]):
                        leaderboard[name] = {"mu": r.mu, "sigma": r.sigma}
                    # history
                    history.setdefault("matches", []).append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "type": "team",
                        "team_a": team_a,
                        "team_b": team_b,
                        "winner": winner
                    })
                    # push
                    save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record team match for {game_name}")
                    save_history_to_git(game_name, history, commit_message=f"Add team match to {game_name} history")
                    st.success("Team game recorded and pushed to GitLab.")
                except Exception as e:
                    st.error(f"Failed to record team game: {e}")

st.markdown("---")
st.info("This page writes directly to your GitLab repository. Make sure your GITLAB_TOKEN and PROJECT_ID are set in Streamlit secrets or environment variables.")
