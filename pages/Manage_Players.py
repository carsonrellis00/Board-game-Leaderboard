import streamlit as st
import json
import os
from gitlab_utils import update_file_in_gitlab

# ---- Constants ----
PLAYERS_FILE = "leaderboards/players.json"

# ---- Load Players ----
def load_players():
    try:
        with open(PLAYERS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

# ---- Save Players to GitLab ----
def save_players(players):
    content = json.dumps(players, indent=2)
    success = update_file_in_gitlab(
        file_path=PLAYERS_FILE,
        content=content,
        commit_message="Update players list"
    )
    if success:
        st.success("✅ Players saved to GitLab")
    else:
        st.error("❌ Failed to save players to GitLab")

# ---- Streamlit UI ----
st.set_page_config(page_title="Manage Players", page_icon="👥")

st.title("👥 Manage Players")

# Load players
players = load_players()

# Show existing players
st.subheader("Current Players")
if players:
    st.write(", ".join(players))
else:
    st.info("No players yet. Add one below!")

# Add player
with st.form("add_player_form"):
    new_player = st.text_input("Enter new player name")
    submitted = st.form_submit_button("Add Player")
    if submitted and new_player:
        if new_player not in players:
            players.append(new_player)
            save_players(players)
        else:
            st.warning(f"⚠️ Player '{new_player}' already exists.")

# Remove player
with st.form("remove_player_form"):
    remove_player = st.selectbox("Select player to remove", [""] + players)
    submitted_remove = st.form_submit_button("Remove Player")
    if submitted_remove and remove_player:
        players = [p for p in players if p != remove_player]
        save_players(players)
