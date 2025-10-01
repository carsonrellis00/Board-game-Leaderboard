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

# ---- Game selection ----
game_option = st.selectbox("Select game (or type new)", options=["<New Game>"] + game_names, key="select_game")
if game_option == "<New Game>":
    game_name_input = st.text_input("New game name", key="new_game_input")
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

# ---- Game type selection ----
game_type = st.radio("Select game type", ["1v1", "Team", "Free-for-All"], key="game_type")

# ---- 1v1 Game ----
if game_type == "1v1":
    selected_players = st.multiselect("Select two players", options=players, key="1v1_players")
    if len(selected_players) != 2:
        st.info("Select exactly 2 players for 1v1.")
    else:
        winner = st.radio("Select winner", options=selected_players, key="1v1_winner")
        if st.button("Record 1v1 Game", key="record_1v1"):
            try:
                ratings = {}
                for p in selected_players:
                    r = leaderboard.get(p)
                    ratings[p] = env.Rating(**r) if r else env.Rating()
                ranks = [0, 1] if winner == selected_players[0] else [1, 0]
                new_ratings = env.rate([[ratings[selected_players[0]]], [ratings[selected_players[1]]]], ranks=ranks)
                leaderboard[selected_players[0]] = {"mu": new_ratings[0][0].mu, "sigma": new_ratings[0][0].sigma, "wins": leaderboard.get(selected_players[0], {}).get("wins", 0) + (1 if winner == selected_players[0] else 0)}
                leaderboard[selected_players[1]] = {"mu": new_ratings[1][0].mu, "sigma": new_ratings[1][0].sigma, "wins": leaderboard.get(selected_players[1], {}).get("wins", 0) + (1 if winner == selected_players[1] else 0)}
                history["matches"].append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "1v1",
                    "players": selected_players,
                    "winner": winner
                })
                save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record 1v1 match for {game_name}")
                save_history_to_git(game_name, history, commit_message=f"Add 1v1 match to {game_name} history")
                st.success("1v1 game recorded successfully!")
            except Exception as e:
                st.error(f"Failed to record 1v1 game: {e}")

# ---- Team Game ----
elif game_type == "Team":
    selected_players = st.multiselect("Select players", options=players, key="team_players")
    if len(selected_players) < 2:
        st.info("Select at least 2 players for a team game.")
    else:
        manual_team_btn, auto_team_btn = st.columns(2)
        team_a, team_b = [], []
        if manual_team_btn.button("Set Manual Teams", key="manual_team_btn"):
            team_a = st.multiselect("Team A players", options=selected_players, key="team_a_manual")
            team_b = [p for p in selected_players if p not in team_a]
            st.write("Team B:", ", ".join(team_b) if team_b else "(empty)")
        elif auto_team_btn.button("Auto Balance Teams", key="auto_team_btn"):
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
            if st.button("Record Team Game", key="record_team"):
                try:
                    ratings_a = [env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma})) for p in team_a]
                    ratings_b = [env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma})) for p in team_b]
                    ranks = [0, 1] if winner == "Team A" else [1, 0]
                    new_ratings = env.rate([ratings_a, ratings_b], ranks=ranks)
                    for name, r in zip(team_a, new_ratings[0]):
                        leaderboard[name] = {"mu": r.mu, "sigma": r.sigma, "wins": leaderboard.get(name, {}).get("wins", 0) + (1 if winner == "Team A" else 0)}
                    for name, r in zip(team_b, new_ratings[1]):
                        leaderboard[name] = {"mu": r.mu, "sigma": r.sigma, "wins": leaderboard.get(name, {}).get("wins", 0) + (1 if winner == "Team B" else 0)}
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

# ---- Free-for-All ----
elif game_type == "Free-for-All":
    selected_players_ffa = st.multiselect("Select players", options=players, key="ffa_players")
    if len(selected_players_ffa) < 2:
        st.info("Select at least 2 players for FFA.")
    else:
        finishing_order = []
        remaining = selected_players_ffa.copy()
        for i in range(len(selected_players_ffa)):
            pick = st.selectbox(f"Next finisher ({i+1})", options=remaining, key=f"ffa_select_{i}")
            finishing_order.append(pick)
            remaining.remove(pick)
        if st.button("Record FFA Game", key="record_ffa"):
            try:
                rating_list = [env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma})) for p in finishing_order]
                new_ratings = env.rate([[r] for r in rating_list], ranks=list(range(len(rating_list))))
                for p, r in zip(finishing_order, new_ratings):
                    leaderboard[p] = {"mu": r[0].mu, "sigma": r[0].sigma, "wins": leaderboard.get(p, {}).get("wins", 0) + (1 if p == finishing_order[0] else 0)}
                history["matches"].append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "ffa",
                    "order": finishing_order
                })
                save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record FFA match for {game_name}")
                save_history_to_git(game_name, history, commit_message=f"Add FFA match to {game_name} history")
                st.success("FFA game recorded successfully!")
            except Exception as e:
                st.error(f"Failed to record FFA game: {e}")
