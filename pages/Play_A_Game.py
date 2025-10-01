# pages/Play_A_Game.py
import streamlit as st
from GitLab_Persistence import (
    load_players_from_git,
    save_leaderboard_to_git,
    load_leaderboard_from_git,
    load_history_from_git,
    save_history_to_git,
    gitlab_list_leaderboards_dir
)
import trueskill
from datetime import datetime

st.set_page_config(page_title="✏️ Record Game / Matchmaking", page_icon="✏️")
st.title("✏️ Record Game & Matchmaking")

env = trueskill.TrueSkill(draw_probability=0)

# --- Load players and games ---
players = load_players_from_git()
files = gitlab_list_leaderboards_dir()
game_names = sorted(list({fn.replace("_leaderboard.json", "").replace("_history.json", "") 
                          for fn in files if fn.endswith("_leaderboard.json") or fn.endswith("_history.json")}))

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

# --- Load leaderboard and history (auto-create if missing) ---
leaderboard = load_leaderboard_from_git(game_name) or {}
history = load_history_from_git(game_name) or {"matches": []}

if not players:
    st.warning("No global players found. Add players first in Player Manager.")
    st.stop()

# --- Match recording ---
selected_players = st.multiselect("Select players", options=players)
if selected_players:
    st.write("Selected Players:", ", ".join(selected_players))
    
    winner = st.radio("Winner", options=["Team A", "Team B"])
    
    if st.button("Record Team Game"):
        try:
            # Ratings
            ratings = {p: env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma})) 
                       for p in selected_players}

            # Simple split
            mid = len(selected_players) // 2
            team_a = selected_players[:mid]
            team_b = selected_players[mid:]

            ranks = [0,1] if winner == "Team A" else [1,0]
            new_ratings = env.rate([[ratings[p] for p in team_a],
                                    [ratings[p] for p in team_b]], ranks=ranks)

            # Update leaderboard
            for name, r in zip(team_a, new_ratings[0]):
                leaderboard[name] = {"mu": r.mu, "sigma": r.sigma}
            for name, r in zip(team_b, new_ratings[1]):
                leaderboard[name] = {"mu": r.mu, "sigma": r.sigma}

            # Update history
            history.setdefault("matches", []).append({
                "timestamp": datetime.utcnow().isoformat(),
                "type": "team",
                "team_a": team_a,
                "team_b": team_b,
                "winner": winner
            })

            # Push to GitLab (auto-create files if missing)
            save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record match for {game_name}")
            save_history_to_git(game_name, history, commit_message=f"Update match history for {game_name}")

            st.success("Team game recorded successfully!")

        except Exception as e:
            st.error(f"Failed to record game: {e}")
