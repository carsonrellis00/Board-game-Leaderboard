import streamlit as st
from GitLab_Persistence import load_players_from_git, save_players_to_git

st.set_page_config(page_title="Manage Players", page_icon="👥")
st.title("👥 Manage Players")

# --- Load existing players ---
try:
    players = load_players_from_git() or []
except Exception as e:
    st.error(f"Failed to load players from GitLab: {e}")
    players = []

# --- Add Player ---
st.header("Add Player")
with st.form("add_player_form", clear_on_submit=True):
    new_player = st.text_input("Player name")
    submitted = st.form_submit_button("Add Player")
    if submitted:
        new_player = new_player.strip()
        if not new_player:
            st.warning("Please enter a name.")
        elif new_player in players:
            st.info(f"{new_player} already exists.")
        else:
            try:
                players.append(new_player)
                save_players_to_git(players)
                st.success(f"{new_player} added.")
            except Exception as e:
                st.error(f"Failed to save new player: {e}")

st.markdown("---")

# --- Remove Player ---
st.header("Remove Player")
if players:
    remove_player = st.selectbox("Select player to remove", [""] + players)
    if st.button("Remove Player") and remove_player:
        try:
            players.remove(remove_player)
            save_players_to_git(players)
            st.success(f"{remove_player} removed.")
        except Exception as e:
            st.error(f"Failed to remove player: {e}")
else:
    st.info("No players found. Add players above.")

# --- Current Players List ---
st.header("Current Players")
if players:
    st.write(", ".join(players))
else:
    st.info("No players yet.")
