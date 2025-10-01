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
players = players_dict.get("players", []) if isinstance(players_dict, dict) else []

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

# ---- Load leaderboard and history safely ----
leaderboard = load_leaderboard_from_git(game_name)
if not isinstance(leaderboard, dict):
    leaderboard = {}

history = load_history_from_git(game_name)
if not isinstance(history, dict):
    history = {"matches": []}

if not players:
    st.warning("No global players found. Add players first in Player Manager.")
    st.stop()

# ---- Match type selection ----
match_type = st.radio("Match Type", ["1v1", "Team", "Free-for-All"])

# ---- 1v1 Game Recording ----
if match_type == "1v1":
    selected_players = st.multiselect("Select 2 players", options=players)
    if len(selected_players) != 2:
        st.info("Select exactly 2 players for 1v1.")
        st.stop()

    winner = st.radio("Select Winner", options=selected_players)
    if st.button("Record 1v1 Game"):
        try:
            p1, p2 = selected_players
            r1 = env.Rating(**leaderboard.get(p1, {"mu": env.mu, "sigma": env.sigma}))
            r2 = env.Rating(**leaderboard.get(p2, {"mu": env.mu, "sigma": env.sigma}))
            ranks = [0, 1] if winner == p1 else [1, 0]
            new_ratings = env.rate([[r1], [r2]], ranks=ranks)

            leaderboard[p1] = {"mu": new_ratings[0][0].mu, "sigma": new_ratings[0][0].sigma,
                               "wins": leaderboard.get(p1, {}).get("wins", 0) + (1 if winner == p1 else 0)}
            leaderboard[p2] = {"mu": new_ratings[1][0].mu, "sigma": new_ratings[1][0].sigma,
                               "wins": leaderboard.get(p2, {}).get("wins", 0) + (1 if winner == p2 else 0)}

            # Update history
            history.setdefault("matches", []).append({
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

# ---- Team Game Recording ----
elif match_type == "Team":
    selected_players = st.multiselect("Select players", options=players)
    if len(selected_players) < 2:
        st.info("Select at least 2 players for team game.")
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
        def get_mu(p):
            return leaderboard.get(p, {"mu": env.mu}).get("mu", env.mu)
        sorted_players = sorted(selected_players, key=get_mu, reverse=True)
        team_a = sorted_players[::2]
        team_b = sorted_players[1::2]
        st.write("Auto-balanced Teams:")
        st.write("Team A:", ", ".join(team_a))
        st.write("Team B:", ", ".join(team_b))

    if team_a and team_b:
        winner = st.radio("Winner", options=["Team A", "Team B"])
        if st.button("Record Team Game"):
            try:
                ratings_a = [env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma})) for p in team_a]
                ratings_b = [env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma})) for p in team_b]
                ranks = [0, 1] if winner == "Team A" else [1, 0]
                new_ratings = env.rate([ratings_a, ratings_b], ranks=ranks)

                for name, r in zip(team_a, new_ratings[0]):
                    wins = leaderboard.get(name, {}).get("wins", 0) + (1 if winner == "Team A" else 0)
                    leaderboard[name] = {"mu": r.mu, "sigma": r.sigma, "wins": wins}
                for name, r in zip(team_b, new_ratings[1]):
                    wins = leaderboard.get(name, {}).get("wins", 0) + (1 if winner == "Team B" else 0)
                    leaderboard[name] = {"mu": r.mu, "sigma": r.sigma, "wins": wins}

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

# ---- Free-for-All Game Recording ----
elif match_type == "Free-for-All":
    selected_players = st.multiselect("Select players", options=players)
    if len(selected_players) < 2:
        st.info("Select at least 2 players for FFA.")
        st.stop()

    if st.button("Record FFA Game"):
        try:
            ratings = [env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma})) for p in selected_players]
            # Sort players by a ranking input
            ranking_input = []
            for p in selected_players:
                rank = st.number_input(f"Rank for {p} (1=best)", min_value=1, max_value=len(selected_players), value=1)
                ranking_input.append((p, rank))
            ranking_input.sort(key=lambda x: x[1])
            ranks = [i for i in range(len(selected_players))]
            new_ratings = env.rate([[r] for r in ratings], ranks=ranks)

            for idx, (p, _) in enumerate(ranking_input):
                leaderboard[p] = {
                    "mu": new_ratings[idx][0].mu,
                    "sigma": new_ratings[idx][0].sigma,
                    "wins": leaderboard.get(p, {}).get("wins", 0) + (1 if idx == 0 else 0)
                }

            history.setdefault("matches", []).append({
                "timestamp": datetime.utcnow().isoformat(),
                "type": "ffa",
                "players": selected_players,
                "ranking": [p for p, _ in ranking_input]
            })

            save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record FFA match for {game_name}")
            save_history_to_git(game_name, history, commit_message=f"Add FFA match to {game_name} history")
            st.success("FFA game recorded successfully!")

        except Exception as e:
            st.error(f"Failed to record FFA game: {e}")
