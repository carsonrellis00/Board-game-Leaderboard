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

# ---- Helper to ensure valid player ratings ----
def get_player_rating(player_name, leaderboard, env):
    stats = leaderboard.get(player_name)
    if isinstance(stats, dict):
        mu = stats.get("mu", env.mu)
        sigma = stats.get("sigma", env.sigma)
        wins = stats.get("wins", 0)
    else:
        mu = env.mu
        sigma = env.sigma
        wins = 0
    return {"mu": mu, "sigma": sigma, "wins": wins}

# ---- Load players and games ----
players_dict = load_players_from_git() or {"players": []}
players = players_dict.get("players", [])

files = gitlab_list_leaderboards_dir()
game_names = sorted([fn.replace("_leaderboard.json", "") for fn in files if fn.endswith("_leaderboard.json")])

# ---- Select or create game ----
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

# ---- Match type selection ----
match_type = st.selectbox("Match type", ["1v1", "Team", "Free-for-All"])

# ---- 1v1 recording ----
if match_type == "1v1":
    p1, p2 = st.selectbox("Player 1", players), st.selectbox("Player 2", players)
    winner = st.radio("Winner", [p1, p2])
    if st.button("Record 1v1 Game"):
        try:
            r1 = env.Rating(**get_player_rating(p1, leaderboard, env))
            r2 = env.Rating(**get_player_rating(p2, leaderboard, env))
            ranks = [0, 1] if winner == p1 else [1, 0]
            r_new = env.rate([[r1], [r2]], ranks=ranks)

            leaderboard[p1] = {"mu": r_new[0][0].mu, "sigma": r_new[0][0].sigma,
                               "wins": get_player_rating(p1, leaderboard, env)["wins"] + (1 if winner == p1 else 0)}
            leaderboard[p2] = {"mu": r_new[1][0].mu, "sigma": r_new[1][0].sigma,
                               "wins": get_player_rating(p2, leaderboard, env)["wins"] + (1 if winner == p2 else 0)}

            history["matches"].append({
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

# ---- Team-based recording ----
elif match_type == "Team":
    selected_players = st.multiselect("Select players", players)
    if selected_players and len(selected_players) >= 2:
        manual_team_btn = st.button("Manual Teams")
        auto_team_btn = st.button("Auto Balance Teams")

        team_a, team_b = [], []
        if manual_team_btn:
            team_a = st.multiselect("Team A players", selected_players)
            team_b = [p for p in selected_players if p not in team_a]
            st.write("Team B:", ", ".join(team_b) if team_b else "(empty)")
        elif auto_team_btn:
            sorted_players = sorted(selected_players,
                                    key=lambda p: get_player_rating(p, leaderboard, env)["mu"],
                                    reverse=True)
            team_a = sorted_players[::2]
            team_b = sorted_players[1::2]
            st.write("Auto-balanced Teams:")
            st.write("Team A:", ", ".join(team_a))
            st.write("Team B:", ", ".join(team_b))

        if team_a and team_b:
            winner = st.radio("Winner", ["Team A", "Team B"])
            if st.button("Record Team Game"):
                try:
                    ratings_a = [env.Rating(**get_player_rating(p, leaderboard, env)) for p in team_a]
                    ratings_b = [env.Rating(**get_player_rating(p, leaderboard, env)) for p in team_b]
                    ranks = [0, 1] if winner == "Team A" else [1, 0]
                    new_ratings = env.rate([ratings_a, ratings_b], ranks=ranks)

                    for name, r in zip(team_a, new_ratings[0]):
                        prev_wins = get_player_rating(name, leaderboard, env)["wins"]
                        leaderboard[name] = {"mu": r.mu, "sigma": r.sigma, "wins": prev_wins + (1 if winner=="Team A" else 0)}
                    for name, r in zip(team_b, new_ratings[1]):
                        prev_wins = get_player_rating(name, leaderboard, env)["wins"]
                        leaderboard[name] = {"mu": r.mu, "sigma": r.sigma, "wins": prev_wins + (1 if winner=="Team B" else 0)}

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

# ---- Free-for-All recording ----
elif match_type == "Free-for-All":
    selected_players = st.multiselect("Select players", players)
    finishing_order = []

    if selected_players:
        st.info("Select finishing order for each player")
        for i in range(len(selected_players)):
            remaining = [p for p in selected_players if p not in finishing_order]
            pick = st.selectbox(f"Next finisher ({i+1})", options=remaining, key=f"ffa{i}")
            if pick and pick not in finishing_order:
                finishing_order.append(pick)

        if len(finishing_order) == len(selected_players) and st.button("Record FFA Game"):
            try:
                ratings_list = [[env.Rating(**get_player_rating(p, leaderboard, env))] for p in finishing_order]
                ranks = list(range(len(finishing_order)))  # 0=winner, 1=second, etc.
                new_ratings = env.rate(ratings_list, ranks=ranks)

                for p, r in zip(finishing_order, new_ratings):
                    prev = get_player_rating(p, leaderboard, env)
                    leaderboard[p] = {"mu": r[0].mu, "sigma": r[0].sigma, "wins": prev["wins"] + (1 if p==finishing_order[0] else 0)}

                history["matches"].append({
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
