# pages/Play_A_Game.py
import streamlit as st
import trueskill
from datetime import datetime
from GitLab_Persistence import (
    load_players_from_git,
    save_players_to_git,
    load_leaderboard_from_git,
    save_leaderboard_to_git,
    load_history_from_git,
    save_history_to_git,
    gitlab_list_leaderboards_dir
)

st.set_page_config(page_title="Record Game", page_icon="✏️")
st.title("✏️ Record a Game (Individual or Team)")

# ---------------- TrueSkill Environment ----------------
env = trueskill.TrueSkill(draw_probability=0)

# ---------------- Load Players ----------------
players = load_players_from_git()
if not players:
    st.warning("No players found. Add players in the Player Manager page first.")
    st.stop()

# ---------------- Game Selection ----------------
files = gitlab_list_leaderboards_dir()
existing_games = sorted(list({fn.replace("_leaderboard.json", "").replace("_history.json","") for fn in files if fn.endswith(".json")}))
game_option = st.selectbox("Select game (or type new game name)", options=["<New Game>"] + existing_games)

if game_option == "<New Game>":
    game_name_input = st.text_input("New Game Name")
    game_name = game_name_input.strip() if game_name_input else None
else:
    game_name = game_option

if not game_name:
    st.info("Pick or type a game name to record matches for.")
    st.stop()

st.subheader(f"Recording for game: {game_name}")

# ---------------- Load leaderboard & history ----------------
leaderboard = load_leaderboard_from_git(game_name)
history = load_history_from_git(game_name)

# ---------------- Helper function ----------------
def get_rating(name, leaderboard):
    """Return a trueskill.Rating object for a player, default if missing."""
    if name in leaderboard:
        return env.Rating(mu=leaderboard[name]["mu"], sigma=leaderboard[name]["sigma"])
    else:
        return env.Rating()

# ---------------- Tabs ----------------
tab_individual, tab_team = st.tabs(["Individual", "Team"])

# ---------------- Individual Game ----------------
with tab_individual:
    st.write("Select players in **finishing order** (winner first):")
    ordered = st.multiselect("Players", options=players)
    if st.button("Record Individual Game"):
        if len(ordered) < 2:
            st.warning("Select at least two players.")
        else:
            try:
                ratings = [get_rating(p, leaderboard) for p in ordered]
                ranks = list(range(len(ratings)))
                new_ratings = env.rate(ratings, ranks=ranks)
                for name, r in zip(ordered, new_ratings):
                    leaderboard[name] = {"mu": r.mu, "sigma": r.sigma}
                # Update history
                history.setdefault("matches", []).append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "individual",
                    "results": ordered
                })
                # Save to GitLab
                save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record individual match for {game_name}")
                save_history_to_git(game_name, history, commit_message=f"Add match to {game_name} history")
                st.success("Individual game recorded successfully.")
            except Exception as e:
                st.error(f"Failed to record game: {e}")

# ---------------- Team Game ----------------
with tab_team:
    selected_players = st.multiselect("Select all players for this match", options=players)
    if selected_players:
        team_a = st.multiselect("Team A players", options=selected_players)
        team_b = [p for p in selected_players if p not in team_a]
        st.write("Team B:", ", ".join(team_b) if team_b else "(empty)")
        winner = st.radio("Winner", options=["Team A", "Team B"])
        if st.button("Record Team Game"):
            if not team_a or not team_b:
                st.warning("Both teams must have at least one player.")
            else:
                try:
                    ratings_a = [get_rating(p, leaderboard) for p in team_a]
                    ratings_b = [get_rating(p, leaderboard) for p in team_b]
                    if winner == "Team A":
                        new_team_ratings = env.rate([ratings_a, ratings_b], ranks=[0,1])
                    else:
                        new_team_ratings = env.rate([ratings_a, ratings_b], ranks=[1,0])
                    # Update leaderboard
                    for name, r in zip(team_a, new_team_ratings[0]):
                        leaderboard[name] = {"mu": r.mu, "sigma": r.sigma}
                    for name, r in zip(team_b, new_team_ratings[1]):
                        leaderboard[name] = {"mu": r.mu, "sigma": r.sigma}
                    # Update history
                    history.setdefault("matches", []).append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "type": "team",
                        "team_a": team_a,
                        "team_b": team_b,
                        "winner": winner
                    })
                    # Save to GitLab
                    save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record team match for {game_name}")
                    save_history_to_git(game_name, history, commit_message=f"Add team match to {game_name} history")
                    st.success("Team game recorded successfully.")
                except Exception as e:
                    st.error(f"Failed to record game: {e}")

st.markdown("---")
st.info("Games recorded here are saved directly to GitLab. Make sure your GITLAB_TOKEN and PROJECT_ID are set correctly.")
