import streamlit as st
from GitLab_Persistence import (
    gitlab_list_leaderboards_dir,
    load_history_from_git
)
from datetime import datetime

st.set_page_config(page_title="Match History", page_icon="📜")
st.title("📜 Match History")

# --- Select Game ---
files = gitlab_list_leaderboards_dir()
game_names = sorted(list({fn.replace("_leaderboard.json","").replace("_history.json","") for fn in files if fn.endswith(".json")}))
game_name = st.selectbox("Select game", options=game_names)

if not game_name:
    st.info("No games found.")
    st.stop()

history = load_history_from_git(game_name)
matches = history.get("matches", [])

if not matches:
    st.info(f"No match history for {game_name}.")
    st.stop()

st.subheader(f"Match History for {game_name}")

# Display matches
for i, match in enumerate(matches[::-1], start=1):
    # Safely get timestamp
    ts = match.get("timestamp")
    if ts:
        try:
            ts = datetime.fromisoformat(ts).strftime("%Y-%m-%d %H:%M UTC")
        except Exception:
            ts = "Invalid timestamp"
    else:
        ts = "Unknown time"

    match_type = match.get("type", "unknown")

    if match_type == "1v1" or match_type == "individual":
        results = match.get("players") or match.get("results") or []
        winner = match.get("winner", "Unknown")
        st.markdown(f"**{i}. {ts}** — 1v1: {', '.join(results)} (Winner: {winner})")

    elif match_type == "team":
        team1 = match.get("team1") or match.get("team_a") or []
        team2 = match.get("team2") or match.get("team_b") or []
        winner = match.get("winner", "Unknown")
        st.markdown(
            f"**{i}. {ts}** — Team Match:\n"
            f"- Team 1: {', '.join(team1)}\n"
            f"- Team 2: {', '.join(team2)}\n"
            f"- Winner: {winner}"
        )

    elif match_type == "ffa":
        players = match.get("players", [])
        winner = match.get("winner", "Unknown")
        st.markdown(
            f"**{i}. {ts}** — Free-for-All:\n"
            f"- Players: {', '.join(players)}\n"
            f"- Winner: {winner}"
        )

    else:
        st.markdown(f"**{i}. {ts}** — Unknown match type")

    st.markdown("---")
