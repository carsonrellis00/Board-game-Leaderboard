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

# --- Helper functions ---
def get_player_rating(player_name, leaderboard, env):
    """Return a dict with mu, sigma, wins for a player."""
    if player_name in leaderboard:
        r = leaderboard[player_name]
        return {
            "mu": r.get("mu", env.mu),
            "sigma": r.get("sigma", env.sigma),
            "wins": r.get("wins", 0)
        }
    else:
        return {"mu": env.mu, "sigma": env.sigma, "wins": 0}

# --- Game type selection ---
game_type = st.radio("Select game type", ["1v1", "Team", "Free For All (FFA)"])

if game_type == "1v1":
    selected_players = st.multiselect("Select 2 players", options=players, max_selections=2)
    if len(selected_players) != 2:
        st.stop()
    winner = st.radio("Select winner", options=selected_players)
    if st.button("Record 1v1 game"):
        try:
            p1, p2 = selected_players
            ratings = [
                [trueskill.Rating(mu=get_player_rating(p1, leaderboard, env)["mu"],
                                  sigma=get_player_rating(p1, leaderboard, env)["sigma"])],
                [trueskill.Rating(mu=get_player_rating(p2, leaderboard, env)["mu"],
                                  sigma=get_player_rating(p2, leaderboard, env)["sigma"])]
            ]
            ranks = [0, 1] if winner == p1 else [1, 0]
            new_ratings = env.rate(ratings, ranks=ranks)

            # Update leaderboard
            for p, r in zip([p1, p2], new_ratings):
                prev = get_player_rating(p, leaderboard, env)
                leaderboard[p] = {
                    "mu": r[0].mu,
                    "sigma": r[0].sigma,
                    "wins": prev["wins"] + (1 if p == winner else 0)
                }

            # Update history
            history["matches"].append({
                "timestamp": datetime.utcnow().isoformat(),
                "type": "1v1",
                "players": [p1, p2],
                "winner": winner
            })

            # Push updates
            save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record 1v1 match for {game_name}")
            save_history_to_git(game_name, history, commit_message=f"Add 1v1 match to {game_name} history")
            st.success("1v1 game recorded successfully!")

        except Exception as e:
            st.error(f"Failed to record 1v1 game: {e}")

elif game_type == "Team":
    selected_players = st.multiselect("Select players", options=players)
    if not selected_players or len(selected_players) < 2:
        st.stop()

    st.subheader("Manual or Auto Team Assignment")
    team_mode = st.radio("Team setup", ["Manual", "Auto"])

    team_a, team_b = [], []
    if team_mode == "Manual":
        team_a = st.multiselect("Team A players", options=selected_players)
        team_b = [p for p in selected_players if p not in team_a]
    else:  # Auto
        sorted_players = sorted(selected_players,
                                key=lambda p: get_player_rating(p, leaderboard, env)["mu"],
                                reverse=True)
        team_a = sorted_players[::2]
        team_b = sorted_players[1::2]

    st.write(f"Team A: {', '.join(team_a)}")
    st.write(f"Team B: {', '.join(team_b)}")

    winner = st.radio("Select winner", options=["Team A", "Team B"])
    if st.button("Record Team Game"):
        try:
            ratings_a = [trueskill.Rating(**{k: v for k, v in get_player_rating(p, leaderboard, env).items() if k != "wins"})
                         for p in team_a]
            ratings_b = [trueskill.Rating(**{k: v for k, v in get_player_rating(p, leaderboard, env).items() if k != "wins"})
                         for p in team_b]
            ranks = [0, 1] if winner == "Team A" else [1, 0]
            new_ratings = env.rate([ratings_a, ratings_b], ranks=ranks)

            for p, r in zip(team_a, new_ratings[0]):
                prev = get_player_rating(p, leaderboard, env)
                leaderboard[p] = {"mu": r.mu, "sigma": r.sigma, "wins": prev["wins"] + (1 if winner == "Team A" else 0)}
            for p, r in zip(team_b, new_ratings[1]):
                prev = get_player_rating(p, leaderboard, env)
                leaderboard[p] = {"mu": r.mu, "sigma": r.sigma, "wins": prev["wins"] + (1 if winner == "Team B" else 0)}

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

else:  # FFA
    selected_players = st.multiselect("Select players", options=players)
    if not selected_players or len(selected_players) < 2:
        st.stop()

    st.subheader("Assign finishing positions")
    positions = {}
    for p in selected_players:
        positions[p] = st.number_input(f"Position for {p} (1=winner)", min_value=1, max_value=len(selected_players), value=len(selected_players))

    if st.button("Record FFA Game"):
        try:
            finishing_order = sorted(positions, key=lambda p: positions[p])
            ratings_list = [[trueskill.Rating(mu=get_player_rating(p, leaderboard, env)["mu"],
                                             sigma=get_player_rating(p, leaderboard, env)["sigma"])]
                            for p in finishing_order]
            ranks = list(range(len(finishing_order)))
            new_ratings = env.rate(ratings_list, ranks=ranks)

            # Update leaderboard
            for p, r in zip(finishing_order, new_ratings):
                prev = get_player_rating(p, leaderboard, env)
                leaderboard[p] = {
                    "mu": r[0].mu,
                    "sigma": r[0].sigma,
                    "wins": prev["wins"] + (1 if positions[p] == 1 else 0)
                }

            # Update history
            history["matches"].append({
                "timestamp": datetime.utcnow().isoformat(),
                "type": "ffa",
                "players": finishing_order,
                "positions": positions
            })

            save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record FFA match for {game_name}")
            save_history_to_git(game_name, history, commit_message=f"Add FFA match to {game_name} history")
            st.success("FFA game recorded successfully!")
        except Exception as e:
            st.error(f"Failed to record FFA game: {e}")
