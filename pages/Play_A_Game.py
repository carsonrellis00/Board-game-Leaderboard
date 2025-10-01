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
leaderboard = load_leaderboard_from_git(game_name)
history = load_history_from_git(game_name)

if not players:
    st.warning("No global players found. Add players first in Player Manager.")
    st.stop()

# --- Match type selection ---
match_type = st.radio("Select match type", ["1v1", "Team-based", "Free-for-All"])

# ---------------- 1v1 ----------------
if match_type == "1v1":
    st.header("1v1 Game Recording")
    selected_players = st.multiselect("Select 2 players", options=players, max_selections=2)
    if len(selected_players) != 2:
        st.warning("Select exactly 2 players.")
    else:
        winner = st.radio("Winner", options=selected_players)
        if st.button("Record 1v1 Game"):
            try:
                ratings = []
                for p in selected_players:
                    r = leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma})
                    ratings.append(env.Rating(mu=r["mu"], sigma=r["sigma"]))
                ranks = [0, 1] if winner == selected_players[0] else [1, 0]
                new_ratings = env.rate([ratings[0:1], ratings[1:2]], ranks=ranks)

                # Update leaderboard
                for p, r in zip(selected_players, new_ratings):
                    r_obj = r[0] if isinstance(r, list) else r
                    old_wins = leaderboard.get(p, {}).get("wins", 0)
                    leaderboard[p] = {"mu": r_obj.mu, "sigma": r_obj.sigma, 
                                       "wins": old_wins + (1 if p == winner else 0)}

                # Update history
                history.setdefault("matches", []).append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "1v1",
                    "players": selected_players,
                    "winner": winner
                })

                save_leaderboard_to_git(game_name, leaderboard,
                                        commit_message=f"Record 1v1 match for {game_name}")
                save_history_to_git(game_name, history,
                                    commit_message=f"Add 1v1 match to {game_name} history")
                st.success("1v1 game recorded successfully!")

            except Exception as e:
                st.error(f"Failed to record 1v1 game: {e}")

# ---------------- Team-based ----------------
elif match_type == "Team-based":
    st.header("Team-based Game Recording")
    selected_players = st.multiselect("Select players", options=players)
    if len(selected_players) < 2:
        st.warning("Select at least 2 players for a team game.")
    else:
        manual_team_btn = st.button("Set Manual Teams")
        auto_team_btn = st.button("Auto Balance Teams")
        team_a, team_b = [], []

        if manual_team_btn:
            team_a = st.multiselect("Team A players", options=selected_players, key="team_a")
            team_b = [p for p in selected_players if p not in team_a]
            st.write("Team B:", ", ".join(team_b) if team_b else "(empty)")
        elif auto_team_btn:
            def get_mu(p):
                r = leaderboard.get(p, {"mu": env.mu})
                return r.get("mu", env.mu)
            sorted_players = sorted(selected_players, key=get_mu, reverse=True)
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

                    ranks = [0,1] if winner == "Team A" else [1,0]
                    new_ratings = env.rate([ratings_a, ratings_b], ranks=ranks)

                    # Update leaderboard
                    for p, r in zip(team_a, new_ratings[0]):
                        old_wins = leaderboard.get(p, {}).get("wins", 0)
                        leaderboard[p] = {"mu": r.mu, "sigma": r.sigma,
                                          "wins": old_wins + (1 if winner=="Team A" else 0)}
                    for p, r in zip(team_b, new_ratings[1]):
                        old_wins = leaderboard.get(p, {}).get("wins", 0)
                        leaderboard[p] = {"mu": r.mu, "sigma": r.sigma,
                                          "wins": old_wins + (1 if winner=="Team B" else 0)}

                    # Update history
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

# ---------------- Free-for-All ----------------
elif match_type == "Free-for-All":
    st.header("Free-for-All Game Recording")
    selected_players = st.multiselect("Select players", options=players)
    if len(selected_players) < 2:
        st.warning("Select at least 2 players for a Free-for-All match.")
    else:
        # Assign finishing positions
        st.subheader("Assign finishing positions")
        player_positions = {}
        for player in selected_players:
            pos = st.selectbox(f"{player} position", options=list(range(1, len(selected_players)+1)), key=f"pos_{player}")
            player_positions[player] = pos

        if len(set(player_positions.values())) < len(selected_players):
            st.warning("Each position must be unique.")
        else:
            finishing_order = sorted(player_positions, key=lambda p: player_positions[p])

            if st.button("Record Free-for-All Game"):
                try:
                    rating_groups = [[env.Rating(**leaderboard.get(p, {"mu": env.mu, "sigma": env.sigma}))]
                                     for p in finishing_order]
                    ranks = list(range(len(finishing_order)))  # 0 = winner
                    new_ratings = env.rate(rating_groups, ranks=ranks)

                    # Update leaderboard
                    for player, r_list in zip(finishing_order, new_ratings):
                        r = r_list[0] if isinstance(r_list, list) else r_list
                        old_wins = leaderboard.get(player, {}).get("wins", 0)
                        leaderboard[player] = {
                            "mu": r.mu,
                            "sigma": r.sigma,
                            "wins": old_wins + (1 if player == finishing_order[0] else 0)
                        }

                    # Update history
                    history.setdefault("matches", []).append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "type": "ffa",
                        "players": finishing_order,
                        "winner": finishing_order[0]
                    })

                    save_leaderboard_to_git(game_name, leaderboard,
                                            commit_message=f"Record FFA match for {game_name}")
                    save_history_to_git(game_name, history,
                                        commit_message=f"Add FFA match to {game_name} history")
                    st.success("Free-for-All game recorded successfully!")

                except Exception as e:
                    st.error(f"Failed to record FFA game: {e}")
