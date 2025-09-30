import streamlit as st
from GitLab_Persistence import (
    load_players_from_git,
    load_leaderboard_from_git,
    save_leaderboard_to_git,
    load_history_from_git,
    save_history_to_git,
    env
)
from itertools import combinations
import math

st.set_page_config(page_title="Matchmaking", page_icon="⚔️")
st.title("⚔️ Matchmaking & Team Game Recording")

# --- Select game ---
files = [fn for fn in st.session_state.get("leaderboard_files", [])] \
        if "leaderboard_files" in st.session_state else []
all_files = [fn.replace("_leaderboard.json","").replace("_history.json","") 
             for fn in load_players_from_git()]  # fallback if session_state empty
game_names = sorted(list({fn for fn in all_files}))
game_name = st.selectbox("Select game for matchmaking", options=game_names)

if not game_name:
    st.warning("Add players and a game first.")
    st.stop()

# Load leaderboard and history
leaderboard = load_leaderboard_from_git(game_name)
history = load_history_from_git(game_name)

# --- Select players ---
all_players = load_players_from_git()
selected_players = st.multiselect("Select players for this match", options=all_players)

if len(selected_players) < 2:
    st.info("Select at least two players for matchmaking.")
    st.stop()

# --- Team balancing ---
def team_combinations(players):
    n = len(players)
    half = n // 2
    return list(combinations(players, half))

def team_average_rating(team):
    ratings = []
    for name in team:
        r = leaderboard.get(name)
        ratings.append(r['mu'] if r else env.Rating().mu)
    return sum(ratings)/len(ratings)

# --- Generate balanced teams ---
if st.button("Generate Teams"):
    best_diff = math.inf
    best_pair = None
    combos = team_combinations(selected_players)
    for i in range(len(combos)//2):
        team_a = combos[i]
        team_b = tuple(p for p in selected_players if p not in team_a)
        diff = abs(team_average_rating(team_a) - team_average_rating(team_b))
        if diff < best_diff:
            best_diff = diff
            best_pair = (team_a, team_b)
    if best_pair:
        team_a, team_b = best_pair
        st.session_state['team_a'] = team_a
        st.session_state['team_b'] = team_b
        st.success("Balanced teams generated!")

# --- Display teams ---
if 'team_a' in st.session_state and 'team_b' in st.session_state:
    team_a = st.session_state['team_a']
    team_b = st.session_state['team_b']
    st.subheader("Team A")
    st.write(", ".join(team_a))
    st.subheader("Team B")
    st.write(", ".join(team_b))

    winner = st.radio("Select winning team", options=["Team A", "Team B"])

    if st.button("Record Team Match"):
        if not team_a or not team_b:
            st.warning("Both teams must have at least one player.")
        else:
            # Prepare ratings
            ratings_a = [env.Rating(**leaderboard.get(n, {})) for n in team_a]
            ratings_b = [env.Rating(**leaderboard.get(n, {})) for n in team_b]
            ranks = [0,1] if winner=="Team A" else [1,0]
            new_team_ratings = env.rate([ratings_a, ratings_b], ranks=ranks)

            # Update leaderboard
            for name, r in zip(team_a, new_team_ratings[0]):
                leaderboard[name] = {"mu": r.mu, "sigma": r.sigma}
            for name, r in zip(team_b, new_team_ratings[1]):
                leaderboard[name] = {"mu": r.mu, "sigma": r.sigma}

            # Append to history
            history.setdefault("matches", []).append({
                "timestamp": st.session_state.get("timestamp", datetime.utcnow().isoformat()),
                "type": "team",
                "team_a": list(team_a),
                "team_b": list(team_b),
                "winner": winner
            })

            # Save to GitLab
            try:
                save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record team match {game_name}")
                save_history_to_git(game_name, history, commit_message=f"Add team match {game_name} history")
                st.success("Match recorded and pushed to GitLab.")
            except Exception as e:
                st.error(f"Failed to save match: {e}")
