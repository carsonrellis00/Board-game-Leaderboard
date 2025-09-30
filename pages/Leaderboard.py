# pages/Leaderboard.py
import streamlit as st
import pandas as pd
from GitLab_Persistence import (
    load_leaderboard_from_git,
    save_leaderboard_to_git,
    load_history_from_git,
)
import trueskill
from datetime import datetime

# ---- Config ----
st.set_page_config(page_title="Leaderboard", page_icon="🏆", layout="wide")
st.title("🏆 Board Game Leaderboard")

CURRENT_USER = st.text_input("Enter your name (for highlighting)", value="")

# ---- TrueSkill ----
env = trueskill.TrueSkill(draw_probability=0)

# ---- Select game ----
game_names = sorted([f.replace("_leaderboard.json","") 
                     for f in st.session_state.get("games_list", [])])
game_names = game_names or ["Guards of Atlantis 2","Scythe","Unfair","Wyrmspan"]
game_choice = st.selectbox("Select Game", options=game_names)

# ---- Load leaderboard and history ----
leaderboard = load_leaderboard_from_git(game_choice)
history = load_history_from_git(game_choice)
matches = history.get("matches", [])

# ---- Compute Wins ----
wins_counter = {}
for match in matches:
    if match["type"] == "individual":
        if match["results"]:
            winner = match["results"][0]
            wins_counter[winner] = wins_counter.get(winner, 0) + 1
    elif match["type"] == "team":
        winner_team = match.get("winner")
        winning_players = match.get("team_a") if winner_team=="Team A" else match.get("team_b")
        for p in winning_players:
            wins_counter[p] = wins_counter.get(p, 0) + 1

# ---- Prepare DataFrame ----
data = []
for player, rating in leaderboard.items():
    mu = rating.get("mu", 25.0)
    sigma = rating.get("sigma", 8.333)
    wins = wins_counter.get(player, 0)
    data.append({"Player": player, "Mu": mu, "Sigma": sigma, "Wins": wins})

df = pd.DataFrame(data)
if not df.empty:
    df = df.sort_values(by="Mu", ascending=False).reset_index(drop=True)
    df.insert(0, "Rank", range(1, len(df)+1))

# ---- Admin Wipe Feature ----
ADMIN_NAME = "Carson"  # Only this user can wipe
if CURRENT_USER == ADMIN_NAME:
    st.markdown("---")
    st.subheader("⚠️ Admin Wipe Leaderboard")
    if st.button(f"Wipe leaderboard for {game_choice}"):
        for player in leaderboard:
            leaderboard[player] = {"mu": env.mu, "sigma": env.sigma}
        save_leaderboard_to_git(game_choice, leaderboard, commit_message=f"Admin wiped {game_choice} leaderboard")
        st.success(f"{game_choice} leaderboard wiped.")
        st.experimental_rerun()

# ---- Display leaderboard ----
if not df.empty:
    styled_df = df.style.apply(
        lambda x: ['background-color: #FFFF99' if v == CURRENT_USER else '' for v in x],
        subset=["Player"]
    )
    st.dataframe(styled_df, height=500)
else:
    st.info("No players found for this game yet.")
