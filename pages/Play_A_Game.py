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

# --- Load leaderboard and history ---
leaderboard = load_leaderboard_from_git(game_name)
history = load_history_from_git(game_name)
if not players:
    st.warning("No players found. Add players first in Player Manager.")
    st.stop()

# --- Match type selection ---
match_type = st.radio("Match Type", ["1v1", "Free-For-All", "Team"])

# --- 1v1 ---
if match_type == "1v1":
    selected_players = st.multiselect("Select 2 players", options=players)
    if len(selected_players) != 2:
        st.info("Select exactly 2 players for 1v1.")
        st.stop()

    winner = st.radio("Winner", options=selected_players)
    if st.button("Record 1v1 Game"):
        try:
            ratings = []
            for p in selected_players:
                r = leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma})
                ratings.append(env.Rating(mu=r["mu"], sigma=r["sigma"]))

            winner_idx = selected_players.index(winner)
            new_ratings = env.rate(ratings, ranks=[0,1] if winner_idx == 0 else [1,0])

            # Update leaderboard
            for p, r in zip(selected_players, new_ratings):
                stats = leaderboard.get(p, {})
                stats["mu"], stats["sigma"] = r.mu, r.sigma
                stats["wins"] = stats.get("wins", 0) + (1 if p == winner else 0)
                leaderboard[p] = stats

            # Update history
            history.setdefault("matches", []).append({
                "timestamp": datetime.utcnow().isoformat(),
                "type": "1v1",
                "players": selected_players,
                "winner": winner
            })

            # Push to GitLab
            save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record 1v1 match for {game_name}")
            save_history_to_git(game_name, history, commit_message=f"Add 1v1 match to {game_name} history")

            st.success("1v1 game recorded successfully!")

        except Exception as e:
            st.error(f"Failed to record 1v1 game: {e}")

# --- Free-For-All ---
elif match_type == "Free-For-All":
    selected_players = st.multiselect("Select players", options=players)
    if len(selected_players) < 2:
        st.info("Select at least 2 players for FFA.")
        st.stop()

    ranks = {}
    for p in selected_players:
        ranks[p] = st.number_input(f"Rank for {p}", min_value=1, max_value=len(selected_players), value=len(selected_players))

    if st.button("Record FFA Game"):
        try:
            # Create a separate group for each player
            rating_groups = []
            for p in selected_players:
                r = leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma})
                rating_groups.append([env.Rating(mu=r["mu"], sigma=r["sigma"])])

            rank_list = [ranks[p] - 1 for p in selected_players]  # zero-based
            new_ratings = trueskill.rate(rating_groups, ranks=rank_list)

            # Update leaderboard
            for p, r in zip(selected_players, new_ratings):
                stats = leaderboard.get(p, {})
                stats["mu"], stats["sigma"] = r[0].mu, r[0].sigma  # r is a list with 1 rating
                stats["wins"] = stats.get("wins", 0) + (1 if rank_list[selected_players.index(p)] == 0 else 0)
                leaderboard[p] = stats

            # Update history
            history.setdefault("matches", []).append({
                "timestamp": datetime.utcnow().isoformat(),
                "type": "ffa",
                "players": selected_players,
                "ranks": rank_list
            })

            save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record FFA match for {game_name}")
            save_history_to_git(game_name, history, commit_message=f"Add FFA match to {game_name} history")
            st.success("Free-for-All game recorded successfully!")

        except Exception as e:
            st.error(f"Failed to record FFA game: {e}")


# --- Team-based ---
elif match_type == "Team":
    selected_players = st.multiselect("Select players", options=players)
    if len(selected_players) < 2:
        st.info("Select at least 2 players for Team game.")
        st.stop()

    # Manual or auto team assignment
    team_mode = st.radio("Team assignment", ["Manual", "Auto"])
    team_a, team_b = [], []

    if team_mode == "Manual":
        team_a = st.multiselect("Team A players", options=selected_players)
        team_b = [p for p in selected_players if p not in team_a]
        st.write("Team B:", ", ".join(team_b) if team_b else "(empty)")
    else:
        sorted_players = sorted(selected_players,
                                key=lambda p: leaderboard.get(p, {"mu": env.mu})["mu"],
                                reverse=True)
        team_a = sorted_players[::2]
        team_b = sorted_players[1::2]
        st.write("Auto-balanced Teams:")
        st.write("Team A:", ", ".join(team_a))
        st.write("Team B:", ", ".join(team_b))

    winner = st.radio("Winner", options=["Team A", "Team B"])
    if st.button("Record Team Game"):
        try:
            ratings_a = [env.Rating(**{k: v for k, v in leaderboard.get(p, {}).items() if k in ("mu","sigma")}) for p in team_a]
            ratings_b = [env.Rating(**{k: v for k, v in leaderboard.get(p, {}).items() if k in ("mu","sigma")}) for p in team_b]

            ranks = [0, 1] if winner == "Team A" else [1, 0]
            new_ratings = env.rate([ratings_a, ratings_b], ranks=ranks)

            for p, r in zip(team_a, new_ratings[0]):
                stats = leaderboard.get(p, {})
                stats["mu"], stats["sigma"] = r.mu, r.sigma
                stats["wins"] = stats.get("wins", 0) + (1 if winner == "Team A" else 0)
                leaderboard[p] = stats
            for p, r in zip(team_b, new_ratings[1]):
                stats = leaderboard.get(p, {})
                stats["mu"], stats["sigma"] = r.mu, r.sigma
                stats["wins"] = stats.get("wins", 0) + (1 if winner == "Team B" else 0)
                leaderboard[p] = stats

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
