import streamlit as st
import json
import os

# ---- Paths ----
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEADERBOARD_DIR = os.path.join(BASE_DIR, "leaderboards")
os.makedirs(LEADERBOARD_DIR, exist_ok=True)
PLAYERS_FILE = os.path.join(LEADERBOARD_DIR, "players.json")

# ---- Helper Functions ----
def load_players():
    if os.path.exists(PLAYERS_FILE):
        with open(PLAYERS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_players(players):
    with open(PLAYERS_FILE, "w") as f:
        json.dump(players, f, indent=4)

# ---- Streamlit UI ----
st.title("👥 Manage Players")

players_dict = load_players()
player_list = list(players_dict.keys())

# Display current players
if player_list:
    st.subheader("Current Players")
    for name in player_list:
        st.write(f"- {name}")
else:
    st.info("No players yet.")

# Add new player
st.subheader("Add New Player")
new_player = st.text_input("Player Name")
if st.button("Add Player"):
    if not new_player:
        st.error("Enter a valid player name.")
    elif new_player in player_list:
        st.warning(f"{new_player} already exists.")
    else:
        player_list.append(new_player)
        players_dict[new_player] = {}
        save_players(players_dict)
        st.success(f"{new_player} added.")

# Remove player
st.subheader("Remove Player")
remove_player = st.selectbox("Select a player to remove", [""] + player_list)
if st.button("Remove Player"):
    if remove_player and remove_player in player_list:
        player_list.remove(remove_player)
        del players_dict[remove_player]
        save_players(players_dict)
        st.success(f"{remove_player} removed.")
