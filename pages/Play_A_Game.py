import streamlit as st
from GitLab_Persistence import (
    load_players_from_git, save_players_to_git,
    load_leaderboard_from_git, save_leaderboard_to_git,
    load_history_from_git, save_history_to_git,
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

# --- Load or create games ---
files = gitlab_list_leaderboards_dir()
game_names = sorted(list({fn.replace("_leaderboard.json", "") for fn in files if fn.endswith("_leaderboard.json")}))

game_option = st.selectbox("Select game (or type new)", ["<New Game>"] + game_names)
if game_option == "<New Game>":
    game_name_input = st.text_input("New game name")
    game_name = game_name_input.strip() if game_name_input else None
else:
    game_name = game_option

if not game_name:
    st.info("Pick or type a game name to record matches for.")
    st.stop()

st.subheader(f"Recording for game: {game_name}")

# --- Load leaderboard & history ---
leaderboard = load_leaderboard_from_git(game_name)
history = load_history_from_git(game_name)

# --- Team-based game recording ---
selected_players = st.multiselect("Select players", options=players)
team_a, team_b = [], []

if selected_players:
    if st.button("Auto Balance Teams"):
        sorted_players = sorted(selected_players,
                                key=lambda p: leaderboard.get(p, {}).get("mu", env.mu),
                                reverse=True)
        team_a = sorted_players[::2]
        team_b = sorted_players[1::2]
        st.write("Team A:", ", ".join(team_a))
        st.write("Team B:", ", ".join(team_b))

    winner = st.radio("Winner", options=["Team A", "Team B"])
    if st.button("Record Team Game"):
        try:
            ratings_a = [env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma, "wins":0})) for p in team_a]
            ratings_b = [env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma, "wins":0})) for p in team_b]

            ranks = [0, 1] if winner == "Team A" else [1, 0]
            new_ratings = env.rate([ratings_a, ratings_b], ranks=ranks)

            for name, r in zip(team_a, new_ratings[0]):
                stats = leaderboard.get(name, {})
                stats.update({"mu": r.mu, "sigma": r.sigma, "wins": stats.get("wins", 0) + (1 if winner=="Team A" else 0)})
                leaderboard[name] = stats
            for name, r in zip(team_b, new_ratings[1]):
                stats = leaderboard.get(name, {})
                stats.update({"mu": r.mu, "sigma": r.sigma, "wins": stats.get("wins", 0) + (1 if winner=="Team B" else 0)})
                leaderboard[name] = stats

            history.setdefault("matches", []).append({
                "timestamp": datetime.utcnow().isoformat(),
                "type": "team",
                "team_a": team_a,
                "team_b": team_b,
                "winner": winner
            })

            save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record team match for {game_name}")
            save_history_to_git(game_name, history, commit_message=f"Add team match to {game_name} history")

            st.success("Team game recorded successfully!")

        except Exception as e:
            st.error(f"Failed to record game: {e}")
