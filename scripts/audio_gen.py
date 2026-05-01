import os
import re
import asyncio
import numpy as np
import requests
from dotenv import load_dotenv
from loguru import logger
import soundfile as sf
from pydub import AudioSegment

load_dotenv()

FREESOUND_API_KEY  = os.getenv("FREESOUND_API_KEY")
HUGGINGFACE_TOKEN  = os.getenv("HUGGINGFACE_TOKEN")
HUME_API_KEY       = os.getenv("HUME_API_KEY")

SAMPLE_RATE = 24000
HUME_HORROR_VOICE_ID = os.getenv("HUME_VOICE_ID", "") 

HUME_GLOBAL_ACTING = (
    "Narrate like a late-night paranormal storyteller speaking directly into one listener's ear. "
    "Voice should feel intimate, cinematic, and unsettling. "
    "Never theatrical. Never overact. Stay natural—but dark. "
    "Build tension slowly. Let disturbing ideas linger. "
    "Use subtle whispers occasionally. Lower your voice for frightening revelations. "
    "Use breath naturally. Silence is meaningful. "
    "Every sentence should feel like a secret the listener should not hear."
)

HORROR_SFX_MAP = {
    "creak":       "wood creak",
    "door":        "creaking door",
    "whisper":     "ghost whisper",
    "wind":        "wind howling",
    "thunder":     "thunder storm",
    "heartbeat":   "heartbeat",
    "breath":      "heavy breathing",
    "scream":      "horror scream",
    "footstep":    "footsteps dark",
    "laugh":       "sinister laugh",
    "silence":     "ambient horror",
    "forest":      "dark forest night",
    "growl":       "monster growl",
    "music":       "horror ambient music",
    "ambient":     "horror ambient",
}

