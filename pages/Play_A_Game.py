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

# --- Load players and games ---
players_dict = load_players_from_git()
players = players_dict.get("players", [])
if not players:
    st.warning("No global players found. Add players first in Player Manager.")
    st.stop()

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

# --- Match type selection ---
match_type = st.radio("Select match type", ["Team Game", "1v1", "Free-for-All"])

# ---------------- TEAM GAME ----------------
if match_type == "Team Game":
    st.header("Team-based Game Recording")

    selected_players = st.multiselect("Select players", options=players)
    if selected_players:
        # Manual or auto teams
        team_mode = st.radio("Team assignment", ["Manual Teams", "Auto-Balance Teams"])
        team_a, team_b = [], []

        if team_mode == "Manual Teams":
            team_a = st.multiselect("Team A players", options=selected_players)
            team_b = [p for p in selected_players if p not in team_a]
            st.write("Team B:", ", ".join(team_b) if team_b else "(empty)")
        else:
            # Auto-Balance Teams by mu
            sorted_players = sorted(selected_players,
                                    key=lambda p: leaderboard.get(p, {}).get("mu", env.mu),
                                    reverse=True)
            team_a = sorted_players[::2]
            team_b = sorted_players[1::2]
            st.write("Auto-balanced Teams:")
            st.write("Team A:", ", ".join(team_a))
            st.write("Team B:", ", ".join(team_b))

        if team_a and team_b:
            winner = st.radio("Winner", options=["Team A", "Team B"])
            if st.button("Record Team Game"):
                try:
                    ratings_a = [env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma}))
                                 for p in team_a]
                    ratings_b = [env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma}))
                                 for p in team_b]

                    ranks = [0, 1] if winner == "Team A" else [1, 0]
                    new_ratings = env.rate([ratings_a, ratings_b], ranks=ranks)

                    # Update leaderboard
                    for name, r in zip(team_a, new_ratings[0]):
                        leaderboard[name] = {"mu": r.mu, "sigma": r.sigma,
                                             "wins": leaderboard.get(name, {}).get("wins", 0) + (1 if winner == "Team A" else 0)}
                    for name, r in zip(team_b, new_ratings[1]):
                        leaderboard[name] = {"mu": r.mu, "sigma": r.sigma,
                                             "wins": leaderboard.get(name, {}).get("wins", 0) + (1 if winner == "Team B" else 0)}

                    # Update history
                    history.setdefault("matches", []).append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "type": "team",
                        "team_a": team_a,
                        "team_b": team_b,
                        "winner": winner
                    })

                    # Save to GitLab
                    save_leaderboard_to_git(game_name, leaderboard,
                                            commit_message=f"Record team match for {game_name}")
                    save_history_to_git(game_name, history,
                                        commit_message=f"Add team match to {game_name} history")

                    st.success("Team game recorded successfully!")
                except Exception as e:
                    st.error(f"Failed to record game: {e}")

# ---------------- 1v1 ----------------
elif match_type == "1v1":
    st.header("1v1 Game Recording")
    p1, p2 = st.selectbox("Player 1", options=players), st.selectbox("Player 2", options=players)
    if p1 == p2:
        st.warning("Select two different players.")
    else:
        winner = st.radio("Winner", options=[p1, p2])
        if st.button("Record 1v1 Game"):
            try:
                ratings = [[env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma})) for p in [p1, p2]]]
                ranks = [0, 1] if winner == p1 else [1, 0]
                new_ratings = env.rate(ratings, ranks=ranks)

                # Update leaderboard
                for name, r in zip([p1, p2], new_ratings[0]):
                    leaderboard[name] = {"mu": r.mu, "sigma": r.sigma,
                                         "wins": leaderboard.get(name, {}).get("wins", 0) + (1 if name == winner else 0)}

                # Update history
                history.setdefault("matches", []).append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "1v1",
                    "players": [p1, p2],
                    "winner": winner
                })

                # Save to GitLab
                save_leaderboard_to_git(game_name, leaderboard,
                                        commit_message=f"Record 1v1 match for {game_name}")
                save_history_to_git(game_name, history,
                                    commit_message=f"Add 1v1 match to {game_name} history")

                st.success("1v1 game recorded successfully!")
            except Exception as e:
                st.error(f"Failed to record 1v1 game: {e}")

# ---------------- FREE-FOR-ALL ----------------
elif match_type == "Free-for-All":
    st.header("Free-for-All Game Recording")
    selected_players = st.multiselect("Select players", options=players)
    if len(selected_players) < 2:
        st.warning("Select at least 2 players for a Free-for-All match.")
    else:
        st.subheader("Enter finishing order")
        finishing_order = st.session_state.get("ffa_order", [])
        remaining = [p for p in selected_players if p not in finishing_order]

        for idx in range(len(finishing_order), len(selected_players)):
            pick = st.selectbox(
                f"Next finisher ({idx+1})",
                options=remaining,
                key=f"ffa_pick_{idx}"  # <-- unique key per widget
            )
            if st.button(f"Add '{pick}' to order", key=f"ffa_add_{idx}"):
                finishing_order.append(pick)
                remaining.remove(pick)
                st.session_state["ffa_order"] = finishing_order
                st.experimental_rerun()  # refresh so remaining updates

        if len(finishing_order) == len(selected_players):
            if st.button("Record Free-for-All Game", key="record_ffa"):
                try:
                    rating_groups = [[env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma}))] 
                                     for p in finishing_order]
                    ranks = list(range(len(finishing_order)))  # first is rank 0, etc.
                    new_ratings = env.rate(rating_groups, ranks=ranks)

                    # Update leaderboard
                    for name, r_list in zip(finishing_order, new_ratings):
                        r = r_list[0] if isinstance(r_list, list) else r_list
                        leaderboard[name] = {
                            "mu": r.mu,
                            "sigma": r.sigma,
                            "wins": leaderboard.get(name, {}).get("wins", 0) + (1 if name == finishing_order[0] else 0)
                        }

                    # Update history
                    history.setdefault("matches", []).append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "type": "ffa",
                        "players": finishing_order,
                        "winner": finishing_order[0]
                    })

                    # Save to GitLab
                    save_leaderboard_to_git(game_name, leaderboard,
                                            commit_message=f"Record FFA match for {game_name}")
                    save_history_to_git(game_name, history,
                                        commit_message=f"Add FFA match to {game_name} history")

                    st.success("Free-for-All game recorded successfully!")
                    st.session_state["ffa_order"] = []  # reset for next game
                except Exception as e:
                    st.error(f"Failed to record FFA game: {e}")

