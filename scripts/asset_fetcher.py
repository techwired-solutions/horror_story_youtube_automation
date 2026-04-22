import os
import requests
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

class AssetFetcher:
    def __init__(self):
        self.api_key = PEXELS_API_KEY
        self.base_url = "https://api.pexels.com"

    def search_videos(self, query: str, per_page: int = 1):
        """
        Searches Pexels for videos based on context.
        """
        url = f"{self.base_url}/videos/search"
        headers = {
            "Authorization": self.api_key
        }
        params = {
            "query": query,
            "per_page": per_page,
            "orientation": "portrait"  # Priority for Shorts
        }
        
        logger.info(f"Searching Pexels for videos: {query}")
        response = requests.get(url, params=params, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if data["total_results"] > 0:
                # Return the URL of the first video's best match
                # Usually we want the highest resolution or a specific aspect ratio
                video = data["videos"][0]
                # Find a link with HD resolution if possible
                video_files = video["video_files"]
                # Sort by width or just pick the first one which is usually high quality
                best_file = video_files[0]
                for f in video_files:
                    if f["width"] == 1080 and f["height"] == 1920:
                        best_file = f
                        break
                
                return {
                    "id": video["id"],
                    "url": best_file["link"],
                    "duration": video["duration"]
                }
            else:
                logger.warning(f"No videos found for query: {query}")
                return None
    def generate_image(self, prompt: str, width: int = 1080, height: int = 1920):
        """
        Generates an image using Pollinations.ai (Free & Unlimited).
        """
        import urllib.parse
        encoded_prompt = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true&enhance=true&seed={os.urandom(4).hex()}"
        
        logger.info(f"Generating AI image for: {prompt[:50]}...")
        # We can just use the download_asset method since it's a direct URL
        return url

    def download_asset(self, url: str, output_path: str):
        """
        Downloads the asset from URL.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        logger.info(f"Downloading asset from {url} to {output_path}")
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logger.success(f"Downloaded successfully: {output_path}")
            return output_path
        else:
            logger.error(f"Failed to download asset: {response.status_code}")
            return None

if __name__ == "__main__":
    fetcher = AssetFetcher()
    # result = fetcher.search_videos("dark foggy forest")
    # if result:
    #     fetcher.download_asset(result["url"], "assets/test_video.mp4")
