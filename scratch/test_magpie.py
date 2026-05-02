import requests
import os
import dotenv

dotenv.load_dotenv()
api_key = os.getenv("NVIDIA_NIM_API_KEY")

url = "https://ai.api.nvidia.com/v1/audio/speech"
headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "Accept": "application/json"}
payload = {
    "model": "nvidia/magpie-tts-zeroshot",
    "input": "This is a test of the NVIDIA magpie text to speech model.",
    "voice": "A deep male voice."
}
resp = requests.post(url, headers=headers, json=payload)
print(f"Status: {resp.status_code}")
print(resp.text[:200])
