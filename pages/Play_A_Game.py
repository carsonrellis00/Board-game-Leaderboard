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
import random

st.set_page_config(page_title="Record & Matchmake Game", page_icon="⚔️")
st.title("⚔️ Record a Game & Matchmaking")

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

# ---------------- Helper Functions ----------------
def get_rating(name):
    """Return a trueskill.Rating object for a player, default if missing."""
    if name in leaderboard:
        return env.Rating(mu=leaderboard[name]["mu"], sigma=leaderboard[name]["sigma"])
    else:
        return env.Rating()

def auto_balance_teams(selected_players):
    """Split players into two balanced teams by TrueSkill."""
    if not selected_players:
        return [], []
    sorted_players = sorted(selected_players, key=lambda p: leaderboard.get(p, {"mu": env.mu})["mu"], reverse=True)
    team_a, team_b = [], []
    rating_a, rating_b = 0, 0
    for p in sorted_players:
        mu = leaderboard.get(p, {"mu": env.mu})["mu"]
        if rating_a <= rating_b:
            team_a.append(p)
            rating_a += mu
        else:
            team_b.append(p)
            rating_b += mu
    return team_a, team_b

# ---------------- Team / Matchmaking Tab ----------------
selected_players = st.multiselect("Select players for this match", options=players)

if selected_players:
    # Auto-team split
    if st.checkbox("Auto-balance teams"):
        team_a, team_b = auto_balance_teams(selected_players)
    else:
        team_a = st.multiselect("Team A players", options=selected_players)
        team_b = [p for p in selected_players if p not in team_a]

    st.write("Team A:", ", ".join(team_a) if team_a else "(empty)")
    st.write("Team B:", ", ".join(team_b) if team_b else "(empty)")

    winner = st.radio("Select winning team", options=["Team A", "Team B"])

    if st.button("Record Game"):
        if not team_a or not team_b:
            st.warning("Both teams must have at least one player.")
        else:
            try:
                ratings_a = [get_rating(p) for p in team_a]
                ratings_b = [get_rating(p) for p in team_b]

                ranks = [0, 1] if winner == "Team A" else [1, 0]
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

                st.success("Game recorded successfully!")
            except Exception as e:
                st.error(f"Failed to record game: {e}")
