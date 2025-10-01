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

st.set_page_config(page_title="Record Game / Matchmaking", page_icon="✏️")
st.title("✏️ Record Game & Matchmaking")

# ---- TrueSkill environment ----
env = trueskill.TrueSkill(draw_probability=0)

# ---- Load players and games ----
players_dict = load_players_from_git() or {"players": []}
players = players_dict.get("players", [])

files = gitlab_list_leaderboards_dir()
game_names = sorted(list({fn.replace("_leaderboard.json", "").replace("_history.json", "") 
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

st.subheader(f"Recording for game: {game_name}")

# ---- Load leaderboard and history ----
leaderboard = load_leaderboard_from_git(game_name) or {}
history = load_history_from_git(game_name) or {"matches": []}

if not players:
    st.warning("No global players found. Add players first in Player Manager.")
    st.stop()

# ---- Helper function for safe TrueSkill rating ----
def get_player_rating(p):
    stats = leaderboard.get(p)
    if not stats or not isinstance(stats, dict):
        leaderboard[p] = {"mu": env.mu, "sigma": env.sigma, "wins": 0}
        stats = leaderboard[p]
    else:
        stats.setdefault("mu", env.mu)
        stats.setdefault("sigma", env.sigma)
        stats.setdefault("wins", 0)
    return env.Rating(mu=stats["mu"], sigma=stats["sigma"])

# ---- Game type selection ----
game_type = st.radio("Select game type", ["1v1", "Team", "Free for All"])

# -----------------------------
# 1v1 Game
# -----------------------------
if game_type == "1v1":
    st.header("1v1 Game")
    selected_players_1v1 = st.multiselect("Select 2 players", options=players)
    
    if len(selected_players_1v1) == 2:
        winner = st.radio("Select winner", options=selected_players_1v1)
        if st.button("Record 1v1 Game"):
            try:
                ratings = [get_player_rating(p) for p in selected_players_1v1]
                ranks = [0, 1] if winner == selected_players_1v1[0] else [1, 0]
                new_ratings = env.rate(ratings, ranks=ranks)
                
                for p, r in zip(selected_players_1v1, new_ratings):
                    leaderboard[p]["mu"] = r.mu
                    leaderboard[p]["sigma"] = r.sigma
                    leaderboard[p]["wins"] += 1 if p == winner else 0
                
                history["matches"].append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "1v1",
                    "players": selected_players_1v1,
                    "winner": winner
                })
                
                save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record 1v1 match for {game_name}")
                save_history_to_git(game_name, history, commit_message=f"Add 1v1 match to {game_name} history")
                
                st.success("1v1 game recorded successfully!")
            except Exception as e:
                st.error(f"Failed to record 1v1 game: {e}")
    else:
        st.info("Select exactly 2 players.")

# -----------------------------
# Team Game
# -----------------------------
elif game_type == "Team":
    st.header("Team-based Game")
    selected_players_team = st.multiselect("Select players", options=players)
    
    if selected_players_team:
        manual_team_btn = st.button("Set Manual Teams")
        auto_team_btn = st.button("Auto Balance Teams")
        
        team_a, team_b = [], []
        
        if manual_team_btn:
            team_a = st.multiselect("Team A players", options=selected_players_team, key="manual_a")
            team_b = [p for p in selected_players_team if p not in team_a]
            st.write("Team B:", ", ".join(team_b) if team_b else "(empty)")
        elif auto_team_btn:
            sorted_players = sorted(selected_players_team, key=lambda p: leaderboard.get(p, {}).get("mu", env.mu), reverse=True)
            team_a = sorted_players[::2]
            team_b = sorted_players[1::2]
            st.write("Auto-balanced Teams:")
            st.write("Team A:", ", ".join(team_a))
            st.write("Team B:", ", ".join(team_b))
        
        if team_a and team_b:
            winner = st.radio("Winner", options=["Team A", "Team B"], key="team_winner")
            if st.button("Record Team Game", key="record_team"):
                try:
                    ratings_a = [get_player_rating(p) for p in team_a]
                    ratings_b = [get_player_rating(p) for p in team_b]
                    ranks = [0, 1] if winner == "Team A" else [1, 0]
                    new_ratings = env.rate([ratings_a, ratings_b], ranks=ranks)
                    
                    for name, r in zip(team_a, new_ratings[0]):
                        leaderboard[name]["mu"] = r.mu
                        leaderboard[name]["sigma"] = r.sigma
                        leaderboard[name]["wins"] += 1 if winner == "Team A" else 0
                    for name, r in zip(team_b, new_ratings[1]):
                        leaderboard[name]["mu"] = r.mu
                        leaderboard[name]["sigma"] = r.sigma
                        leaderboard[name]["wins"] += 1 if winner == "Team B" else 0
                    
                    history["matches"].append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "type": "team",
                        "team_a": team_a,
                        "team_b": team_b,
                        "winner": winner
                    })
                    
                    save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record team match for {game_name}")
                    save_history_to_git(game_name, history, commit_message=f"Add team match to {game_name} history")
                    
                    st.success("Team game recorded successfully!")
                except Exception as e:
                    st.error(f"Failed to record team game: {e}")

# -----------------------------
# Free For All (FFA)
# -----------------------------
elif game_type == "Free for All":
    st.header("Free For All Game")
    selected_players_ffa = st.multiselect("Select players", options=players, key="ffa_players")
    
    if selected_players_ffa:
        finishing_order = []
        remaining = selected_players_ffa.copy()
        while remaining:
            pick = st.selectbox(f"Next finisher ({len(finishing_order)+1})", options=remaining, key=len(finishing_order))
            finishing_order.append(pick)
            remaining.remove(pick)
            st.experimental_rerun() if remaining else None
        
        if len(finishing_order) == len(selected_players_ffa):
            if st.button("Record FFA Game"):
                try:
                    ratings = [get_player_rating(p) for p in finishing_order]
                    ranks = list(range(len(finishing_order)))
                    new_ratings = env.rate(ratings, ranks=ranks)
                    
                    for p, r, rank in zip(finishing_order, new_ratings, ranks):
                        leaderboard[p]["mu"] = r.mu
                        leaderboard[p]["sigma"] = r.sigma
                        leaderboard[p]["wins"] += 1 if rank == 0 else 0
                    
                    history["matches"].append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "type": "ffa",
                        "players": finishing_order,
                        "winner": finishing_order[0]
                    })
                    
                    save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record FFA match for {game_name}")
                    save_history_to_git(game_name, history, commit_message=f"Add FFA match to {game_name} history")
                    
                    st.success("FFA game recorded successfully!")
                except Exception as e:
                    st.error(f"Failed to record FFA game: {e}")
