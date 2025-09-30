# pages/Leaderboard.py
import streamlit as st
import pandas as pd
from GitLab_Persistence import (
    gitlab_list_leaderboards_dir,
    load_leaderboard_from_git,
    save_leaderboard_to_git,
    load_history_from_git
)

st.set_page_config(page_title="Leaderboard", page_icon="🏆")
st.title("🏆 Leaderboard")

# ---------- Select Game ----------
files = gitlab_list_leaderboards_dir()
game_names = sorted(list({fn.replace("_leaderboard.json","").replace("_history.json","") 
                          for fn in files if fn.endswith(".json")}))
game_name = st.selectbox("Select game", options=game_names)

if not game_name:
    st.info("No games found. Add a game first.")
    st.stop()

# ---------- Load Data ----------
leaderboard = load_leaderboard_from_git(game_name)  # dict: name -> {mu, sigma}
history = load_history_from_git(game_name)          # dict: matches

# ---------- Compute Wins ----------
wins_counter = {}
for match in history.get("matches", []):
    if match.get("type") == "team":
        winner_team = match.get("winner")
        if winner_team == "Team A":
            winners = match.get("team_a", [])
        elif winner_team == "Team B":
            winners = match.get("team_b", [])
        else:
            winners = []
        for player in winners:
            wins_counter[player] = wins_counter.get(player, 0) + 1
    elif match.get("type") == "individual":
        results = match.get("results", [])
        if results:
            winner = results[0]
            wins_counter[winner] = wins_counter.get(winner, 0) + 1

# ---------- Prepare DataFrame ----------
data = []
for player, stats in leaderboard.items():
    mu = stats.get("mu", 25)
    sigma = stats.get("sigma", 8.33)
    wins = wins_counter.get(player, 0)
    data.append({"Player": player, "Mu": mu, "Sigma": sigma, "Wins": wins})

# Sort by mu descending
df = pd.DataFrame(data)
df = df.sort_values(by="Mu", ascending=False).reset_index(drop=True)
df.index += 1  # Rank starting at 1
df.index.name = "Rank"

# Display leaderboard
st.dataframe(df, use_container_width=True)

# --- Admin-only leaderboard wipe ---
st.markdown("---")
st.header("⚠️ Admin: Wipe Game Leaderboard & History")

admin_pass = st.text_input("Enter admin name to unlock wipe", type="password")

if admin_pass == "Carson":  # replace with your name or check via secret
    wipe_game = st.selectbox("Select game to wipe", options=game_names)
    if st.button("Wipe Leaderboard & History"):
        try:
            # Reset leaderboard
            save_leaderboard_to_git(wipe_game, {}, commit_message=f"Admin wipe: {wipe_game} leaderboard")
            # Reset history
            save_history_to_git(wipe_game, {"matches":[]}, commit_message=f"Admin wipe: {wipe_game} history")
            st.success(f"Leaderboard and history for '{wipe_game}' wiped successfully.")
        except Exception as e:
            st.error(f"Failed to wipe: {e}")
else:
    st.info("Enter admin name to access leaderboard wipe functionality.")


