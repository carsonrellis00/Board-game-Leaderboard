# pages/Leaderboard.py
import streamlit as st
import pandas as pd
from GitLab_Persistence import (
    load_leaderboard_from_git,
    gitlab_list_leaderboards_dir,
    save_leaderboard_to_git
)
import os

st.set_page_config(page_title="🏆 Leaderboards", page_icon="🏆")
st.title("🏆 Leaderboards")

# ---- Load all games from GitLab ----
try:
    game_files = gitlab_list_leaderboards_dir()
    all_games = sorted([f.replace("_leaderboard.json", "") for f in game_files])
except Exception as e:
    st.error(f"Failed to load games: {e}")
    all_games = []

if not all_games:
    st.info("No games found. Add a game by recording a match first.")
    st.stop()

# ---- Game selection ----
selected_game = st.selectbox("Select a game", all_games)

# ---- Load leaderboard ----
leaderboard = load_leaderboard_from_git(selected_game) or {}

# ---- Convert to DataFrame ----
rows = []
for player, rating in leaderboard.items():
    mu = rating.get("mu", 25.0)
    sigma = rating.get("sigma", 8.333)
    rows.append({
        "Player": player,
        "Rating": f"{mu:.2f} ± {sigma:.2f}",
        "Mu": mu,
        "Sigma": sigma
    })

df = pd.DataFrame(rows)
if not df.empty:
    df = df.sort_values(by="Mu", ascending=False).reset_index(drop=True)
    df.index += 1  # Start rank at 1
    df.index.name = "Rank"
    st.dataframe(df[["Player", "Rating"]], use_container_width=True)
else:
    st.info(f"No players yet for {selected_game}. Record a game to get started!")

# ---- Admin Wipe Feature ----
st.markdown("---")
st.subheader("⚠️ Admin Tools")

admin_code = st.text_input("Enter admin code to unlock reset tools", type="password")
if admin_code == os.getenv("ADMIN_CODE", "letmein"):
    if st.button(f"🔄 Wipe Leaderboard for {selected_game}"):
        save_leaderboard_to_git(selected_game, {})
        st.success(f"{selected_game} leaderboard wiped.")
