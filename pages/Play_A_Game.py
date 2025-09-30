# pages/Game_Recording.py
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

st.set_page_config(page_title="Record Game / Matchmaking", page_icon="✏️")
st.title("✏️ Record Game / Matchmaking")

# TrueSkill environment
env = trueskill.TrueSkill(draw_probability=0)

# --- Load players ---
players = load_players_from_git()
if not players:
    st.warning("No players found. Add players in 'Manage Players' first.")
    st.stop()

# --- Select or create game ---
files = gitlab_list_leaderboards_dir()
existing_games = sorted(list({fn.replace("_leaderboard.json","").replace("_history.json","") 
                              for fn in files if fn.endswith(".json")}))
game_option = st.selectbox("Select game (or type new name)", options=["<New Game>"] + existing_games)

if game_option == "<New Game>":
    game_name_input = st.text_input("New game name")
    game_name = game_name_input.strip() if game_name_input else None
else:
    game_name = game_option

if not game_name:
    st.info("Pick or type a game name to record matches for.")
    st.stop()

st.subheader(f"Recording for game: {game_name}")

# --- Load leaderboard & history ---
leaderboard = load_leaderboard_from_git(game_name)
history = load_history_from_git(game_name)

tab_ind, tab_team = st.tabs(["Individual Game", "Team / Matchmaking"])

# ---------- Individual Game ----------
with tab_ind:
    st.write("Select players in finishing order (winner first).")
    selected_players = st.multiselect("Players", options=players)
    
    if st.button("Record Individual Game"):
        if len(selected_players) < 2:
            st.warning("Select at least 2 players.")
        else:
            try:
                # Prepare TrueSkill ratings
                ratings = [env.Rating(mu=leaderboard.get(n, {}).get("mu",25),
                                      sigma=leaderboard.get(n, {}).get("sigma",8.333)) 
                           for n in selected_players]
                ranks = list(range(len(ratings)))  # winner first
                new_ratings = env.rate(ratings, ranks=ranks)
                
                # Update leaderboard
                for name, r in zip(selected_players, new_ratings):
                    leaderboard[name] = {"mu": r.mu, "sigma": r.sigma}
                
                # Update history
                history.setdefault("matches", []).append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "individual",
                    "results": selected_players
                })
                
                # Push to GitLab
                save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record individual match for {game_name}")
                save_history_to_git(game_name, history, commit_message=f"Add match to {game_name} history")
                
                st.success("Individual game recorded!")
            except Exception as e:
                st.error(f"Failed to record game: {e}")

# ---------- Team / Matchmaking ----------
with tab_team:
    st.write("Select all players for this team match.")
    selected_team_players = st.multiselect("Players", options=players)
    
    if selected_team_players:
        team_a = st.multiselect("Team A players", options=selected_team_players)
        team_b = [p for p in selected_team_players if p not in team_a]
        st.write("Team B:", ", ".join(team_b) if team_b else "(empty)")
        winner = st.radio("Select Winning Team", options=["Team A", "Team B"])
        
        if st.button("Record Team Game"):
            if not team_a or not team_b:
                st.warning("Both teams must have at least one player.")
            else:
                try:
                    ratings_a = [env.Rating(mu=leaderboard.get(n, {}).get("mu",25),
                                             sigma=leaderboard.get(n, {}).get("sigma",8.333)) 
                                 for n in team_a]
                    ratings_b = [env.Rating(mu=leaderboard.get(n, {}).get("mu",25),
                                             sigma=leaderboard.get(n, {}).get("sigma",8.333)) 
                                 for n in team_b]
                    
                    # TrueSkill expects list of teams
                    teams = [ratings_a, ratings_b]
                    ranks = [0,1] if winner == "Team A" else [1,0]
                    new_team_ratings = env.rate(teams, ranks=ranks)
                    
                    # Update leaderboard
                    for names, ratings in zip([team_a, team_b], new_team_ratings):
                        for n, r in zip(names, ratings):
                            leaderboard[n] = {"mu": r.mu, "sigma": r.sigma}
                    
                    # Update history
                    history.setdefault("matches", []).append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "type": "team",
                        "team_a": team_a,
                        "team_b": team_b,
                        "winner": winner
                    })
                    
                    # Push to GitLab
                    save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record team match for {game_name}")
                    save_history_to_git(game_name, history, commit_message=f"Add team match to {game_name} history")
                    
                    st.success("Team game recorded!")
                except Exception as e:
                    st.error(f"Failed to record team game: {e}")
