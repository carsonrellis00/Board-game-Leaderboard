import streamlit as st
import json
import os
import trueskill
from datetime import datetime

# ---- Paths ----
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEADERBOARD_DIR = os.path.join(BASE_DIR, "leaderboards")
os.makedirs(LEADERBOARD_DIR, exist_ok=True)
PLAYERS_FILE = os.path.join(LEADERBOARD_DIR, "players.json")

env = trueskill.TrueSkill(draw_probability=0)

# ---- Helper Functions ----
def get_games():
    files = os.listdir(LEADERBOARD_DIR)
    games = sorted(set(f.replace("_leaderboard.json","") for f in files if f.endswith("_leaderboard.json")))
    return games

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

# Game selection
games = get_games()
game = st.selectbox("Select game", options=games + ["<New Game>"])
if game == "<New Game>":
    new_game_name = st.text_input("Enter new game name")
    if new_game_name:
        game = new_game_name

# Load global players
all_players = load_players()
if not all_players:
    st.warning("No players found. Add players in Manage Players first.")
else:
    leaderboard = load_leaderboard(game)
    game_type = st.radio("Select game type", ["Individual", "Team-based"])

    # Individual game
    if game_type == "Individual":
        players = st.multiselect("Select players in finishing order", all_players)
        if players and st.button("Record Individual Game"):
            ratings = [leaderboard.get(p, env.Rating()) for p in players]
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

    # Team-based game
    else:
        selected_players = st.multiselect("Select all players", all_players)
        if len(selected_players) >= 2 and len(selected_players) % 2 == 0:
            team_a = st.multiselect("Team A", selected_players)
            team_b = [p for p in selected_players if p not in team_a]
            st.write(f"**Team B automatically includes:** {', '.join(team_b)}")

            winner = st.radio("Which team won?", ["Team A", "Team B"])
            if st.button("Record Team Game"):
                ratings_a = [leaderboard.get(p, env.Rating()) for p in team_a]
                ratings_b = [leaderboard.get(p, env.Rating()) for p in team_b]

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
