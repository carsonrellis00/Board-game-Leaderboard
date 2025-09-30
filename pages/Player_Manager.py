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

st.set_page_config(page_title="Player Manager", page_icon="🎲")
st.title("🎲 Game Manager")

# --- TrueSkill environment ---
env = trueskill.TrueSkill(draw_probability=0)

# --- Tabs: Players / Match Entry ---
tab_players, tab_matches = st.tabs(["👥 Manage Players", "✏️ Record Game"])

# ---------------- Manage Players Tab ----------------
with tab_players:
    st.header("Add / Remove Players (persistent in GitLab)")

    # Load players
    try:
        players = load_players_from_git() or []
    except Exception as e:
        st.error(f"Failed to load players: {e}")
        players = []

    # Add Player
    with st.form("add_player_form", clear_on_submit=True):
        new_player = st.text_input("Player name")
        submitted = st.form_submit_button("Add Player")
        if submitted:
            new_player = new_player.strip()
            if not new_player:
                st.warning("Please enter a name.")
            elif new_player in players:
                st.info(f"{new_player} already exists.")
            else:
                try:
                    players.append(new_player)
                    save_players_to_git(players)
                    st.success(f"{new_player} added.")
                except Exception as e:
                    st.error(f"Failed to save new player: {e}")

    st.markdown("---")

    # Remove Player
    st.header("Remove Player")
    if players:
        remove_player = st.selectbox("Select player to remove", [""] + players)
        if st.button("Remove Player") and remove_player:
            try:
                players.remove(remove_player)
                save_players_to_git(players)
                st.success(f"{remove_player} removed.")
            except Exception as e:
                st.error(f"Failed to remove player: {e}")
    else:
        st.info("No players found. Add players above.")

    st.markdown("---")

    # Current players
    st.header("Current Players")
    if players:
        st.write(", ".join(players))
    else:
        st.info("No players yet.")

# ---------------- Record Game Tab ----------------
with tab_matches:
    st.header("Record a Game")

    # Reload players in case updated
    try:
        all_players = load_players_from_git() or []
    except Exception as e:
        st.error(f"Failed to load players: {e}")
        st.stop()

    if not all_players:
        st.warning("No players available. Add players first.")
        st.stop()

    # Select game
    files = gitlab_list_leaderboards_dir()
    game_names = sorted(list({fn.replace("_leaderboard.json","").replace("_history.json","") for fn in files if fn.endswith(".json")}))
    game_option = st.selectbox("Select a game (or type new)", options=["<New Game>"] + game_names)

    if game_option == "<New Game>":
        game_name_input = st.text_input("New game name")
        game_name = game_name_input.strip() if game_name_input else None
    else:
        game_name = game_option

    if not game_name:
        st.info("Pick or type a game name to record matches for.")
        st.stop()

    st.subheader(f"Recording for game: {game_name}")

    # Load leaderboard & history
    leaderboard = load_leaderboard_from_git(game_name) or {}
    history = load_history_from_git(game_name) or {"matches": []}

    tab_individual, tab_team = st.tabs(["Individual", "Team"])

    # --- Individual tab ---
    with tab_individual:
        ordered = st.multiselect("Select players in finishing order (winner first)", options=all_players)
        if st.button("Record Individual Game"):
            if len(ordered) < 2:
                st.warning("Select at least two players.")
            else:
                try:
                    ratings = [env.Rating(mu=leaderboard.get(n, {}).get("mu",25.0),
                                           sigma=leaderboard.get(n, {}).get("sigma",8.333)) for n in ordered]
                    ranks = list(range(len(ratings)))
                    new_ratings = env.rate(ratings, ranks=ranks)
                    for name, r in zip(ordered, new_ratings):
                        leaderboard[name] = {"mu": r.mu, "sigma": r.sigma}
                    history.setdefault("matches", []).append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "type": "individual",
                        "results": ordered
                    })
                    save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record individual match for {game_name}")
                    save_history_to_git(game_name, history, commit_message=f"Add match to {game_name} history")
                    st.success("Individual game recorded and pushed to GitLab.")
                except Exception as e:
                    st.error(f"Failed to record game: {e}")

    # --- Team tab ---
    with tab_team:
        selected_players = st.multiselect("Select all players for this team match", options=all_players)
        if selected_players:
            team_a = st.multiselect("Team A players", options=selected_players)
            team_b = [p for p in selected_players if p not in team_a]
            st.write("Team B:", ", ".join(team_b) if team_b else "(empty)")
            winner = st.radio("Winner", options=["Team A", "Team B"])
            if st.button("Record Team Game"):
                if not team_a or not team_b:
                    st.warning("Both teams must have at least one player.")
                else:
                    try:
                        ratings_a = [env.Rating(mu=leaderboard.get(n, {}).get("mu",25.0),
                                                sigma=leaderboard.get(n, {}).get("sigma",8.333)) for n in team_a]
                        ratings_b = [env.Rating(mu=leaderboard.get(n, {}).get("mu",25.0),
                                                sigma=leaderboard.get(n, {}).get("sigma",8.333)) for n in team_b]
                        ranks = [0,1] if winner == "Team A" else [1,0]
                        new_team_ratings = env.rate([ratings_a, ratings_b], ranks=ranks)
                        for name, r in zip(team_a, new_team_ratings[0]):
                            leaderboard[name] = {"mu": r.mu, "sigma": r.sigma}
                        for name, r in zip(team_b, new_team_ratings[1]):
                            leaderboard[name] = {"mu": r.mu, "sigma": r.sigma}
                        history.setdefault("matches", []).append({
                            "timestamp": datetime.utcnow().isoformat(),
                            "type": "team",
                            "team_a": team_a,
                            "team_b": team_b,
                            "winner": winner
                        })
                        save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record team match for {game_name}")
                        save_history_to_git(game_name, history, commit_message=f"Add team match to {game_name} history")
                        st.success("Team game recorded and pushed to GitLab.")
                    except Exception as e:
                        st.error(f"Failed to record team game: {e}")

st.markdown("---")
st.info("This page writes directly to your GitLab repository. Make sure your GITLAB_TOKEN and PROJECT_ID are set in Streamlit secrets or environment variables.")

