# pages/Home.py
import streamlit as st
import os, json

st.set_page_config(page_title="Home", page_icon="🎲")
st.title("🎲 Board Game Leaderboard Home")

# ---- Load Next Event ----
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EVENT_FILE = os.path.join(BASE_DIR, "../event.json")  # adjust path if needed

next_event = ""
if os.path.exists(EVENT_FILE):
    with open(EVENT_FILE, "r") as f:
        data = json.load(f)
        next_event = data.get("next_event", "")
else:
    next_event = "Set your next event in event.json"

if next_event:
    st.markdown(f"### 📅 Next Board Game Night: {next_event}")

st.markdown("---")
st.header("App Pages & Features")
st.write("Welcome! Use the sidebar to navigate:")

st.markdown("""
- **👥 Manage Players**: Add or remove players globally. All pages reference this list.
- **✏️ Record Game**: Record individual or team-based games for any selected game (includes balanced team generation).
- **🏆 Leaderboard**: View rankings for each game based on TrueSkill ratings.
- **📜 Match History**: See past matches with timestamps and results.
""")

st.markdown("---")
st.info("Use the sidebar to navigate between pages.")
