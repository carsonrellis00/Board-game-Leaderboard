# pages/Play_A_Game.py
import streamlit as st
from GitLab_Persistence import (
    load_players_from_git,
    save_players_to_git,
    load_leaderboard_from_git,
    save_leaderboard_to_git,
    load_history_from_git,
    save_history_to_git,
    gitlab_list_leaderboards_dir
)
import trueskill
from datetime import datetime

st.set_page_config(page_title="Record Game / Matchmaking", page_icon="✏️")
st.title("✏️ Record Game & Matchmaking")

# --- TrueSkill environment ---
env = trueskill.TrueSkill(draw_probability=0)

# --- Load players ---
players_dict = load_players_from_git()
players = players_dict.get("players", [])

if not players:
    st.warning("No global players found. Add players first in Player Manager.")
    st.stop()

# --- Load games ---
files = gitlab_list_leaderboards_dir()
game_names = sorted(list({fn.replace("_leaderboard.json", "").replace("_history.json", "")
                          for fn in files if fn.endswith(".json")}))

game_option = st.selectbox("Select game (or type new)", options=["<New Game>"] + game_names)
if game_option == "<New Game>":
    game_name_input = st.text_input("New game name")
    game_name = game_name_input.strip() if game_name_input else None
else:
    game_name = game_option

if not game_name:
    st.info("Pick or type a game name to record matches for.")
    st.stop()

st.subheader(f"Recording for game: {game_name}")

# --- Load leaderboard and history ---
leaderboard = load_leaderboard_from_git(game_name) or {}
history = load_history_from_git(game_name) or {"matches": []}

# --- Helper to get TrueSkill ratings ---
def get_rating(player):
    r = leaderboard.get(player, {"mu": env.mu, "sigma": env.sigma, "wins": 0})
    return env.Rating(mu=r["mu"], sigma=r["sigma"])

# --- Tabs for match type ---
tab_1v1 = st.container()
tab_team = st.container()
tab_ffa = st.container()

# ---------------- 1v1 Match ----------------
with tab_1v1:
    st.header("1v1 Game Recording")
    if len(players) >= 2:
        p1, p2 = st.selectbox("Player 1", players), st.selectbox("Player 2", players)
        if p1 == p2:
            st.warning("Select two different players.")
        else:
            winner = st.radio("Winner", options=[p1, p2])
            if st.button("Record 1v1 Game"):
                try:
                    r1, r2 = get_rating(p1), get_rating(p2)
                    ranks = [0, 1] if winner == p1 else [1, 0]
                    new_r1, new_r2 = env.rate([[r1], [r2]], ranks=ranks)

                    # Update leaderboard
                    leaderboard[p1] = {"mu": new_r1[0].mu, "sigma": new_r1[0].sigma,
                                       "wins": leaderboard.get(p1, {}).get("wins", 0) + (1 if winner==p1 else 0)}
                    leaderboard[p2] = {"mu": new_r2[0].mu, "sigma": new_r2[0].sigma,
                                       "wins": leaderboard.get(p2, {}).get("wins", 0) + (1 if winner==p2 else 0)}

                    # Update history
                    history.setdefault("matches", []).append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "type": "1v1",
                        "players": [p1, p2],
                        "winner": winner
                    })

                    save_leaderboard_to_git(game_name, leaderboard,
                                            commit_message=f"Record 1v1 match for {game_name}")
                    save_history_to_git(game_name, history,
                                        commit_message=f"Add 1v1 match to {game_name} history")
                    st.success("1v1 game recorded successfully!")
                except Exception as e:
                    st.error(f"Failed to record 1v1 game: {e}")

