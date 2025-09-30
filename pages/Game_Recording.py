import streamlit as st
import trueskill
from datetime import datetime
from GitLab_Persistence import (
    load_players_from_git,
    save_players_to_git,
    load_leaderboard_from_git,
    save_leaderboard_to_git,
    load_history_from_git,
    save_history_to_git,
    env
)

st.set_page_config(page_title="Record Game", page_icon="✏️")
st.title("✏️ Record a Game (Individual & Team)")

# --- Select game ---
# Gather games from leaderboards directory
all_players = load_players_from_git()
if not all_players:
    st.warning("No players found. Add players first in Manage Players.")
    st.stop()

# Extract game names from existing leaderboards
files = [fn.replace("_leaderboard.json", "").replace("_history.json", "") 
         for fn in st.session_state.get("leaderboard_files", [])] \
         if "leaderboard_files" in st.session_state else []

game_names = sorted(list({fn for fn in files}))
game_option = st.selectbox("Select game (or type new)", options=["<New Game>"] + game_names)

if game_option == "<New Game>":
    game_name_input = st.text_input("New game name")
    game_name = game_name_input.strip() if game_name_input else None
else:
    game_name = game_option

if not game_name:
    st.info("Enter or select a game name to record matches.")
    st.stop()

# Load leaderboard and history
leaderboard = load_leaderboard_from_git(game_name)
history = load_history_from_git(game_name)

# --- Select mode ---
mode = st.radio("Select mode", options=["Individual", "Team"])

# --- Individual Game ---
if mode == "Individual":
    ordered_players = st.multiselect(
        "Select players in finishing order (winner first)", options=all_players
    )
    if st.button("Record Individual Game"):
        if len(ordered_players) < 2:
            st.warning("Select at least two players.")
        else:
            try:
                ratings = []
                for name in ordered_players:
                    p = leaderboard.get(name)
                    ratings.append(env.Rating(mu=p["mu"], sigma=p["sigma"]) if p else env.Rating())
                ranks = list(range(len(ratings)))
                new_ratings = env.rate(ratings, ranks=ranks)
                # Update leaderboard
                for name, r in zip(ordered_players, new_ratings):
                    leaderboard[name] = {"mu": r.mu, "sigma": r.sigma}
                # Append to history
                history.setdefault("matches", []).append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "individual",
                    "results": ordered_players
                })
                save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record individual match for {game_name}")
                save_history_to_git(game_name, history, commit_message=f"Add individual match to {game_name} history")
                st.success("Individual game recorded and pushed to GitLab.")
            except Exception as e:
                st.error(f"Failed to record game: {e}")

# --- Team Game ---
else:
    selected_players = st.multiselect("Select players for team match", options=all_players)
    if len(selected_players) < 2:
        st.info("Select at least two players for team mode.")
        st.stop()

    # Option to auto-generate balanced teams
    auto_balance = st.checkbox("Auto-generate balanced teams")
    if auto_balance:
        # Generate best balanced split
        from itertools import combinations
        import math

        def team_average_rating(team):
            ratings = [leaderboard.get(n, {}).get("mu", env.Rating().mu) for n in team]
            return sum(ratings)/len(ratings)

        best_diff = math.inf
        best_pair = None
        n = len(selected_players)
        half = n//2
        for combo in combinations(selected_players, half):
            team_a = combo
            team_b = tuple(p for p in selected_players if p not in team_a)
            diff = abs(team_average_rating(team_a) - team_average_rating(team_b))
            if diff < best_diff:
                best_diff = diff
                best_pair = (team_a, team_b)
        team_a, team_b = best_pair
    else:
        team_a = st.multiselect("Select Team A", options=selected_players)
        team_b = [p for p in selected_players if p not in team_a]

    st.subheader("Team A")
    st.write(", ".join(team_a))
    st.subheader("Team B")
    st.write(", ".join(team_b))

    winner = st.radio("Select winning team", options=["Team A", "Team B"])

    if st.button("Record Team Game"):
        if not team_a or not team_b:
            st.warning("Both teams must have at least one player.")
        else:
            try:
                ratings_a = [env.Rating(**leaderboard.get(n, {})) for n in team_a]
                ratings_b = [env.Rating(**leaderboard.get(n, {})) for n in team_b]
                ranks = [0,1] if winner=="Team A" else [1,0]
                new_team_ratings = env.rate([ratings_a, ratings_b], ranks=ranks)
                for name, r in zip(team_a, new_team_ratings[0]):
                    leaderboard[name] = {"mu": r.mu, "sigma": r.sigma}
                for name, r in zip(team_b, new_team_ratings[1]):
                    leaderboard[name] = {"mu": r.mu, "sigma": r.sigma}
                # Append to history
                history.setdefault("matches", []).append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "team",
                    "team_a": list(team_a),
                    "team_b": list(team_b),
                    "winner": winner
                })
                save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record team match for {game_name}")
                save_history_to_git(game_name, history, commit_message=f"Add team match to {game_name} history")
                st.success("Team game recorded and pushed to GitLab.")
            except Exception as e:
                st.error(f"Failed to record team game: {e}")
