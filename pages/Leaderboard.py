import streamlit as st
import json
import os
import trueskill

# ---- Paths ----
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEADERBOARD_DIR = os.path.join(BASE_DIR, "leaderboards")

env = trueskill.TrueSkill(draw_probability=0)

# ---- Helper Functions ----
def get_games():
    files = os.listdir(LEADERBOARD_DIR)
    games = sorted(set(f.replace("_leaderboard.json","") for f in files if f.endswith("_leaderboard.json")))
    return games

def load_leaderboard(game):
    path = os.path.join(LEADERBOARD_DIR, f"{game}_leaderboard.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            data = json.load(f)
        return {name: env.Rating(mu, sigma) for name, (mu, sigma) in data.items()}
    return {}

# ---- Streamlit UI ----
st.title("🏆 Leaderboard")

# Select game
games = get_games()
if not games:
    st.info("No games found. Add a game in Manual Game Entry first.")
else:
    game = st.selectbox("Select game", options=games)
    leaderboard = load_leaderboard(game)

    if leaderboard:
        # Sort by conservative rating
        sorted_players = sorted(
            leaderboard.items(),
            key=lambda item: item[1].mu - 3*item[1].sigma,
            reverse=True
        )

        st.write(f"### {game} Leaderboard")
        for i, (name, rating) in enumerate(sorted_players, start=1):
            conservative = rating.mu - 3*rating.sigma
            st.write(f"{i}. {name:10} | μ={rating.mu:.2f}, σ={rating.sigma:.2f}, rating={conservative:.2f}")
    else:
        st.info(f"No players yet for {game}.")
