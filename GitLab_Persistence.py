import streamlit as st
import os
import json
import requests
import trueskill
from datetime import datetime
from urllib.parse import quote_plus
import base64

# ---- Streamlit page config ----
st.set_page_config(page_title="💾 GitLab Persistence", page_icon="💾")
st.title("💾 GitLab-backed Persistence (Players & Matches)")

# ---------- Configuration: get token/repo/branch ----------
def get_secret(name):
    v = os.getenv(name)
    if v:
        return v
    try:
        return st.secrets[name]
    except Exception:
        return None

GITLAB_TOKEN = get_secret("GITLAB_TOKEN")
GITLAB_REPO = get_secret("GITLAB_REPO")  # string like "username/repo"
BRANCH = get_secret("BRANCH") or "main"

if not GITLAB_TOKEN or not GITLAB_REPO:
    st.error("GitLab config missing — set GITLAB_TOKEN and GITLAB_REPO as Streamlit secrets or environment variables.")
    st.stop()

API_BASE = f"https://gitlab.com/api/v4/projects/{quote_plus(GITLAB_REPO)}"
HEADERS = {"PRIVATE-TOKEN": GITLAB_TOKEN}

# ---------- Helper functions ----------
def gitlab_raw_get(file_path):
    """Return content of a file in GitLab as string, or None if not found."""
    url = f"{API_BASE}/repository/files/{quote_plus(file_path)}?ref={BRANCH}"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    if resp.status_code == 200:
        file_info = resp.json()
        content_encoded = file_info.get("content", "")
        try:
            return base64.b64decode(content_encoded).decode("utf-8")
        except Exception:
            return content_encoded
    return None

def gitlab_file_exists(file_path):
    url = f"{API_BASE}/repository/files/{quote_plus(file_path)}?ref={BRANCH}"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    return resp.status_code == 200

def gitlab_create_or_update_file(file_path, data, commit_message):
    """Create or update JSON file in GitLab."""
    content = json.dumps(data, indent=2, ensure_ascii=False)
    url = f"{API_BASE}/repository/files/{quote_plus(file_path)}"
    payload = {
        "branch": BRANCH,
        "content": content,
        "commit_message": commit_message,
        "encoding": "text"
    }
    if gitlab_file_exists(file_path):
        resp = requests.put(url, headers=HEADERS, json=payload, timeout=20)
    else:
        resp = requests.post(url, headers=HEADERS, json=payload, timeout=20)
    if resp.status_code not in (200, 201):
        st.error(f"GitLab API error {resp.status_code}: {resp.text}")
    return resp.json()

def gitlab_list_leaderboards_dir():
    """Return list of files under leaderboards/"""
    url = f"{API_BASE}/repository/tree?path=leaderboards&ref={BRANCH}&per_page=100"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    if resp.status_code == 200:
        return [item["name"] for item in resp.json()]
    return []

# ---------- TrueSkill env ----------
env = trueskill.TrueSkill(draw_probability=0)

# ---------- Load / Save helpers ----------
def load_leaderboard_from_git(game_name):
    file_path = f"leaderboards/{game_name}_leaderboard.json"
    data = gitlab_raw_get(file_path)
    if data:
        try:
            return json.loads(data)
        except Exception:
            return {}
    return {}

def save_leaderboard_to_git(game_name, leaderboard_dict, commit_message=None):
    if commit_message is None:
        commit_message = f"Update {game_name} leaderboard"
    file_path = f"leaderboards/{game_name}_leaderboard.json"
    gitlab_create_or_update_file(file_path, leaderboard_dict, commit_message)

def load_history_from_git(game_name):
    file_path = f"leaderboards/{game_name}_history.json"
    data = gitlab_raw_get(file_path)
    if data:
        try:
            return json.loads(data)
        except Exception:
            return {"matches": []}
    return {"matches": []}

def save_history_to_git(game_name, history_dict, commit_message=None):
    if commit_message is None:
        commit_message = f"Update {game_name} history"
    file_path = f"leaderboards/{game_name}_history.json"
    gitlab_create_or_update_file(file_path, history_dict, commit_message)

