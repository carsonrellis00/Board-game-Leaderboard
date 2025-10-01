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
players_dict = load_players_from_git() or {}
players = players_dict.get("players", [])
files = gitlab_list_leaderboards_dir()
game_names = sorted(list({fn.replace("_leaderboard.json", "").replace("_history.json", "") 
                          for fn in files if fn.endswith(".json")}))

# ---- Game selection ----
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

# ---- Game Type Tabs ----
game_type = st.radio("Game Type", ["1v1", "Team", "Free For All"])

# ---------------- 1v1 ----------------
if game_type == "1v1":
    selected_players_1v1 = st.multiselect("Select two players", options=players)
    if len(selected_players_1v1) != 2:
        st.info("Select exactly 2 players for 1v1.")
    else:
        winner_1v1 = st.radio("Select winner", options=selected_players_1v1)
        if st.button("Record 1v1 Game"):
            try:
                # Load ratings (only mu and sigma)
                ratings = [
                    env.Rating(**{k: v for k, v in leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma}).items() if k in ["mu","sigma"]})
                    for p in selected_players_1v1
                ]
                ranks = [0, 1] if winner_1v1 == selected_players_1v1[0] else [1, 0]
                new_ratings = env.rate(ratings, ranks=ranks)

                # Update leaderboard and wins
                for i, p in enumerate(selected_players_1v1):
                    leaderboard[p] = {
                        "mu": new_ratings[i].mu,
                        "sigma": new_ratings[i].sigma,
                        "wins": leaderboard.get(p, {}).get("wins", 0) + (1 if winner_1v1 == p else 0)
                    }

                # Update history
                history["matches"].append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "1v1",
                    "players": selected_players_1v1,
                    "winner": winner_1v1
                })

                save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record 1v1 match for {game_name}")
                save_history_to_git(game_name, history, commit_message=f"Add 1v1 match to {game_name} history")

                st.success("1v1 game recorded successfully!")
            except Exception as e:
                st.error(f"Failed to record 1v1 game: {e}")

# ---------------- Team ----------------
elif game_type == "Team":
    selected_players_team = st.multiselect("Select players", options=players)
    if selected_players_team:
        manual_team_btn = st.button("Set Manual Teams")
        auto_team_btn = st.button("Auto Balance Teams")

        team_a, team_b = [], []

        if manual_team_btn:
            team_a = st.multiselect("Team A players", options=selected_players_team)
            team_b = [p for p in selected_players_team if p not in team_a]
            st.write("Team B:", ", ".join(team_b) if team_b else "(empty)")
        elif auto_team_btn:
            def get_mu(p):
                return leaderboard.get(p, {"mu": env.mu}).get("mu", env.mu)
            sorted_players = sorted(selected_players_team, key=get_mu, reverse=True)
            team_a = sorted_players[::2]
            team_b = sorted_players[1::2]
            st.write("Auto-balanced Teams:")
            st.write("Team A:", ", ".join(team_a))
            st.write("Team B:", ", ".join(team_b))

        if team_a and team_b:
            winner_team = st.radio("Winner", options=["Team A", "Team B"])
            if st.button("Record Team Game"):
                try:
                    ratings_a = [
                        env.Rating(**{k: v for k, v in leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma}).items() if k in ["mu","sigma"]})
                        for p in team_a
                    ]
                    ratings_b = [
                        env.Rating(**{k: v for k, v in leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma}).items() if k in ["mu","sigma"]})
                        for p in team_b
                    ]
                    ranks = [0, 1] if winner_team == "Team A" else [1, 0]
                    new_ratings = env.rate([ratings_a, ratings_b], ranks=ranks)

                    # Update leaderboard and wins
                    for i, p in enumerate(team_a):
                        leaderboard[p] = {
                            "mu": new_ratings[0][i].mu,
                            "sigma": new_ratings[0][i].sigma,
                            "wins": leaderboard.get(p, {}).get("wins", 0) + (1 if winner_team == "Team A" else 0)
                        }
                    for i, p in enumerate(team_b):
                        leaderboard[p] = {
                            "mu": new_ratings[1][i].mu,
                            "sigma": new_ratings[1][i].sigma,
                            "wins": leaderboard.get(p, {}).get("wins", 0) + (1 if winner_team == "Team B" else 0)
                        }

                    # Update history
                    history["matches"].append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "type": "team",
                        "team_a": team_a,
                        "team_b": team_b,
                        "winner": winner_team
                    })

                    save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record team match for {game_name}")
                    save_history_to_git(game_name, history, commit_message=f"Add team match to {game_name} history")

                    st.success("Team game recorded successfully!")
                except Exception as e:
                    st.error(f"Failed to record team game: {e}")

# ---------------- Free For All ----------------
elif game_type == "Free For All":
    selected_players_ffa = st.multiselect("Select players", options=players)
    if selected_players_ffa:
        finishing_order = []
        remaining = selected_players_ffa.copy()

        while remaining:
            pick = st.selectbox(f"Next finisher ({len(finishing_order)+1})", options=remaining, key=len(finishing_order))
            finishing_order.append(pick)
            remaining.remove(pick)
            if st.button("Record FFA Game", key="record_ffa"):
                try:
                    ratings = [
                        env.Rating(**{k: v for k, v in leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma}).items() if k in ["mu","sigma"]})
                        for p in selected_players_ffa
                    ]
                    # Each player's rank corresponds to index in finishing_order
                    ranks = [finishing_order.index(p) for p in selected_players_ffa]
                    new_ratings = env.rate(ratings, ranks=ranks)

                    # Update leaderboard and wins
                    for i, p in enumerate(selected_players_ffa):
                        leaderboard[p] = {
                            "mu": new_ratings[i].mu,
                            "sigma": new_ratings[i].sigma,
                            "wins": leaderboard.get(p, {}).get("wins", 0) + (1 if finishing_order[0] == p else 0)
                        }

                    # Update history
                    history["matches"].append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "type": "ffa",
                        "players": selected_players_ffa,
                        "finishing_order": finishing_order
                    })

                    save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record FFA match for {game_name}")
                    save_history_to_git(game_name, history, commit_message=f"Add FFA match to {game_name} history")

                    st.success("FFA game recorded successfully!")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"Failed to record FFA game: {e}")
