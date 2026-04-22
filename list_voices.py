import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('ELEVENLABS_API_KEY')
url = "https://api.elevenlabs.io/v1/voices"
headers = {"xi-api-key": api_key}

response = requests.get(url, headers=headers)
if response.status_code == 200:
    voices = response.json().get('voices', [])
    for v in voices[:30]:
        print(f"{v['name']}: {v['voice_id']}")
else:
    print(f"Error: {response.text}")