def load_players_from_git():
    file_path = "leaderboards/players.json"
    data = gitlab_raw_get(file_path)
    if data:
        try:
            players_data = json.loads(data)
            if isinstance(players_data, list):
                return players_data
            if isinstance(players_data, dict):
                return list(players_data.keys())
        except Exception:
            return []
    return []

def save_players_to_git(players_list):
    file_path = "leaderboards/players.json"
    gitlab_create_or_update_file(file_path, players_list, "Update players list")

# ---------- UI: Add / Remove Players ----------
st.header("👥 Add / Remove Players (GitLab-backed)")

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
                    st.success(f"{new_player} added to GitLab players list.")
            except Exception as e:
                st.error(f"Failed to add player: {e}")

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

# ---------- UI: Record a Game ----------
st.header("✏️ Record a Game (Individual or Team)")

# Gather existing games from leaderboards dir
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

leaderboard = load_leaderboard_from_git(game_name)
history = load_history_from_git(game_name)
all_players = load_players_from_git()
if not all_players:
    st.warning("No players found. Add players first.")
    st.stop()

tab1, tab2 = st.tabs(["Individual", "Team"])

# --- Individual Tab ---
with tab1:
    ordered = st.multiselect("Select players in finishing order (winner first)", options=all_players)
    if st.button("Record Individual Game"):
        if len(ordered) < 2:
            st.warning("Select at least two players.")
        else:
            try:
                ratings = [env.Rating(mu=leaderboard.get(n, {}).get("mu",25.0),
                                       sigma=leaderboard.get(n, {}).get("sigma",8.333))
                           for n in ordered]
                ranks = list(range(len(ratings)))
                new_ratings = env.rate(ratings, ranks=ranks)
                for name, r in zip(ordered, new_ratings):
                    leaderboard[name] = {"mu": r.mu, "sigma": r.sigma}
                history.setdefault("matches", []).append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "individual",
                    "results": ordered
                })
                save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record individual match for {game_name}")
                save_history_to_git(game_name, history, commit_message=f"Add match to {game_name} history")
                st.success("Individual game recorded and pushed to GitLab.")
            except Exception as e:
                st.error(f"Failed to record game: {e}")

# --- Team Tab ---
with tab2:
    sel = st.multiselect("Select all players for this team match", options=all_players)
    if sel:
        team_a = st.multiselect("Team A players", options=sel)
        team_b = [p for p in sel if p not in team_a]
        st.write("Team B:", ", ".join(team_b) if team_b else "(empty)")
        winner = st.radio("Winner", options=["Team A", "Team B"])
        if st.button("Record Team Game"):
            if not team_a or not team_b:
                st.warning("Both teams must have at least one player.")
            else:
                try:
                    ratings_a = [env.Rating(mu=leaderboard.get(n, {}).get("mu",25.0),
                                            sigma=leaderboard.get(n, {}).get("sigma",8.333)) for n in team_a]
                    ratings_b = [env.Rating(mu=leaderboard.get(n, {}).get("mu",25.0),
                                            sigma=leaderboard.get(n, {}).get("sigma",8.333)) for n in team_b]
                    ranks = [0,1] if winner == "Team A" else [1,0]
                    new_team_ratings = env.rate([ratings_a, ratings_b], ranks=ranks)
                    for name, r in zip(team_a, new_team_ratings[0]):
                        leaderboard[name] = {"mu": r.mu, "sigma": r.sigma}
                    for name, r in zip(team_b, new_team_ratings[1]):
                        leaderboard[name] = {"mu": r.mu, "sigma": r.sigma}
                    history.setdefault("matches", []).append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "type": "team",
                        "team_a": team_a,
                        "team_b": team_b,
                        "winner": winner
                    })
                    save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record team match for {game_name}")
                    save_history_to_git(game_name, history, commit_message=f"Add team match to {game_name} history")
                    st.success("Team game recorded and pushed to GitLab.")
                except Exception as e:
                    st.error(f"Failed to record team game: {e}")

st.markdown("---")
st.info("This page writes directly to your GitLab repository. Make sure your GITLAB_TOKEN and GITLAB_REPO are set in Streamlit secrets or environment variables.")
