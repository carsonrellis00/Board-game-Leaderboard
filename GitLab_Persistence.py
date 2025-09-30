# GitLab_Persistence.py
import streamlit as st
import os, json, requests
import trueskill
from datetime import datetime
from urllib.parse import quote_plus

st.set_page_config(page_title="GitLab Persistence", page_icon="💾")

# ---------- Configuration ----------
def get_secret(name):
    # Try environment variable first, then Streamlit secrets
    v = os.getenv(name)
    if v:
        return v
    try:
        return st.secrets[name]
    except Exception:
        return None

GITLAB_TOKEN = get_secret("GITLAB_TOKEN")
PROJECT_ID = get_secret("PROJECT_ID")  # numeric ID or URL-encoded path
BRANCH = get_secret("BRANCH") or "main"

if not GITLAB_TOKEN or not PROJECT_ID:
    st.error("GitLab config missing — set GITLAB_TOKEN and PROJECT_ID as secrets or env vars.")
    st.stop()

# API base
API_BASE = f"https://gitlab.com/api/v4/projects/{PROJECT_ID}"
HEADERS = {"PRIVATE-TOKEN": GITLAB_TOKEN}

# ---------- Helper functions ----------
def gitlab_raw_get(file_path):
    """Return (status_code, parsed_json_or_text)"""
    url = f"{API_BASE}/repository/files/{quote_plus(file_path)}/raw?ref={BRANCH}"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    if resp.status_code == 200:
        try:
            return 200, resp.json()
        except Exception:
            return 200, resp.text
    return resp.status_code, resp.text

def gitlab_file_exists(file_path):
    url = f"{API_BASE}/repository/files/{quote_plus(file_path)}?ref={BRANCH}"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    return resp.status_code == 200

def gitlab_create_or_update_file(file_path, data, commit_message):
    content = json.dumps(data, indent=2, ensure_ascii=False)
    api_path = f"{API_BASE}/repository/files/{quote_plus(file_path)}"
    payload = {
        "branch": BRANCH,
        "content": content,
        "commit_message": commit_message,
        "encoding": "text"
    }
    if gitlab_file_exists(file_path):
        resp = requests.put(api_path, headers=HEADERS, json=payload, timeout=20)
    else:
        resp = requests.post(api_path, headers=HEADERS, json=payload, timeout=20)
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"GitLab API error {resp.status_code}: {resp.text}")
    return resp.json()

def gitlab_list_leaderboards_dir():
    url = f"{API_BASE}/repository/tree?path=leaderboards&ref={BRANCH}&per_page=100"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    if resp.status_code == 200:
        return [item["name"] for item in resp.json()]
    return []

# ---------- TrueSkill environment ----------
env = trueskill.TrueSkill(draw_probability=0)

# ---------- Player / Leaderboard utilities ----------
def load_players_from_git():
    file_path = "leaderboards/players.json"
    status, data = gitlab_raw_get(file_path)
    if status == 200:
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return list(data.keys())
    return []

def save_players_to_git(players_list):
    file_path = "leaderboards/players.json"
    gitlab_create_or_update_file(file_path, players_list, "Update players list")

def load_leaderboard_from_git(game_name):
    file_path = f"leaderboards/{game_name}_leaderboard.json"
    status, data = gitlab_raw_get(file_path)
    if status == 200 and isinstance(data, dict):
        return data
    return {}

def save_leaderboard_to_git(game_name, leaderboard_dict, commit_message=None):
    if commit_message is None:
        commit_message = f"Update {game_name} leaderboard"
    file_path = f"leaderboards/{game_name}_leaderboard.json"
    gitlab_create_or_update_file(file_path, leaderboard_dict, commit_message)

def load_history_from_git(game_name):
    file_path = f"leaderboards/{game_name}_history.json"
    status, data = gitlab_raw_get(file_path)
    if status == 200 and isinstance(data, dict):
        return data
    return {"matches": []}

def save_history_to_git(game_name, history_dict, commit_message=None):
    if commit_message is None:
        commit_message = f"Update {game_name} history"
    file_path = f"leaderboards/{game_name}_history.json"
    gitlab_create_or_update_file(file_path, history_dict, commit_message)
