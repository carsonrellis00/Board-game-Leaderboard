# pages/Leaderboard.py
import streamlit as st
import pandas as pd
from GitLab_Persistence import (
    load_leaderboard_from_git,
    save_leaderboard_to_git,
    gitlab_list_leaderboards_dir
)

st.set_page_config(page_title="Leaderboard", page_icon="🏆")
st.title("🏆 Leaderboards")

# --- Load all games from GitLab ---
try:
    files = gitlab_list_leaderboards_dir()
    game_names = sorted([f.replace("_leaderboard.json", "") for f in files])
    st.write("Debug: Games fetched from GitLab:", game_names)
except Exception as e:
    st.error(f"Failed to load games: {e}")
    game_names = []

if not game_names:
    st.info("No games found. Add a game by recording a match first.")
    st.stop()

# --- Game selection ---
selected_game = st.selectbox("Select game", game_names)

# --- Load leaderboard ---
try:
    leaderboard = load_leaderboard_from_git(selected_game)
except Exception:
    leaderboard = {}

# --- Convert leaderboard to DataFrame ---
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

# --- Admin Wipe Feature ---
st.markdown("---")
st.subheader("⚠️ Admin Tools")
admin_code = st.text_input("Enter admin code to unlock reset tools", type="password")

if admin_code == st.secrets.get("ADMIN_CODE", "letmein"):  # Use Streamlit secrets for security
    if st.button(f"🔄 Wipe Leaderboard for {selected_game}"):
        save_leaderboard_to_git(selected_game, {})
        st.success(f"{selected_game} leaderboard wiped.")
