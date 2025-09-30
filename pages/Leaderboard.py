import streamlit as st
from GitLab_Persistence import load_leaderboard_from_git, env
import trueskill

st.set_page_config(page_title="Leaderboard", page_icon="🏆")
st.title("🏆 Game Leaderboards")

# --- Select Game ---
files = [fn.replace("_leaderboard.json", "").replace("_history.json", "") 
         for fn in st.session_state.get("leaderboard_files", [])] \
         if "leaderboard_files" in st.session_state else []
game_names = sorted(list({fn for fn in files}))
if not game_names:
    st.info("No games found. Record a game first.")
    st.stop()

game_option = st.selectbox("Select a game", options=game_names)
leaderboard = load_leaderboard_from_git(game_option)

if not leaderboard:
    st.info("No leaderboard data for this game yet.")
    st.stop()

# --- Display leaderboard ---
st.subheader(f"{game_option} Leaderboard")
# Conservative rating = mu - 3*sigma
sorted_players = sorted(leaderboard.items(), key=lambda item: item[1]["mu"] - 3*item[1]["sigma"], reverse=True)
for i, (name, rating) in enumerate(sorted_players, start=1):
    conservative = rating["mu"] - 3*rating["sigma"]
    st.write(f"{i}. {name:10} | μ={rating['mu']:.2f}, σ={rating['sigma']:.2f}, rating={conservative:.2f}")
