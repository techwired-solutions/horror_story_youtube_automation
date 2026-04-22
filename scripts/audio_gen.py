import os
import requests
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

class AudioGenerator:
    def __init__(self):
        self.api_key = ELEVENLABS_API_KEY
        self.base_url = "https://api.elevenlabs.io/v1"

    def generate_speech(self, text: str, voice_id: str = "Aano0MRpH01ekWzUtv60", output_path: str = "assets/speech.mp3"):
        """
        Generates speech using ElevenLabs TTS with character-level timestamps.
        Default voice: Shardul K (Professional horror/storytelling voice)
        """
        # Prioritize voice ID from env if available
        voice_id = os.getenv("ELEVENLABS_VOICE_ID", voice_id)
        
        url = f"{self.base_url}/text-to-speech/{voice_id}/with-timestamps"
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        data = {
            "text": text,
            "model_id": "eleven_v3",
            "voice_settings": {
                "stability": 0.3, # Lower stability for more expressive range/emotion
                "similarity_boost": 0.75,
                "style": 0.8, # Higher style for more character delivery
                "use_speaker_boost": True
            }
        }
        
        logger.info(f"Generating speech with timestamps for: {text[:50]}...")
        response = requests.post(url, json=data, headers=headers)
        
        if response.status_code == 200:
            resp_json = response.json()
            audio_base64 = resp_json.get("audio_base64")
            alignment = resp_json.get("alignment")
            
            import base64
            audio_data = base64.b64decode(audio_base64)
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(audio_data)
            
            logger.success(f"Speech saved to {output_path}")
            return {
                "audio_path": output_path,
                "alignment": alignment
            }
        else:
            logger.error(f"Failed to generate speech: {response.text}")
            return None

    def generate_sfx(self, prompt: str, output_path: str = "assets/sfx.mp3", duration_seconds: float = None):
        """
        Generates sound effects using ElevenLabs Sound Effects API.
        """
        url = f"{self.base_url}/sound-generation"
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        data = {
            "text": prompt
        }
        if duration_seconds:
            data["duration_seconds"] = duration_seconds
            
        logger.info(f"Generating SFX for: {prompt}")
        response = requests.post(url, json=data, headers=headers)
        
        if response.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(response.content)
            logger.success(f"SFX saved to {output_path}")
            return output_path
        else:
            logger.error(f"Failed to generate SFX: {response.text}")
            return None

    def get_timestamps(self, text: str, voice_id: str = "JBFqnCBvURKb0CaYV9Yt"):
        """
        Gets word-level timestamps for captions.
        Note: This is available in the ElevenLabs WebSocket API or via specific endpoints.
        For simplicity, we'll use the 'output_format' parameter in some models or a secondary call.
        Actually, ElevenLabs TTS API v1 doesn't return timestamps in the standard MP3 response.
        We might need to use 'stream' or a different approach for true word-level sync.
        Alternative: Use Python 'edged-tts' just for timestamps or a local alignment tool.
        BUT the user specifically wants ElevenLabs.
        """
        # For now, we'll implement a placeholder or assume a manual duration estimate 
        # unless we find a better way to get alignment from ElevenLabs.
        pass

if __name__ == "__main__":
    audio = AudioGenerator()
    # audio.generate_speech("In the heart of the whispering woods, something hungry waits.")
    # audio.generate_sfx("deep atmospheric horror drone with wind")
