# pages/Play_A_Game.py
import streamlit as st
from GitLab_Persistence import (
    load_players_from_git,
    save_players_to_git,
    load_leaderboard_from_git,
    save_leaderboard_to_git,
    load_history_from_git,
    save_history_to_git,
    gitlab_list_leaderboards_dir
)
import trueskill
from datetime import datetime

st.set_page_config(page_title="Play a Game", page_icon="⚔️")
st.title("⚔️ Play a Game / Record Match")

# TrueSkill environment
env = trueskill.TrueSkill(draw_probability=0)

# Load all players
players = load_players_from_git()
if not players:
    st.warning("No players found. Add players first in Manage Players.")
    st.stop()

# Load games from GitLab
files = gitlab_list_leaderboards_dir()
game_names = sorted(list({fn.replace("_leaderboard.json","").replace("_history.json","") 
                          for fn in files if fn.endswith(".json")}))
game_option = st.selectbox("Select game (or type a new game name)", options=["<New Game>"] + game_names)

if game_option == "<New Game>":
    game_name_input = st.text_input("New game name")
    game_name = game_name_input.strip() if game_name_input else None
else:
    game_name = game_option

if not game_name:
    st.info("Pick or type a game name to record matches for.")
    st.stop()

st.subheader(f"Recording for game: {game_name}")

# Load leaderboard and history
leaderboard = load_leaderboard_from_git(game_name)
history = load_history_from_git(game_name)

# Select players participating
selected_players = st.multiselect("Select players for this match", options=players)
if not selected_players or len(selected_players) < 2:
    st.info("Select at least 2 players.")
    st.stop()

# Choose team mode
team_mode = st.radio("Team mode", options=["Auto-Balanced Teams", "Manual Teams"])

def auto_balance_teams(selected_players):
    # sort players by mu descending
    sorted_players = sorted(selected_players, key=lambda p: leaderboard.get(p, {"mu": env.mu})["mu"], reverse=True)
    team_a, team_b = [], []
    sum_a, sum_b = 0, 0
    for p in sorted_players:
        rating = leaderboard.get(p, {"mu": env.mu})["mu"]
        if sum_a <= sum_b:
            team_a.append(p)
            sum_a += rating
        else:
            team_b.append(p)
            sum_b += rating
    return team_a, team_b

team_a, team_b = [], []

if team_mode == "Auto-Balanced Teams":
    team_a, team_b = auto_balance_teams(selected_players)
    st.subheader("Auto-Balanced Teams")
    st.write("**Team A:**", ", ".join(team_a))
    st.write("**Team B:**", ", ".join(team_b))
else:
    # Manual teams
    team_a = st.multiselect("Select Team A players", options=selected_players)
    team_b = [p for p in selected_players if p not in team_a]
    st.write("**Team B players:**", ", ".join(team_b) if team_b else "(empty)")

winner = st.radio("Select winning team", options=["Team A", "Team B"])

if st.button("Record Game"):
    if not team_a or not team_b:
        st.warning("Both teams must have at least one player.")
    else:
        try:
            # Prepare TrueSkill ratings
            ratings_a = [env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma})) 
                         if p in leaderboard else env.Rating() for p in team_a]
            ratings_b = [env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma})) 
                         if p in leaderboard else env.Rating() for p in team_b]

            # Determine ranks
            if winner == "Team A":
                new_ratings = env.rate([ratings_a, ratings_b], ranks=[0,1])
            else:
                new_ratings = env.rate([ratings_a, ratings_b], ranks=[1,0])

            # Update leaderboard
            for name, r in zip(team_a, new_ratings[0]):
                leaderboard[name] = {"mu": r.mu, "sigma": r.sigma}
            for name, r in zip(team_b, new_ratings[1]):
                leaderboard[name] = {"mu": r.mu, "sigma": r.sigma}

            # Update history
            history.setdefault("matches", []).append({
                "timestamp": datetime.utcnow().isoformat(),
                "type": "team",
                "team_a": team_a,
                "team_b": team_b,
                "winner": winner
            })

            # Save to GitLab
            save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record team match for {game_name}")
            save_history_to_git(game_name, history, commit_message=f"Add team match to {game_name} history")

            st.success("Game recorded and ratings updated successfully!")

        except Exception as e:
            st.error(f"Failed to record game: {e}")
