import json
import os
import csv
from datetime import datetime
import trueskill
from openpyxl import Workbook
import matplotlib.pyplot as plt

# ---- Setup TrueSkill Environment ----
env = trueskill.TrueSkill(draw_probability=0.0)

# ---- Base directories for multi-game support ----
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LEADERBOARD_DIR = os.path.join(BASE_DIR, "leaderboards")
os.makedirs(LEADERBOARD_DIR, exist_ok=True)

# ---- Functions to handle multiple games ----
def list_games():
    existing_files = os.listdir(LEADERBOARD_DIR)
    existing_games = sorted(list(set(f.split("_leaderboard.json")[0] for f in existing_files if f.endswith("_leaderboard.json"))))
    return existing_games

def select_game_menu():
    existing_games = list_games()
    if existing_games:
        print("\nExisting games:")
        for i, g in enumerate(existing_games, start=1):
            print(f"{i}. {g.title()}")
    else:
        print("\nNo existing games found.")

    print("0. Create a new game")
    choice = input("Select a game by number: ").strip()
    if choice == "0" or choice.lower() == "new":
        game_name = input("Enter new game name: ").strip().lower()
    else:
        try:
            index = int(choice) - 1
            game_name = existing_games[index]
        except:
            print("Invalid choice, defaulting to new game.")
            game_name = input("Enter new game name: ").strip().lower()

    save_file = os.path.join(LEADERBOARD_DIR, f"{game_name}_leaderboard.json")
    history_file = os.path.join(LEADERBOARD_DIR, f"{game_name}_history.json")
    return game_name, save_file, history_file

# ---- Initialize first game ----
game_name, SAVE_FILE, HISTORY_FILE = select_game_menu()

# ---- Load or Initialize Leaderboard ----
def load_leaderboard():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r") as f:
            data = json.load(f)
            return {name: env.Rating(mu, sigma) for name, (mu, sigma) in data.items()}
    return {}

def save_leaderboard(leaderboard):
    data = {name: (r.mu, r.sigma) for name, r in leaderboard.items()}
    with open(SAVE_FILE, "w") as f:
        json.dump(data, f)

# ---- Load / Save History ----
def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return []

def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f)

# ---- Global Leaderboard ----
leaderboard = load_leaderboard()

# ---- Recalculate Ratings from History ----
def recalc_ratings():
    global leaderboard
    leaderboard = {}
    history = load_history()
    for entry in history:
        teams = entry["teams"]
        ranks = entry["ranks"]
        team_ratings = []
        for team in teams:
            ratings = []
            for player in team:
                if player not in leaderboard:
                    leaderboard[player] = env.Rating()
                ratings.append(leaderboard[player])
            team_ratings.append(ratings)
        new_team_ratings = env.rate(team_ratings, ranks=ranks)
        for team, new_ratings in zip(teams, new_team_ratings):
            for player, new_rating in zip(team, new_ratings):
                leaderboard[player] = new_rating
    save_leaderboard(leaderboard)

