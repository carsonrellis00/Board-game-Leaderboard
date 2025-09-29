import streamlit as st
import json
import os
import trueskill

# ---- Paths ----
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAVE_FILE = os.path.join(BASE_DIR, "leaderboard.json")

env = trueskill.TrueSkill(draw_probability=0)

def load_leaderboard():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r") as f:
            data = json.load(f)
        return {name: env.Rating(mu, sigma) for name, (mu, sigma) in data.items()}
    return {}

leaderboard = load_leaderboard()

# ---- UI ----
st.title("🏆 Leaderboard")

if not leaderboard:
    st.warning("No players yet. Add matches in Matchmaking to populate the leaderboard.")
else:
    sorted_players = sorted(
        leaderboard.items(),
        key=lambda item: item[1].mu - 3 * item[1].sigma,
        reverse=True,
    )

    for i, (name, rating) in enumerate(sorted_players, start=1):
        conservative = rating.mu - 3 * rating.sigma
        st.write(f"{i}. **{name}** — μ={rating.mu:.2f}, σ={rating.sigma:.2f}, rating={conservative:.2f}")
