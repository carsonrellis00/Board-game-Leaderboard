# pages/Play_A_Game.py
import streamlit as st
from GitLab_Persistence import (
    load_players_from_git,
    save_players_to_git,
    load_leaderboard_from_git,
    save_leaderboard_to_git,
    load_history_from_git,
    save_history_to_git,
    gitlab_list_leaderboards_dir
)
import trueskill
from datetime import datetime

st.set_page_config(page_title="Record Game / Matchmaking", page_icon="✏️")
st.title("✏️ Record Game & Matchmaking")

# ---- TrueSkill environment ----
env = trueskill.TrueSkill(draw_probability=0)

# ---- Load players and games ----
players = load_players_from_git() or []  # players is now a list of names
if not players:
    st.warning("No global players found. Add players first in Player Manager.")
    st.stop()

files = gitlab_list_leaderboards_dir() or []
game_names = sorted(list({
    fn.replace("_leaderboard.json", "").replace("_history.json", "")
    for fn in files if fn.endswith("_leaderboard.json")
}))

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

# ---- Load leaderboard and history ----
leaderboard = load_leaderboard_from_git(game_name) or {}
history = load_history_from_git(game_name) or {"matches": []}

# Ensure 'wins' exists for each player
for p in players:
    if p not in leaderboard:
        leaderboard[p] = {"mu": env.mu, "sigma": env.sigma, "wins": 0}
    elif "wins" not in leaderboard[p]:
        leaderboard[p]["wins"] = 0

# ---- Match recording tabs ----
st.header("Team-based Game Recording")

selected_players = st.multiselect("Select players", options=players)
if selected_players:
    manual_team_btn = st.button("Set Manual Teams")
    auto_team_btn = st.button("Auto Balance Teams")

    team_a, team_b = [], []

    if manual_team_btn:
        team_a = st.multiselect("Team A players", options=selected_players)
        team_b = [p for p in selected_players if p not in team_a]
        st.write("Team B:", ", ".join(team_b) if team_b else "(empty)")
    elif auto_team_btn:
        def get_mu(p):
            return leaderboard.get(p, {"mu": env.mu}).get("mu", env.mu)
        sorted_players = sorted(selected_players, key=get_mu, reverse=True)
        team_a = sorted_players[::2]
        team_b = sorted_players[1::2]
        st.write("Auto-balanced Teams:")
        st.write("Team A:", ", ".join(team_a))
        st.write("Team B:", ", ".join(team_b))

    if team_a and team_b:
        winner = st.radio("Winner", options=["Team A", "Team B"])
        if st.button("Record Team Game"):
            try:
                # Prepare ratings
                ratings_a = [env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma})) for p in team_a]
                ratings_b = [env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma})) for p in team_b]

                ranks = [0, 1] if winner == "Team A" else [1, 0]
                new_ratings = env.rate([ratings_a, ratings_b], ranks=ranks)

                # Update leaderboard
                for name, r in zip(team_a, new_ratings[0]):
                    leaderboard[name]["mu"] = r.mu
                    leaderboard[name]["sigma"] = r.sigma
                    if winner == "Team A":
                        leaderboard[name]["wins"] += 1
                for name, r in zip(team_b, new_ratings[1]):
                    leaderboard[name]["mu"] = r.mu
                    leaderboard[name]["sigma"] = r.sigma
                    if winner == "Team B":
                        leaderboard[name]["wins"] += 1

                # Update history
                history["matches"].append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "team",
                    "team_a": team_a,
                    "team_b": team_b,
                    "winner": winner
                })

                # Push updates to GitLab
                save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record team match for {game_name}")
                save_history_to_git(game_name, history, commit_message=f"Add team match to {game_name} history")

                st.success("Team game recorded successfully!")

            except Exception as e:
                st.error(f"Failed to record game: {e}")
