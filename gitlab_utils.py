import base64
import requests
import streamlit as st

# Load secrets
GITLAB_TOKEN = st.secrets["GITLAB_TOKEN"]
GITLAB_REPO = st.secrets["GITLAB_REPO"]
GITLAB_BRANCH = st.secrets.get("GITLAB_BRANCH", "main")

API_BASE = "https://gitlab.com/api/v4"

def update_file_in_gitlab(file_path: str, content: str, commit_message: str):
    """
    Updates or creates a file in the GitLab repo using the API.
    
    file_path: path inside repo (e.g. "leaderboards/scythe_leaderboard.json")
    content: file contents as a string
    commit_message: message to show in repo history
    """

    url = f"{API_BASE}/projects/{requests.utils.quote(GITLAB_REPO, safe='')}/repository/files/{requests.utils.quote(file_path, safe='')}"
    
    headers = {"PRIVATE-TOKEN": GITLAB_TOKEN}
    data = {
        "branch": GITLAB_BRANCH,
        "content": content,
        "commit_message": commit_message,
    }

    # First try to update the file
    r = requests.put(url, headers=headers, data=data)
    if r.status_code == 200:
        return True
    
    # If the file doesn't exist, create it
    if r.status_code == 404:
        r = requests.post(url, headers=headers, data=data)
        return r.status_code == 201

    # Debug print if something goes wrong
    st.error(f"GitLab update failed: {r.status_code}, {r.text}")
    return False
