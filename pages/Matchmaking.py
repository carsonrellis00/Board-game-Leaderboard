import itertools
import streamlit as st
import json
import os
import trueskill
from datetime import datetime

# ---- Paths ----
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEADERBOARD_DIR = os.path.join(BASE_DIR, "leaderboards")
PLAYERS_FILE = os.path.join(LEADERBOARD_DIR, "players.json")
os.makedirs(LEADERBOARD_DIR, exist_ok=True)

env = trueskill.TrueSkill(draw_probability=0)

# ---- Helper Functions ----
def load_players():
    if os.path.exists(PLAYERS_FILE):
        with open(PLAYERS_FILE, "r") as f:
            return list(json.load(f).keys())
    return []

def load_leaderboard(game):
    path = os.path.join(LEADERBOARD_DIR, f"{game}_leaderboard.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            data = json.load(f)
        return {name: env.Rating(mu, sigma) for name, (mu, sigma) in data.items()}
    return {}

def save_leaderboard(game, leaderboard):
    path = os.path.join(LEADERBOARD_DIR, f"{game}_leaderboard.json")
    data = {name: (r.mu, r.sigma) for name, r in leaderboard.items()}
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

# ---- Balanced Teams Function ----
def make_teams(players, leaderboard):
    ratings = {p: leaderboard.get(p, env.Rating()).mu - 3*leaderboard.get(p, env.Rating()).sigma for p in players}
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

# Select game for leaderboard updates
games = [f.replace("_leaderboard.json","") for f in os.listdir(LEADERBOARD_DIR) if f.endswith("_leaderboard.json")]
game = st.selectbox("Select game to update ratings", options=games)

leaderboard = load_leaderboard(game)
all_players = load_players()

if not all_players:
    st.warning("No players found. Add players in Manage Players first.")
else:
    # Sort by conservative rating
    sorted_players = sorted(all_players, key=lambda p: leaderboard.get(p, env.Rating()).mu - 3*leaderboard.get(p, env.Rating()).sigma, reverse=True)

    selected_players = st.multiselect("Select players for this match", sorted_players)

    if len(selected_players) % 2 == 0 and len(selected_players) > 1:
        if st.button("Generate Balanced Teams"):
            team_a, team_b, score_a, score_b = make_teams(selected_players, leaderboard)
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
            ratings_a = [leaderboard.get(p, env.Rating()) for p in team_a]
            ratings_b = [leaderboard.get(p, env.Rating()) for p in team_b]

            if winner == "Team A":
                new_ratings = env.rate([ratings_a, ratings_b], ranks=[0, 1])
            else:
                new_ratings = env.rate([ratings_a, ratings_b], ranks=[1, 0])

            for p, r in zip(team_a, new_ratings[0]):
                leaderboard[p] = r
            for p, r in zip(team_b, new_ratings[1]):
                leaderboard[p] = r

            save_leaderboard(game, leaderboard)
            st.success(f"Team game recorded! {winner} wins.")
            del st.session_state["match_teams"]
