import streamlit as st
import pandas as pd
from GitLab_Persistence import load_leaderboard_from_git, save_leaderboard_to_git
import trueskill

st.set_page_config(page_title="Leaderboard", page_icon="🏆")

# ---- Config ----
CURRENT_USER = st.secrets.get("ADMIN_USER") or "Carson"  # highlight this user
env = trueskill.TrueSkill(draw_probability=0)

# ---- Select Game ----
game_names = ["guards of atlantis 2", "scythe", "unfair", "wyrmspan"]  # Or dynamically load
selected_game = st.selectbox("Select Game", game_names)

# ---- Load Leaderboard ----
leaderboard = load_leaderboard_from_git(selected_game)

# ---- Prepare DataFrame ----
rows = []
for name, data in leaderboard.items():
    if isinstance(data, dict):
        mu = data.get("mu", 25.0)
        sigma = data.get("sigma", 8.333)
        wins = data.get("wins", 0)
    else:
        mu = 25.0
        sigma = 8.333
        wins = 0
    rows.append({"Player": name, "Mu": mu, "Sigma": sigma, "Wins": wins})

df = pd.DataFrame(rows)
df = df.sort_values(by="Mu", ascending=False).reset_index(drop=True)
df.insert(0, "Rank", range(1, len(df) + 1))

# ---- Display Leaderboard ----
st.header(f"🏆 {selected_game} Leaderboard")
st.dataframe(df.style.apply(lambda x: ['background-color: #FFFF99' if v == CURRENT_USER else '' for v in x], subset=["Player"]), height=500)

# ---- Admin Wipe ----
st.markdown("---")
if st.secrets.get("ADMIN_USER") == CURRENT_USER:
    st.subheader("⚠️ Admin: Wipe Leaderboard")
    if st.button(f"Wipe {selected_game} Leaderboard"):
        for name in leaderboard:
            leaderboard[name]["mu"] = env.mu
            leaderboard[name]["sigma"] = env.sigma
            leaderboard[name]["wins"] = 0
        save_leaderboard_to_git(selected_game, leaderboard, commit_message=f"Wipe {selected_game} leaderboard")
        st.success(f"{selected_game} leaderboard wiped and ratings reset.")
