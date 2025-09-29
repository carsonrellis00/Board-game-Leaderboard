import json
import os
import trueskill
import streamlit as st
import matplotlib.pyplot as plt

# ---- Setup ----
env = trueskill.TrueSkill(draw_probability=0.0)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LEADERBOARD_DIR = os.path.join(BASE_DIR, "leaderboards")

# ---- Event Banner ----
EVENT_FILE = os.path.join(BASE_DIR, "event.json")

def load_event():
    if os.path.exists(EVENT_FILE):
        with open(EVENT_FILE, "r") as f:
            data = json.load(f)
            return data.get("next_event", "")
    return ""

next_event = load_event()
if next_event:
    st.markdown(
        f"""
        <div style="background-color:#4CAF50;padding:12px;border-radius:8px;margin-bottom:15px">
            <h2 style="color:white;text-align:center;">🎲 Next Board Game Night: {next_event} 🎲</h2>
        </div>
        """,
        unsafe_allow_html=True
    )

def list_games():
    existing_files = os.listdir(LEADERBOARD_DIR)
    existing_games = sorted(list(set(f.split("_leaderboard.json")[0] for f in existing_files if f.endswith("_leaderboard.json"))))
    return existing_games

def load_leaderboard(game_name):
    save_file = os.path.join(LEADERBOARD_DIR, f"{game_name}_leaderboard.json")
    if os.path.exists(save_file):
        with open(save_file, "r") as f:
            data = json.load(f)
            return {name: env.Rating(mu, sigma) for name, (mu, sigma) in data.items()}
    return {}

def load_history(game_name):
    history_file = os.path.join(LEADERBOARD_DIR, f"{game_name}_history.json")
    if os.path.exists(history_file):
        with open(history_file, "r") as f:
            return json.load(f)
    return []

# ---- Streamlit UI ----
st.title("Board Game Leaderboard Viewer")

games = list_games()
if not games:
    st.warning("No games found.")
else:
    game_name = st.selectbox("Select a game", games)
    if game_name:
        leaderboard = load_leaderboard(game_name)
        history = load_history(game_name)

        st.header(f"Leaderboard: {game_name.title()}")
        if leaderboard:
            sorted_players = sorted(
                leaderboard.items(),
                key=lambda item: item[1].mu - 3*item[1].sigma,
                reverse=True
            )
            medal_map = ["🥇","🥈","🥉"]
            for i, (name, rating) in enumerate(sorted_players):
                star = medal_map[i] if i < 3 else ""
                st.write(f"{i+1}. {name} | μ={rating.mu:.2f}, σ={rating.sigma:.2f}, rating={rating.mu-3*rating.sigma:.2f} {star}")
        else:
            st.write("No players yet.")

        st.subheader("Match History")
        if history:
            for i, entry in enumerate(history, start=1):
                timestamp = entry.get("timestamp","Unknown")
                st.write(f"Game {i} at {timestamp}")
                for rank, team in zip(entry["ranks"], entry["teams"]):
                    st.write(f"  Rank {rank+1}: {', '.join(team)}")
        else:
            st.write("No games recorded yet.")

        # Skill progression graph
        st.subheader("Skill Progression")
        player_history = {}
        temp_lb = {}
        for entry in history:
            teams = entry["teams"]
            for team in teams:
                for player in team:
                    if player not in temp_lb:
                        temp_lb[player] = env.Rating()
            team_ratings = [[temp_lb.get(p, env.Rating()) for p in team] for team in teams]
            new_team_ratings = env.rate(team_ratings, ranks=entry["ranks"])
            for team, new_ratings in zip(teams, new_team_ratings):
                for player, new_rating in zip(team, new_ratings):
                    temp_lb[player] = new_rating
                    player_history.setdefault(player, []).append(new_rating.mu)

        if player_history:
            plt.figure(figsize=(10,6))
            for player, mus in player_history.items():
                plt.plot(range(1,len(mus)+1), mus, marker='o', label=player)
            plt.xlabel("Game #")
            plt.ylabel("μ (Skill Rating)")
            plt.title(f"Skill Progression for {game_name.title()}")
            plt.legend()
            plt.grid(True)
            st.pyplot(plt)
