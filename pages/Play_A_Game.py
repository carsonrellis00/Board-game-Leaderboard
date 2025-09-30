# pages/Play_A_Game.py
import streamlit as st
import trueskill
from datetime import datetime
from GitLab_Persistence import (
    load_players_from_git,
    load_leaderboard_from_git,
    save_leaderboard_to_git,
    load_history_from_git,
    save_history_to_git,
    gitlab_list_leaderboards_dir
)

st.set_page_config(page_title="Play a Game", page_icon="⚔️")
st.title("⚔️ Play a Game / Matchmaking")

# -------------------- TrueSkill env --------------------
env = trueskill.TrueSkill(draw_probability=0)

# -------------------- Helper: Auto Balance Teams --------------------
def auto_balance_teams(players, leaderboard, env):
    """
    Takes a list of player names and returns two teams that are approximately balanced.
    Uses TrueSkill mu values for balancing.
    """
    if len(players) < 2:
        return players, []

    # Helper to get mu, default to env.mu if player not in leaderboard
    def get_mu(player):
        rating = leaderboard.get(player)
        if rating:
            return rating.get("mu", env.mu)
        return env.mu

    # Sort descending by skill
    sorted_players = sorted(players, key=get_mu, reverse=True)

    team_a = []
    team_b = []
    sum_a = 0
    sum_b = 0

    for player in sorted_players:
        if sum_a <= sum_b:
            team_a.append(player)
            sum_a += get_mu(player)
        else:
            team_b.append(player)
            sum_b += get_mu(player)

    return team_a, team_b

# -------------------- Load Data --------------------
all_players = load_players_from_git()
if not all_players:
    st.warning("No players found. Add players first in Player Manager page.")
    st.stop()

# Gather existing games from leaderboards dir
files = gitlab_list_leaderboards_dir()
game_names = sorted(list({fn.replace("_leaderboard.json","").replace("_history.json","") 
                          for fn in files if fn.endswith(".json")}))
game_option = st.selectbox("Select game (or type new)", options=["<New Game>"] + game_names)

if game_option == "<New Game>":
    game_name_input = st.text_input("New game name")
    game_name = game_name_input.strip() if game_name_input else None
else:
    game_name = game_option

if not game_name:
    st.info("Pick or type a game name to record matches for.")
    st.stop()

leaderboard = load_leaderboard_from_git(game_name)
history = load_history_from_git(game_name)

# -------------------- Team Selection --------------------
st.subheader(f"Recording for game: {game_name}")

selected_players = st.multiselect("Select players for this match", options=all_players)

if not selected_players:
    st.info("Select at least 2 players.")
    st.stop()

# Manual vs Auto
team_mode = st.radio("Team assignment mode:", ["Manual Teams", "Auto-Balance Teams"])

if team_mode == "Manual Teams":
    team_a = st.multiselect("Team A", options=selected_players)
    team_b = [p for p in selected_players if p not in team_a]
    st.write("Team B:", ", ".join(team_b) if team_b else "(empty)")
else:
    team_a, team_b = auto_balance_teams(selected_players, leaderboard, env)
    st.write("Auto-Balanced Teams:")
    st.write("Team A:", ", ".join(team_a))
    st.write("Team B:", ", ".join(team_b))

winner = st.radio("Select Winner:", options=["Team A", "Team B"])

if st.button("Record Game"):
    if not team_a or not team_b:
        st.warning("Make sure both teams have at least one player.")
    else:
        try:
            # Prepare ratings
            ratings_a = [env.Rating(**leaderboard[p]) if p in leaderboard else env.Rating() for p in team_a]
            ratings_b = [env.Rating(**leaderboard[p]) if p in leaderboard else env.Rating() for p in team_b]

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

            # Append to history
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

            st.success("Game recorded successfully!")

        except Exception as e:
            st.error(f"Failed to record game: {e}")
