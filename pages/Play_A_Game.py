# pages/Play_A_Game.py
import streamlit as st
import trueskill
from datetime import datetime
from GitLab_Persistence import (
    load_players_from_git,
    save_players_to_git,
    load_leaderboard_from_git,
    save_leaderboard_to_git,
    load_history_from_git,
    save_history_to_git,
    gitlab_list_leaderboards_dir
)

st.set_page_config(page_title="Play a Game", page_icon="⚔️")
st.title("⚔️ Game Recording & Matchmaking")

# ----- TrueSkill environment -----
env = trueskill.TrueSkill(draw_probability=0)

# ----- Load players and games -----
players = load_players_from_git() or []
if not players:
    st.warning("No players found. Add players first in Player Manager.")
    st.stop()

files = gitlab_list_leaderboards_dir()
game_names = sorted(list({fn.replace("_leaderboard.json","").replace("_history.json","") 
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

leaderboard = load_leaderboard_from_git(game_name)
history = load_history_from_git(game_name)

# ----- Helper: Auto-balance teams -----
def auto_balance_teams(selected_players, leaderboard, env):
    def get_mu(p):
        rating = leaderboard.get(p)
        if rating is None:
            return env.create_rating().mu  # default rating
        return rating["mu"]
    
    sorted_players = sorted(selected_players, key=get_mu, reverse=True)
    team_a = sorted_players[::2]
    team_b = sorted_players[1::2]
    return team_a, team_b

# ----- Game recording UI -----
st.header(f"Record a Game: {game_name}")

# Player selection
selected_players = st.multiselect("Select players participating", options=players)

if not selected_players:
    st.info("Select at least 2 players.")
    st.stop()

# Team assignment
mode = st.radio("Team assignment", options=["Manual Teams", "Auto-balanced Teams"])

if mode == "Manual Teams":
    team_a = st.multiselect("Team A players", options=selected_players)
    team_b = [p for p in selected_players if p not in team_a]
    st.write("Team B:", ", ".join(team_b) if team_b else "(empty)")
else:
    team_a, team_b = auto_balance_teams(selected_players, leaderboard, env)
    st.write("Team A:", ", ".join(team_a))
    st.write("Team B:", ", ".join(team_b))

winner = st.radio("Select winner", options=["Team A", "Team B"])

if st.button("Record Match"):
    if not team_a or not team_b:
        st.warning("Both teams must have at least one player.")
    else:
        try:
            # Prepare ratings
            ratings_a = [env.Rating(mu=leaderboard[p]["mu"], sigma=leaderboard[p]["sigma"])
                         if p in leaderboard else env.create_rating() for p in team_a]
            ratings_b = [env.Rating(mu=leaderboard[p]["mu"], sigma=leaderboard[p]["sigma"])
                         if p in leaderboard else env.create_rating() for p in team_b]

            # Compute new ratings
            ranks = [0, 1] if winner == "Team A" else [1, 0]
            new_ratings_a, new_ratings_b = env.rate([ratings_a, ratings_b], ranks=ranks)

            # Update leaderboard
            for name, r in zip(team_a, new_ratings_a):
                leaderboard[name] = {"mu": r.mu, "sigma": r.sigma}
            for name, r in zip(team_b, new_ratings_b):
                leaderboard[name] = {"mu": r.mu, "sigma": r.sigma}

            # Update history
            history.setdefault("matches", []).append({
                "timestamp": datetime.utcnow().isoformat(),
                "team_a": team_a,
                "team_b": team_b,
                "winner": winner
            })

            # Push to GitLab
            save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record match for {game_name}")
            save_history_to_git(game_name, history, commit_message=f"Add match to {game_name} history")

            st.success(f"Game recorded! {winner} won.")
        except Exception as e:
            st.error(f"Failed to record game: {e}")
