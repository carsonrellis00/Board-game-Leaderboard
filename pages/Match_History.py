import streamlit as st
import json
import os

# ---- Paths ----
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEADERBOARD_DIR = os.path.join(BASE_DIR, "leaderboards")

# ---- Helper Functions ----
def get_games():
    files = os.listdir(LEADERBOARD_DIR)
    games = sorted(set(f.replace("_history.json","") for f in files if f.endswith("_history.json")))
    return games

def load_history(game):
    path = os.path.join(LEADERBOARD_DIR, f"{game}_history.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return []

# ---- Streamlit UI ----
st.title("📜 Match History")

games = get_games()
if not games:
    st.info("No games found yet.")
else:
    game = st.selectbox("Select game", options=games)
    history = load_history(game)

    if history:
        st.write(f"### {game} Match History")
        for match in reversed(history):  # newest first
            if match.get("type") == "Individual":
                st.write(f"{match['timestamp']}: {', '.join(match['players'])}")
            elif match.get("type") == "Team-based":
                st.write(f"{match['timestamp']}: Team A ({', '.join(match['team_a'])}) vs Team B ({', '.join(match['team_b'])}) | Winner: {match['winner']}")
    else:
        st.info(f"No matches recorded yet for {game}.")
