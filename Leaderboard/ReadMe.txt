Hello!
----------------------------------
Math:

TrueSkill Microsoft patented flexible Elo rating system
μ (mu)

μ = 27.06

This is the mean skill estimate for the player.

Higher μ → stronger expected performance.

Think of it as “how good the system thinks the player is.”

σ (sigma)
 

σ = 4.55

This is the uncertainty in the skill estimate.

Higher σ → the system is less certain about the player’s true skill.

Lower σ → the system is confident about their skill.

Conservative Rating (rating)


rating = μ - 3σ = 13.40

This is a conservative estimate of the player’s skill.

The formula μ - 3σ comes from TrueSkill’s standard approach: it ensures that with high probability (≈99.7%) the player’s true skill is at least this rating.

It’s used to rank players safely, accounting for uncertainty.

----------------------------------

Open web app:
py -m streamlit run "C:\Users\Carson\Documents\Leaderboard\leaderboard_web_app.py"
Manage games in here: leaderboard_web_app.py

Viewers: leaderboard_viewer.py