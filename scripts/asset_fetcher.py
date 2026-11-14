"""Free stock search with provider fallbacks and an auditable credit manifest."""
import json
import os
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv()


class AssetFetcher:
    def __init__(self):
        self.session = requests.Session()

    def search(self, query, orientation="portrait", kind="photo"):
        for provider in ("pexels", "pixabay"):
            key = os.getenv(provider.upper() + "_API_KEY")
            if not key:
                continue
            try:
                if provider == "pexels":
                    url = "https://api.pexels.com/videos/search" if kind == "video" else "https://api.pexels.com/v1/search"
                    data = self.session.get(url, headers={"Authorization": key}, params={
                        "query": query, "orientation": orientation, "per_page": 5}, timeout=30)
                    data.raise_for_status()
                    for item in data.json().get("videos" if kind == "video" else "photos", []):
                        files = [f for f in item.get("video_files", []) if f.get("file_type") == "video/mp4" and f.get("width", 0) <= 1920]
                        if kind == "video" and not files:
                            continue
                        return {"url": max(files, key=lambda f: f.get("width", 0))["link"] if kind == "video" else item["src"]["large2x"],
                                "page_url": item["url"], "creator": item.get("photographer", item.get("user", {}).get("name", "")),
                                "provider": provider, "kind": kind, "license_url": "https://www.pexels.com/license/"}
                else:
                    url = "https://pixabay.com/api/videos/" if kind == "video" else "https://pixabay.com/api/"
                    params = {"key": key, "q": query[:100], "safesearch": "true", "per_page": 5}
                    if kind == "photo":
                        params.update(image_type="photo", orientation="horizontal" if orientation == "landscape" else "vertical")
                    data = self.session.get(url, params=params, timeout=30)
                    data.raise_for_status()
                    for item in data.json().get("hits", []):
                        return {"url": item["videos"]["medium"]["url"] if kind == "video" else item["largeImageURL"],
                                "page_url": item["pageURL"], "creator": item.get("user", ""),
                                "provider": provider, "kind": kind, "license_url": "https://pixabay.com/service/license-summary/"}
            except (requests.RequestException, KeyError, ValueError):
                # Do not log request URLs containing API keys.
                continue
        return None

    def fetch_scene(self, query, stem, orientation="portrait", prefer_video=True):
        asset = self.search(query, orientation, "video") if prefer_video else None
        asset = asset or self.search(query, orientation, "photo")
        if not asset:
            raise RuntimeError(f"No free stock visual for {query!r}; configure PEXELS_API_KEY or PIXABAY_API_KEY or refine query")
        path = Path(str(stem) + (".mp4" if asset["kind"] == "video" else ".jpg"))
        self.download_asset(asset["url"], str(path))
        asset["local_path"] = str(path)
        path.with_suffix(path.suffix + ".credit.json").write_text(json.dumps(asset, indent=2), encoding="utf-8")
        return asset

    def generate_image(self, prompt, width=1080, height=1920):
        asset = self.search(prompt[:100], "landscape" if width > height else "portrait")
        if not asset:
            raise RuntimeError("No stock photo found")
        return asset["url"]

    def download_asset(self, url, output_path):
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        response = self.session.get(url, timeout=60)
        response.raise_for_status()
        path.write_bytes(response.content)
        return str(path)
