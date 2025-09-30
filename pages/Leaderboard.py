import streamlit as st
import json
from gitlab_utils import get_file_from_gitlab

st.set_page_config(page_title="🏆 Leaderboard", page_icon="🏆")
st.title("🏆 Leaderboard")

# ---- Select game ----
game_name = st.text_input("Enter game name")
if not game_name:
    st.info("Enter a game name to view its leaderboard.")
    st.stop()

leaderboard_file = f"leaderboards/{game_name.lower().replace(' ', '_')}_leaderboard.json"

# ---- Load leaderboard from GitLab ----
leaderboard_data = get_file_from_gitlab(leaderboard_file)

if not leaderboard_data:
    st.warning(f"No leaderboard found for **{game_name}**.")
    st.stop()

try:
    leaderboard = json.loads(leaderboard_data)
except json.JSONDecodeError:
    st.error("❌ Failed to parse leaderboard.")
    st.stop()

# ---- Display ----
sorted_players = sorted(
    leaderboard.items(),
    key=lambda item: item[1]["mu"] - 3 * item[1]["sigma"],
    reverse=True
)

st.subheader(f"Leaderboard for {game_name}")
for i, (player, rating) in enumerate(sorted_players, start=1):
    conservative = rating["mu"] - 3 * rating["sigma"]
    st.write(f"{i}. {player} — μ={rating['mu']:.2f}, σ={rating['sigma']:.2f}, rating={conservative:.2f}")
