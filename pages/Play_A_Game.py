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

# --- Streamlit page setup ---
st.set_page_config(page_title="Record Game / Matchmaking", page_icon="✏️")
st.title("✏️ Record Game & Matchmaking")

# --- TrueSkill environment ---
env = trueskill.TrueSkill(draw_probability=0)

# --- Load global players ---
players_dict = load_players_from_git()
players = players_dict.get("players", [])  # always a list

if not players:
    st.warning("No players found. Add players first in Player Manager.")
    st.stop()

# --- Load games ---
game_files = gitlab_list_leaderboards_dir()
game_names = sorted(list({fn.replace("_leaderboard.json", "").replace("_history.json", "")
                          for fn in game_files if fn.endswith(".json")}))

# --- Select or create game ---
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

# --- Game type ---
game_type = st.radio("Select game type", ["1v1", "Team", "Free-for-All"])

# ---------------- 1v1 ----------------
if game_type == "1v1":
    p1, p2 = st.columns(2)
    with p1:
        player_a = st.selectbox("Player A", options=players)
    with p2:
        player_b = st.selectbox("Player B", options=[p for p in players if p != player_a])

    winner = st.radio("Winner", options=[player_a, player_b])

    if st.button("Record 1v1 Game"):
        try:
            # Ratings
            rating_a = env.Rating(**leaderboard.get(player_a, {"mu": env.mu, "sigma": env.sigma}))
            rating_b = env.Rating(**leaderboard.get(player_b, {"mu": env.mu, "sigma": env.sigma}))

            ranks = [0,1] if winner == player_a else [1,0]
            new_ratings = env.rate([[rating_a], [rating_b]], ranks=ranks)

            leaderboard[player_a] = {"mu": new_ratings[0][0].mu, "sigma": new_ratings[0][0].sigma,
                                     "wins": leaderboard.get(player_a, {}).get("wins",0) + (1 if winner==player_a else 0)}
            leaderboard[player_b] = {"mu": new_ratings[1][0].mu, "sigma": new_ratings[1][0].sigma,
                                     "wins": leaderboard.get(player_b, {}).get("wins",0) + (1 if winner==player_b else 0)}

            # Update history
            history["matches"].append({
                "timestamp": datetime.utcnow().isoformat(),
                "type": "1v1",
                "player_a": player_a,
                "player_b": player_b,
                "winner": winner
            })

            # Push to GitLab
            save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record 1v1 match for {game_name}")
            save_history_to_git(game_name, history, commit_message=f"Add 1v1 match to {game_name} history")

            st.success(f"1v1 game recorded: {winner} won!")

        except Exception as e:
            st.error(f"Failed to record 1v1 game: {e}")

# ---------------- Team ----------------
elif game_type == "Team":
    selected_players = st.multiselect("Select players (2+)", options=players)
    if len(selected_players) < 2:
        st.info("Select at least 2 players for a team game.")
        st.stop()

    manual_team_btn = st.button("Set Manual Teams")
    auto_team_btn = st.button("Auto Balance Teams")

    team_a, team_b = [], []
    if manual_team_btn:
        team_a = st.multiselect("Team A players", options=selected_players)
        team_b = [p for p in selected_players if p not in team_a]
    elif auto_team_btn:
        # Auto split by mu
        sorted_players = sorted(selected_players,
                                key=lambda p: leaderboard.get(p, {}).get("mu", env.mu),
                                reverse=True)
        team_a = sorted_players[::2]
        team_b = sorted_players[1::2]

    if team_a and team_b:
        winner = st.radio("Winner", options=["Team A", "Team B"])
        if st.button("Record Team Game"):
            try:
                ratings_a = [env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma})) for p in team_a]
                ratings_b = [env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma})) for p in team_b]

                new_ratings = env.rate([ratings_a, ratings_b], ranks=[0,1] if winner=="Team A" else [1,0])

                for name, r in zip(team_a, new_ratings[0]):
                    leaderboard[name] = {"mu": r.mu, "sigma": r.sigma,
                                         "wins": leaderboard.get(name, {}).get("wins",0)+ (1 if winner=="Team A" else 0)}
                for name, r in zip(team_b, new_ratings[1]):
                    leaderboard[name] = {"mu": r.mu, "sigma": r.sigma,
                                         "wins": leaderboard.get(name, {}).get("wins",0)+ (1 if winner=="Team B" else 0)}

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

# ---------------- Free-for-All ----------------
elif game_type == "Free-for-All":
    selected_players = st.multiselect("Select players (2+)", options=players)
    if len(selected_players) < 2:
        st.info("Select at least 2 players for FFA.")
        st.stop()

    # Select finishing order
    finishing_order = []
    remaining = selected_players.copy()
    while remaining:
        pick = st.selectbox(f"Next finisher ({len(finishing_order)+1})", options=remaining, key=len(finishing_order))
        if st.button(f"Confirm position {len(finishing_order)+1}", key=f"confirm_{len(finishing_order)}"):
            finishing_order.append(pick)
            remaining.remove(pick)
            st.experimental_rerun()  # refresh to update remaining

    if len(finishing_order) == len(selected_players):
        if st.button("Record FFA Game"):
            try:
                ratings = [[env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma}))] for p in finishing_order]
                ranks = list(range(len(finishing_order)))
                new_ratings = env.rate(ratings, ranks=ranks)

                for p, r in zip(finishing_order, new_ratings):
                    leaderboard[p] = {"mu": r[0].mu, "sigma": r[0].sigma,
                                      "wins": leaderboard.get(p, {}).get("wins",0) + (1 if ranks.index(r)==0 else 0)}

                history["matches"].append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "FFA",
                    "finishing_order": finishing_order
                })

                save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record FFA match for {game_name}")
                save_history_to_git(game_name, history, commit_message=f"Add FFA match to {game_name} history")

                st.success("FFA game recorded successfully!")

            except Exception as e:
                st.error(f"Failed to record FFA game: {e}")
