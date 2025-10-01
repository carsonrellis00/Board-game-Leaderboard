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

game_option = st.selectbox("Select game (or type new)", options=["<New Game>"] + game_names, key="game_select")
if game_option == "<New Game>":
    game_name_input = st.text_input("New game name", key="new_game_name")
    game_name = game_name_input.strip() if game_name_input else None
else:
    game_name = game_option

if not game_name:
    st.info("Pick or type a game name to record matches for.")
    st.stop()

st.subheader(f"Recording for game: {game_name}")

# ---- Load leaderboard and history ----
leaderboard = load_leaderboard_from_git(game_name) or {}
history = load_history_from_git(game_name) or {}
if not players:
    st.warning("No global players found. Add players first in Player Manager.")
    st.stop()

# ---- Tabs for game types ----
game_type = st.radio("Game Type", ["1v1", "Team", "Free-for-All"], key="game_type_radio")

# ---- 1v1 Game ----
if game_type == "1v1":
    selected_players_1v1 = st.multiselect("Select 2 players", options=players, key="1v1_players")
    if len(selected_players_1v1) == 2:
        winner_1v1 = st.radio("Winner", options=selected_players_1v1, key="1v1_winner")
        if st.button("Record 1v1 Game", key="record_1v1"):
            try:
                ratings = {p: env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma})) 
                           for p in selected_players_1v1}
                ranks = [0,1] if winner_1v1 == selected_players_1v1[0] else [1,0]
                new_ratings = env.rate([[ratings[selected_players_1v1[0]]],
                                        [ratings[selected_players_1v1[1]]]], ranks=ranks)

                for i, p in enumerate(selected_players_1v1):
                    leaderboard[p] = {"mu": new_ratings[i][0].mu, "sigma": new_ratings[i][0].sigma,
                                      "wins": leaderboard.get(p, {}).get("wins", 0) + (1 if winner_1v1 == p else 0)}

                history.setdefault("matches", []).append({
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

# ---- Team Game ----
elif game_type == "Team":
    selected_players_team = st.multiselect("Select players", options=players, key="team_players")
    if selected_players_team:
        manual_team_btn = st.button("Set Manual Teams", key="manual_team_btn")
        auto_team_btn = st.button("Auto Balance Teams", key="auto_team_btn")

        team_a, team_b = [], []
        if manual_team_btn:
            team_a = st.multiselect("Team A players", options=selected_players_team, key="manual_team_a")
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
            winner = st.radio("Winner", options=["Team A", "Team B"], key="team_winner")
            if st.button("Record Team Game", key="record_team"):
                try:
                    ratings_a = [env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma})) for p in team_a]
                    ratings_b = [env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma})) for p in team_b]

                    ranks = [0,1] if winner == "Team A" else [1,0]
                    new_ratings = env.rate([ratings_a, ratings_b], ranks=ranks)

                    for name, r in zip(team_a, new_ratings[0]):
                        leaderboard[name] = {"mu": r.mu, "sigma": r.sigma,
                                             "wins": leaderboard.get(name, {}).get("wins", 0) + (1 if winner=="Team A" else 0)}
                    for name, r in zip(team_b, new_ratings[1]):
                        leaderboard[name] = {"mu": r.mu, "sigma": r.sigma,
                                             "wins": leaderboard.get(name, {}).get("wins", 0) + (1 if winner=="Team B" else 0)}

                    history.setdefault("matches", []).append({
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
    if selected_players_ffa:
        finishing_order = []
        remaining = selected_players_ffa.copy()
        while remaining:
            pick = st.selectbox(f"Next finisher ({len(finishing_order)+1})", options=remaining, key=f"ffa_{len(finishing_order)}")
            finishing_order.append(pick)
            remaining.remove(pick)

        if len(finishing_order) == len(selected_players_ffa):
            if st.button("Record FFA Game", key="record_ffa"):
                try:
                    ratings_list = [env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma})) for p in finishing_order]
                    new_ratings = env.rate([[r] for r in ratings_list], ranks=list(range(len(finishing_order))))
                    for p, r in zip(finishing_order, new_ratings):
                        leaderboard[p] = {"mu": r[0].mu, "sigma": r[0].sigma,
                                          "wins": leaderboard.get(p, {}).get("wins", 0) + (1 if finishing_order[0]==p else 0)}

                    history.setdefault("matches", []).append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "type": "ffa",
                        "players": finishing_order
                    })

                    save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record FFA match for {game_name}")
                    save_history_to_git(game_name, history, commit_message=f"Add FFA match to {game_name} history")

                    st.success("FFA game recorded successfully!")

                except Exception as e:
                    st.error(f"Failed to record FFA game: {e}")
