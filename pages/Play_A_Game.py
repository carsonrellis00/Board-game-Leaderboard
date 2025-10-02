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

st.title("🎲 Play a Game")

# --- Load players ---
players_dict = load_players_from_git()
players = players_dict.get("players", [])

if not players:
    st.warning("No players available. Add players in the Player Manager first.")
    st.stop()

# --- Load games ---
try:
    game_files = gitlab_list_leaderboards_dir()
    all_games = [f.replace("_leaderboard.json", "") for f in game_files if f.endswith("_leaderboard.json")]
except Exception as e:
    st.error(f"Failed to load games: {e}")
    all_games = []

# Option to enter a new game or pick existing
new_game_name = st.text_input("Or enter a new game name")
selected_game = st.selectbox("Select a game", all_games, key="existing_game") if all_games else ""
if new_game_name.strip():
    selected_game = new_game_name.strip()

if not selected_game:
    st.stop()

# --- Load leaderboard and history ---
leaderboard = load_leaderboard_from_git(selected_game)
history = load_history_from_git(selected_game)

# --- TrueSkill environment ---
env = trueskill.TrueSkill(draw_probability=0.0)

# --- Game type selection ---
st.subheader("Game Type")
game_type = st.radio("Select game type", ["1v1", "Team", "Free-for-All"], key="game_type")

# --- 1v1 ---
if game_type == "1v1":
    st.subheader("1v1 Match")
    p1, p2 = st.selectbox("Player 1", players, key="p1"), st.selectbox("Player 2", players, key="p2")
    winner = st.radio("Winner", [p1, p2], key="1v1_winner")
    if st.button("Record 1v1 Game", key="record_1v1"):
        try:
            for p in [p1, p2]:
                if p not in leaderboard:
                    leaderboard[p] = {"mu": env.mu, "sigma": env.sigma, "wins": 0}
            r1 = env.create_rating(leaderboard[p1]["mu"], leaderboard[p1]["sigma"])
            r2 = env.create_rating(leaderboard[p2]["mu"], leaderboard[p2]["sigma"])
            if winner == p1:
                rated1, rated2 = env.rate([r1], [r2])
            else:
                rated2, rated1 = env.rate([r2], [r1])
            leaderboard[p1]["mu"], leaderboard[p1]["sigma"] = rated1[0].mu, rated1[0].sigma
            leaderboard[p2]["mu"], leaderboard[p2]["sigma"] = rated2[0].mu, rated2[0].sigma
            leaderboard[winner]["wins"] += 1
            save_leaderboard_to_git(selected_game, leaderboard)

            history_entry = {
                "type": "1v1",
                "players": [p1, p2],
                "winner": winner
            }
            history.setdefault("matches", []).append(history_entry)
            save_history_to_git(selected_game, history)
            st.success("1v1 game recorded.")
        except Exception as e:
            st.error(f"Failed to record 1v1 game: {e}")

# --- Team ---
elif game_type == "Team":
    st.subheader("Team Match")
    selected_players = st.multiselect("Select players for this match", players, key="team_players")
    team_assignment = st.radio("Team assignment method", ["Auto-Balance", "Manual"], key="team_method")
    winner_team = st.radio("Winning team", ["Team 1", "Team 2"], key="team_winner")

    if st.button("Record Team Game", key="record_team"):
        if len(selected_players) < 2:
            st.error("Select at least 2 players")
        else:
            for p in selected_players:
                if p not in leaderboard:
                    leaderboard[p] = {"mu": env.mu, "sigma": env.sigma, "wins": 0}
            try:
                if team_assignment == "Auto-Balance":
                    sorted_players = sorted(
                        selected_players,
                        key=lambda p: leaderboard.get(p, {}).get("mu", env.mu),
                        reverse=True
                    )
                    mid = len(sorted_players) // 2
                    team1, team2 = sorted_players[:mid], sorted_players[mid:]
                else:
                    team1 = st.multiselect("Select Team 1", selected_players, key="manual_team1")
                    team2 = [p for p in selected_players if p not in team1]

                team1_ratings = [env.create_rating(leaderboard[p]["mu"], leaderboard[p]["sigma"]) for p in team1]
                team2_ratings = [env.create_rating(leaderboard[p]["mu"], leaderboard[p]["sigma"]) for p in team2]

                if len(team1_ratings) == 0 or len(team2_ratings) == 0:
                    st.error("Each team must have at least one player")
                else:
                    if winner_team == "Team 1":
                        rated1, rated2 = env.rate(team1_ratings, team2_ratings)
                    else:
                        rated2, rated1 = env.rate(team2_ratings, team1_ratings)

                    for idx, p in enumerate(team1):
                        leaderboard[p]["mu"], leaderboard[p]["sigma"] = rated1[idx].mu, rated1[idx].sigma
                        if winner_team == "Team 1":
                            leaderboard[p]["wins"] += 1
                    for idx, p in enumerate(team2):
                        leaderboard[p]["mu"], leaderboard[p]["sigma"] = rated2[idx].mu, rated2[idx].sigma
                        if winner_team == "Team 2":
                            leaderboard[p]["wins"] += 1

                    save_leaderboard_to_git(selected_game, leaderboard)

                    history_entry = {
                        "type": "team",
                        "team1": team1,
                        "team2": team2,
                        "winner": winner_team
                    }
                    history.setdefault("matches", []).append(history_entry)
                    save_history_to_git(selected_game, history)
                    st.success("Team game recorded.")
            except Exception as e:
                st.error(f"Failed to record team game: {e}")

# --- Free-for-All ---
elif game_type == "Free-for-All":
    st.subheader("Free-for-All Match")
    finishing_order = []
    remaining_players = players.copy()
    for i in range(len(players)):
        pick = st.selectbox(f"Next finisher ({i+1})", remaining_players, key=f"ffa_pick_{i}")
        if st.button("Confirm selection", key=f"ffa_confirm_{i}"):
            finishing_order.append(pick)
            remaining_players.remove(pick)
            st.experimental_rerun()  # refresh so remaining updates

    winner = finishing_order[0] if finishing_order else None
    if st.button("Record FFA Game", key="record_ffa") and finishing_order:
        try:
            for p in finishing_order:
                if p not in leaderboard:
                    leaderboard[p] = {"mu": env.mu, "sigma": env.sigma, "wins": 0}

            ranked_ratings = [[env.create_rating(leaderboard[p]["mu"], leaderboard[p]["sigma"])] for p in finishing_order]
            if len(ranked_ratings) > 1:
                rated = env.rate(ranked_ratings, ranks=list(range(len(finishing_order))))
                for idx, p in enumerate(finishing_order):
                    leaderboard[p]["mu"], leaderboard[p]["sigma"] = rated[idx][0].mu, rated[idx][0].sigma
                    if idx == 0:
                        leaderboard[p]["wins"] += 1
            else:
                st.warning("FFA requires at least 2 players to rate")

            save_leaderboard_to_git(selected_game, leaderboard)

            history_entry = {
                "type": "ffa",
                "players": finishing_order,
                "winner": winner
            }
            history.setdefault("matches", []).append(history_entry)
            save_history_to_git(selected_game, history)
            st.success("Free-for-All game recorded.")
        except Exception as e:
            st.error(f"Failed to record FFA game: {e}")
