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
        Takes an array of beats, generates one Hume utterance per beat with
        trailing_silence for dramatic pauses, overlays micro-breaths, and masters audio.
        Returns: {"audio_path": str, "words": [{text, start, end}], "duration": float}
        """
        # Filter duplicate consecutive lines
        filtered_beats = []
        prev_text = ""
        for b in beats:
            t = b.get("text", "").strip()
            if t and t.lower() == prev_text.lower():
                continue
            filtered_beats.append(b)
            prev_text = t
        beats = filtered_beats

        performance_script = self._compile_performance_script(beats)
        logger.info(f"Compiled Performance Script:\n{performance_script[:200]}...")

        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        # Fallback Chain: Hume -> Kokoro -> Edge-TTS
        # (NVIDIA TTS models are currently returning 404 from the NIM API)
        raw_output_path = output_path.replace(".mp3", "_raw.mp3")
        
        result = self._generate_with_hume(beats, raw_output_path)

        if not result:
            logger.warning("Hume generation failed. Falling back to Kokoro...")
            result = self._generate_with_kokoro(beats, raw_output_path)

        if not result:
            logger.warning("Kokoro generation failed. Falling back to Edge-TTS...")
            result = self._generate_with_edge_tts(beats, raw_output_path)

        if not result:
            logger.error("Speech generation failed entirely — aborting props build.")
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

    def _estimate_word_boundaries(self, text: str, output_path: str):
        try:
            import soundfile as sf
            duration = sf.info(output_path).duration
            
            words = text.split()
            if not words:
                return {"audio_path": output_path, "words": [], "duration": duration}
                
            time_per_word = duration / len(words)
            word_objs = []
            current_time = 0.0
            
            for w in words:
                word_objs.append({
                    "text": w,
                    "start": current_time,
                    "end": current_time + time_per_word
                })
                current_time += time_per_word
                
            logger.success(f"Estimated {len(word_objs)} word timestamps, duration: {duration:.1f}s")
            return {"audio_path": output_path, "words": word_objs, "duration": duration}
        except Exception as e:
            logger.error(f"Failed to estimate boundaries: {e}")
            return None

    def _generate_with_nvidia(self, beats: list, output_path: str):
        api_key = os.getenv("NVIDIA_NIM_API_KEY")
        if not api_key:
            return None

        try:
            logger.info("Calling NVIDIA NIM API for TTS...")
            text = " ".join([b.get("text", "") for b in beats]).strip()
            text = re.sub(r'\s+', ' ', text)
            if not text:
                return None
                
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "audio/mp3"
            }
            
            models_to_try = [
                "nvidia/nemotron-voicechat",
                "nvidia/magpie-tts"
            ]
            
            for model_name in models_to_try:
                payload = {
                    "model": model_name,
                    "input": text,
                    "voice": "A male speaker with a low, deep, and slightly sinister voice delivering a horror story. He speaks slowly with dramatic pauses.",
                }
                
                logger.info(f"Trying NVIDIA TTS model: {model_name}")
                resp = requests.post("https://integrate.api.nvidia.com/v1/audio/speech", headers=headers, json=payload, timeout=60)
                if resp.status_code == 200:
                    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
                    with open(output_path, 'wb') as f:
                        f.write(resp.content)
                    return self._estimate_word_boundaries(text, output_path)
                else:
                    logger.error(f"NVIDIA API Error {resp.status_code} with {model_name}: {resp.text}")
            
            return None
        except Exception as e:
            logger.error(f"NVIDIA generation failed: {e}")
            return None

    def _generate_with_kokoro(self, beats: list, output_path: str):
        try:
            from kokoro import KPipeline
            import soundfile as sf
            from pydub import AudioSegment
            import io
            import numpy as np
            
            logger.info("Calling Kokoro TTS...")
            
            # Initialize pipeline (American English)
            pipeline = KPipeline(lang_code='a')
            voice = "am_onyx" # Deep male voice, great for horror
            
            master_audio = AudioSegment.empty()
            master_words = []
            
            for beat in beats:
                text = beat.get("text", "").strip()
                if not text:
                    continue
                    
                # Generate audio for the beat
                generator = pipeline(text, voice=voice, speed=0.85, split_pattern=r'\n+')
                
                beat_audio_data = []
                for _, _, audio in generator:
                    beat_audio_data.append(audio)
                
                if not beat_audio_data:
                    continue
                    
                combined_audio = np.concatenate(beat_audio_data)
                
                # Convert numpy array to pydub AudioSegment
                temp_buffer = io.BytesIO()
                sf.write(temp_buffer, combined_audio, 24000, format='wav')
                temp_buffer.seek(0)
                audio_segment = AudioSegment.from_file(temp_buffer, format="wav")
                
                current_duration = len(master_audio) / 1000.0
                beat_duration = len(audio_segment) / 1000.0
                
                # Estimate word boundaries since Kokoro doesn't return them directly
                words = text.split()
                if words:
                    time_per_word = beat_duration / len(words)
                    for i, w in enumerate(words):
                        master_words.append({
                            "text": w,
                            "start": current_duration + (i * time_per_word),
                            "end": current_duration + ((i + 1) * time_per_word)
                        })
                        
                master_audio += audio_segment
                
                # Add requested silence for dramatic pacing
                pause_seconds = float(beat.get("pause_after", 0.5))
                pause_ms = int(pause_seconds * 1000)
                master_audio += AudioSegment.silent(duration=pause_ms)
                
            os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
            master_audio.export(output_path, format="mp3")
            
            duration = len(master_audio) / 1000.0
            logger.success(f"Kokoro generation success. {len(master_words)} words, duration: {duration:.1f}s")
            return {"audio_path": output_path, "words": master_words, "duration": duration}
            
        except ImportError:
            logger.warning("Kokoro is not installed (`pip install kokoro`). Skipping.")
            return None
        except Exception as e:
            logger.error(f"Kokoro generation failed: {e}")
            return None

    # Minimum trailing silence (seconds) per delivery type for horror pacing
    _DELIVERY_MIN_PAUSE = {
        "calm":    0.3,
        "unease":  0.5,
        "dread":   0.8,
        "whisper": 1.0,
        "reveal":  1.2,
        "panic":   0.5,
        "terror":  0.8,
        "ending":  1.5,
    }

    def _generate_with_hume(self, beats: list, output_path: str):
        """
        Sends one PostedUtterance per beat so each beat gets its own trailing
        silence — this is what produces the dramatic pause timing the narrator needs.
        Snippet extraction uses a flat iteration (Hume v1 SDK structure).
        """
        try:
            from hume import HumeClient
            from hume.tts import PostedUtterance, PostedUtteranceVoiceWithId, PostedUtteranceVoiceWithName
            import base64
            import soundfile as sf
            
            # Collect all available Hume API keys
            hume_keys = [
                os.getenv("HUME_API_KEY"),
                os.getenv("HUME_API_KEY1"),
                os.getenv("HUME_API_KEY2"),
                os.getenv("HUME_API_KEY3"),
                os.getenv("HUME_API_KEY4"),
                os.getenv("HUME_API_KEY5"),
                os.getenv("HUME_API_KEY6"),
                os.getenv("HUME_API_KEY7"),
                os.getenv("HUME_API_KEY8"),
                os.getenv("HUME_API_KEY9")
            ]
            # Filter out empty or None keys
            hume_keys = [k for k in hume_keys if k]
            
            if not hume_keys:
                logger.error("No Hume API keys available.")
                return None

            for i, current_key in enumerate(hume_keys):
                logger.info(f"Trying Hume API key {i+1}/{len(hume_keys)}...")
                try:
                    client = HumeClient(api_key=current_key)
        
                    voice_kwargs = {}
                    if HUME_HORROR_VOICE_ID:
                        voice_kwargs["voice"] = PostedUtteranceVoiceWithId(id=HUME_HORROR_VOICE_ID)
                    else:
                        voice_kwargs["voice"] = PostedUtteranceVoiceWithName(name="ITO", provider="HUME_AI")
        
                    # One utterance per beat with delivery-aware trailing silence
                    utterances = []
                    for beat in beats:
                        text = beat.get("text", "").strip()
                        # Sanitize text to remove brackets and asterisks
                        text = re.sub(r'\[.*?\]', '', text)
                        text = re.sub(r'\*.*?\*', '', text)
                        text = re.sub(r'\(.*?\)', '', text)
                        text = text.strip()
                        if not text:
                            continue
                        pause      = float(beat.get("pause_after", 0.3))
                        delivery   = beat.get("delivery", "calm")
                        min_pause  = self._DELIVERY_MIN_PAUSE.get(delivery, 0.3)
                        trailing   = max(pause, min_pause)
                        utterances.append(PostedUtterance(
                            text=text,
                            description=f"{HUME_GLOBAL_ACTING} Delivery style for this line: {delivery}.",
                            trailing_silence=trailing,
                            **voice_kwargs
                        ))
        
                    if not utterances:
                        logger.error("No utterances built from beats.")
                        return None
        
                    logger.info(f"Calling Hume Octave TTS ({len(utterances)} utterances with pauses)...")
                    response = client.tts.synthesize_json(
                        utterances=utterances,
                        format={"type": "mp3"},
                        include_timestamp_types=["word"],
                        version="1",
                    )
        
                    if not response or not response.generations:
                        logger.warning(f"Empty response from Hume API key {i+1}. Trying next key...")
                        continue
        
                    generation = response.generations[0]
                    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        
                    audio_bytes = base64.b64decode(generation.audio)
                    with open(output_path, 'wb') as f:
                        f.write(audio_bytes)
        
                    # ── Snippet extraction: Hume v1 returns a FLAT list of SnippetAudioResult
                    # (not a list-of-lists). Iterating as nested was the caption bug.
                    words = []
                    current_offset = 0.0
                    if hasattr(generation, 'snippets') and generation.snippets:
                        for idx, snippet in enumerate(generation.snippets):
                            snippet_duration = 0.0
                            if hasattr(snippet, 'timestamps') and snippet.timestamps:
                                for ts in snippet.timestamps:
                                    if getattr(ts, 'type', '') == 'word':
                                        # Hume API might return seconds directly. If values are large, it's milliseconds.
                                        begin_val = getattr(ts.time, 'begin', 0.0)
                                        end_val = getattr(ts.time, 'end', 0.0)
                                        start_sec = begin_val if begin_val < 1000 and begin_val > 0 else begin_val / 1000.0
                                        end_sec = end_val if end_val < 1000 and end_val > 0 else end_val / 1000.0
                                        
                                        words.append({
                                            "text":  ts.text,
                                            "start": current_offset + start_sec,
                                            "end":   current_offset + end_sec,
                                        })
                                        snippet_duration = max(snippet_duration, end_sec)
                            
                            # Add the trailing silence that we requested for this utterance
                            trailing = utterances[idx].trailing_silence if idx < len(utterances) else 0.3
                            current_offset += snippet_duration + trailing
        
                    if words:
                        duration = words[-1]['end']
                    else:
                        duration = sf.info(output_path).duration
        
                    logger.success(f"Extracted {len(words)} word timestamps, duration: {duration:.1f}s")
                    return {"audio_path": output_path, "words": words, "duration": duration}
                
                except Exception as inner_e:
                    logger.warning(f"Hume API key {i+1} failed: {inner_e}")
            
            logger.error("All Hume API keys failed or exhausted credits.")
            return None

        except Exception as e:
            logger.error(f"Hume generation pipeline failed: {e}")
            return None

    def _generate_with_edge_tts(self, beats: list, output_path: str):
        try:
            import edge_tts
            import io
            from pydub import AudioSegment
            
            # Using ChristopherNeural for a deeper voice.
            voice = "en-US-ChristopherNeural"
            
            master_audio = AudioSegment.empty()
            master_words = []
            
            async def run_edge():
                nonlocal master_audio, master_words
                for beat in beats:
                    text = beat.get("text", "").strip()
                    if not text:
                        continue
                        
                    # Slow rate slightly and drop pitch for horror effect
                    communicate = edge_tts.Communicate(text, voice, rate="-10%", pitch="-15Hz")
                    
                    audio_data = b""
                    word_boundaries = []
                    
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            audio_data += chunk["data"]
                        elif chunk["type"] == "WordBoundary":
                            word_boundaries.append({
                                "text": chunk["text"],
                                "offset": chunk["offset"],
                                "duration": chunk["duration"]
                            })
                            
                    if not audio_data:
                        continue
                        
                    # Load this beat's audio
                    audio_segment = AudioSegment.from_file(io.BytesIO(audio_data), format="mp3")
                    current_duration = len(master_audio) / 1000.0
                    
                    if word_boundaries:
                        for wb in word_boundaries:
                            start = (wb["offset"] / 10000000.0) + current_duration
                            end = start + (wb["duration"] / 10000000.0)
                            master_words.append({
                                "text": wb["text"],
                                "start": start,
                                "end": end
                            })
                    else:
                        # Fallback for voices that don't return WordBoundary
                        beat_duration = len(audio_segment) / 1000.0
                        words = text.split()
                        if words:
                            time_per_word = beat_duration / len(words)
                            for i, w in enumerate(words):
                                master_words.append({
                                    "text": w,
                                    "start": current_duration + (i * time_per_word),
                                    "end": current_duration + ((i + 1) * time_per_word)
                                })
                                
                    master_audio += audio_segment
                    
                    # Add requested silence for dramatic pacing
                    pause_seconds = float(beat.get("pause_after", 0.5))
                    pause_ms = int(pause_seconds * 1000)
                    master_audio += AudioSegment.silent(duration=pause_ms)
                    
            asyncio.run(run_edge())
            
            os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
            master_audio.export(output_path, format="mp3")
            
            duration = len(master_audio) / 1000.0
            logger.success(f"Edge-TTS fallback success. {len(master_words)} words, duration: {duration:.1f}s")
            return {"audio_path": output_path, "words": master_words, "duration": duration}
            
        except Exception as e:
            logger.error(f"Edge-TTS failed: {e}")
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
        if not self.freesound_key:
            logger.warning("FREESOUND_API_KEY is not set! Background music and SFX will be silent.")
            self._create_silence(output_path, duration=duration_seconds or 3.0)
            return output_path
            
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
        """
        Uses Freesound for background horror ambient music.
        HuggingFace MusicGen endpoint is unreliable and has been removed.
        """
        logger.info(f"Fetching horror ambient music from Freesound for mood: {mood_prompt[:60]}")
        return self.generate_sfx("horror ambient drone", output_path, duration_seconds)

    def _create_silence(self, output_path: str, duration: float = 3.0):
        try:
            os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
            silence = np.zeros(int(duration * SAMPLE_RATE))
            sf.write(output_path, silence, SAMPLE_RATE)
        except Exception as e:
            logger.error(f"Failed to create silence: {e}")
