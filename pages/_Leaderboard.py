import streamlit as st
from GitLab_Persistence import (
    gitlab_list_leaderboards_dir,
    load_leaderboard_from_git
)

st.set_page_config(page_title="Leaderboard", page_icon="🏆")
st.title("🏆 Game Leaderboards")

# --- Select Game ---
files = gitlab_list_leaderboards_dir()
game_names = sorted(list({fn.replace("_leaderboard.json","").replace("_history.json","") for fn in files if fn.endswith(".json")}))
game_name = st.selectbox("Select game", options=game_names)

if not game_name:
    st.info("No games found.")
    st.stop()

leaderboard = load_leaderboard_from_git(game_name)

if not leaderboard:
    st.info(f"No leaderboard data for {game_name}.")
    st.stop()

# --- Display leaderboard ---
st.subheader(f"Leaderboard for {game_name}")

# Compute conservative rating
for player, data in leaderboard.items():
    data["rating"] = data["mu"] - 3*data["sigma"]

sorted_players = sorted(leaderboard.items(), key=lambda x: x[1]["rating"], reverse=True)

st.table([
    {"Rank": i+1, "Player": name, "μ": f"{data['mu']:.2f}", "σ": f"{data['sigma']:.2f}", "Rating": f"{data['rating']:.2f}"}
    for i, (name, data) in enumerate(sorted_players)
])
