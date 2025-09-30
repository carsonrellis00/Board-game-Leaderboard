# leaderboard_web_app.py
import streamlit as st
import os, json

# --- Page config ---
st.set_page_config(
    page_title="Home",
    page_icon="🎲",
    layout="wide"
)

# --- Sidebar Hub ---
st.sidebar.title("Home")  # This makes a "Home" label in the sidebar
st.sidebar.markdown("Welcome! Use the sidebar to navigate to other pages:")

st.sidebar.markdown("""
- 👥 Manage Players
- ✏️ Record Game / Matchmaking
- 🏆 Leaderboard
- 📜 Match History
""")

# --- Main page title ---
st.title("🎲 Board Game Leaderboard Home")

# --- Load Next Event ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EVENT_FILE = os.path.join(BASE_DIR, "event.json")

next_event = "Set your next event in event.json"
if os.path.exists(EVENT_FILE):
    try:
        with open(EVENT_FILE, "r") as f:
            data = json.load(f)
            next_event = data.get("next_event", next_event)
    except Exception:
        pass

if next_event:
    st.markdown(f"### 📅 Next Board Game Night: {next_event}")

st.markdown("---")
st.header("Welcome to the Board Game Leaderboard Hub!")
st.write("Use the sidebar to navigate between the pages, or read below for details about each page.")

st.markdown("""
### 📌 App Pages & Features

- **👥 Manage Players**: Add or remove players globally. All pages reference this list.
- **✏️ Record Game / Matchmaking**: Record individual or team-based games for any selected game, including balanced team generation.
- **🏆 Leaderboard**: View rankings for each game based on TrueSkill ratings.
- **📜 Match History**: Review past matches with timestamps and results.
""")

st.markdown("---")
st.info("Use the sidebar to navigate between pages.")
