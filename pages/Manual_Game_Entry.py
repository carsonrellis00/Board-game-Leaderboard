import streamlit as st
import json
import os
import trueskill
from datetime import datetime

# ---- Paths ----
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEADERBOARD_DIR = os.path.join(BASE_DIR, "leaderboards")
os.makedirs(LEADERBOARD_DIR, exist_ok=True)

env = trueskill.TrueSkill(draw_probability=0)

# ---- Helper Functions ----
def get_games():
    """Return a list of games based on existing leaderboard JSON files."""
    files = os.listdir(LEADERBOARD_DIR)
    games = sorted(set(f.replace("_leaderboard.json","") for f in files if f.endswith("_leaderboard.json")))
    return games

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

def load_history(game):
    path = os.path.join(LEADERBOARD_DIR, f"{game}_history.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return []

def save_history(game, history):
    path = os.path.join(LEADERBOARD_DIR, f"{game}_history.json")
    with open(path, "w") as f:
        json.dump(history, f, indent=4)

# ---- Streamlit UI ----
st.title("✏️ Manual Game Entry")

# Select which game to record
games = get_games()
game = st.selectbox("Select game", options=games + ["<New Game>"])

# If new game, ask for name
if game == "<New Game>":
    new_game_name = st.text_input("Enter new game name")
    if new_game_name:
        game = new_game_name

leaderboard = load_leaderboard(game)

if not leaderboard:
    st.info(f"No players yet for {game}. Add some players first.")

game_type = st.radio("Select game type", ["Individual", "Team-based"])

if leaderboard:
    if game_type == "Individual":
        players = st.multiselect("Select players in finishing order", list(leaderboard.keys()))
        if players and st.button("Record Individual Game"):
            ratings = [leaderboard[p] for p in players]
            ranks = list(range(len(players)))
            new_ratings = env.rate(ratings, ranks=ranks)
            for p, r in zip(players, new_ratings):
                leaderboard[p] = r
            save_leaderboard(game, leaderboard)

            history = load_history(game)
            history.append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "players": players,
                "type": "Individual"
            })
            save_history(game, history)
            st.success(f"Individual game recorded for {game}!")

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
                    new_ratings = env.rate([ratings_a, ratings_b], ranks=[0,1])
                else:
                    new_ratings = env.rate([ratings_a, ratings_b], ranks=[1,0])

                for p, r in zip(team_a, new_ratings[0]):
                    leaderboard[p] = r
                for p, r in zip(team_b, new_ratings[1]):
                    leaderboard[p] = r

                save_leaderboard(game, leaderboard)

                history = load_history(game)
                history.append({
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "type": "Team-based",
                    "team_a": team_a,
                    "team_b": team_b,
                    "winner": winner
                })
                save_history(game, history)
                st.success(f"Team game recorded for {game}!")
