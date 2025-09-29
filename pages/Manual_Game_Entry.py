import streamlit as st
import json
import os
import trueskill
from datetime import datetime

# ---- Paths ----
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAVE_FILE = os.path.join(BASE_DIR, "leaderboard.json")
HISTORY_FILE = os.path.join(BASE_DIR, "history.json")

env = trueskill.TrueSkill(draw_probability=0)

# ---- Helper Functions ----
def load_leaderboard():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r") as f:
            data = json.load(f)
        return {name: env.Rating(mu, sigma) for name, (mu, sigma) in data.items()}
    return {}

def save_leaderboard(leaderboard):
    data = {name: (r.mu, r.sigma) for name, r in leaderboard.items()}
    with open(SAVE_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return []

def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=4)

# ---- Streamlit UI ----
st.title("✏️ Manual Game Entry")

leaderboard = load_leaderboard()

if not leaderboard:
    st.warning("Leaderboard is empty! Add some players first.")
else:
    game_type = st.radio("Select game type", ["Individual", "Team-based"])

    if game_type == "Individual":
        players = st.multiselect("Select players in finishing order", list(leaderboard.keys()))
        if players and st.button("Record Individual Game"):
            ratings = [leaderboard[p] for p in players]
            ranks = list(range(len(players)))  # 0 = winner
            new_ratings = env.rate(ratings, ranks=ranks)
            for p, r in zip(players, new_ratings):
                leaderboard[p] = r
            save_leaderboard(leaderboard)

            # Save history
            history = load_history()
            history.append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "type": "Individual",
                "players": players
            })
            save_history(history)
            st.success("Individual game recorded successfully!")

    else:  # Team-based
        all_players = st.multiselect("Select all players", list(leaderboard.keys()))
        if len(all_players) >= 2 and len(all_players) % 2 == 0:
            team_a = st.multiselect("Team A", all_players)
            team_b = [p for p in all_players if p not in team_a]

            st.write(f"**Team B automatically includes:** {', '.join(team_b)}")

            winner = st.radio("Which team won?", ["Team A", "Team B"])

            if st.button("Record Team Game"):
                ratings_a = [leaderboard[p] for p in team_a]
                ratings_b = [leaderboard[p] for p in team_b]

                if winner == "Team A":
                    new_ratings = env.rate([ratings_a, ratings_b], ranks=[0, 1])
                else:
                    new_ratings = env.rate([ratings_a, ratings_b], ranks=[1, 0])

                for p, r in zip(team_a, new_ratings[0]):
                    leaderboard[p] = r
                for p, r in zip(team_b, new_ratings[1]):
                    leaderboard[p] = r

                save_leaderboard(leaderboard)

                history = load_history()
                history.append({
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "type": "Team-based",
                    "team_a": team_a,
                    "team_b": team_b,
                    "winner": winner
                })
                save_history(history)
                st.success(f"Team game recorded! {winner} wins.")
