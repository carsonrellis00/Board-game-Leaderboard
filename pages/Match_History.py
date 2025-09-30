import streamlit as st
from GitLab_Persistence import load_history_from_git
from datetime import datetime

st.set_page_config(page_title="Match History", page_icon="📜")
st.title("📜 Match History")

# --- Select Game ---
files = [fn.replace("_leaderboard.json", "").replace("_history.json", "") 
         for fn in st.session_state.get("leaderboard_files", [])] \
         if "leaderboard_files" in st.session_state else []
game_names = sorted(list({fn for fn in files}))
if not game_names:
    st.info("No games found. Record a game first.")
    st.stop()

game_option = st.selectbox("Select a game", options=game_names)
history = load_history_from_git(game_option)

if not history.get("matches"):
    st.info("No matches recorded yet.")
    st.stop()

# --- Display matches ---
st.subheader(f"{game_option} Match History")
for match in reversed(history["matches"]):
    timestamp = match.get("timestamp", "")
    dt = datetime.fromisoformat(timestamp) if timestamp else ""
    if match["type"] == "individual":
        players = ", ".join(match["results"])
        st.write(f"{dt} - Individual match: {players}")
    else:
        team_a = ", ".join(match["team_a"])
        team_b = ", ".join(match["team_b"])
        winner = match["winner"]
        st.write(f"{dt} - Team match | Team A: {team_a} vs Team B: {team_b} | Winner: {winner}")
