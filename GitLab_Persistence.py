import os
import json
import requests
from urllib.parse import quote, unquote

# --- Configuration ---
GITLAB_PROJECT_ID = os.getenv("GITLAB_PROJECT_ID")
GITLAB_TOKEN = os.getenv("GITLAB_TOKEN")
BRANCH = os.getenv("GITLAB_BRANCH", "main")

API_BASE = f"https://gitlab.com/api/v4/projects/{GITLAB_PROJECT_ID}"
HEADERS = {"PRIVATE-TOKEN": GITLAB_TOKEN}


# --- Helpers for clean game names ---
def _normalize_game_basename(name: str) -> str:
    """
    Convert a supplied game identifier into a clean basename.

    - Removes known suffixes if present (_leaderboard.json, _history.json, .json)
    - Converts '+' to spaces and URL-decodes any %XX encodings
    - Strips any folder components
    """
    if not name:
        return name
    # ensure no folder path
    name = os.path.basename(name)
    # decode URL encodings and plus signs
    name = name.replace("+", " ")
    name = unquote(name)
    # strip known suffixes
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


# --- GitLab raw file utilities ---
def gitlab_raw_get(file_path):
    """Return (status_code, parsed_json_or_text)."""
    url_path = quote(file_path, safe="")  # spaces → %20, no +
    url = f"{API_BASE}/repository/files/{url_path}/raw?ref={BRANCH}"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    if resp.status_code == 200:
        try:
            return 200, resp.json()
        except Exception:
            return 200, resp.text
    return resp.status_code, resp.text


def gitlab_file_exists(file_path):
    url_path = quote(file_path, safe="")
    url = f"{API_BASE}/repository/files/{url_path}?ref={BRANCH}"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    return resp.status_code == 200


def gitlab_create_or_update_file(file_path, data, commit_message):
    content = json.dumps(data, indent=2, ensure_ascii=False)
    url_path = quote(file_path, safe="")
    api_path = f"{API_BASE}/repository/files/{url_path}"
    payload = {
        "branch": BRANCH,
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


# --- Player list utilities ---
def load_players_from_git():
    status, data = gitlab_raw_get("leaderboards/players.json")
    if status == 200 and isinstance(data, dict):
        return data
    return {"players": []}


def save_players_to_git(players_dict, commit_message="Update players list"):
    gitlab_create_or_update_file(
        "leaderboards/players.json", players_dict, commit_message
    )


# --- Leaderboard utilities ---
def load_leaderboard_from_git(game_name):
    file_path = _leaderboard_path_for_game(game_name)
    status, data = gitlab_raw_get(file_path)
    if status == 200 and isinstance(data, dict):
        return data
    return {}
    
def gitlab_list_leaderboards_dir():
    """
    List all leaderboard JSON files in GitLab for this project.
    Returns a list of filenames (like 'Chess_leaderboard.json').
    """
    url = f"{API_BASE}/repository/tree?ref={BRANCH}&path=leaderboards"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    if resp.status_code == 200:
        files = [f["name"] for f in resp.json() if f["name"].endswith("_leaderboard.json")]
        return files
    return []


def save_leaderboard_to_git(
    game_name, leaderboard_dict, commit_message=None
):
    file_path = _leaderboard_path_for_game(game_name)
    if commit_message is None:
        commit_message = f"Update {game_name} leaderboard"
    gitlab_create_or_update_file(file_path, leaderboard_dict, commit_message)


# --- History utilities ---
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


