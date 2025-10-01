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
leaderboard = load_leaderboard_from_git(game_name) or {}
history = load_history_from_git(game_name) or {"matches": []}

if not players:
    st.warning("No global players found. Add players first in Player Manager.")
    st.stop()

# ---- Tabs for different match types ----
tab_1v1, tab_team, tab_ffa = st.tabs(["1v1", "Team", "Free-for-All"])

# ----------------- 1v1 -----------------
with tab_1v1:
    st.header("1v1 Match")
    selected_players_1v1 = st.multiselect("Select 2 players", options=players)
    if len(selected_players_1v1) == 2:
        winner_1v1 = st.radio("Winner", options=selected_players_1v1)
        if st.button("Record 1v1 Game"):
            try:
                ratings = []
                for p in selected_players_1v1:
                    r = leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma})
                    ratings.append(env.Rating(r["mu"], r["sigma"]))

                ranks = [0, 1] if winner_1v1 == selected_players_1v1[0] else [1, 0]
                new_ratings = env.rate(ratings, ranks=ranks)

                for p, r in zip(selected_players_1v1, new_ratings):
                    leaderboard[p] = {
                        "mu": r.mu,
                        "sigma": r.sigma,
                        "wins": leaderboard.get(p, {}).get("wins", 0)
                    }
                # Increment winner's wins
                leaderboard[winner_1v1]["wins"] = leaderboard[winner_1v1].get("wins", 0) + 1

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

# ----------------- Team -----------------
with tab_team:
    st.header("Team-based Match")
    selected_players_team = st.multiselect("Select players", options=players)
    if selected_players_team:
        team_a_manual = st.multiselect("Team A players (manual)", options=selected_players_team, key="manual_team_a")
        team_b_manual = [p for p in selected_players_team if p not in team_a_manual]

        auto_team_btn = st.button("Auto Balance Teams")
        if auto_team_btn:
            sorted_players = sorted(
                selected_players_team,
                key=lambda p: leaderboard.get(p, {"mu": env.mu}).get("mu", env.mu),
                reverse=True
            )
            team_a_manual = sorted_players[::2]
            team_b_manual = sorted_players[1::2]

        st.write("Team A:", ", ".join(team_a_manual))
        st.write("Team B:", ", ".join(team_b_manual))

        winner_team = st.radio("Winner", options=["Team A", "Team B"])
        if st.button("Record Team Game"):
            try:
                ratings_a = [env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma})) for p in team_a_manual]
                ratings_b = [env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma})) for p in team_b_manual]

                ranks = [0, 1] if winner_team == "Team A" else [1, 0]
                new_ratings = env.rate([ratings_a, ratings_b], ranks=ranks)

                for p, r in zip(team_a_manual, new_ratings[0]):
                    leaderboard[p] = {
                        "mu": r.mu,
                        "sigma": r.sigma,
                        "wins": leaderboard.get(p, {}).get("wins", 0)
                    }
                for p, r in zip(team_b_manual, new_ratings[1]):
                    leaderboard[p] = {
                        "mu": r.mu,
                        "sigma": r.sigma,
                        "wins": leaderboard.get(p, {}).get("wins", 0)
                    }

                # Increment winner's wins
                winning_team = team_a_manual if winner_team == "Team A" else team_b_manual
                for p in winning_team:
                    leaderboard[p]["wins"] += 1

                history.setdefault("matches", []).append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "team",
                    "team_a": team_a_manual,
                    "team_b": team_b_manual,
                    "winner": winner_team
                })

                save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record team match for {game_name}")
                save_history_to_git(game_name, history, commit_message=f"Add team match to {game_name} history")

                st.success("Team game recorded successfully!")
            except Exception as e:
                st.error(f"Failed to record team game: {e}")

# ----------------- Free-for-All -----------------
with tab_ffa:
    st.header("Free-for-All")
    selected_players_ffa = st.multiselect("Select players", options=players)
    if selected_players_ffa:
        positions = {}
        for idx, p in enumerate(selected_players_ffa):
            positions[p] = st.selectbox(f"Position for {p}", options=list(range(1, len(selected_players_ffa)+1)), key=f"ffa_{p}")

        if st.button("Record FFA Game"):
            try:
                # Sort players by finishing position (1 = first)
                sorted_players = sorted(selected_players_ffa, key=lambda p: positions[p])
                ratings = [env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma})) for p in sorted_players]

                # Compute new ratings
                new_ratings = env.rate(ratings, ranks=[positions[p]-1 for p in sorted_players])

                for p, r in zip(sorted_players, new_ratings):
                    leaderboard[p] = {
                        "mu": r.mu,
                        "sigma": r.sigma,
                        "wins": leaderboard.get(p, {}).get("wins", 0)
                    }

                # Increment win for first place
                leaderboard[sorted_players[0]]["wins"] += 1

                history.setdefault("matches", []).append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "ffa",
                    "players": sorted_players,
                    "positions": {p: positions[p] for p in sorted_players},
                    "winner": sorted_players[0]
                })

                save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record FFA match for {game_name}")
                save_history_to_git(game_name, history, commit_message=f"Add FFA match to {game_name} history")

                st.success("Free-for-All game recorded successfully!")
            except Exception as e:
                st.error(f"Failed to record FFA game: {e}")
