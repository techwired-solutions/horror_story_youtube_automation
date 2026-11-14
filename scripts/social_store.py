"""Public GitHub image hosting and durable daily publication state."""
import base64
import hashlib
import json
import os
import time
from urllib.parse import quote
import requests


class SocialStore:
    def __init__(self, repository=None, token=None, branch="automation/social-media"):
        self.repository = repository or os.environ["GITHUB_REPOSITORY"]
        self.branch = branch
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token or os.environ['GITHUB_TOKEN']}",
                                     "Accept": "application/vnd.github+json"})
        self.base = f"https://api.github.com/repos/{self.repository}"

    def request(self, method, path, missing_ok=False, **kwargs):
        response = self.session.request(method, self.base + path, timeout=60, **kwargs)
        if response.status_code == 404 and missing_ok:
            return None
        if not response.ok:
            raise RuntimeError(f"GitHub social storage failed: HTTP {response.status_code}; check Actions contents:write permission")
        return response.json()

    def ensure_branch(self):
        repo = self.request("GET", "")
        if repo.get("private", True):
            raise ValueError("Automatic Instagram image hosting requires this repository to be public")
        if self.request("GET", f"/git/ref/heads/{self.branch}", missing_ok=True):
            return
        base = self.request("GET", f"/git/ref/heads/{repo['default_branch']}")
        self.request("POST", "/git/refs", json={"ref": f"refs/heads/{self.branch}", "sha": base["object"]["sha"]})

    def read(self, path):
        item = self.request("GET", "/contents/" + quote(path, safe="/"), missing_ok=True, params={"ref": self.branch})
        if item is None:
            return None
        return base64.b64decode(item["content"])

    def write(self, path, content):
        endpoint = "/contents/" + quote(path, safe="/")
        prior = self.request("GET", endpoint, missing_ok=True, params={"ref": self.branch})
        payload = {"message": f"Save automated social media: {path}", "branch": self.branch,
                   "content": base64.b64encode(content).decode("ascii")}
        if prior:
            if base64.b64decode(prior["content"]) == content:
                ref = self.request("GET", f"/git/ref/heads/{self.branch}")
                return self.public_url(path, ref["object"]["sha"])
            payload["sha"] = prior["sha"]
        result = self.request("PUT", endpoint, json=payload)
        return self.public_url(path, result["commit"]["sha"])

    def public_url(self, path, commit):
        return f"https://raw.githubusercontent.com/{self.repository}/{commit}/{quote(path, safe='/')}"

    def save_json(self, path, value):
        return self.write(path, json.dumps(value, indent=2, ensure_ascii=False).encode("utf-8"))


def verify_public_image(url, expected):
    # No GitHub credentials are sent: this is exactly what Instagram must fetch.
    digest = hashlib.sha256(expected).digest()
    for attempt in range(12):
        try:
            response = requests.get(url, timeout=20)
            if response.ok and hashlib.sha256(response.content).digest() == digest:
                return
        except requests.RequestException:
            pass
        if attempt < 11:
            time.sleep(3)
    raise RuntimeError("Generated image is not publicly reachable yet; rerun to resume the saved post")
