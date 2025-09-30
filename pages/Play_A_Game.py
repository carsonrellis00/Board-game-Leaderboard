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
st.title("⚔️ Game Recording & Matchmaking")

# TrueSkill environment
env = trueskill.TrueSkill(draw_probability=0)

# Load global players
players = load_players_from_git()
if not players:
    st.warning("No players found. Please add players first in the Player Manager page.")
    st.stop()

# Load games
files = gitlab_list_leaderboards_dir()
game_names = sorted(list({fn.replace("_leaderboard.json", "").replace("_history.json","") 
                          for fn in files if fn.endswith(".json")}))
game_option = st.selectbox("Select game (or type a new name)", options=["<New Game>"] + game_names)

if game_option == "<New Game>":
    game_name_input = st.text_input("New game name")
    game_name = game_name_input.strip() if game_name_input else None
else:
    game_name = game_option

if not game_name:
    st.info("Pick or type a game name to record matches for.")
    st.stop()

# Load leaderboard & history
leaderboard = load_leaderboard_from_git(game_name)
history = load_history_from_git(game_name)

# -------------------- Team Selection --------------------
st.subheader("Teams")
team_selection_method = st.radio(
    "Select team setup method:",
    options=["Auto Balance Teams", "Manual Teams"]
)

if team_selection_method == "Manual Teams":
    team_a = st.multiselect("Team A players", options=selected_players)
    team_b = [p for p in selected_players if p not in team_a]
    st.write("Team B:", ", ".join(team_b) if team_b else "(empty)")
else:
    team_a, team_b = auto_balance_teams(selected_players, leaderboard, env)
    st.write("Team A:", ", ".join(team_a))
    st.write("Team B:", ", ".join(team_b))


# Auto-balance teams
def auto_balance_teams(selected_players, leaderboard, env):
    def get_mu(p):
        rating = leaderboard.get(p)
        if not isinstance(rating, dict):
            return env.create_rating().mu
        return rating.get("mu", env.create_rating().mu)
    
    sorted_players = sorted(selected_players, key=get_mu, reverse=True)
    team_a = sorted_players[::2]
    team_b = sorted_players[1::2]
    return team_a, team_b

st.subheader("Teams")
manual_team_selection = st.checkbox("Manually select teams?", value=False)

if manual_team_selection:
    team_a = st.multiselect("Team A players", options=selected_players)
    team_b = [p for p in selected_players if p not in team_a]
    st.write("Team B:", ", ".join(team_b) if team_b else "(empty)")
else:
    team_a, team_b = auto_balance_teams(selected_players, leaderboard, env)
    st.write("Team A:", ", ".join(team_a))
    st.write("Team B:", ", ".join(team_b))

winner = st.radio("Select winning team", options=["Team A", "Team B"])

# -------------------- Record Match --------------------
if st.button("Record Match"):
    if not team_a or not team_b:
        st.warning("Both teams must have at least one player.")
    else:
        try:
            ratings_a = [env.Rating(mu=leaderboard[p]["mu"], sigma=leaderboard[p]["sigma"])
                         if p in leaderboard else env.Rating()
                         for p in team_a]
            ratings_b = [env.Rating(mu=leaderboard[p]["mu"], sigma=leaderboard[p]["sigma"])
                         if p in leaderboard else env.Rating()
                         for p in team_b]
            
            if winner == "Team A":
                new_team_ratings = env.rate([ratings_a, ratings_b], ranks=[0,1])
            else:
                new_team_ratings = env.rate([ratings_a, ratings_b], ranks=[1,0])
            
            # Update leaderboard
            for name, r in zip(team_a, new_team_ratings[0]):
                leaderboard[name] = {"mu": r.mu, "sigma": r.sigma}
            for name, r in zip(team_b, new_team_ratings[1]):
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
            save_history_to_git(game_name, history, commit_message=f"Add match to {game_name} history")
            st.success("Match recorded successfully!")
        except Exception as e:
            st.error(f"Failed to record match: {e}")
