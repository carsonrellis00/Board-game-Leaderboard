import streamlit as st
import os
import json

# ---- Paths ----
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LEADERBOARDS_DIR = os.path.join(BASE_DIR, "leaderboards")
EVENT_FILE = os.path.join(BASE_DIR, "event.json")
PLAYERS_FILE = os.path.join(LEADERBOARDS_DIR, "players.json")

# ---- Ensure directories exist ----
if not os.path.exists(LEADERBOARDS_DIR):
    os.makedirs(LEADERBOARDS_DIR)

# ---- Ensure JSON files exist ----
if not os.path.exists(EVENT_FILE):
    with open(EVENT_FILE, "w") as f:
        json.dump({"next_event": "Friday 9/26"}, f)

if not os.path.exists(PLAYERS_FILE):
    with open(PLAYERS_FILE, "w") as f:
        json.dump({}, f)  # empty dict for players

# ---- Load Next Event ----
with open(EVENT_FILE, "r") as f:
    event_data = json.load(f)
next_event = event_data.get("next_event", "")

# ---- Streamlit Config ----
st.set_page_config(
    page_title="🎲 Board Game Leaderboard",
    page_icon="🎲",
)

# ---- UI ----
st.title("🎲 Board Game Leaderboard")

# Banner
if next_event:
    st.markdown(f"### 📅 Next Board Game Night: {next_event}")

st.markdown("---")

# Page descriptions
st.header("App Pages & Features")
st.markdown("""
- **Manage Players**: Add or remove players globally. All pages reference this list.
- **Manual Game Entry**: Record individual or team-based games for any selected game.
- **Leaderboard**: View rankings for each game based on TrueSkill ratings.
- **Match History**: See past matches with timestamps and results.
- **Matchmaking**: Generate balanced teams and record team match results easily.
""")

st.markdown("---")
st.info("Use the sidebar to navigate between pages.")
