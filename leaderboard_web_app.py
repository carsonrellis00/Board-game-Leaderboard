import streamlit as st

st.set_page_config(page_title="Home", page_icon="🎲", layout="wide")

# ---- Sidebar ----
st.sidebar.title("🎲 Board Game Leaderboard")
st.sidebar.markdown("Navigate to different pages:")

# Custom buttons to jump to pages
if st.sidebar.button("👥 Manage Players"):
    st.experimental_set_query_params(page="Player_Manager")
if st.sidebar.button("✏️ Record Game / Matchmaking"):
    st.experimental_set_query_params(page="Record_Game")
if st.sidebar.button("🏆 Leaderboard"):
    st.experimental_set_query_params(page="Leaderboard")
if st.sidebar.button("📜 Match History"):
    st.experimental_set_query_params(page="Match_History")

# ---- Main Page ----
st.title("🎲 Board Game Leaderboard Hub")
st.write("Welcome! Use the sidebar to navigate:")
st.markdown("""
- 👥 Manage Players
- ✏️ Record Game / Matchmaking
- 🏆 Leaderboard
- 📜 Match History
""")

# Optional: show next event if available
import os, json
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EVENT_FILE = os.path.join(BASE_DIR, "event.json")
if os.path.exists(EVENT_FILE):
    with open(EVENT_FILE, "r") as f:
        data = json.load(f)
        next_event = data.get("next_event", "")
else:
    next_event = "Set your next event in event.json"

if next_event:
    st.markdown(f"### 📅 Next Board Game Night: {next_event}")
