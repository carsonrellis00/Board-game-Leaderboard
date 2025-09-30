# pages/Leaderboard.py
import streamlit as st
import pandas as pd
from GitLab_Persistence import load_leaderboard_from_git, save_leaderboard_to_git, load_history_from_git
from datetime import datetime

st.set_page_config(page_title="Leaderboard", page_icon="🏆")
st.title("🏆 Leaderboard")

# ---- Select Game ----
files = [f.replace("_leaderboard.json","") for f in st.session_state.get("leaderboard_files", [])]
if not files:
    # Fallback: fetch all games
    files = ["scythe", "unfair", "guards of atlantis 2", "wyrmspan"]  # Example
game = st.selectbox("Select a game", options=files)

# ---- Load leaderboard and history ----
leaderboard = load_leaderboard_from_git(game)
history = load_history_from_git(game)

# Compute wins per player
wins_counter = {}
for match in history.get("matches", []):
    if match["type"] == "individual":
        winner = match["results"][0]  # winner first
        wins_counter[winner] = wins_counter.get(winner, 0) + 1
    elif match["type"] == "team":
        winner_team = match["winner"]
        team = match["team_a"] if winner_team=="Team A" else match["team_b"]
        for p in team:
            wins_counter[p] = wins_counter.get(p, 0) + 1

# ---- Prepare dataframe safely ----
rows = []
for name, rating in leaderboard.items():
    if isinstance(rating, dict):
        mu = rating.get("mu", 25.0)
        sigma = rating.get("sigma", 8.333)
    else:
        # fallback if rating is not a dict
        mu = float(rating) if isinstance(rating, (int, float)) else 25.0
        sigma = 8.333
    rows.append({
        "Player": name,
        "Mu": mu,
        "Sigma": sigma,
        "Wins": wins_counter.get(name, 0)
    })


df = pd.DataFrame(rows)

if not df.empty:
    # Sort by Mu descending
    df = df.sort_values(by="Mu", ascending=False).reset_index(drop=True)
    # Add rank starting at 1
    df.insert(0, "Rank", df.index + 1)
    
    # Highlight current user
    current_user = st.session_state.get("current_user", "")
    df_display = df.copy()
    df_display = df_display.style.apply(
        lambda x: ["background-color: yellow" if v == current_user else "" for v in x], axis=1, subset=["Player"]
    )

    st.dataframe(df_display, use_container_width=True)
else:
    st.info("No leaderboard data yet.")

st.markdown("---")

# ---- Admin Wipe ----
admin_password = st.text_input("Admin password to wipe leaderboard (leave blank if not admin)", type="password")
if admin_password == "YOUR_SECRET_PASSWORD":  # Replace with your password
    st.warning("You are about to wipe the leaderboard for this game!")
    if st.button(f"Confirm Wipe {game}"):
        leaderboard = {}
        history = {"matches": []}
        save_leaderboard_to_git(game, leaderboard, commit_message=f"Wipe {game} leaderboard")
        st.success(f"{game} leaderboard wiped!")
