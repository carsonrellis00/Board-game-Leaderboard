import streamlit as st
from GitLab_Persistence import (
    load_players_from_git,
    save_leaderboard_to_git,
    load_leaderboard_from_git,
    save_history_to_git,
    load_history_from_git,
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

# --- Game selection or new game ---
new_game_name = st.text_input("Or enter a new game name")
selected_game = st.selectbox("Select a game", all_games) if all_games else ""
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
game_type = st.radio("Select game type", ["1v1", "Team", "Free-for-All"])

# --- 1v1 ---
if game_type == "1v1":
    st.subheader("1v1 Match")
    p1, p2 = st.selectbox("Player 1", players, key="1v1p1"), st.selectbox("Player 2", players, key="1v1p2")
    
    winner = st.radio("Winner", [p1, p2], key="1v1winner")
    
    if st.button("Record 1v1 Game"):
        try:
            # Ensure players exist in leaderboard
            for p in [p1, p2]:
                if p not in leaderboard or not isinstance(leaderboard[p], dict):
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

            # Update history
            history_entry = {"type": "1v1", "players": [p1, p2], "winner": winner}
            history.setdefault("matches", []).append(history_entry)
            save_history_to_git(selected_game, history)

            st.success("1v1 game recorded.")
        except Exception as e:
            st.error(f"Failed to record 1v1 game: {e}")

# --- Team ---
elif game_type == "Team":
    st.subheader("Team Match")
    selected_players = st.multiselect("Select players for this match", players, key="teamplayers")
    team_assignment = st.radio("Team assignment method", ["Auto-Balance", "Manual"], key="teammethod")

    team1, team2 = [], []
    if team_assignment == "Auto-Balance" and selected_players:
        # Sort by mu descending
        sorted_players = sorted(
            selected_players,
            key=lambda p: leaderboard.get(p, {"mu": env.mu}).get("mu", env.mu),
            reverse=True
        )
        mid = len(sorted_players) // 2
        team1, team2 = sorted_players[:mid], sorted_players[mid:]
        st.info(f"Team 1: {team1}")
        st.info(f"Team 2: {team2}")
    elif team_assignment == "Manual" and selected_players:
        team1 = st.multiselect("Select Team 1", selected_players, key="manual_team1")
        team2 = [p for p in selected_players if p not in team1]
        st.info(f"Team 1: {team1}")
        st.info(f"Team 2: {team2}")

    winner_team = st.radio("Winning team", ["Team 1", "Team 2"], key="teamwinner")

    if st.button("Record Team Game"):
        try:
            if len(selected_players) < 2:
                st.error("Select at least 2 players")
            else:
                # Ensure all players exist in leaderboard
                for p in selected_players:
                    if p not in leaderboard or not isinstance(leaderboard[p], dict):
                        leaderboard[p] = {"mu": env.mu, "sigma": env.sigma, "wins": 0}

                team1_ratings = [env.create_rating(leaderboard[p]["mu"], leaderboard[p]["sigma"]) for p in team1]
                team2_ratings = [env.create_rating(leaderboard[p]["mu"], leaderboard[p]["sigma"]) for p in team2]

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

                history_entry = {"type": "team", "team1": team1, "team2": team2, "winner": winner_team}
                history.setdefault("matches", []).append(history_entry)
                save_history_to_git(selected_game, history)

                st.success("Team game recorded.")
        except Exception as e:
            st.error(f"Failed to record team game: {e}")

# --- Free-for-All ---
elif game_type == "Free-for-All":
    st.subheader("Free-for-All Match")
    finishing_order = []
    ffa_positions = {}
    for idx, p in enumerate(players):
        ffa_positions[p] = st.number_input(f"Finishing position for {p} (1=winner, higher=last)", min_value=1, max_value=len(players), value=idx+1, key=f"ffa_{p}")

    if st.button("Record FFA Game"):
        try:
            # Order players by finishing positions
            finishing_order = [p for p, pos in sorted(ffa_positions.items(), key=lambda x: x[1])]
            # Ensure all players exist
            for p in finishing_order:
                if p not in leaderboard or not isinstance(leaderboard[p], dict):
                    leaderboard[p] = {"mu": env.mu, "sigma": env.sigma, "wins": 0}

            ratings = [env.create_rating(leaderboard[p]["mu"], leaderboard[p]["sigma"]) for p in finishing_order]
            ranked_ratings = [[r] for r in ratings]
            rated = env.rate(ranked_ratings, ranks=list(range(len(finishing_order))))

            for idx, p in enumerate(finishing_order):
                leaderboard[p]["mu"], leaderboard[p]["sigma"] = rated[idx][0].mu, rated[idx][0].sigma
                if idx == 0:
                    leaderboard[p]["wins"] += 1  # only winner increments wins

            save_leaderboard_to_git(selected_game, leaderboard)

            history_entry = {"type": "ffa", "players": finishing_order, "winner": finishing_order[0]}
            history.setdefault("matches", []).append(history_entry)
            save_history_to_git(selected_game, history)

            st.success("Free-for-All game recorded.")
        except Exception as e:
            st.error(f"Failed to record FFA game: {e}")
