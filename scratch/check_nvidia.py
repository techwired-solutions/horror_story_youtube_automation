import requests
import os
import dotenv

dotenv.load_dotenv()
api_key = os.getenv("NVIDIA_NIM_API_KEY")
url = "https://integrate.api.nvidia.com/v1/models"
headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
resp = requests.get(url, headers=headers)
if resp.status_code == 200:
    models = resp.json()["data"]
    for m in models:
        if "audio" in m["id"] or "voice" in m["id"] or "tts" in m["id"]:
            print(m["id"])
else:
    print(resp.status_code, resp.text)
