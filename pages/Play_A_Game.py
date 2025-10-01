# pages/Play_A_Game.py
import streamlit as st
from GitLab_Persistence import (
    load_players_from_git,
    save_leaderboard_to_git,
    load_leaderboard_from_git,
    load_history_from_git,
    save_history_to_git,
    gitlab_list_leaderboards_dir
)
import trueskill
from datetime import datetime

st.set_page_config(page_title="✏️ Record Game / Matchmaking", page_icon="✏️")
st.title("✏️ Record Game & Matchmaking")

env = trueskill.TrueSkill(draw_probability=0)

# --- Load players and games ---
players = load_players_from_git()
files = gitlab_list_leaderboards_dir()
game_names = sorted(list({fn.replace("_leaderboard.json", "").replace("_history.json", "")
                          for fn in files if fn.endswith("_leaderboard.json") or fn.endswith("_history.json")}))

game_option = st.selectbox("Select game (or type new)", options=["<New Game>"] + game_names)
if game_option == "<New Game>":
    game_name_input = st.text_input("New game name")
    game_name = game_name_input.strip() if game_name_input else None
else:
    game_name = game_option

if not game_name:
    st.info("Pick or type a game name to record matches for.")
    st.stop()

st.subheader(f"Recording for game: {game_name}")

# --- Load leaderboard and history (auto-create if missing) ---
leaderboard = load_leaderboard_from_git(game_name) or {}
history = load_history_from_git(game_name) or {"matches": []}

if not players:
    st.warning("No global players found. Add players first in Player Manager.")
    st.stop()

# --- Match recording tabs ---
st.header("Select Players")
selected_players = st.multiselect("Pick players for this match", options=players)

if selected_players:
    # --- Team setup ---
    team_mode = st.radio("Team Setup Mode", options=["Manual Teams", "Auto-Balance Teams"])
    team_a, team_b = [], []

    if team_mode == "Manual Teams":
        team_a = st.multiselect("Team A players", options=selected_players)
        team_b = [p for p in selected_players if p not in team_a]
        st.write("Team B:", ", ".join(team_b) if team_b else "(empty)")

    elif team_mode == "Auto-Balance Teams":
        def player_mu(p):
            return leaderboard.get(p, {"mu": env.mu}).get("mu", env.mu)

        sorted_players = sorted(selected_players, key=player_mu, reverse=True)
        team_a = sorted_players[::2]
        team_b = sorted_players[1::2]
        st.write("Auto-balanced Teams:")
        st.write("Team A:", ", ".join(team_a))
        st.write("Team B:", ", ".join(team_b))

    # --- Record match ---
    winner = st.radio("Winner", options=["Team A", "Team B"])

    if st.button("Record Match"):
        try:
            # Ratings
            ratings_a = [trueskill.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma})) for p in team_a]
            ratings_b = [trueskill.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma})) for p in team_b]

            ranks = [0, 1] if winner == "Team A" else [1, 0]
            new_ratings = env.rate([ratings_a, ratings_b], ranks=ranks)

            # Update leaderboard
            for name, r in zip(team_a, new_ratings[0]):
                leaderboard[name] = {"mu": r.mu, "sigma": r.sigma}
            for name, r in zip(team_b, new_ratings[1]):
                leaderboard[name] = {"mu": r.mu, "sigma": r.sigma}

            # Update history
            history.setdefault("matches", []).append({
                "timestamp": datetime.utcnow().isoformat(),
                "type": "team",
                "team_a": team_a,
                "team_b": team_b,
                "winner": winner
            })

            # Push updates to GitLab
            save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record match for {game_name}")
            save_history_to_git(game_name, history, commit_message=f"Update match history for {game_name}")

            st.success("Match recorded successfully!")

        except Exception as e:
            st.error(f"Failed to record match: {e}")
