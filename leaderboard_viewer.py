import streamlit as st
from GitLab_Persistence import load_leaderboard_from_git, gitlab_list_leaderboards_dir

st.set_page_config(page_title="Leaderboard Viewer", page_icon="🏆")
st.title("🏆 Board Game Leaderboard Viewer (Read-only)")

# --- Select Game ---
files = gitlab_list_leaderboards_dir()
game_names = sorted(list({fn.replace("_leaderboard.json","").replace("_history.json","") 
                          for fn in files if fn.endswith(".json")}))

if not game_names:
    st.info("No games found in the repository.")
    st.stop()

game_name = st.selectbox("Select a game to view", options=game_names)

# --- Load Leaderboard ---
leaderboard = load_leaderboard_from_git(game_name)

if not leaderboard:
    st.info(f"No leaderboard data yet for {game_name}.")
    st.stop()

# --- Display Leaderboard ---
st.subheader(f"Leaderboard: {game_name}")
st.write("Players are ranked by conservative TrueSkill rating (μ - 3σ).")

# Compute conservative rating
def conservative(r):
    return r.get("mu",25.0) - 3 * r.get("sigma",8.333)

sorted_players = sorted(leaderboard.items(), key=lambda kv: conservative(kv[1]), reverse=True)

st.table([{
    "Rank": i+1,
    "Player": name,
    "μ": f"{r['mu']:.2f}",
    "σ": f"{r['sigma']:.2f}",
    "Conservative Rating": f"{conservative(r):.2f}"
} for i, (name, r) in enumerate(sorted_players)])
