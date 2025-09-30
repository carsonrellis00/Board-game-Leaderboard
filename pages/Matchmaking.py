import streamlit as st
import trueskill
from datetime import datetime
from GitLab_Persistence import (
    load_players_from_git,
    load_leaderboard_from_git,
    save_leaderboard_to_git,
    load_history_from_git,
    save_history_to_git,
    env
)

st.set_page_config(page_title="Matchmaking", page_icon="⚔️")
st.title("⚔️ Matchmaking & Team Results")

# --- Select Game ---
all_players = load_players_from_git()
if not all_players:
    st.warning("No players found. Add players first in Manage Players.")
    st.stop()

game_files = st.session_state.get("leaderboard_files", [])
game_names = sorted(list({fn.replace("_leaderboard.json","").replace("_history.json","") 
                          for fn in game_files})) if game_files else []

game_option = st.selectbox("Select game for matchmaking", options=game_names)
if not game_option:
    st.info("Record a game first to initialize the leaderboard.")
    st.stop()

game_name = game_option
leaderboard = load_leaderboard_from_git(game_name) or {}
history = load_history_from_git(game_name) or {"matches": []}

# --- Player Selection ---
selected_players = st.multiselect("Select players to include in matchmaking", options=all_players)
if len(selected_players) < 2:
    st.info("Select at least two players for matchmaking.")
    st.stop()

# --- Generate Balanced Teams ---
if st.button("Generate Balanced Teams"):
    # Fetch ratings
    ratings = []
    for p in selected_players:
        if p in leaderboard:
            ratings.append(env.Rating(mu=leaderboard[p]["mu"], sigma=leaderboard[p]["sigma"]))
        else:
            ratings.append(env.Rating())
    
    # Sort players by skill descending
    sorted_players = [p for _,p in sorted(zip([r.mu for r in ratings], selected_players), reverse=True)]

    # Alternate assigning to two teams for balance
    team_a, team_b = [], []
    for i, player in enumerate(sorted_players):
        if i % 2 == 0:
            team_a.append(player)
        else:
            team_b.append(player)

    st.session_state["team_a"] = team_a
    st.session_state["team_b"] = team_b
    st.success("Balanced teams generated!")

# --- Display Teams ---
team_a = st.session_state.get("team_a", [])
team_b = st.session_state.get("team_b", [])
st.write("**Team A:**", ", ".join(team_a) if team_a else "(empty)")
st.write("**Team B:**", ", ".join(team_b) if team_b else "(empty)")

# --- Select Winner and Record Match ---
if team_a and team_b:
    winner = st.radio("Select the winning team", options=["Team A", "Team B"])
    if st.button("Record Team Match"):
        try:
            # Build TrueSkill ratings
            ratings_a = [env.Rating(**leaderboard.get(p, {})) if p in leaderboard else env.Rating() for p in team_a]
            ratings_b = [env.Rating(**leaderboard.get(p, {})) if p in leaderboard else env.Rating() for p in team_b]

            ranks = [0,1] if winner=="Team A" else [1,0]
            new_team_ratings = env.rate([ratings_a, ratings_b], ranks=ranks)

            # Update leaderboard
            for name, r in zip(team_a, new_team_ratings[0]):
                leaderboard[name] = {"mu": r.mu, "sigma": r.sigma}
            for name, r in zip(team_b, new_team_ratings[1]):
                leaderboard[name] = {"mu": r.mu, "sigma": r.sigma}

            # Update history
            history.setdefault("matches", []).append({
                "timestamp": datetime.utcnow().isoformat(),
                "type": "team",
                "team_a": team_a,
                "team_b": team_b,
                "winner": winner
            })

            # Save to GitLab
            save_leaderboard_to_git(game_name, leaderboard)
            save_history_to_git(game_name, history)

            st.success("Team match recorded and pushed to GitLab!")
            # Clear teams from session
            st.session_state["team_a"] = []
            st.session_state["team_b"] = []

        except Exception as e:
            st.error(f"Failed to record team match: {e}")
