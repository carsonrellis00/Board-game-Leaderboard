import streamlit as st
import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY_FILE = os.path.join(BASE_DIR, "history.json")

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return []

history = load_history()

st.title("📜 Match History")

if not history:
    st.info("No matches recorded yet.")
else:
    for i, match in enumerate(history, start=1):
        st.write(f"**Game {i}** — {match}")
