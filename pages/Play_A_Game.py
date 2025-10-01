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

# ---- Load players ----
players_dict = load_players_from_git() or {"players": []}
players = players_dict.get("players", [])

if not players:
    st.warning("No global players found. Add players first in Player Manager.")
    st.stop()

# ---- Load existing games ----
files = gitlab_list_leaderboards_dir() or []
game_names = sorted(list({fn.replace("_leaderboard.json", "").replace("_history.json", "")
                          for fn in files if fn.endswith(".json")}))

# ---- Select or create a game ----
game_option = st.selectbox("Select game (or type new)", options=["<New Game>"] + game_names, key="select_game")
if game_option == "<New Game>":
    game_name_input = st.text_input("New game name", key="new_game_name")
    game_name = game_name_input.strip() if game_name_input else None
else:
    game_name = game_option

if not game_name:
    st.info("Pick or type a game name to record matches for.")
    st.stop()

st.subheader(f"Recording for game: {game_name}")

# ---- Load leaderboard and history (initialize if missing) ----
leaderboard = load_leaderboard_from_git(game_name) or {}
history = load_history_from_git(game_name) or {"matches": []}

# Ensure all players in leaderboard are initialized
for p in players:
    if p not in leaderboard:
        leaderboard[p] = {"mu": env.mu, "sigma": env.sigma, "wins": 0}

# ---- Select game type ----
game_type = st.radio("Game Type", options=["Team", "1v1", "Free For All"], index=0)

# -------------------- TEAM GAME --------------------
if game_type == "Team":
    selected_players = st.multiselect("Select players for teams", options=players, key="team_players")
    if selected_players:
        # Manual or auto teams
        manual_team = st.checkbox("Set Manual Teams", key="manual_team")
        auto_team = st.checkbox("Auto Balance Teams", key="auto_team")
        team_a, team_b = [], []

        if manual_team:
            team_a = st.multiselect("Team A", options=selected_players, key="manual_team_a")
            team_b = [p for p in selected_players if p not in team_a]
            st.write("Team B:", ", ".join(team_b) if team_b else "(empty)")
        elif auto_team:
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
            if st.button("Record Team Game", key="record_team_game"):
                try:
                    ratings_a = [env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma})) for p in team_a]
                    ratings_b = [env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma})) for p in team_b]
                    ranks = [0, 1] if winner == "Team A" else [1, 0]
                    new_ratings = env.rate([ratings_a, ratings_b], ranks=ranks)

                    # Update leaderboard
                    for name, r in zip(team_a, new_ratings[0]):
                        leaderboard[name]["mu"] = r.mu
                        leaderboard[name]["sigma"] = r.sigma
                        if winner == "Team A":
                            leaderboard[name]["wins"] += 1
                    for name, r in zip(team_b, new_ratings[1]):
                        leaderboard[name]["mu"] = r.mu
                        leaderboard[name]["sigma"] = r.sigma
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

                    # Save
                    save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record team match for {game_name}")
                    save_history_to_git(game_name, history, commit_message=f"Add team match to {game_name} history")
                    st.success("Team game recorded successfully!")

                except Exception as e:
                    st.error(f"Failed to record game: {e}")

# -------------------- 1v1 GAME --------------------
elif game_type == "1v1":
    p1, p2 = st.selectbox("Player 1", players, key="p1"), st.selectbox("Player 2", players, key="p2")
    winner = st.radio("Winner", options=[p1, p2], key="1v1_winner")
    if st.button("Record 1v1 Game", key="record_1v1_game"):
        try:
            ratings = [env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma})) for p in [p1, p2]]
            ranks = [0, 1] if winner == p1 else [1, 0]
            new_ratings = env.rate(ratings, ranks=ranks)

            for i, p in enumerate([p1, p2]):
                leaderboard[p]["mu"] = new_ratings[i].mu
                leaderboard[p]["sigma"] = new_ratings[i].sigma
                if winner == p:
                    leaderboard[p]["wins"] += 1

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

# -------------------- FREE FOR ALL --------------------
elif game_type == "Free For All":
    selected_players_ffa = st.multiselect("Select players for FFA", options=players, key="ffa_players")
    finishing_order = []
    if selected_players_ffa:
        remaining = selected_players_ffa.copy()
        for i in range(len(selected_players_ffa)):
            pick = st.selectbox(f"Finishing position {i+1}", options=remaining, key=f"ffa_{i}")
            finishing_order.append(pick)
            remaining.remove(pick)

        if len(finishing_order) == len(selected_players_ffa):
            if st.button("Record FFA Game", key="record_ffa_game"):
                try:
                    # Prepare ratings
                    ratings = [env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma})) for p in finishing_order]
                    ranks = list(range(len(ratings)))
                    new_ratings = env.rate(ratings, ranks=ranks)

                    # Update leaderboard
                    for i, p in enumerate(finishing_order):
                        leaderboard[p]["mu"] = new_ratings[i].mu
                        leaderboard[p]["sigma"] = new_ratings[i].sigma
                        if i == 0:  # first place winner
                            leaderboard[p]["wins"] += 1

                    history["matches"].append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "type": "FFA",
                        "players": finishing_order
                    })

                    save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record FFA match for {game_name}")
                    save_history_to_git(game_name, history, commit_message=f"Add FFA match to {game_name} history")
                    st.success("FFA game recorded successfully!")

                except Exception as e:
                    st.error(f"Failed to record FFA game: {e}")
