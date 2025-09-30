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

st.set_page_config(page_title="Play a Game", page_icon="🎲")

st.title("✏️ Record a Game / Matchmaking")

# TrueSkill environment
env = trueskill.TrueSkill(draw_probability=0)

# --- Load Players ---
try:
    players = load_players_from_git()
except Exception as e:
    st.error(f"Failed to load players: {e}")
    players = []

if not players:
    st.warning("No players found. Add players first in Manage Players.")
    st.stop()

# --- Select Game ---
files = gitlab_list_leaderboards_dir()
game_names = sorted(list({fn.replace("_leaderboard.json","").replace("_history.json","") 
                          for fn in files if fn.endswith(".json")}))
game_option = st.selectbox("Select game or type new", ["<New Game>"] + game_names, key="game_select")

if game_option == "<New Game>":
    game_name_input = st.text_input("New game name", key="new_game_input")
    game_name = game_name_input.strip() if game_name_input else None
else:
    game_name = game_option

if not game_name:
    st.info("Pick or type a game name.")
    st.stop()

# --- Load leaderboard & history ---
leaderboard = load_leaderboard_from_git(game_name)
history = load_history_from_git(game_name)

tab1, tab2 = st.tabs(["Individual", "Team/Matchmaking"])

# ---------------- Individual ----------------
with tab1:
    ordered = st.multiselect("Select players in finishing order (winner first)",
                             options=players, key="individual_players")
    if st.button("Record Individual Game", key="record_individual"):
        if len(ordered) < 2:
            st.warning("Select at least two players.")
        else:
            try:
                ratings = []
                for name in ordered:
                    p = leaderboard.get(name)
                    ratings.append(env.Rating(mu=p["mu"], sigma=p["sigma"]) if p else env.Rating())
                ranks = list(range(len(ratings)))
                new_ratings = env.rate(ratings, ranks=ranks)
                # update leaderboard
                for name, r in zip(ordered, new_ratings):
                    leaderboard[name] = {"mu": r.mu, "sigma": r.sigma}
                # update history
                history.setdefault("matches", []).append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "individual",
                    "results": ordered
                })
                # save
                save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record individual match for {game_name}")
                save_history_to_git(game_name, history, commit_message=f"Add match to {game_name} history")
                st.success("Individual game recorded successfully!")
            except Exception as e:
                st.error(f"Failed to record game: {e}")

# ---------------- Team / Matchmaking ----------------
with tab2:
    selected_players = st.multiselect("Select players for team match", options=players, key="team_players")
    if selected_players:
        team_a = st.multiselect("Team A players", options=selected_players, key="team_a_players")
        team_b = [p for p in selected_players if p not in team_a]
        st.write("Team B:", ", ".join(team_b) if team_b else "(empty)")

        winner = st.radio("Winner", options=["Team A", "Team B"], key="team_winner")

        if st.button("Record Team Game", key="record_team"):
            if not team_a or not team_b:
                st.warning("Both teams must have at least one player.")
            else:
                try:
                    ratings_a = [env.Rating(mu=leaderboard[p]["mu"], sigma=leaderboard[p]["sigma"]) 
                                 if p in leaderboard else env.Rating() for p in team_a]
                    ratings_b = [env.Rating(mu=leaderboard[p]["mu"], sigma=leaderboard[p]["sigma"]) 
                                 if p in leaderboard else env.Rating() for p in team_b]
                    if winner == "Team A":
                        new_team_ratings = env.rate([ratings_a, ratings_b], ranks=[0,1])
                    else:
                        new_team_ratings = env.rate([ratings_a, ratings_b], ranks=[1,0])
                    # update leaderboard
                    for name, r in zip(team_a, new_team_ratings[0]):
                        leaderboard[name] = {"mu": r.mu, "sigma": r.sigma}
                    for name, r in zip(team_b, new_team_ratings[1]):
                        leaderboard[name] = {"mu": r.mu, "sigma": r.sigma}
                    # update history
                    history.setdefault("matches", []).append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "type": "team",
                        "team_a": team_a,
                        "team_b": team_b,
                        "winner": winner
                    })
                    # save
                    save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record team match for {game_name}")
                    save_history_to_git(game_name, history, commit_message=f"Add team match to {game_name} history")
                    st.success("Team game recorded successfully!")
                except Exception as e:
                    st.error(f"Failed to record team game: {e}")