# ---------------- Team Match ----------------
with tab_team:
    st.header("Team-based Game Recording")
    selected_players = st.multiselect("Select players", options=players)
    if selected_players and len(selected_players) >= 2:
        manual_team_btn = st.button("Set Manual Teams", key="manual_team")
        auto_team_btn = st.button("Auto Balance Teams", key="auto_team")

        team_a, team_b = [], []
        if manual_team_btn:
            team_a = st.multiselect("Team A players", options=selected_players, key="team_a_manual")
            team_b = [p for p in selected_players if p not in team_a]
            st.write("Team B:", ", ".join(team_b) if team_b else "(empty)")
        elif auto_team_btn:
            sorted_players = sorted(selected_players,
                                    key=lambda p: leaderboard.get(p, {"mu": env.mu}).get("mu", env.mu),
                                    reverse=True)
            team_a = sorted_players[::2]
            team_b = sorted_players[1::2]
            st.write("Auto-balanced Teams:")
            st.write("Team A:", ", ".join(team_a))
            st.write("Team B:", ", ".join(team_b))

        if team_a and team_b:
            winner = st.radio("Winner", options=["Team A", "Team B"], key="team_winner")
            if st.button("Record Team Game", key="record_team"):
                try:
                    ratings_a = [get_rating(p) for p in team_a]
                    ratings_b = [get_rating(p) for p in team_b]
                    ranks = [0, 1] if winner == "Team A" else [1, 0]
                    new_ratings = env.rate([ratings_a, ratings_b], ranks=ranks)

                    for name, r in zip(team_a, new_ratings[0]):
                        leaderboard[name] = {"mu": r.mu, "sigma": r.sigma,
                                             "wins": leaderboard.get(name, {}).get("wins", 0) + (1 if winner=="Team A" else 0)}
                    for name, r in zip(team_b, new_ratings[1]):
                        leaderboard[name] = {"mu": r.mu, "sigma": r.sigma,
                                             "wins": leaderboard.get(name, {}).get("wins", 0) + (1 if winner=="Team B" else 0)}

                    history.setdefault("matches", []).append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "type": "team",
                        "team_a": team_a,
                        "team_b": team_b,
                        "winner": winner
                    })

                    save_leaderboard_to_git(game_name, leaderboard,
                                            commit_message=f"Record team match for {game_name}")
                    save_history_to_git(game_name, history,
                                        commit_message=f"Add team match to {game_name} history")
                    st.success("Team game recorded successfully!")
                except Exception as e:
                    st.error(f"Failed to record team game: {e}")

# ---------------- Free For All ----------------
with tab_ffa:
    st.header("Free-For-All Game Recording")
    if len(players) >= 2:
        ffa_selected = st.multiselect("Select players for FFA", options=players, key="ffa_players")
        if ffa_selected:
            finishing_order = []
            remaining = ffa_selected.copy()
            while remaining:
                pick = st.selectbox(f"Select next finisher ({len(finishing_order)+1})",
                                    options=remaining,
                                    key=f"ffa_{len(finishing_order)}")
                if st.button(f"Confirm position {len(finishing_order)+1}", key=f"confirm_{len(finishing_order)}"):
                    finishing_order.append(pick)
                    remaining.remove(pick)
                    st.experimental_rerun()  # refresh for next selection

            if not remaining and finishing_order:
                if st.button("Record FFA Game", key="record_ffa"):
                    try:
                        rating_list = [get_rating(p) for p in finishing_order]
                        ranks = list(range(len(finishing_order)))  # lower rank = better
                        new_ratings = env.rate([[r] for r in rating_list], ranks=ranks)

                        for player, r in zip(finishing_order, new_ratings):
                            leaderboard[player] = {"mu": r[0].mu, "sigma": r[0].sigma,
                                                   "wins": leaderboard.get(player, {}).get("wins", 0) + (1 if player==finishing_order[0] else 0)}

                        history.setdefault("matches", []).append({
                            "timestamp": datetime.utcnow().isoformat(),
                            "type": "FFA",
                            "players": finishing_order,
                            "winner": finishing_order[0]
                        })

                        save_leaderboard_to_git(game_name, leaderboard,
                                                commit_message=f"Record FFA match for {game_name}")
                        save_history_to_git(game_name, history,
                                            commit_message=f"Add FFA match to {game_name} history")
                        st.success("FFA game recorded successfully!")
                    except Exception as e:
                        st.error(f"Failed to record FFA game: {e}")
