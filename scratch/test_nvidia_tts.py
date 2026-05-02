import requests
import os
import dotenv

dotenv.load_dotenv()
api_key = os.getenv("NVIDIA_NIM_API_KEY")

urls = [
    "https://integrate.api.nvidia.com/v1/audio/speech",
    "https://ai.api.nvidia.com/v1/audio/speech"
]

for url in urls:
    print(f"Trying {url}")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "nvidia/magpie-tts-zeroshot",
        "input": "This is a test of the NVIDIA magpie text to speech model.",
        "voice": "A deep voice."
    }
    resp = requests.post(url, headers=headers, json=payload)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        print("Success! Got audio.")
        break
    else:
        print(resp.text[:200])
