import streamlit as st
import json
import os
import trueskill

# ---- Paths ----
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAVE_FILE = os.path.join(BASE_DIR, "leaderboard.json")

env = trueskill.TrueSkill(draw_probability=0)
DEFAULT_SIGMA = env.sigma

# ---- Helper Functions ----
def load_leaderboard():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r") as f:
            data = json.load(f)
        return {name: env.Rating(mu, sigma) for name, (mu, sigma) in data.items()}
    return {}

def save_leaderboard(leaderboard):
    data = {name: (r.mu, r.sigma) for name, r in leaderboard.items()}
    with open(SAVE_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ---- Streamlit UI ----
st.title("👥 Manage Players")

leaderboard = load_leaderboard()

# Display current players
if leaderboard:
    st.subheader("Current Players")
    for name, rating in leaderboard.items():
        conservative = rating.mu - 3 * rating.sigma
        st.write(f"{name}: μ={rating.mu:.2f}, σ={rating.sigma:.2f}, rating={conservative:.2f}")
else:
    st.info("No players yet.")

# Add new player
st.subheader("Add New Player")
new_player = st.text_input("Player Name")
if st.button("Add Player"):
    if not new_player:
        st.error("Enter a valid player name.")
    elif new_player in leaderboard:
        st.warning(f"{new_player} already exists.")
    else:
        # Default rating = 1/2 average μ, σ = default sigma
        if leaderboard:
            avg_mu = sum(r.mu for r in leaderboard.values()) / len(leaderboard)
            default_mu = avg_mu / 2
        else:
            default_mu = env.mu  # TrueSkill default if first player
        leaderboard[new_player] = env.Rating(mu=default_mu, sigma=DEFAULT_SIGMA)
        save_leaderboard(leaderboard)
        st.success(f"{new_player} added with μ={default_mu:.2f} and σ={DEFAULT_SIGMA:.2f}.")

# Remove player
st.subheader("Remove Player")
remove_player = st.selectbox("Select a player to remove", [""] + list(leaderboard.keys()))
if st.button("Remove Player"):
    if remove_player and remove_player in leaderboard:
        del leaderboard[remove_player]
        save_leaderboard(leaderboard)
        st.success(f"{remove_player} removed.")
