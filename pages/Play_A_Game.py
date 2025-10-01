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

# --- Load players ---
players_dict = load_players_from_git()
players = players_dict.get("players", [])
if not players:
    st.warning("No players found. Add players in the Player Manager first.")
    st.stop()

# --- Load games ---
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

# --- Load leaderboard & history ---
leaderboard = load_leaderboard_from_git(game_name) or {}
history = load_history_from_git(game_name)
if not isinstance(history, dict):
    history = {"matches": []}
history.setdefault("matches", [])

# --- Select match type ---
match_type = st.radio("Select match type", options=["1v1", "Team", "Free-for-All (FFA)"])

# --- 1v1 Match Recording ---
if match_type == "1v1":
    st.header("1v1 Match")
    p1, p2 = st.selectbox("Player 1", options=players), st.selectbox("Player 2", options=players)
    winner = st.radio("Winner", options=[p1, p2])
    if st.button("Record 1v1 Game"):
        try:
            ratings = {p: env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma})) for p in [p1, p2]}
            ranks = [0, 1] if winner == p1 else [1, 0]
            new_ratings = env.rate([[ratings[p1]], [ratings[p2]]], ranks=ranks)
            leaderboard[p1] = {"mu": new_ratings[0][0].mu, "sigma": new_ratings[0][0].sigma,
                               "wins": leaderboard.get(p1, {}).get("wins", 0) + (1 if winner == p1 else 0)}
            leaderboard[p2] = {"mu": new_ratings[1][0].mu, "sigma": new_ratings[1][0].sigma,
                               "wins": leaderboard.get(p2, {}).get("wins", 0) + (1 if winner == p2 else 0)}
            history["matches"].append({
                "timestamp": datetime.utcnow().isoformat(),
                "type": "1v1",
                "players": [p1, p2],
                "winner": winner
            })
            save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record 1v1 match for {game_name}")
            save_history_to_git(game_name, history, commit_message=f"Add 1v1 match to {game_name} history")
            st.success("1v1 match recorded successfully!")
        except Exception as e:
            st.error(f"Failed to record 1v1 game: {e}")

# --- Team Match Recording ---
elif match_type == "Team":
    st.header("Team Match")
    selected_players = st.multiselect("Select players", options=players)
    if selected_players and len(selected_players) > 1:
        team_a, team_b = [], []
        if st.button("Set Manual Teams"):
            team_a = st.multiselect("Team A players", options=selected_players)
            team_b = [p for p in selected_players if p not in team_a]
            st.write("Team B:", ", ".join(team_b) if team_b else "(empty)")
        elif st.button("Auto Balance Teams"):
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
                    ratings_a = [env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma})) for p in team_a]
                    ratings_b = [env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma})) for p in team_b]
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

# --- Free-for-All Match Recording ---
elif match_type == "Free-for-All (FFA)":
    st.header("Free-for-All Match")
    selected_players = st.multiselect("Select players", options=players)
    ranks_dict = {p: i+1 for i, p in enumerate(selected_players)}  # default rank order
    ranks_input = st.text_area("Enter ranks (player:rank) per line, optional", 
                               value="\n".join(f"{p}:{i+1}" for i, p in enumerate(selected_players)))
    if st.button("Record FFA Game") and selected_players:
        try:
            # parse ranks input if provided
            ranks_dict = {}
            for line in ranks_input.splitlines():
                if ":" in line:
                    p, r = line.split(":")
                    ranks_dict[p.strip()] = int(r.strip())
            sorted_players_by_rank = sorted(selected_players, key=lambda p: ranks_dict.get(p, 1))
            ratings_list = [env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma})) for p in sorted_players_by_rank]
            # Each player as its own group
            new_ratings = env.rate([[r] for r in ratings_list], ranks=list(range(len(ratings_list))))
            for p, r in zip(sorted_players_by_rank, [r[0] for r in new_ratings]):
                wins_add = 1 if ranks_dict[p] == 1 else 0
                leaderboard[p] = {"mu": r.mu, "sigma": r.sigma,
                                  "wins": leaderboard.get(p, {}).get("wins", 0) + wins_add}
            history["matches"].append({
                "timestamp": datetime.utcnow().isoformat(),
                "type": "ffa",
                "players": selected_players,
                "ranks": [ranks_dict.get(p, 1) for p in selected_players]
            })
            save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record FFA match for {game_name}")
            save_history_to_git(game_name, history, commit_message=f"Add FFA match to {game_name} history")
            st.success("FFA game recorded successfully!")
        except Exception as e:
            st.error(f"Failed to record FFA game: {e}")
