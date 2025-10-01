import streamlit as st
import pandas as pd
import sys
import os
from GitLab_Persistence import (
    load_players_from_git,
    load_leaderboard_from_git,
    load_history_from_git,
    save_leaderboard_to_git,   # ← add this
    gitlab_list_leaderboards_dir
)


# --- Root path setup ---
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

st.set_page_config(page_title="Leaderboard", page_icon="🏆")
st.title("🏆 Leaderboards")

# --- Load games ---
try:
    game_files = gitlab_list_leaderboards_dir()
    all_games = [f.replace("_leaderboard.json", "") for f in game_files if f.endswith("_leaderboard.json")]
except Exception as e:
    st.error(f"Failed to load games: {e}")
    all_games = []

if not all_games:
    st.info("No games found. Record a match first to create a game.")
    st.stop()

selected_game = st.selectbox("Select a game", all_games)

# --- Load leaderboard ---
leaderboard = load_leaderboard_from_git(selected_game) or {}

# --- Display leaderboard ---
rows = []
for player, stats in leaderboard.items():
    mu = stats.get("mu", 25.0) if isinstance(stats, dict) else 25.0
    sigma = stats.get("sigma", 8.333) if isinstance(stats, dict) else 8.333
    wins = stats.get("wins", 0) if isinstance(stats, dict) else 0
    rows.append({"Player": player, "Skill": f"{mu:.2f} ± {sigma:.2f}", "Wins": wins})

df = pd.DataFrame(rows)

if not df.empty:
    df = df.sort_values(by="Skill", ascending=False).reset_index(drop=True)
    df.index += 1
    df.index.name = "Rank"
    st.dataframe(df[["Player", "Skill", "Wins"]], use_container_width=True, hide_index=False)
else:
    st.info(f"No players yet for {selected_game}. Record a game to start tracking stats!")
# ---------------- Admin Reset Feature ----------------
st.markdown("---")
st.subheader("⚠️ Admin Tools")

admin_code = st.text_input("Enter admin code to unlock reset tools", type="password")

if admin_code == os.getenv("ADMIN_CODE", "letmein"):  # Replace with a secure method later
    if st.button(f"🔄 Reset Stats for {selected_game}"):
        for player in leaderboard:
            leaderboard[player]["mu"] = 25.0
            leaderboard[player]["sigma"] = 8.333
            leaderboard[player]["wins"] = 0
        save_leaderboard_to_git(selected_game, leaderboard, commit_message=f"Reset stats for {selected_game}")
        st.success(f"{selected_game} stats reset to default!")


