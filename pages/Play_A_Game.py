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

# --- Load players and games ---
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

# --- Load leaderboard and history ---
leaderboard = load_leaderboard_from_git(game_name) or {}
history = load_history_from_git(game_name) or {"matches": []}

if not players:
    st.warning("No global players found. Add players first in Player Manager.")
    st.stop()

# --- Select mode ---
mode = st.radio("Game Mode", options=["1v1", "Team", "Free-for-All"])

# ---------------- 1v1 Game ----------------
if mode == "1v1":
    col1, col2 = st.columns(2)
    with col1:
        player_a = st.selectbox("Player A", options=players)
    with col2:
        player_b = st.selectbox("Player B", options=[p for p in players if p != player_a])

    winner = st.radio("Winner", options=[player_a, player_b])

    if st.button("Record 1v1 Game"):
        try:
            ratings = {}
            for p in [player_a, player_b]:
                r = leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma})
                ratings[p] = env.Rating(mu=r["mu"], sigma=r["sigma"])

            ranks = [0, 1] if winner == player_a else [1, 0]
            new_ratings = env.rate([[ratings[player_a]], [ratings[player_b]]], ranks=ranks)

            # Update leaderboard
            leaderboard[player_a] = {"mu": new_ratings[0][0].mu, "sigma": new_ratings[0][0].sigma,
                                     "wins": leaderboard.get(player_a, {}).get("wins", 0) + (1 if winner == player_a else 0)}
            leaderboard[player_b] = {"mu": new_ratings[1][0].mu, "sigma": new_ratings[1][0].sigma,
                                     "wins": leaderboard.get(player_b, {}).get("wins", 0) + (1 if winner == player_b else 0)}

            # Update history
            history["matches"].append({
                "timestamp": datetime.utcnow().isoformat(),
                "type": "1v1",
                "players": [player_a, player_b],
                "winner": winner
            })

            # Push to GitLab
            save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record 1v1 match for {game_name}")
            save_history_to_git(game_name, history, commit_message=f"Add 1v1 match to {game_name} history")

            st.success("1v1 game recorded successfully!")
        except Exception as e:
            st.error(f"Failed to record 1v1 game: {e}")

# ---------------- Team Game ----------------
elif mode == "Team":
    selected_players = st.multiselect("Select players", options=players)
    if selected_players:
        manual_team_btn = st.button("Set Manual Teams")
        auto_team_btn = st.button("Auto Balance Teams")

        team_a, team_b = [], []

        if manual_team_btn:
            team_a = st.multiselect("Team A players", options=selected_players)
            team_b = [p for p in selected_players if p not in team_a]
            st.write("Team A:", ", ".join(team_a))
            st.write("Team B:", ", ".join(team_b))

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
            winner = st.radio("Winner", options=["Team A", "Team B"])
            if st.button("Record Team Game"):
                try:
                    ratings_a = [env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma}))
                                 for p in team_a]
                    ratings_b = [env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma}))
                                 for p in team_b]

                    ranks = [0, 1] if winner == "Team A" else [1, 0]
                    new_ratings = env.rate([ratings_a, ratings_b], ranks=ranks)

                    for name, r in zip(team_a, new_ratings[0]):
                        leaderboard[name] = {"mu": r.mu, "sigma": r.sigma,
                                             "wins": leaderboard.get(name, {}).get("wins", 0) + (1 if winner == "Team A" else 0)}
                    for name, r in zip(team_b, new_ratings[1]):
                        leaderboard[name] = {"mu": r.mu, "sigma": r.sigma,
                                             "wins": leaderboard.get(name, {}).get("wins", 0) + (1 if winner == "Team B" else 0)}

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

# ---------------- Free-for-All ----------------
elif mode == "Free-for-All":
    selected_players = st.multiselect("Select players", options=players)
    if selected_players:
        finishing_order_input = st.text_area(
            "Enter players in finishing order (top to bottom), separated by commas",
            value=", ".join(selected_players)
        )
        finishing_order = [p.strip() for p in finishing_order_input.split(",") if p.strip() in selected_players]

        if st.button("Record FFA Game"):
            try:
                if len(finishing_order) < 2:
                    st.error("FFA requires at least 2 players.")
                else:
                    # Build ratings for all players
                    ratings = [env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma}))
                               for p in finishing_order]
                    # TrueSkill ranking: lower rank means better finish
                    ranks = list(range(len(finishing_order)))
                    new_ratings = env.rate([[r] for r in ratings], ranks=ranks)

                    for p, r in zip(finishing_order, new_ratings):
                        leaderboard[p] = {"mu": r[0].mu, "sigma": r[0].sigma,
                                          "wins": leaderboard.get(p, {}).get("wins", 0) + (1 if ranks.index(0) == finishing_order.index(p) else 0)}

                    history["matches"].append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "type": "ffa",
                        "players": finishing_order
                    })

                    save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record FFA match for {game_name}")
                    save_history_to_git(game_name, history, commit_message=f"Add FFA match to {game_name} history")

                    st.success("Free-for-all game recorded successfully!")

            except Exception as e:
                st.error(f"Failed to record FFA game: {e}")
