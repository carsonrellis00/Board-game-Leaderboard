import streamlit as st
import json
import os

# ---- Paths ----
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EVENT_FILE = os.path.join(BASE_DIR, "event.json")

# ---- Page Config ----
st.set_page_config(
    page_title="🎲 Board Game Leaderboard",
    page_icon="🎲",
)

# ---- Load Next Event ----
next_event = ""
if os.path.exists(EVENT_FILE):
    with open(EVENT_FILE, "r") as f:
        data = json.load(f)
        next_event = data.get("next_event", "")
else:
    next_event = "Set your next event in event.json"

# ---- UI ----
st.title("🎲 Welcome to the Board Game Leaderboard!")

# Banner for next game night
if next_event:
    st.markdown(f"### 📅 Next Board Game Night: {next_event}")

st.markdown("---")

st.header("Quick Guide")
st.markdown("""
- **Manage Players**: Add or remove players globally. All pages reference this list.
- **Manual Game Entry**: Record individual or team-based games for any selected game.
- **Leaderboard**: View rankings for each game based on TrueSkill ratings.
- **Match History**: See past matches with timestamps and results.
- **Matchmaking**: Generate balanced teams and record team match results easily.
""")

st.markdown("---")
st.info("Use the sidebar to navigate between pages.")
