import os
import json
import requests
from urllib.parse import quote, unquote

# --- Configuration ---
GITLAB_PROJECT_ID = os.getenv("GITLAB_PROJECT_ID")
GITLAB_TOKEN = os.getenv("GITLAB_TOKEN")
GITLAB_BRANCH = os.getenv("GITLAB_BRANCH", "main")
API_BASE = f"https://gitlab.com/api/v4/projects/{GITLAB_PROJECT_ID}"
HEADERS = {"PRIVATE-TOKEN": GITLAB_TOKEN}


# --- Helpers ---
def _normalize_game_basename(name: str) -> str:
    if not name:
        return name
    name = os.path.basename(name)
    name = name.replace("+", " ")
    name = unquote(name)
    for suffix in ("_leaderboard.json", "_history.json", ".json"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
    return name


def _leaderboard_path_for_game(game_name: str) -> str:
    base = _normalize_game_basename(game_name)
    return f"leaderboards/{base}_leaderboard.json"


def _history_path_for_game(game_name: str) -> str:
    base = _normalize_game_basename(game_name)
    return f"leaderboards/{base}_history.json"


# --- GitLab utilities ---
def gitlab_raw_get(file_path):
    url_path = quote(file_path, safe="")
    url = f"{API_BASE}/repository/files/{url_path}/raw?ref={GITLAB_BRANCH}"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    if resp.status_code == 200:
        try:
            return 200, resp.json()
        except Exception:
            return 200, resp.text
    return resp.status_code, resp.text


def gitlab_file_exists(file_path):
    url_path = quote(file_path, safe="")
    url = f"{API_BASE}/repository/files/{url_path}?ref={GITLAB_BRANCH}"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    return resp.status_code == 200


def gitlab_create_or_update_file(file_path, data, commit_message):
    content = json.dumps(data, indent=2, ensure_ascii=False)
    url_path = quote(file_path, safe="")
    api_path = f"{API_BASE}/repository/files/{url_path}"
    payload = {
        "branch": GITLAB_BRANCH,
        "content": content,
        "commit_message": commit_message,
        "encoding": "text",
    }
    if gitlab_file_exists(file_path):
        resp = requests.put(api_path, headers=HEADERS, json=payload, timeout=20)
    else:
        resp = requests.post(api_path, headers=HEADERS, json=payload, timeout=20)
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"GitLab API error {resp.status_code}: {resp.text}")
    return resp.json()


# --- Players ---
def load_players_from_git():
    status, data = gitlab_raw_get("leaderboards/players.json")
    if status == 200:
        if isinstance(data, dict) and "players" in data and isinstance(data["players"], list):
            return data
        elif isinstance(data, list):
            return {"players": data}
    return {"players": []}


def save_players_to_git(players_dict, commit_message="Update players list"):
    if not isinstance(players_dict, dict) or "players" not in players_dict:
        players_dict = {"players": list(players_dict) if isinstance(players_dict, list) else []}
    gitlab_create_or_update_file("leaderboards/players.json", players_dict, commit_message)


# --- Leaderboards ---
def load_leaderboard_from_git(game_name):
    file_path = _leaderboard_path_for_game(game_name)
    status, data = gitlab_raw_get(file_path)
    if status == 200 and isinstance(data, dict):
        return data
    return {}


def save_leaderboard_to_git(game_name, leaderboard_dict, commit_message=None):
    file_path = _leaderboard_path_for_game(game_name)
    if commit_message is None:
        commit_message = f"Update {game_name} leaderboard"
    gitlab_create_or_update_file(file_path, leaderboard_dict, commit_message)


# --- History ---
def load_history_from_git(game_name):
    file_path = _history_path_for_game(game_name)
    status, data = gitlab_raw_get(file_path)
    if status == 200 and isinstance(data, dict):
        return data
    return {"matches": []}


def save_history_to_git(game_name, history_dict, commit_message=None):
    file_path = _history_path_for_game(game_name)
    if commit_message is None:
        commit_message = f"Update {game_name} history"
    gitlab_create_or_update_file(file_path, history_dict, commit_message)


# --- List leaderboards ---
def gitlab_list_leaderboards_dir():
    url = f"{API_BASE}/repository/tree?ref={GITLAB_BRANCH}&path=leaderboards"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    if resp.status_code == 200:
        files = [f["name"] for f in resp.json() if f["name"].endswith("_leaderboard.json")]
        return files
    return []
