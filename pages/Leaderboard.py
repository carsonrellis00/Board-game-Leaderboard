# pages/Leaderboard.py
import streamlit as st
import pandas as pd
import sys
import os

# --- Root path setup ---
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from GitLab_Persistence import (
    load_leaderboard_from_git,
    gitlab_list_leaderboards_dir
)

# --- Streamlit page config ---
st.set_page_config(page_title="Leaderboard", page_icon="🏆")
st.title("🏆 Leaderboards")

# --- Load all games ---
try:
    game_files = gitlab_list_leaderboards_dir()
    all_games = [f.replace("_leaderboard.json", "") for f in game_files if f.endswith("_leaderboard.json")]
except Exception as e:
    st.error(f"Failed to load games: {e}")
    all_games = []

if not all_games:
    st.info("No games found. Record a match first to create a game.")
    st.stop()

# --- Game selection ---
selected_game = st.selectbox("Select a game", all_games)

# --- Load leaderboard ---
try:
    leaderboard = load_leaderboard_from_git(selected_game) or {}
except Exception:
    leaderboard = {}

# --- Convert to DataFrame for display ---
rows = []
for player, stats in leaderboard.items():
    mu = stats.get("mu", 25.0) if isinstance(stats, dict) else 25.0
    sigma = stats.get("sigma", 8.333) if isinstance(stats, dict) else 8.333
    wins = stats.get("wins", 0) if isinstance(stats, dict) else 0
    rows.append({
        "Player": player,
        "Mu": mu,
        "Sigma": sigma,
        "Skill": f"{mu:.2f} ± {sigma:.2f}",
        "Wins": wins
    })

df = pd.DataFrame(rows)

if not df.empty:
    # Sort by Mu descending for ranking
    df = df.sort_values(by="Mu", ascending=False).reset_index(drop=True)
    df.index += 1  # Start rank at 1
    df.index.name = "Rank"
    st.dataframe(df[["Player", "Skill", "Wins"]], use_container_width=True, hide_index=False)
else:
    st.info(f"No players yet for {selected_game}. Record a game to start tracking stats!")
