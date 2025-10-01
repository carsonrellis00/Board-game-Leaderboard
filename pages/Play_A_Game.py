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
players_dict = load_players_from_git()
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
leaderboard = load_leaderboard_from_git(game_name)
history = load_history_from_git(game_name)
if not players:
    st.warning("No global players found. Add players first in Player Manager.")
    st.stop()

# ---- Game type selection ----
game_type = st.radio("Select match type", ["1v1", "Free-for-All", "Team"])

# ---- 1v1 match ----
if game_type == "1v1":
    p1, p2 = st.multiselect("Select two players", options=players, default=players[:2])
    if len([p1, p2]) < 2:
        st.warning("Select exactly two players.")
        st.stop()
    winner = st.radio("Winner", options=[p1, p2])
    if st.button("Record 1v1 Game"):
        try:
            r1 = env.Rating(mu=leaderboard.get(p1, {}).get("mu", env.mu),
                            sigma=leaderboard.get(p1, {}).get("sigma", env.sigma))
            r2 = env.Rating(mu=leaderboard.get(p2, {}).get("mu", env.mu),
                            sigma=leaderboard.get(p2, {}).get("sigma", env.sigma))
            ranks = [0, 1] if winner == p1 else [1, 0]
            new_ratings = env.rate([[r1], [r2]], ranks=ranks)
            leaderboard[p1] = {"mu": new_ratings[0][0].mu,
                               "sigma": new_ratings[0][0].sigma,
                               "wins": leaderboard.get(p1, {}).get("wins", 0) + (1 if winner == p1 else 0)}
            leaderboard[p2] = {"mu": new_ratings[1][0].mu,
                               "sigma": new_ratings[1][0].sigma,
                               "wins": leaderboard.get(p2, {}).get("wins", 0) + (1 if winner == p2 else 0)}

            # Update history
            history.setdefault("matches", []).append({
                "timestamp": datetime.utcnow().isoformat(),
                "type": "1v1",
                "players": [p1, p2],
                "winner": winner
            })

            save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record 1v1 match for {game_name}")
            save_history_to_git(game_name, history, commit_message=f"Add 1v1 match to {game_name} history")
            st.success("1v1 game recorded successfully!")
        except Exception as e:
            st.error(f"Failed to record 1v1 game: {e}")

# ---- Free-for-All match ----
elif game_type == "Free-for-All":
    selected_players = st.multiselect("Select players", options=players)
    if len(selected_players) < 2:
        st.warning("Select at least 2 players for Free-for-All.")
        st.stop()
    ranks_input = st.text_area("Enter finishing order (top player first), comma separated", 
                               value=", ".join(selected_players))
    if st.button("Record FFA Game"):
        try:
            finishing_order = [p.strip() for p in ranks_input.split(",") if p.strip() in selected_players]
            ratings = [[env.Rating(mu=leaderboard.get(p, {}).get("mu", env.mu),
                                   sigma=leaderboard.get(p, {}).get("sigma", env.sigma))] 
                       for p in finishing_order]
            ranks = list(range(len(finishing_order)))
            new_ratings = env.rate(ratings, ranks=ranks)

            for p, r in zip(finishing_order, new_ratings):
                leaderboard[p] = {"mu": r[0].mu,
                                   "sigma": r[0].sigma,
                                   "wins": leaderboard.get(p, {}).get("wins", 0) + (1 if finishing_order.index(p) == 0 else 0)}

            history.setdefault("matches", []).append({
                "timestamp": datetime.utcnow().isoformat(),
                "type": "ffa",
                "players": finishing_order,
                "winner": finishing_order[0]
            })

            save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record FFA match for {game_name}")
            save_history_to_git(game_name, history, commit_message=f"Add FFA match to {game_name} history")
            st.success("Free-for-All game recorded successfully!")
        except Exception as e:
            st.error(f"Failed to record FFA game: {e}")

# ---- Team-based match ----
elif game_type == "Team":
    selected_players = st.multiselect("Select players", options=players)
    if len(selected_players) < 2:
        st.warning("Select at least 2 players for team-based games.")
        st.stop()

    # Manual or auto teams
    manual_team_btn = st.button("Set Manual Teams")
    auto_team_btn = st.button("Auto Balance Teams")
    team_a, team_b = [], []

    if manual_team_btn:
        team_a = st.multiselect("Team A players", options=selected_players)
        team_b = [p for p in selected_players if p not in team_a]
        st.write("Team B:", ", ".join(team_b) if team_b else "(empty)")
    elif auto_team_btn:
        sorted_players = sorted(selected_players, key=lambda p: leaderboard.get(p, {}).get("mu", env.mu), reverse=True)
        team_a = sorted_players[::2]
        team_b = sorted_players[1::2]
        st.write("Auto-balanced Teams:")
        st.write("Team A:", ", ".join(team_a))
        st.write("Team B:", ", ".join(team_b))

    if team_a and team_b:
        winner = st.radio("Winner", options=["Team A", "Team B"])
        if st.button("Record Team Game"):
            try:
                ratings_a = [env.Rating(mu=leaderboard.get(p, {}).get("mu", env.mu),
                                        sigma=leaderboard.get(p, {}).get("sigma", env.sigma)) for p in team_a]
                ratings_b = [env.Rating(mu=leaderboard.get(p, {}).get("mu", env.mu),
                                        sigma=leaderboard.get(p, {}).get("sigma", env.sigma)) for p in team_b]
                ranks = [0,1] if winner == "Team A" else [1,0]
                new_ratings = env.rate([ratings_a, ratings_b], ranks=ranks)

                for p, r in zip(team_a, new_ratings[0]):
                    leaderboard[p] = {"mu": r.mu,
                                      "sigma": r.sigma,
                                      "wins": leaderboard.get(p, {}).get("wins", 0) + (1 if winner=="Team A" else 0)}
                for p, r in zip(team_b, new_ratings[1]):
                    leaderboard[p] = {"mu": r.mu,
                                      "sigma": r.sigma,
                                      "wins": leaderboard.get(p, {}).get("wins", 0) + (1 if winner=="Team B" else 0)}

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
