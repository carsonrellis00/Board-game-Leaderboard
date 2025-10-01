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
players_data = load_players_from_git()
players = players_data.get("players", []) if isinstance(players_data, dict) else []
if not players:
    st.warning("No players found. Add players first in Player Manager.")
    st.stop()

files = gitlab_list_leaderboards_dir()
game_names = sorted(list({fn.replace("_leaderboard.json", "").replace("_history.json", "") 
                          for fn in files if fn.endswith(".json")}))

# ---- Game selection ----
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

# ---- Load leaderboard and history (or create new if doesn't exist) ----
leaderboard = load_leaderboard_from_git(game_name) or {}
history = load_history_from_git(game_name)
if "matches" not in history:
    history["matches"] = []

# ---- Game type selection ----
game_type = st.radio("Select game type", ["Team", "1v1", "Free-for-All"])

# ---- Player selection ----
num_min_players = {"Team": 2, "1v1": 2, "Free-for-All": 2}[game_type]
selected_players = st.multiselect(f"Select players ({num_min_players}+)", options=players)

if len(selected_players) < num_min_players:
    st.info(f"Select at least {num_min_players} players for {game_type} games.")
    st.stop()

# ---- Team game logic ----
if game_type == "Team":
    team_option = st.radio("Team setup", ["Manual Teams", "Auto Balance"])
    team_a, team_b = [], []

    if team_option == "Manual Teams":
        team_a = st.multiselect("Team A players", options=selected_players)
        team_b = [p for p in selected_players if p not in team_a]
        st.write("Team B:", ", ".join(team_b) if team_b else "(empty)")
    else:
        # Auto balance based on mu
        def get_mu(p):
            rating = leaderboard.get(p, {"mu": env.mu})
            return rating.get("mu", env.mu)
        sorted_players = sorted(selected_players, key=get_mu, reverse=True)
        team_a = sorted_players[::2]
        team_b = sorted_players[1::2]
        st.write("Auto-balanced Teams:")
        st.write("Team A:", ", ".join(team_a))
        st.write("Team B:", ", ".join(team_b))

    if not team_a or not team_b:
        st.warning("Both teams must have at least one player.")
        st.stop()

    winner = st.radio("Winner", options=["Team A", "Team B"])
    if st.button("Record Team Game"):
        try:
            ratings_a = [env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma})) for p in team_a]
            ratings_b = [env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma})) for p in team_b]
            ranks = [0, 1] if winner == "Team A" else [1, 0]
            new_ratings = env.rate([ratings_a, ratings_b], ranks=ranks)
            # Update leaderboard & wins
            for name, r in zip(team_a, new_ratings[0]):
                leaderboard[name] = {"mu": r.mu, "sigma": r.sigma, "wins": leaderboard.get(name, {}).get("wins", 0)}
                if winner == "Team A":
                    leaderboard[name]["wins"] += 1
            for name, r in zip(team_b, new_ratings[1]):
                leaderboard[name] = {"mu": r.mu, "sigma": r.sigma, "wins": leaderboard.get(name, {}).get("wins", 0)}
                if winner == "Team B":
                    leaderboard[name]["wins"] += 1
            # Update history
            history["matches"].append({
                "timestamp": datetime.utcnow().isoformat(),
                "type": "team",
                "team_a": team_a,
                "team_b": team_b,
                "winner": winner
            })
            # Push to GitLab
            save_leaderboard_to_git(game_name, leaderboard)
            save_history_to_git(game_name, history)
            st.success("Team game recorded successfully!")
        except Exception as e:
            st.error(f"Failed to record game: {e}")

# ---- 1v1 logic ----
elif game_type == "1v1":
    if len(selected_players) != 2:
        st.info("Select exactly 2 players for 1v1.")
        st.stop()
    player1, player2 = selected_players
    winner = st.radio("Winner", options=[player1, player2])
    if st.button("Record 1v1 Game"):
        try:
            ratings = [env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma})) for p in selected_players]
            ranks = [0, 1] if winner == player1 else [1, 0]
            new_ratings = env.rate([ratings], ranks=ranks)
            for p, r in zip(selected_players, new_ratings[0]):
                leaderboard[p] = {"mu": r.mu, "sigma": r.sigma, "wins": leaderboard.get(p, {}).get("wins", 0)}
                if p == winner:
                    leaderboard[p]["wins"] += 1
            # Update history
            history["matches"].append({
                "timestamp": datetime.utcnow().isoformat(),
                "type": "1v1",
                "players": selected_players,
                "winner": winner
            })
            save_leaderboard_to_git(game_name, leaderboard)
            save_history_to_git(game_name, history)
            st.success("1v1 game recorded successfully!")
        except Exception as e:
            st.error(f"Failed to record game: {e}")

# ---- Free-for-All logic ----
elif game_type == "Free-for-All":
    winner = st.selectbox("Select winner", options=selected_players)
    if st.button("Record Free-for-All Game"):
        try:
            ratings = [env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma})) for p in selected_players]
            ranks = [0 if p == winner else 1 for p in selected_players]
            new_ratings = env.rate([ratings], ranks=ranks)
            for p, r in zip(selected_players, new_ratings[0]):
                leaderboard[p] = {"mu": r.mu, "sigma": r.sigma, "wins": leaderboard.get(p, {}).get("wins", 0)}
                if p == winner:
                    leaderboard[p]["wins"] += 1
            history["matches"].append({
                "timestamp": datetime.utcnow().isoformat(),
                "type": "ffa",
                "players": selected_players,
                "winner": winner
            })
            save_leaderboard_to_git(game_name, leaderboard)
            save_history_to_git(game_name, history)
            st.success("Free-for-All game recorded successfully!")
        except Exception as e:
            st.error(f"Failed to record game: {e}")
