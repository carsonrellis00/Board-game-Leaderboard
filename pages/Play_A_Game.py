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
players_dict = load_players_from_git() or {"players": []}
players = players_dict.get("players", [])
files = gitlab_list_leaderboards_dir()
game_names = sorted(list({fn.replace("_leaderboard.json", "").replace("_history.json", "")
                          for fn in files if fn.endswith(".json")}))

# --- Game selection ---
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

if not players:
    st.warning("No global players found. Add players first in Player Manager.")
    st.stop()

# --- Game type selection ---
game_type = st.radio("Game Type", ["1v1", "Team", "Free For All"])

# ---------------- 1v1 ----------------
if game_type == "1v1":
    st.header("1v1 Match")
    selected = st.multiselect("Select 2 players", options=players)
    if len(selected) == 2:
        winner = st.radio("Winner", options=selected)
        if st.button("Record 1v1 Game"):
            try:
                # Create TrueSkill ratings only from mu and sigma
                ratings = []
                for p in selected:
                    r_dict = leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma})
                    ratings.append(env.Rating(mu=r_dict["mu"], sigma=r_dict["sigma"]))

                ranks = [0,1] if winner == selected[0] else [1,0]
                new_ratings = env.rate([[ratings[0]], [ratings[1]]], ranks=ranks)

                # Update leaderboard
                for p, r in zip(selected, [new_ratings[0][0], new_ratings[1][0]]):
                    leaderboard[p] = {"mu": r.mu, "sigma": r.sigma,
                                      "wins": leaderboard.get(p, {}).get("wins", 0) + (1 if p==winner else 0)}

                # Update history
                history["matches"].append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "1v1",
                    "players": selected,
                    "winner": winner
                })

                save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record 1v1 game for {game_name}")
                save_history_to_git(game_name, history, commit_message=f"Add 1v1 match to {game_name} history")

                st.success("1v1 game recorded successfully!")
            except Exception as e:
                st.error(f"Failed to record 1v1 game: {e}")

# ---------------- Team ----------------
elif game_type == "Team":
    st.header("Team-based Game Recording")
    selected_players = st.multiselect("Select players", options=players)
    if selected_players:
        team_a_btn = st.button("Set Manual Teams")
        team_b_btn = st.button("Auto Balance Teams")

        team_a, team_b = [], []
        if team_a_btn:
            team_a = st.multiselect("Team A players", options=selected_players)
            team_b = [p for p in selected_players if p not in team_a]
            st.write("Team B:", ", ".join(team_b) if team_b else "(empty)")
        elif team_b_btn:
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
                    ratings_a = [env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma})) for p in team_a]
                    ratings_b = [env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma})) for p in team_b]

                    ranks = [0,1] if winner == "Team A" else [1,0]
                    new_ratings = env.rate([ratings_a, ratings_b], ranks=ranks)

                    for p, r in zip(team_a, new_ratings[0]):
                        leaderboard[p] = {"mu": r.mu, "sigma": r.sigma,
                                          "wins": leaderboard.get(p, {}).get("wins", 0) + (1 if winner=="Team A" else 0)}
                    for p, r in zip(team_b, new_ratings[1]):
                        leaderboard[p] = {"mu": r.mu, "sigma": r.sigma,
                                          "wins": leaderboard.get(p, {}).get("wins", 0) + (1 if winner=="Team B" else 0)}

                    history["matches"].append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "type": "team",
                        "team_a": team_a,
                        "team_b": team_b,
                        "winner": winner
                    })

                    save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record team match for {game_name}")
                    save_history_to_git(game_name, history, commit_message=f"Add team match to {game_name} history")

                    st.success("Team game recorded successfully!")
                except Exception as e:
                    st.error(f"Failed to record team game: {e}")

# ---------------- Free For All ----------------
elif game_type == "Free For All":
    st.header("Free For All Recording")
    selected_players_ffa = st.multiselect("Select players", options=players, key="ffa_players")
    finishing_order = []

    if selected_players_ffa:
        remaining = [p for p in selected_players_ffa if p not in finishing_order]
        for i in range(len(selected_players_ffa)):
            pick = st.selectbox(f"Next finisher ({i+1})", options=remaining, key=f"ffa_pick_{i}")
            if st.button("Confirm Placement", key=f"ffa_btn_{i}"):
                finishing_order.append(pick)
                remaining.remove(pick)
                st.experimental_rerun()  # refresh to show remaining

        if len(finishing_order) == len(selected_players_ffa):
            if st.button("Record FFA Game", key="record_ffa"):
                try:
                    ratings = [env.Rating(mu=leaderboard.get(p, {}).get("mu", env.mu),
                                          sigma=leaderboard.get(p, {}).get("sigma", env.sigma))
                               for p in finishing_order]

                    # Build ranks list from finishing order
                    ranks = list(range(len(finishing_order)))

                    new_ratings = env.rate([[r] for r in ratings], ranks=ranks)

                    for p, r in zip(finishing_order, [nr[0] for nr in new_ratings]):
                        leaderboard[p] = {"mu": r.mu, "sigma": r.sigma,
                                          "wins": leaderboard.get(p, {}).get("wins", 0) + (1 if p==finishing_order[0] else 0)}

                    history["matches"].append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "type": "ffa",
                        "players": finishing_order
                    })

                    save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record FFA match for {game_name}")
                    save_history_to_git(game_name, history, commit_message=f"Add FFA match to {game_name} history")

                    st.success("FFA game recorded successfully!")
                except Exception as e:
                    st.error(f"Failed to record FFA game: {e}")
