import streamlit as st
from GitLab_Persistence import (
    load_players_from_git,
    save_players_to_git,
    load_leaderboard_from_git,
    save_leaderboard_to_git,
    load_history_from_git,
    save_history_to_git,
    gitlab_list_leaderboards_dir
)
import trueskill
from datetime import datetime

st.set_page_config(page_title="Player Manager", page_icon="🎲")
st.title("👥 Manage Players")

# --- TrueSkill environment ---
env = trueskill.TrueSkill(draw_probability=0)

# ---------------- Manage Players Tab ----------------
with tab_players:
    st.header("Add / Remove Players (persistent in GitLab)")

    # Load players
    try:
        players = load_players_from_git() or []
    except Exception as e:
        st.error(f"Failed to load players: {e}")
        players = []

    # Add Player
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

    # Remove Player
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

    st.markdown("---")

    # Current players
    st.header("Current Players")
    if players:
        st.write(", ".join(players))
    else:
        st.info("No players yet.")


st.markdown("---")
st.info("This page writes directly to your GitLab repository. Make sure your GITLAB_TOKEN and PROJECT_ID are set in Streamlit secrets or environment variables.")


