# pages/Play_A_Game.py
import streamlit as st
import trueskill
from datetime import datetime
from GitLab_Persistence import (
    load_players_from_git,
    save_players_to_git,
    load_leaderboard_from_git,
    save_leaderboard_to_git,
    load_history_from_git,
    save_history_to_git,
    gitlab_list_leaderboards_dir
)

st.set_page_config(page_title="Record Game & Matchmaking", page_icon="⚔️")

st.title("⚔️ Record Game & Matchmaking")

# --- TrueSkill environment ---
env = trueskill.TrueSkill(draw_probability=0)

# --- Load players ---
all_players = load_players_from_git()
if not all_players:
    st.warning("No players found. Add players in 'Player Manager' first.")
    st.stop()

# --- Select game ---
files = gitlab_list_leaderboards_dir()
game_names = sorted(list({fn.replace("_leaderboard.json","").replace("_history.json","") 
                          for fn in files if fn.endswith(".json")}))
game_option = st.selectbox("Select game (or type a new name)", options=["<New Game>"] + game_names)

if game_option == "<New Game>":
    game_name_input = st.text_input("New game name")
    game_name = game_name_input.strip() if game_name_input else None
else:
    game_name = game_option

if not game_name:
    st.info("Pick or type a game name to record matches for.")
    st.stop()

# --- Load leaderboard and history ---
leaderboard = load_leaderboard_from_git(game_name)
history = load_history_from_git(game_name)

# --- Team selection ---
st.subheader(f"Recording for game: {game_name}")
selected_players = st.multiselect("Players", options=all_players)

def get_mu(player):
    """Safe retrieval of a player's mu rating."""
    entry = leaderboard.get(player)
    if isinstance(entry, dict):
        return entry.get("mu", env.mu)
    return env.mu

def auto_balance_teams(players):
    """Split players into two balanced teams by TrueSkill."""
    if not players:
        return [], []

    sorted_players = sorted(players, key=get_mu, reverse=True)
    team_a, team_b = [], []
    rating_a, rating_b = 0, 0
    for p in sorted_players:
        mu = get_mu(p)
        if rating_a <= rating_b:
            team_a.append(p)
            rating_a += mu
        else:
            team_b.append(p)
            rating_b += mu
    return team_a, team_b

team_a, team_b = auto_balance_teams(selected_players)

# --- Team selection UI ---
st.write("Team A:", ", ".join(team_a) if team_a else "(empty)")
st.write("Team B:", ", ".join(team_b) if team_b else "(empty)")

winner = st.radio("Select winning team", options=["Team A", "Team B"])

if st.button("Record Team Game"):
    if not team_a or not team_b:
        st.warning("Both teams must have at least one player.")
    else:
        try:
            # Prepare ratings
            ratings_a = [env.Rating(mu=leaderboard.get(p, {}).get("mu", env.mu),
                                    sigma=leaderboard.get(p, {}).get("sigma", env.sigma)) 
                         for p in team_a]
            ratings_b = [env.Rating(mu=leaderboard.get(p, {}).get("mu", env.mu),
                                    sigma=leaderboard.get(p, {}).get("sigma", env.sigma)) 
                         for p in team_b]

            # Determine ranks
            if winner == "Team A":
                new_ratings = env.rate([ratings_a, ratings_b], ranks=[0,1])
            else:
                new_ratings = env.rate([ratings_a, ratings_b], ranks=[1,0])

            # Update leaderboard
            for p, r in zip(team_a, new_ratings[0]):
                leaderboard[p] = {"mu": r.mu, "sigma": r.sigma}
            for p, r in zip(team_b, new_ratings[1]):
                leaderboard[p] = {"mu": r.mu, "sigma": r.sigma}

            # Update history
            history.setdefault("matches", []).append({
                "timestamp": datetime.utcnow().isoformat(),
                "team_a": team_a,
                "team_b": team_b,
                "winner": winner
            })

            # Save to GitLab
            save_leaderboard_to_git(game_name, leaderboard, commit_message=f"Record team match for {game_name}")
            save_history_to_git(game_name, history, commit_message=f"Add team match to {game_name} history")
            st.success("Team game recorded successfully!")

        except Exception as e:
            st.error(f"Failed to record game: {e}")
