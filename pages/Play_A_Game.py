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

env = trueskill.TrueSkill(draw_probability=0)

# --- Load players ---
players_dict = load_players_from_git()
players = players_dict.get("players", [])

if not players:
    st.warning("No players found. Add players first in Player Manager.")
    st.stop()

# --- Load games ---
files = gitlab_list_leaderboards_dir()
game_names = sorted({fn.replace("_leaderboard.json","") for fn in files if fn.endswith("_leaderboard.json")})

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

# --- Load leaderboard and history ---
leaderboard = load_leaderboard_from_git(game_name)
history = load_history_from_git(game_name)

# Ensure leaderboard entries are normalized
for p in players:
    if p not in leaderboard:
        leaderboard[p] = {"mu": env.mu, "sigma": env.sigma, "wins": 0}

# --- Game type selection ---
game_type = st.radio("Select game type", ["1v1", "Team", "Free-for-All"])

if game_type == "1v1":
    p1 = st.selectbox("Player 1", players)
    p2 = st.selectbox("Player 2", [p for p in players if p != p1])
    winner = st.radio("Winner", [p1, p2])
    if st.button("Record 1v1 Game"):
        try:
            r1 = env.Rating(**leaderboard[p1])
            r2 = env.Rating(**leaderboard[p2])
            ranks = [0,1] if winner == p1 else [1,0]
            new_ratings = env.rate([[r1],[r2]], ranks=ranks)
            leaderboard[p1].update(mu=new_ratings[0][0].mu, sigma=new_ratings[0][0].sigma)
            leaderboard[p2].update(mu=new_ratings[1][0].mu, sigma=new_ratings[1][0].sigma)
            leaderboard[winner]["wins"] += 1

            # Update history
            history.setdefault("matches", []).append({
                "timestamp": datetime.utcnow().isoformat(),
                "type": "1v1",
                "players": [p1, p2],
                "winner": winner
            })

            save_leaderboard_to_git(game_name, leaderboard)
            save_history_to_git(game_name, history)
            st.success("1v1 game recorded!")

        except Exception as e:
            st.error(f"Failed to record 1v1 game: {e}")

elif game_type == "Team":
    selected_players = st.multiselect("Select players", players)
    if selected_players:
        team_a = st.multiselect("Team A players", selected_players)
        team_b = [p for p in selected_players if p not in team_a]
        winner = st.radio("Winner", ["Team A", "Team B"])
        if st.button("Record Team Game") and team_a and team_b:
            try:
                ratings_a = [env.Rating(**leaderboard[p]) for p in team_a]
                ratings_b = [env.Rating(**leaderboard[p]) for p in team_b]
                ranks = [0,1] if winner=="Team A" else [1,0]
                new_ratings = env.rate([ratings_a, ratings_b], ranks=ranks)

                for p,r in zip(team_a, new_ratings[0]):
                    leaderboard[p].update(mu=r.mu, sigma=r.sigma)
                    if winner=="Team A":
                        leaderboard[p]["wins"] += 1
                for p,r in zip(team_b, new_ratings[1]):
                    leaderboard[p].update(mu=r.mu, sigma=r.sigma)
                    if winner=="Team B":
                        leaderboard[p]["wins"] += 1

                # History
                history.setdefault("matches", []).append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "team",
                    "team_a": team_a,
                    "team_b": team_b,
                    "winner": winner
                })

                save_leaderboard_to_git(game_name, leaderboard)
                save_history_to_git(game_name, history)
                st.success("Team game recorded
