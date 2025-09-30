import streamlit as st
import json
from gitlab_utils import get_file_from_gitlab

st.set_page_config(page_title="📜 Match History", page_icon="📜")
st.title("📜 Match History")

# ---- Select game ----
game_name = st.text_input("Enter game name")
if not game_name:
    st.info("Enter a game name to view its history.")
    st.stop()

history_file = f"leaderboards/{game_name.lower().replace(' ', '_')}_history.json"

# ---- Load history from GitLab ----
history_data = get_file_from_gitlab(history_file)

if not history_data:
    st.warning(f"No history found for **{game_name}**.")
    st.stop()

try:
    history = json.loads(history_data)
except json.JSONDecodeError:
    st.error("❌ Failed to parse match history.")
    st.stop()

# ---- Display ----
for match in history:
    st.markdown(f"**{match['timestamp']}** — {', '.join(match['players'])}")
    st.write(f"Ranks: {match['ranks']}")
    st.markdown("---")
