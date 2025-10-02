import streamlit as st
from trueskill import TrueSkill, Rating
from GitLab_Persistence import (
    load_players_from_git,
    load_leaderboard_from_git,
    save_leaderboard_to_git,
    load_history_from_git,
    save_history_to_git,
)

# --- Setup TrueSkill environment ---
env = TrueSkill(draw_probability=0.0)

# --- Helper to safely get a player's rating ---
def get_rating(player_name, leaderboard, env):
    """
    Return a trueskill.Rating object for the given player.
    Defaults to env.mu/env.sigma if player is new.
    """
    if player_name in leaderboard:
        mu = leaderboard[player_name].get("mu", env.mu)
        sigma = leaderboard[player_name].get("sigma", env.sigma)
    else:
        mu, sigma = env.mu, env.sigma
    return Rating(mu=mu, sigma=sigma)


# --- UI Setup ---
st.title("🎮 Play a Game")

# Load players
players_dict = load_players_from_git()
players = players_dict.get("players", [])

if not players:
    st.warning("No players yet. Add some in Player Manager first.")
    st.stop()

# Select game
leaderboards = [lb.replace("_leaderboard.json", "") for lb in
                []]  # placeholder if you don’t yet have list logic
selected_game = st.selectbox("Select Game", leaderboards)

if not selected_game:
    st.stop()

leaderboard = load_leaderboard_from_git(selected_game)
history = load_history_from_git(selected_game)

# Select game mode
mode = st.radio("Choose Game Type", ["1v1", "Team", "Free-for-All"], horizontal=True)


# --- 1v1 Mode ---
if mode == "1v1":
    st.subheader("⚔️ 1v1 Match")

    p1 = st.selectbox("Player 1", players, key="1v1_p1")
    p2 = st.selectbox("Player 2", [p for p in players if p != p1], key="1v1_p2")
    winner = st.radio("Winner", [p1, p2], key="1v1_winner")

    if st.button("Record 1v1 Game", key="record_1v1"):
        try:
            r1 = get_rating(p1, leaderboard, env)
            r2 = get_rating(p2, leaderboard, env)

            rating_groups = [[r1], [r2]]
            ranks = [0, 1] if winner == p1 else [1, 0]
            new_ratings = env.rate(rating_groups, ranks=ranks)

            leaderboard[p1] = {"mu": new_ratings[0][0].mu, "sigma": new_ratings[0][0].sigma}
            leaderboard[p2] = {"mu": new_ratings[1][0].mu, "sigma": new_ratings[1][0].sigma}

            save_leaderboard_to_git(selected_game, leaderboard)
            history["matches"].append({"type": "1v1", "p1": p1, "p2": p2, "winner": winner})
            save_history_to_git(selected_game, history)

            st.success("1v1 game recorded successfully!")
            st.experimental_rerun()
        except Exception as e:
            st.error(f"Failed to record 1v1 game: {e}")


# --- Team Mode ---
elif mode == "Team":
    st.subheader("👥 Team Match")

    selected_players = st.multiselect("Select players", players, key="team_players")
    if len(selected_players) < 2:
        st.info("Pick at least 2 players to form teams.")
    else:
        team1 = st.multiselect("Team 1", selected_players, key="team1")
        team2 = [p for p in selected_players if p not in team1]

        if team1 and team2:
            winner = st.radio("Winning Team", ["Team 1", "Team 2"], key="team_winner")

            if st.button("Record Team Game", key="record_team"):
                try:
                    team1_ratings = [get_rating(p, leaderboard, env) for p in team1]
                    team2_ratings = [get_rating(p, leaderboard, env) for p in team2]

                    rating_groups = [team1_ratings, team2_ratings]
                    ranks = [0, 1] if winner == "Team 1" else [1, 0]

                    new_ratings = env.rate(rating_groups, ranks=ranks)

                    for i, player in enumerate(team1):
                        leaderboard[player] = {"mu": new_ratings[0][i].mu, "sigma": new_ratings[0][i].sigma}
                    for i, player in enumerate(team2):
                        leaderboard[player] = {"mu": new_ratings[1][i].mu, "sigma": new_ratings[1][i].sigma}

                    save_leaderboard_to_git(selected_game, leaderboard)
                    history["matches"].append({
                        "type": "team",
                        "team1": team1,
                        "team2": team2,
                        "winner": winner
                    })
                    save_history_to_git(selected_game, history)

                    st.success("Team game recorded successfully!")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"Failed to record team game: {e}")


# --- Free-for-All Mode ---
elif mode == "Free-for-All":
    st.subheader("🎲 Free-for-All")

    selected_players_ffa = st.multiselect("Select players", players, key="ffa_players")
    finishing_order = st.session_state.get("ffa_finishing_order", [])

    if selected_players_ffa:
        remaining = [p for p in selected_players_ffa if p not in finishing_order]

        if remaining:
            pick = st.selectbox(
                f"Next finisher ({len(finishing_order)+1})",
                options=remaining,
                key=f"ffa_pick_{len(finishing_order)}"
            )
            if st.button("Add Finisher", key=f"ffa_add_{len(finishing_order)}"):
                finishing_order.append(pick)
                st.session_state["ffa_finishing_order"] = finishing_order
                st.experimental_rerun()

        st.write("**Finishing order so far:**", " → ".join(finishing_order))

    if len(finishing_order) == len(selected_players_ffa) and st.button("Record FFA Game", key="record_ffa"):
        try:
            rating_groups = [[get_rating(p, leaderboard, env)] for p in finishing_order]
            ranks = list(range(len(finishing_order)))

            new_ratings = env.rate(rating_groups, ranks=ranks)

            for idx, player in enumerate(finishing_order):
                new_rating = new_ratings[idx][0]
                leaderboard[player] = {"mu": new_rating.mu, "sigma": new_rating.sigma}

            save_leaderboard_to_git(selected_game, leaderboard)
            history["matches"].append({"type": "FFA", "order": finishing_order})
            save_history_to_git(selected_game, history)

            st.success("FFA game recorded successfully!")
            st.session_state["ffa_finishing_order"] = []
            st.experimental_rerun()
        except Exception as e:
            st.error(f"Failed to record FFA game: {e}")
