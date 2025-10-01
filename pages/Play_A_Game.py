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
if not isinstance(leaderboard, dict):
    leaderboard = {}

history = load_history_from_git(game_name)
if not isinstance(history, dict):
    history = {"matches": []}
history.setdefault("matches", [])

if not players:
    st.warning("No global players found. Add players first in Player Manager.")
    st.stop()

# ---- Tabs for game type ----
game_type = st.radio("Select game type", options=["Team-based", "1v1", "Free-for-All"])

# ---------------- Team-based recording ----------------
if game_type == "Team-based":
    st.header("Team-based Game Recording")
    selected_players = st.multiselect("Select players", options=players)

    if selected_players:
        manual_team_btn = st.button("Set Manual Teams")
        auto_team_btn = st.button("Auto Balance Teams")

        team_a, team_b = [], []
        if manual_team_btn:
            team_a = st.multiselect("Team A players", options=selected_players)
            team_b = [p for p in selected_players if p not in team_a]
            st.write("Team B:", ", ".join(team_b) if team_b else "(empty)")
        elif auto_team_btn:
            def get_mu(p):
                rating = leaderboard.get(p, {"mu": env.mu})
                return rating.get("mu", env.mu)
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
                    ratings_a = [env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma, "wins": 0}))
                                 for p in team_a]
                    ratings_b = [env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma, "wins": 0}))
                                 for p in team_b]

                    ranks = [0, 1] if winner == "Team A" else [1, 0]
                    new_ratings = env.rate([ratings_a, ratings_b], ranks=ranks)

                    # Update leaderboard
                    for name, r in zip(team_a, new_ratings[0]):
                        leaderboard.setdefault(name, {"wins": 0})
                        leaderboard[name].update({"mu": r.mu, "sigma": r.sigma})
                    for name, r in zip(team_b, new_ratings[1]):
                        leaderboard.setdefault(name, {"wins": 0})
                        leaderboard[name].update({"mu": r.mu, "sigma": r.sigma})

                    # Increment wins
                    winning_team = team_a if winner == "Team A" else team_b
                    for p in winning_team:
                        leaderboard[p]["wins"] = leaderboard.get(p, {}).get("wins", 0) + 1

                    # Append to history
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

# ---------------- 1v1 recording ----------------
elif game_type == "1v1":
    st.header("1v1 Game Recording")
    if len(players) < 2:
        st.warning("At least 2 players are required for a 1v1 match.")
    else:
        selected_1v1_players = st.multiselect("Select two players", options=players)
        if len(selected_1v1_players) == 2:
            winner = st.radio("Select the winner", options=selected_1v1_players)
            if st.button("Record 1v1 Game"):
                try:
                    p1, p2 = selected_1v1_players
                    leaderboard.setdefault(p1, {"mu": env.mu, "sigma": env.sigma, "wins": 0})
                    leaderboard.setdefault(p2, {"mu": env.mu, "sigma": env.sigma, "wins": 0})

                    r1 = env.Rating(**leaderboard[p1])
                    r2 = env.Rating(**leaderboard[p2])
                    ranks = [0, 1] if winner == p1 else [1, 0]

                    new_ratings = env.rate([[r1], [r2]], ranks=ranks)

                    leaderboard[p1].update({"mu": new_ratings[0][0].mu, "sigma": new_ratings[0][0].sigma})
                    leaderboard[p2].update({"mu": new_ratings[1][0].mu, "sigma": new_ratings[1][0].sigma})
                    leaderboard[winner]["wins"] += 1

                    history["matches"].append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "type": "1v1",
                        "players": selected_1v1_players,
                        "winner": winner
                    })

                    save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record 1v1 match for {game_name}")
                    save_history_to_git(game_name, history, commit_message=f"Add 1v1 match to {game_name} history")

                    st.success("1v1 game recorded successfully!")

                except Exception as e:
                    st.error(f"Failed to record 1v1 game: {e}")
        else:
            st.info("Select exactly two players to record a 1v1 match.")

# ---------------- Free-for-All recording ----------------
elif game_type == "Free-for-All":
    st.header("Free-for-All Game Recording")
    selected_ffa_players = st.multiselect("Select players", options=players)
    if selected_ffa_players:
        ranks = []
        rank_inputs = {}
        for p in selected_ffa_players:
            rank_inputs[p] = st.number_input(f"Rank for {p} (1 = best)", min_value=1, max_value=len(selected_ffa_players), value=len(selected_ffa_players))
        if st.button("Record FFA Game"):
            try:
                # Ensure leaderboard entries
                ratings_list = []
                for p in selected_ffa_players:
                    leaderboard.setdefault(p, {"mu": env.mu, "sigma": env.sigma, "wins": 0})
                    ratings_list.append([env.Rating(**leaderboard[p])])

                # Convert rank_inputs to list of ranks in the same order
                rank_order = [rank_inputs[p] for p in selected_ffa_players]

                new_ratings = env.rate(ratings_list, ranks=rank_order)

                for p, r_group in zip(selected_ffa_players, new_ratings):
                    leaderboard[p].update({"mu": r_group[0].mu, "sigma": r_group[0].sigma})
                    leaderboard[p]["wins"] += 1  # FFA win = survived/participated

                # Append to history
                history["matches"].append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "ffa",
                    "players": selected_ffa_players,
                    "ranks": rank_order
                })

                save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record FFA match for {game_name}")
                save_history_to_git(game_name, history, commit_message=f"Add FFA match to {game_name} history")

                st.success("FFA game recorded successfully!")

            except Exception as e:
                st.error(f"Failed to record FFA game: {e}")
    else:
        st.info("Select at least one player for FFA match.")
