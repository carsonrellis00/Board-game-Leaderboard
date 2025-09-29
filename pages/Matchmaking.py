import itertools
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

def make_teams(players, leaderboard):
    # Conservative rating: mu - 3*sigma
    ratings = {p: leaderboard[p].mu - 3*leaderboard[p].sigma for p in players}
    best_split = None
    best_diff = float("inf")

    for team_a in itertools.combinations(players, len(players)//2):
        team_b = [p for p in players if p not in team_a]
        score_a = sum(ratings[p] for p in team_a)
        score_b = sum(ratings[p] for p in team_b)
        diff = abs(score_a - score_b)
        if diff < best_diff:
            best_diff = diff
            best_split = (list(team_a), list(team_b), score_a, score_b)
    return best_split

# ---- Streamlit UI ----
st.title("⚔️ Matchmaking")

# Reload leaderboard each time
leaderboard = load_leaderboard()

if not leaderboard:
    st.warning("Leaderboard is empty! Add players first.")
else:
    # Auto-sort players by conservative rating (highest first)
    sorted_players = sorted(
        leaderboard.keys(),
        key=lambda p: leaderboard[p].mu - 3*leaderboard[p].sigma,
        reverse=True
    )

    players = st.multiselect(
        "Select players for this match",
        options=sorted_players
    )

    if len(players) % 2 == 0 and len(players) > 1:
        if st.button("Generate Balanced Teams"):
            team_a, team_b, score_a, score_b = make_teams(players, leaderboard)
            st.subheader("Suggested Teams")
            st.write(f"**Team A** ({score_a:.2f}): {', '.join(team_a)}")
            st.write(f"**Team B** ({score_b:.2f}): {', '.join(team_b)}")
            st.session_state["match_teams"] = (team_a, team_b)

    # Record match result
    if "match_teams" in st.session_state:
        team_a, team_b = st.session_state["match_teams"]
        st.subheader("Record Match Result")
        winner = st.radio("Which team won?", ["Team A", "Team B"])
        if st.button("Record Result"):
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
            del st.session_state["match_teams"]

    else:
        st.info("Select players and generate teams to begin.")