class AudioGenerator:
    def __init__(self):
        self.freesound_key = FREESOUND_API_KEY
        self.hf_token      = HUGGINGFACE_TOKEN
        self.hume_key      = HUME_API_KEY

    def generate_speech(self, beats: list, output_path: str = "assets/speech.mp3"):
        """
        Takes an array of beats, compiles them into a single performance script,
        generates the narration via Hume, overlays micro-breaths, and masters the audio.
        Returns: {"audio_path": str, "words": [{text, start, end}], "duration": float}
        """
        performance_script = self._compile_performance_script(beats)
        logger.info(f"Compiled Performance Script:\n{performance_script[:200]}...")

        # 1. Generate Core Narration (Hume)
        raw_output_path = output_path.replace(".mp3", "_raw.mp3")
        result = self._generate_with_hume(performance_script, raw_output_path)
        
        if not result:
            logger.error("Hume generation failed. Check API key and quota.")
            return None

        # 2. Add Micro-Breaths
        with_breaths_path = output_path.replace(".mp3", "_with_breaths.wav")
        self._overlay_micro_breaths(raw_output_path, beats, result["words"], with_breaths_path)

        # 3. Master Audio
        self._master_audio(with_breaths_path, output_path)
        
        result["audio_path"] = output_path
        return result

    def _compile_performance_script(self, beats: list) -> str:
        """
        Combines beats into one continuous narration string with punctuation shaping.
        """
        lines = []
        for beat in beats:
            text = beat.get("text", "").strip()
            # Collapse multiple spaces
            text = re.sub(r' +', ' ', text)
            
            pause = float(beat.get("pause_after", 0.0))
            if pause >= 1.0 and not text.endswith(('.', '…', '!', '?')):
                text += "..."
                
            lines.append(text)
            
            if pause >= 1.0:
                lines.append("\n\n") # Paragraph break = long pause
            elif pause >= 0.5:
                lines.append("\n")   # Line break
                
        script = " ".join(lines).replace(" \n", "\n").replace("\n ", "\n")
        script = re.sub(r' +', ' ', script)
        script = re.sub(r'\n{3,}', '\n\n', script)
        return script.strip()

    def _generate_with_hume(self, text: str, output_path: str):
        try:
            from hume import HumeClient
            from hume.tts import PostedUtterance, PostedUtteranceVoiceWithId
            client = HumeClient(api_key=self.hume_key)

            voice_kwargs = {}
            if HUME_HORROR_VOICE_ID:
                voice_kwargs["voice"] = PostedUtteranceVoiceWithId(id=HUME_HORROR_VOICE_ID)

            utterance = PostedUtterance(
                text=text,
                description=HUME_GLOBAL_ACTING,
                **voice_kwargs
            )

            logger.info("Calling Hume Octave TTS (Single Generation)...")
            response = client.tts.synthesize_json(
                utterances=[utterance],
                format={"type": "mp3"},
                include_timestamp_types=["word"],
                version="2",
            )

            if not response or not response.generations:
                return None
                
            generation = response.generations[0]
            os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
            
            import base64
            audio_bytes = base64.b64decode(generation.audio)
            with open(output_path, 'wb') as f:
                f.write(audio_bytes)

            words = []
            if hasattr(generation, 'snippets') and generation.snippets:
                for snippet_group in generation.snippets:
                    for snippet in snippet_group:
                        if hasattr(snippet, 'timestamps') and snippet.timestamps:
                            for ts in snippet.timestamps:
                                if getattr(ts, 'type', '') == 'word':
                                    words.append({
                                        "text":  ts.text,
                                        "start": ts.time.begin / 1000.0,
                                        "end":   ts.time.end / 1000.0,
                                    })

            if words:
                duration = words[-1]['end']
            else:
                import soundfile as sf
                duration = sf.info(output_path).duration
            
            return {"audio_path": output_path, "words": words, "duration": duration}

        except Exception as e:
            logger.error(f"Hume Octave failed: {e}")
            return None

    def _overlay_micro_breaths(self, input_path: str, beats: list, words: list, output_path: str):
        """
        Overlays subtle human breath sounds strictly on whisper/dread/panic/ending beats.
        """
        try:
            narration = AudioSegment.from_file(input_path)
            
            breath_file = "assets/breath_sfx.wav"
            if not os.path.exists(breath_file):
                self.generate_sfx("deep subtle human breath", breath_file, duration_seconds=1.5)
            
            if os.path.exists(breath_file):
                breath = AudioSegment.from_file(breath_file)
                # target volume: -26 dB (subtle)
                breath = breath + (-26 - breath.dBFS) 

                target_deliveries = ['whisper', 'dread', 'panic', 'ending']
                
                word_idx = 0
                for beat in beats:
                    if beat.get('delivery') in target_deliveries:
                        beat_text = beat.get('text', '').split()
                        if not beat_text: continue
                        last_word = re.sub(r'[^\w]', '', beat_text[-1].lower())
                        
                        found_time = None
                        while word_idx < len(words):
                            w = re.sub(r'[^\w]', '', words[word_idx]['text'].lower())
                            end_time = words[word_idx]['end']
                            word_idx += 1
                            if w == last_word:
                                found_time = end_time * 1000 # ms
                                break
                        
                        if found_time and found_time < len(narration):
                            # Overlay breath shortly after the word ends
                            narration = narration.overlay(breath, position=found_time + 100)
            
            narration.export(output_path, format="wav")
            
        except Exception as e:
            logger.error(f"Failed to overlay breaths: {e}")
            # fallback
            AudioSegment.from_file(input_path).export(output_path, format="wav")

    def _master_audio(self, input_path: str, output_path: str):
        """
        Pedalboard Mastering Chain: Compressor -> Saturator -> Reverb -> EQ/Limiter
        """
        try:
            from pedalboard import Pedalboard, Compressor, Reverb, LowShelfFilter, HighShelfFilter, Limiter, Distortion
            audio, sample_rate = sf.read(input_path)
            
            # Ensure audio is mono for pedalboard processing if needed, or pedalboard handles stereo
            if len(audio.shape) > 1:
                audio = audio.mean(axis=1)

            board = Pedalboard([
                Compressor(threshold_db=-20, ratio=4, attack_ms=2.0, release_ms=100),
                Distortion(drive_db=1.5), # Acts as Saturator for warmth
                LowShelfFilter(cutoff_frequency_hz=100, gain_db=3.0),   # Chesty warmth
                HighShelfFilter(cutoff_frequency_hz=8000, gain_db=-2.0),# Roll off harsh digital highs
                Reverb(room_size=0.1, damping=0.8, wet_level=0.1, dry_level=0.9), # Subtle room space
                Limiter(threshold_db=-1.0)
            ])
            
            mastered = board(audio, sample_rate)
            sf.write(output_path, mastered, sample_rate)
            logger.success(f"Mastered audio saved to {output_path}")
            
        except ImportError:
            logger.warning("pedalboard not installed. Skipping mastering chain.")
            audio, sr = sf.read(input_path)
            sf.write(output_path, audio, sr)
        except Exception as e:
            logger.error(f"Failed to master audio: {e}")
            audio, sr = sf.read(input_path)
            sf.write(output_path, audio, sr)

    def generate_sfx(self, prompt: str, output_path: str = "assets/sfx.mp3", duration_seconds: float = None):
        try:
            query = self._build_freesound_query(prompt)
            url = "https://freesound.org/apiv2/search/text/"
            params = {
                "query": query,
                "token": self.freesound_key,
                "fields": "id,name,previews,duration",
                "sort": "rating_desc",
                "page_size": 5,
            }

            resp = requests.get(url, params=params, timeout=20)
            if resp.status_code == 200:
                results = resp.json().get('results', [])
                if results:
                    sound = results[0]
                    preview_url = sound['previews'].get('preview-hq-mp3', sound['previews'].get('preview-lq-mp3'))
                    if preview_url:
                        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
                        pr = requests.get(preview_url, timeout=30)
                        if pr.status_code == 200:
                            with open(output_path, 'wb') as f:
                                f.write(pr.content)
                            return output_path

            self._create_silence(output_path, duration=duration_seconds or 3.0)
            return output_path

        except Exception as e:
            logger.error(f"generate_sfx failed: {e}")
            self._create_silence(output_path, duration=duration_seconds or 3.0)
            return output_path

    def _build_freesound_query(self, prompt: str) -> str:
        prompt_lower = prompt.lower()
        for key, mapped_query in HORROR_SFX_MAP.items():
            if key in prompt_lower:
                return mapped_query
        return "horror ambient"

    def generate_music(self, mood_prompt: str, output_path: str = "assets/music.wav", duration_seconds: int = 30):
        try:
            music_prompt = (
                f"slow dark horror ambient drone, {mood_prompt}, "
                "40 BPM, deep sustained bass tones, eerie silence with texture, "
                "minimal, no percussion, no melody, no rhythm, no beat, "
                "cinematic tension, long slow notes, dark atmospheric sound design, "
                "whisper-quiet background, spine-chilling, sub-bass rumble"
            )

            API_URL = "https://api-inference.huggingface.co/models/facebook/musicgen-small"
            headers = {"Authorization": f"Bearer {self.hf_token}"}
            payload = {"inputs": music_prompt}
            
            response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
            if response.status_code != 200:
                raise Exception(f"HF API Error: {response.text}")
                
            audio_bytes = response.content
            os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(audio_bytes)
            return output_path

        except Exception as e:
            logger.warning(f"MusicGen failed ({e}) — falling back to Freesound ambient")
            return self.generate_sfx("horror ambient drone", output_path, duration_seconds)

    def _create_silence(self, output_path: str, duration: float = 3.0):
        try:
            os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
            silence = np.zeros(int(duration * SAMPLE_RATE))
            sf.write(output_path, silence, SAMPLE_RATE)
        except Exception as e:
            logger.error(f"Failed to create silence: {e}")
