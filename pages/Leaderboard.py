# pages/Leaderboard.py
import streamlit as st
import pandas as pd
from GitLab_Persistence import (
    load_leaderboard_from_git,
    save_leaderboard_to_git,
    load_history_from_git,
    save_history_to_git,
    gitlab_list_leaderboards_dir
)
from datetime import datetime

st.set_page_config(page_title="Leaderboard", page_icon="🏆")
st.title("🏆 Leaderboard")

# ---- Game Selection ----
all_files = gitlab_list_leaderboards_dir()
game_names = sorted(list({fn.replace("_leaderboard.json", "").replace("_history.json", "")
                          for fn in all_files if fn.endswith(".json")}))
if not game_names:
    st.info("No games found yet.")
    st.stop()

selected_game = st.selectbox("Select Game", options=game_names)

# ---- Load Leaderboard and History ----
leaderboard = load_leaderboard_from_git(selected_game)
history = load_history_from_git(selected_game)

# ---- Prepare Leaderboard DataFrame ----
rows = []
for name, data in leaderboard.items():
    if isinstance(data, dict):
        mu = data.get("mu", 25.0)
        sigma = data.get("sigma", 8.333)
        wins = data.get("wins", 0)
    else:
        # Handle corrupted or old-format entries
        mu = 25.0
        sigma = 8.333
        wins = 0
    rows.append({"Player": name, "Mu": mu, "Sigma": sigma, "Wins": wins})

df = pd.DataFrame(rows)
df = df.sort_values(by="Mu", ascending=False).reset_index(drop=True)
df.insert(0, "Rank", range(1, len(df) + 1))


# ---- Display Leaderboard ----
st.subheader(f"Leaderboard: {selected_game}")
st.dataframe(df, use_container_width=True)

# Highlight top 3
def highlight_top(row):
    if row.name == 0:
        return ["background-color: gold"] * len(row)
    elif row.name == 1:
        return ["background-color: silver"] * len(row)
    elif row.name == 2:
        return ["background-color: #cd7f32"] * len(row)
    else:
        return [""] * len(row)

if not df.empty:
    st.dataframe(df.style.apply(highlight_top, axis=1), use_container_width=True)

st.markdown("---")
# ---- Admin User ----
ADMIN_USERNAME = "Carson"  # replace with your username
current_user = st.text_input("Enter username for admin actions:", "")
# ---- Admin: Wipe Leaderboard ----
if current_user == ADMIN_USERNAME:
    st.subheader("⚠️ Admin: Wipe Leaderboard")
    st.warning("This will reset all Mu, Sigma, and Wins for this game.")
    if st.button(f"Wipe {selected_game} Leaderboard"):
        # Reset leaderboard
        for player in leaderboard.keys():
            leaderboard[player]["mu"] = 25.0
            leaderboard[player]["sigma"] = 8.333
            leaderboard[player]["wins"] = 0
        save_leaderboard_to_git(selected_game, leaderboard, commit_message=f"Reset {selected_game} leaderboard by admin")
        
        # Reset history
        history["matches"] = []
        save_history_to_git(selected_game, history, commit_message=f"Clear {selected_game} match history by admin")
        
        st.success(f"{selected_game} leaderboard and history wiped.")



