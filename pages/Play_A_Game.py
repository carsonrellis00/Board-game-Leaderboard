import streamlit as st
from datetime import datetime
import trueskill
from GitLab_Persistence import (
    load_players_from_git,
    load_leaderboard_from_git,
    save_leaderboard_to_git,
    load_history_from_git,
    save_history_to_git,
    gitlab_list_leaderboards_dir,
    env
)

st.set_page_config(page_title="Game Recording & Matchmaking", page_icon="🎮")
st.title("🎮 Game Recording & Matchmaking")

# --- Load players ---
all_players = load_players_from_git()
if not all_players:
    st.warning("No players found. Add players first in Player Manager.")
    st.stop()

# --- Load games ---
files = gitlab_list_leaderboards_dir()
game_names = sorted(list({fn.replace("_leaderboard.json","").replace("_history.json","") 
                          for fn in files if fn.endswith(".json")}))
game_option = st.selectbox("Select game (or type new)", options=["<New Game>"] + game_names)
if game_option == "<New Game>":
    game_name_input = st.text_input("New game name")
    game_name = game_name_input.strip() if game_name_input else None
else:
    game_name = game_option

if not game_name:
    st.info("Enter or select a game name to record matches.")
    st.stop()

# --- Load leaderboard and history ---
leaderboard = load_leaderboard_from_git(game_name) or {}
history = load_history_from_git(game_name) or {"matches": []}

# --- Tabs for Individual / Team ---
tab1, tab2 = st.tabs(["Individual Game", "Team Game / Matchmaking"])

# ---------------- Individual Game ----------------
with tab1:
    ordered_players = st.multiselect(
        "Select players in finishing order (winner first)", options=all_players
    )

    if st.button("Record Individual Game"):
        if len(ordered_players) < 2:
            st.warning("Select at least two players.")
        else:
            try:
                ratings = [
                    trueskill.Rating(**leaderboard.get(p, {})) if p in leaderboard else trueskill.Rating()
                    for p in ordered_players
                ]
                ranks = list(range(len(ratings)))
                new_ratings = env.rate(ratings, ranks=ranks)

                for name, r in zip(ordered_players, new_ratings):
                    leaderboard[name] = {"mu": r.mu, "sigma": r.sigma}

                history.setdefault("matches", []).append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "individual",
                    "results": ordered_players
                })

                save_leaderboard_to_git(game_name, leaderboard)
                save_history_to_git(game_name, history)
                st.success("Individual game recorded successfully!")
            except Exception as e:
                st.error(f"Failed to record game: {e}")

# ---------------- Team Game / Matchmaking ----------------
with tab2:
    selected_players = st.multiselect("Select players for team match", options=all_players)
    if len(selected_players) < 2:
        st.info("Select at least two players for team mode.")
        st.stop()

    if st.button("Generate Balanced Teams"):
        # Fetch ratings
        ratings = [trueskill.Rating(**leaderboard.get(p, {})) if p in leaderboard else trueskill.Rating()
                   for p in selected_players]

        # Sort by skill descending
        sorted_players = [p for _, p in sorted(zip([r.mu for r in ratings], selected_players), reverse=True)]

        # Alternate assigning to teams
        team_a, team_b = [], []
        for i, player in enumerate(sorted_players):
            if i % 2 == 0:
                team_a.append(player)
            else:
                team_b.append(player)

        st.session_state["team_a"] = team_a
        st.session_state["team_b"] = team_b
        st.success("Balanced teams generated!")

    # Display teams
    team_a = st.session_state.get("team_a", [])
    team_b = st.session_state.get("team_b", [])
    st.write("**Team A:**", ", ".join(team_a) if team_a else "(empty)")
    st.write("**Team B:**", ", ".join(team_b) if team_b else "(empty)")

    if team_a and team_b:
        winner = st.radio("Select winning team", options=["Team A", "Team B"])
        if st.button("Record Team Match"):
            try:
                ratings_a = [trueskill.Rating(**leaderboard.get(p, {})) if p in leaderboard else trueskill.Rating() for p in team_a]
                ratings_b = [trueskill.Rating(**leaderboard.get(p, {})) if p in leaderboard else trueskill.Rating() for p in team_b]

                ranks = [0,1] if winner=="Team A" else [1,0]
                new_team_ratings = env.rate([ratings_a, ratings_b], ranks=ranks)

                for name, r in zip(team_a, new_team_ratings[0]):
                    leaderboard[name] = {"mu": r.mu, "sigma": r.sigma}
                for name, r in zip(team_b, new_team_ratings[1]):
                    leaderboard[name] = {"mu": r.mu, "sigma": r.sigma}

                history.setdefault("matches", []).append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "team",
                    "team_a": team_a,
                    "team_b": team_b,
                    "winner": winner
                })

                save_leaderboard_to_git(game_name, leaderboard)
                save_history_to_git(game_name, history)

                st.success("Team match recorded successfully!")
                # Clear teams from session
                st.session_state["team_a"] = []
                st.session_state["team_b"] = []

            except Exception as e:
                st.error(f"Failed to record team match: {e}")
