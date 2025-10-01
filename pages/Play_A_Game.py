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

# --- TrueSkill environment ---
env = trueskill.TrueSkill(draw_probability=0)

# --- Load global players ---
players_dict = load_players_from_git() or {"players": []}
players = players_dict.get("players", [])

if not players:
    st.warning("No global players found. Add players first in Player Manager.")
    st.stop()

# --- Load games ---
files = gitlab_list_leaderboards_dir()
game_names = sorted(list({fn.replace("_leaderboard.json", "").replace("_history.json", "") 
                          for fn in files if fn.endswith(".json")}))

# --- Select or create game ---
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

# --- Load leaderboard and history ---
leaderboard = load_leaderboard_from_git(game_name) or {}
history = load_history_from_git(game_name) or {"matches": []}

# --- Initialize missing players in leaderboard ---
for p in players:
    if p not in leaderboard:
        leaderboard[p] = {"mu": env.mu, "sigma": env.sigma, "wins": 0}

# --- Game type selection ---
game_type = st.radio("Game Type", ["1v1", "Team", "Free For All"])

# ------------------- 1v1 -------------------
if game_type == "1v1":
    st.header("1v1 Match Recording")
    selected = st.multiselect("Select 2 players", options=players, key="1v1_players")
    if len(selected) == 2:
        winner = st.radio("Winner", options=selected, key="1v1_winner")
        if st.button("Record 1v1 Game", key="1v1_record"):
            try:
                ratings = [trueskill.Rating(**leaderboard[p]) for p in selected]
                ranks = [0,1] if winner == selected[0] else [1,0]
                new_ratings = env.rate(ratings, ranks=ranks)
                
                # Update leaderboard
                for p, r in zip(selected, new_ratings):
                    leaderboard[p]["mu"] = r.mu
                    leaderboard[p]["sigma"] = r.sigma
                    if p == winner:
                        leaderboard[p]["wins"] += 1

                # Update history
                history["matches"].append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "1v1",
                    "players": selected,
                    "winner": winner
                })

                save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record 1v1 match for {game_name}")
                save_history_to_git(game_name, history, commit_message=f"Add 1v1 match to {game_name} history")
                st.success("1v1 game recorded successfully!")
            except Exception as e:
                st.error(f"Failed to record 1v1 game: {e}")

# ------------------- Team -------------------
elif game_type == "Team":
    st.header("Team-based Game Recording")
    selected_players = st.multiselect("Select players", options=players, key="team_players")
    if selected_players:
        manual_team_btn = st.button("Set Manual Teams", key="team_manual")
        auto_team_btn = st.button("Auto Balance Teams", key="team_auto")
        team_a, team_b = [], []

        if manual_team_btn:
            team_a = st.multiselect("Team A players", options=selected_players, key="manual_team_a")
            team_b = [p for p in selected_players if p not in team_a]
            st.write("Team B:", ", ".join(team_b) if team_b else "(empty)")
        elif auto_team_btn:
            sorted_players = sorted(selected_players,
                                    key=lambda p: leaderboard.get(p, {}).get("mu", env.mu),
                                    reverse=True)
            team_a = sorted_players[::2]
            team_b = sorted_players[1::2]
            st.write("Auto-balanced Teams:")
            st.write("Team A:", ", ".join(team_a))
            st.write("Team B:", ", ".join(team_b))

        if team_a and team_b:
            winner = st.radio("Winner", options=["Team A", "Team B"], key="team_winner")
            if st.button("Record Team Game", key="team_record"):
                try:
                    ratings_a = [trueskill.Rating(**leaderboard[p]) for p in team_a]
                    ratings_b = [trueskill.Rating(**leaderboard[p]) for p in team_b]
                    ranks = [0,1] if winner == "Team A" else [1,0]
                    new_ratings = env.rate([ratings_a, ratings_b], ranks=ranks)

                    for p, r in zip(team_a, new_ratings[0]):
                        leaderboard[p]["mu"] = r.mu
                        leaderboard[p]["sigma"] = r.sigma
                        if winner == "Team A":
                            leaderboard[p]["wins"] += 1
                    for p, r in zip(team_b, new_ratings[1]):
                        leaderboard[p]["mu"] = r.mu
                        leaderboard[p]["sigma"] = r.sigma
                        if winner == "Team B":
                            leaderboard[p]["wins"] += 1

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

# ------------------- Free For All -------------------
elif game_type == "Free For All":
    st.header("Free For All Match Recording")
    selected_players_ffa = st.multiselect("Select players", options=players, key="ffa_players")
    if selected_players_ffa:
        st.write("Select finishing order:")
        finishing_order = []
        remaining = selected_players_ffa.copy()
        for i in range(len(selected_players_ffa)):
            pick = st.selectbox(f"Next finisher ({i+1})", options=remaining, key=f"ffa_{i}")
            finishing_order.append(pick)
            remaining.remove(pick)
        if st.button("Record FFA Game", key="ffa_record"):
            try:
                # Prepare ratings in finishing order
                rating_groups = [[trueskill.Rating(**leaderboard[p])] for p in finishing_order]
                ranks = list(range(len(rating_groups)))  # first = 0, etc.
                new_ratings = env.rate(rating_groups, ranks=ranks)

                for p, r in zip(finishing_order, new_ratings):
                    leaderboard[p]["mu"] = r.mu
                    leaderboard[p]["sigma"] = r.sigma
                    leaderboard[p]["wins"] += 1 if p == finishing_order[0] else 0

                history["matches"].append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "ffa",
                    "players": finishing_order
                })

                save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record FFA match for {game_name}")
                save_history_to_git(game_name, history, commit_message=f"Add FFA match to {game_name} history")
                st.success("FFA game recorded successfully!")
            except Exception as e:
                st.error(f"Failed to record FFA game: {e}")
