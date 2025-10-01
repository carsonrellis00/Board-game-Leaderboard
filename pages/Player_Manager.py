import streamlit as st
from GitLab_Persistence import load_players_from_git, save_players_to_git
import os

st.title("👥 Manage Players")

# --- Load players ---
players_dict = load_players_from_git()
player_list = players_dict.get("players", [])

# --- Display current players ---
if player_list:
    st.subheader("Current Players")
    for p in player_list:
        st.write(f"- {p}")
else:
    st.info("No players yet.")

# --- Add new player ---
st.subheader("Add New Player")
new_player = st.text_input("Player Name")
if st.button("Add Player"):
    if not new_player.strip():
        st.error("Enter a valid player name.")
    elif new_player.strip() in player_list:
        st.warning(f"{new_player} already exists.")
    else:
        player_list.append(new_player.strip())
        players_dict["players"] = player_list
        save_players_to_git(players_dict)
        st.success(f"{new_player.strip()} added.")

# --- Remove player ---
st.subheader("Remove Player")
remove_player = st.selectbox("Select a player to remove", [""] + player_list)
if st.button("Remove Player"):
    if remove_player in player_list:
        player_list.remove(remove_player)
        players_dict["players"] = player_list
        save_players_to_git(players_dict)
        st.success(f"{remove_player} removed.")
