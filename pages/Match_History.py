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
    ts = datetime.fromisoformat(match["timestamp"]).strftime("%Y-%m-%d %H:%M UTC")
    if match["type"] == "individual":
        st.markdown(f"**{i}. {ts}** — Individual: {', '.join(match['results'])}")
    elif match["type"] == "team":
        st.markdown(
            f"**{i}. {ts}** — Team Match:\n"
            f"- Team A: {', '.join(match['team_a'])}\n"
            f"- Team B: {', '.join(match['team_b'])}\n"
            f"- Winner: {match['winner']}"
        )
    st.markdown("---")