# ---- Record Team Game ----
def record_team_game(teams, ranks):
    history = load_history()
    history.append({
        "teams": teams,
        "ranks": ranks,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    save_history(history)
    recalc_ratings()

# ---- Display Leaderboard ----
def show_leaderboard():
    print(f"\n=== Leaderboard: {game_name.title()} ===")
    if not leaderboard:
        print("No players yet.")
        return
    sorted_players = sorted(
        leaderboard.items(),
        key=lambda item: item[1].mu - 3 * item[1].sigma,
        reverse=True,
    )
    for i, (name, rating) in enumerate(sorted_players, start=1):
        conservative = rating.mu - 3 * rating.sigma
        star = ""
        if i == 1:
            star = " 🥇"
        elif i == 2:
            star = " 🥈"
        elif i == 3:
            star = " 🥉"
        print(f"{i:2}. {name:10} | μ={rating.mu:.2f}, σ={rating.sigma:.2f}, rating={conservative:.2f}{star}")
    print("="*40 + "\n")

# ---- Wipe Leaderboard ----
def wipe_leaderboard():
    global leaderboard
    leaderboard = {}
    if os.path.exists(SAVE_FILE):
        os.remove(SAVE_FILE)
    if os.path.exists(HISTORY_FILE):
        os.remove(HISTORY_FILE)
    print(f"Leaderboard for {game_name.title()} wiped!\n")

# ---- Undo Last Game ----
def undo_last_game():
    history = load_history()
    if not history:
        print("No games to undo.\n")
        return
    history.pop()
    save_history(history)
    recalc_ratings()
    print("Last game undone!\n")

# ---- Show Game History ----
def show_history():
    history = load_history()
    if not history:
        print("\nNo games in history.\n")
        return

    print(f"\n=== Game History: {game_name.title()} ===")
    for i, entry in enumerate(history, start=1):
        timestamp = entry.get("timestamp", "Unknown time")
        print(f"\nGame {i} recorded at: {timestamp}")
        rank_map = {}
        for team, rank in zip(entry["teams"], entry["ranks"]):
            rank_map.setdefault(rank, []).append(",".join(team))
        for rank in sorted(rank_map.keys()):
            teams_str = " = ".join(rank_map[rank])
            print(f"  Rank {rank+1}: {teams_str}")
    print("="*40 + "\n")

# ---- Export Leaderboard to CSV ----
def export_leaderboard_csv(filename=None):
    if not leaderboard:
        print("Leaderboard is empty, nothing to export.\n")
        return
    if not filename:
        filename = os.path.join(LEADERBOARD_DIR, f"{game_name}_leaderboard.csv")

    with open(filename, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Rank", "Player", "Mu", "Sigma", "Conservative Rating"])
        sorted_players = sorted(
            leaderboard.items(),
            key=lambda item: item[1].mu - 3 * item[1].sigma,
            reverse=True,
        )
        for i, (name, rating) in enumerate(sorted_players, start=1):
            conservative = rating.mu - 3 * rating.sigma
            writer.writerow([i, name, f"{rating.mu:.2f}", f"{rating.sigma:.2f}", f"{conservative:.2f}"])

    print(f"Leaderboard exported to {filename}\n")

# ---- Export Match History to Excel ----
def export_history_excel(filename=None):
    history = load_history()
    if not history:
        print("No game history to export.\n")
        return
    if not filename:
        filename = os.path.join(LEADERBOARD_DIR, f"{game_name}_history.xlsx")

    wb = Workbook()
    ws = wb.active
    ws.title = "Match History"
    ws.append(["Game #", "Timestamp", "Rank", "Teams"])

    for i, entry in enumerate(history, start=1):
        timestamp = entry.get("timestamp", "Unknown")
        rank_map = {}
        for team, rank in zip(entry["teams"], entry["ranks"]):
            rank_map.setdefault(rank, []).append(",".join(team))
        for rank in sorted(rank_map.keys()):
            teams_str = " = ".join(rank_map[rank])
            ws.append([i, timestamp, rank + 1, teams_str])

    wb.save(filename)
    print(f"Match history exported to {filename}\n")

# ---- Plot skill progression graphs ----
def plot_skill_progression():
    history = load_history()
    if not history:
        print("No history to plot.\n")
        return

    # Track μ over time for each player
    player_history = {}

    temp_leaderboard = {}
    for entry in history:
        teams = entry["teams"]
        for team in teams:
            for player in team:
                if player not in temp_leaderboard:
                    temp_leaderboard[player] = env.Rating()
        # Rate this game
        team_ratings = [[temp_leaderboard[player] for player in team] for team in teams]
        new_team_ratings = env.rate(team_ratings, ranks=entry["ranks"])
        for team, new_ratings in zip(teams, new_team_ratings):
            for player, new_rating in zip(team, new_ratings):
                temp_leaderboard[player] = new_rating
                player_history.setdefault(player, []).append(new_rating.mu)

    # Plot each player's μ over games
    plt.figure(figsize=(10,6))
    for player, mus in player_history.items():
        plt.plot(range(1, len(mus)+1), mus, marker='o', label=player)
    plt.xlabel("Game #")
    plt.ylabel("μ (Skill Rating)")
    plt.title(f"Skill Progression for {game_name.title()}")
    plt.legend()
    plt.grid(True)
    plt.show()

# ---- Interactive Menu ----
def main():
    global game_name, SAVE_FILE, HISTORY_FILE, leaderboard

    while True:
        print(f"\n=== Managing Leaderboard for: {game_name.title()} ===")
        print("1. Show leaderboard")
        print("2. Record a new team game")
        print("3. Wipe leaderboard")
        print("4. Undo last game")
        print("5. View game history")
        print("6. Export leaderboard to CSV")
        print("7. Export match history to Excel")
        print("8. Plot skill progression graph")
        print("9. Switch game")
        print("10. Quit")
        choice = input("Choose an option: ")

        if choice == "1":
            show_leaderboard()

        elif choice == "2":
            teams_input = input(
                "Enter teams in finishing order.\n"
                "Use ';' to separate ranks and ',' to separate players.\n"
                "Use '=' between teams that tie.\n"
                "Example: Alice,Bob=Charlie,David;Eve,Frank\n"
            )
            rank_groups = [grp.strip() for grp in teams_input.split(";") if grp.strip()]
            teams = []
            ranks = []
            for rank, group in enumerate(rank_groups):
                tied_teams = [t.strip() for t in group.split("=") if t.strip()]
                for team in tied_teams:
                    players = [p.strip() for p in team.split(",") if p.strip()]
                    if players:
                        teams.append(players)
                        ranks.append(rank)

            if len(teams) < 2:
                print("Need at least 2 teams.\n")
                continue

            record_team_game(teams, ranks)
            print("Game recorded!\n")

        elif choice == "3":
            confirm = input(f"Are you sure you want to wipe the leaderboard for {game_name.title()}? (yes/no): ")
            if confirm.lower() == "yes":
                wipe_leaderboard()
            else:
                print("Cancelled.\n")

        elif choice == "4":
            undo_last_game()

        elif choice == "5":
            show_history()

        elif choice == "6":
            export_leaderboard_csv()

        elif choice == "7":
            export_history_excel()

        elif choice == "8":
            plot_skill_progression()

        elif choice == "9":
            game_name, SAVE_FILE, HISTORY_FILE = select_game_menu()
            leaderboard = load_leaderboard()
            print(f"Switched to game: {game_name.title()}\n")

        elif choice == "10":
            print("\nThank you for using the leaderboard!")
            input("Press Enter to exit...")
            break

        else:
            print("Invalid choice.\n")

if __name__ == "__main__":
    main()
