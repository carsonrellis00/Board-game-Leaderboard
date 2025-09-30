import requests
import streamlit as st
import base64

# ---- Load secrets ----
GITLAB_TOKEN = st.secrets["GITLAB_TOKEN"]
GITLAB_REPO = st.secrets["GITLAB_REPO"]
GITLAB_BRANCH = st.secrets.get("GITLAB_BRANCH", "main")

API_BASE = "https://gitlab.com/api/v4"

def update_file_in_gitlab(file_path: str, content: str, commit_message: str):
    """
    Create or update a file in GitLab.
    """
    url = f"{API_BASE}/projects/{requests.utils.quote(GITLAB_REPO, safe='')}/repository/files/{requests.utils.quote(file_path, safe='')}"
    
    headers = {"PRIVATE-TOKEN": GITLAB_TOKEN}
    data = {
        "branch": GITLAB_BRANCH,
        "content": content,
        "commit_message": commit_message,
    }

    # Try to update
    r = requests.put(url, headers=headers, data=data)
    if r.status_code == 200:
        return True
    if r.status_code == 404:
        # File does not exist, create it
        r = requests.post(url, headers=headers, data=data)
        return r.status_code == 201

    st.error(f"GitLab update failed: {r.status_code}, {r.text}")
    return False


def get_file_from_gitlab(file_path: str):
    """
    Get a file's content from GitLab as a string.
    Returns None if file doesn't exist or fails.
    """
    url = f"{API_BASE}/projects/{requests.utils.quote(GITLAB_REPO, safe='')}/repository/files/{requests.utils.quote(file_path, safe='')}?ref={GITLAB_BRANCH}"
    headers = {"PRIVATE-TOKEN": GITLAB_TOKEN}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        file_info = r.json()
        encoded_content = file_info.get("content", "")
        # Decode Base64
        decoded_bytes = base64.b64decode(encoded_content)
        return decoded_bytes.decode("utf-8")
    elif r.status_code == 404:
        return None
    else:
        st.error(f"Failed to fetch {file_path} from GitLab: {r.status_code}, {r.text}")
        return None
