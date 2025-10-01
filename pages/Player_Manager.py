# pages/Player_Manager.py
import streamlit as st
from GitLab_Persistence import load_players_from_git, save_players_to_git

st.set_page_config(page_title="👥 Manage Players", page_icon="👥")
st.title("👥 Manage Players")

# --- Load players from GitLab ---
player_list = load_players_from_git()  # now a list of player names

# --- Display current players ---
if player_list:
    st.subheader("Current Players")
    for name in player_list:
        st.write(f"- {name}")
else:
    st.info("No players yet.")

# --- Add new player ---
st.subheader("Add New Player")
new_player = st.text_input("Player Name")
if st.button("Add Player"):
    if not new_player.strip():
        st.error("Enter a valid player name.")
    elif new_player.strip() in player_list:
        st.warning(f"{new_player.strip()} already exists.")
    else:
        player_list.append(new_player.strip())
        save_players_to_git(player_list)
        st.success(f"{new_player.strip()} added.")

# --- Remove player ---
st.subheader("Remove Player")
remove_player = st.selectbox("Select a player to remove", [""] + player_list)
if st.button("Remove Player"):
    if remove_player and remove_player in player_list:
        player_list.remove(remove_player)
        save_players_to_git(player_list)
        st.success(f"{remove_player} removed.")
