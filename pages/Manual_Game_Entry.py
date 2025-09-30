import streamlit as st
import json
import os
import datetime
import trueskill
from gitlab_utils import update_file_in_gitlab

# ---- Constants ----
PLAYERS_FILE = "leaderboards/players.json"

# ---- Helpers ----
def load_json(file_path, default):
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return default

def save_json_to_gitlab(file_path, data, commit_message):
    content = json.dumps(data, indent=2)
    success = update_file_in_gitlab(file_path, content, commit_message)
    if not success:
        st.error(f"❌ Failed to save {file_path} to GitLab")

# ---- Load Players ----
players = load_json(PLAYERS_FILE, [])

# ---- Streamlit UI ----
st.set_page_config(page_title="Manual Game Entry", page_icon="✍️")
st.title("✍️ Manual Game Entry")

if not players:
    st.warning("⚠️ No players found. Please add players first in **Manage Players**.")
    st.stop()

# Select game
game_name = st.text_input("Enter game name")
if not game_name:
    st.info("Enter a game name to continue.")
    st.stop()

# Define leaderboard + history paths for this game
leaderboard_file = f"leaderboards/{game_name.lower().replace(' ', '_')}_leaderboard.json"
history_file = f"leaderboards/{game_name.lower().replace(' ', '_')}_history.json"

# Load data
leaderboard = load_json(leaderboard_file, {})
history = load_json(history_file, [])

# ---- Enter Results ----
st.subheader("Record a Match")

selected_players = st.multiselect("Select players in this match", players)
if len(selected_players) < 2:
    st.info("Select at least 2 players to record a match.")
    st.stop()

st.write("Rank players (1 = winner, higher = worse). Ties get the same rank.")
ranks = {}
for p in selected_players:
    ranks[p] = st.number_input(f"Rank for {p}", min_value=1, max_value=len(selected_players), value=1)

if st.button("Record Match"):
    env = trueskill.TrueSkill(draw_probability=0)  # no draws unless same rank
    rating_group = []
    rank_list = []

    # Ensure ratings exist
    for p in selected_players:
        if p not in leaderboard:
            leaderboard[p] = {"mu": 25.0, "sigma": 8.333}  # default TrueSkill rating

    # Prepare ratings and ranks
    for p in selected_players:
        mu = leaderboard[p]["mu"]
        sigma = leaderboard[p]["sigma"]
        rating_group.append(env.Rating(mu, sigma))
        rank_list.append(ranks[p])

    # Update ratings
    new_ratings = env.rate(rating_group, ranks=rank_list)

    for p, r in zip(selected_players, new_ratings):
        leaderboard[p] = {"mu": r.mu, "sigma": r.sigma}

    # Save match history
    match_record = {
        "game": game_name,
        "players": selected_players,
        "ranks": ranks,
        "timestamp": datetime.datetime.now().isoformat()
    }
    history.append(match_record)

    # Save leaderboard + history to GitLab
    save_json_to_gitlab(leaderboard_file, leaderboard, f"Update {game_name} leaderboard")
    save_json_to_gitlab(history_file, history, f"Update {game_name} match history")

    st.success("✅ Match recorded and saved to GitLab!")
