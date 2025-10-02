# --- 1v1 ---
if game_type == "1v1":
    st.subheader("1v1 Match")
    p1 = st.selectbox("Player 1", players, key="1v1_p1")
    p2 = st.selectbox("Player 2", players, key="1v1_p2")

    if p1 == p2:
        st.warning("Select two different players.")
        st.stop()

    # Ensure both players exist in leaderboard
    for p in [p1, p2]:
        if p not in leaderboard:
            leaderboard[p] = {"mu": env.mu, "sigma": env.sigma, "wins": 0}

    winner = st.radio("Winner", [p1, p2], key="1v1_winner")

    if st.button("Record 1v1 Game"):
        try:
            # Create ratings
            r1 = env.create_rating(leaderboard[p1]["mu"], leaderboard[p1]["sigma"])
            r2 = env.create_rating(leaderboard[p2]["mu"], leaderboard[p2]["sigma"])

            # Wrap each player in a list (group) and set ranks
            if winner == p1:
                rated = env.rate([[r1], [r2]], ranks=[0, 1])
            else:
                rated = env.rate([[r2], [r1]], ranks=[0, 1])

            leaderboard[p1]["mu"], leaderboard[p1]["sigma"] = rated[0][0].mu, rated[0][0].sigma
            leaderboard[p2]["mu"], leaderboard[p2]["sigma"] = rated[1][0].mu, rated[1][0].sigma
            leaderboard[winner]["wins"] += 1

            save_leaderboard_to_git(selected_game, leaderboard)

            # Update history
            history_entry = {
                "type": "1v1",
                "players": [p1, p2],
                "winner": winner
            }
            if "matches" not in history:
                history["matches"] = []
            history["matches"].append(history_entry)
            save_history_to_git(selected_game, history)

            st.success("1v1 game recorded.")
        except Exception as e:
            st.error(f"Failed to record 1v1 game: {e}")
