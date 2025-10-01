# pages/Leaderboard.py
import streamlit as st
import pandas as pd
import sys
import os

# --- Add root folder to Python path ---
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from GitLab_Persistence import (
    load_players_from_git,
    save_players_to_git,
    load_leaderboard_from_git,
    save_leaderboard_to_git,
    load_history_from_git,
    save_history_to_git,
    gitlab_list_leaderboards_dir,
)

# ---------------- Streamlit page config ----------------
st.set_page_config(page_title="Leaderboard", page_icon="🏆")
st.title("🏆 Leaderboards")

# ---------------- Load all games ----------------
try:
    game_files = gitlab_list_leaderboards_dir()
    all_games = [f.replace("_leaderboard.json", "") for f in game_files]
except Exception as e:
    st.error(f"Failed to load games from GitLab: {e}")
    all_games = []

if not all_games:
    st.info("No games found. Add a game by recording a match first.")
    st.stop()

# ---------------- Game selection ----------------
selected_game = st.selectbox("Select a game", all_games)

# ---------------- Load leaderboard ----------------
try:
    leaderboard = load_leaderboard_from_git(selected_game) or {}
except Exception as e:
    st.error(f"Failed to load leaderboard from GitLab: {e}")
    leaderboard = {}

# ---------------- Convert to DataFrame ----------------
rows = []
for player, rating in leaderboard.items():
    mu = rating.get("mu", 25.0) if isinstance(rating, dict) else 25.0
    sigma = rating.get("sigma", 8.333) if isinstance(rating, dict) else 8.333
    wins = rating.get("wins", 0) if isinstance(rating, dict) else 0
    rows.append({
        "Player": player,
        "Mu": round(mu, 2),
        "Sigma": round(sigma, 2),
        "Rating": f"{mu:.2f} ± {sigma:.2f}",
        "Wins": wins,
    })

df = pd.DataFrame(rows)

if not df.empty:
    df = df.sort_values(by="Mu", ascending=False).reset_index(drop=True)
    df.index += 1  # Start rank at 1
    df.index.name = "Rank"
    st.dataframe(df[["Player", "Rating", "Wins"]], use_container_width=True, hide_index=False)
else:
    st.info(f"No players yet for {selected_game}. Record a game to get started!")

# ---------------- Admin Wipe Feature ----------------
st.markdown("---")
st.subheader("⚠️ Admin Tools")

admin_code = st.text_input("Enter admin code to unlock reset tools", type="password")

if admin_code == os.getenv("ADMIN_CODE", "letmein"):  # Replace with a secure method later
    if st.button(f"🔄 Wipe Leaderboard for {selected_game}"):
        save_leaderboard_to_git(selected_game, {})
        st.success(f"{selected_game} leaderboard wiped.")
