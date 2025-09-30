# pages/Leaderboard.py
import streamlit as st
from GitLab_Persistence import (
    load_leaderboard_from_git,
    save_leaderboard_to_git,
    load_history_from_git,
    save_history_to_git,
    gitlab_list_leaderboards_dir
)

st.set_page_config(page_title="Leaderboard", page_icon="🏆")
st.title("🏆 Game Leaderboards")

# --- Load games ---
files = gitlab_list_leaderboards_dir()
game_names = sorted(list({fn.replace("_leaderboard.json","").replace("_history.json","") for fn in files if fn.endswith(".json")}))

if not game_names:
    st.info("No games found yet.")
    st.stop()

selected_game = st.selectbox("Select a game to view leaderboard", options=game_names)

# --- Load leaderboard ---
leaderboard = load_leaderboard_from_git(selected_game)

if leaderboard:
    # Sort by mu descending
    sorted_leaderboard = sorted(leaderboard.items(), key=lambda x: x[1]["mu"], reverse=True)
    st.subheader(f"Leaderboard for {selected_game}")
    st.table({name: f'{info["mu"]:.2f} ± {info["sigma"]:.2f}' for name, info in sorted_leaderboard}.items())
else:
    st.info("No leaderboard data for this game yet.")

# --- Admin-only leaderboard wipe ---
st.markdown("---")
st.header("⚠️ Admin: Wipe Game Leaderboard & History")

admin_pass = st.text_input("Enter admin name to unlock wipe", type="password")

if admin_pass == "Carson":  # replace with your name or check via secret
    wipe_game = st.selectbox("Select game to wipe", options=game_names)
    if st.button("Wipe Leaderboard & History"):
        try:
            # Reset leaderboard
            save_leaderboard_to_git(wipe_game, {}, commit_message=f"Admin wipe: {wipe_game} leaderboard")
            # Reset history
            save_history_to_git(wipe_game, {"matches":[]}, commit_message=f"Admin wipe: {wipe_game} history")
            st.success(f"Leaderboard and history for '{wipe_game}' wiped successfully.")
        except Exception as e:
            st.error(f"Failed to wipe: {e}")
else:
    st.info("Enter admin name to access leaderboard wipe functionality.")

