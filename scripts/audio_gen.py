import os
import re
import asyncio
import numpy as np
import requests
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

FREESOUND_API_KEY  = os.getenv("FREESOUND_API_KEY")
HUGGINGFACE_TOKEN  = os.getenv("HUGGINGFACE_TOKEN")
HUME_API_KEY       = os.getenv("HUME_API_KEY")

SAMPLE_RATE = 24000  # Kokoro native sample rate

# ─────────────────────────────────────────────────────────────────────────────
# Hume Octave voice ID for horror narration.
# Visit https://platform.hume.ai/tts/voices to browse and copy a voice ID.
# This default is a deep, cinematic male storyteller.
# ─────────────────────────────────────────────────────────────────────────────
HUME_HORROR_VOICE_ID = os.getenv("HUME_VOICE_ID", "")   # leave blank → Hume auto-selects

# Acting instructions sent to Hume Octave alongside the narration text.
# These replace ElevenLabs-style [audio tags] with natural language direction.
HUME_ACTING_INSTRUCTIONS = (
    "Narrate this horror story in the style of a seasoned paranormal storyteller. "
    "Your voice should be deep, slow, and gravely serious — as if you witnessed these "
    "events yourself. Speak with controlled dread: lower your pitch on tense moments, "
    "pause before reveals, and let fear seep into every word. Never rush. "
    "The silence between sentences should feel heavy."
)

# Horror-specific keyword mapping for Freesound search
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
    "footsteps":   "footsteps dark",
    "laugh":       "sinister laugh",
    "giggle":      "creepy giggle",
    "silence":     "ambient horror",
    "forest":      "dark forest night",
    "rain":        "rain storm",
    "church":      "church bell",
    "bell":        "bell toll",
    "scratch":     "scratch wall",
    "knock":       "knocking door",
    "static":      "tv static noise",
    "growl":       "monster growl",
    "howl":        "wolf howl",
    "music":       "horror ambient music",
    "ambient":     "horror ambient",
    "atmosphere":  "horror atmosphere",
}


class AudioGenerator:
    def __init__(self):
        self.freesound_key = FREESOUND_API_KEY
        self.hf_token      = HUGGINGFACE_TOKEN
        self.hume_key      = HUME_API_KEY
        self._kokoro_pipeline = None

    # ─────────────────────────────────────────────
    # PUBLIC: generate_speech
    # Returns: {"audio_path": str, "words": [{text, start, end}], "duration": float}
    # Chain: Hume Octave → Kokoro → Edge-TTS
    # ─────────────────────────────────────────────

    def generate_speech(self, text: str, output_path: str = "assets/speech.mp3"):
        """
        Generate narration with word-level timestamps.
        Strips bracketed emotion tags for display, but uses them to enrich
        the acting instructions sent to Hume Octave for expressive delivery.
        """
        # Extract emotion hints before stripping tags (used for Hume instructions)
        emotion_hints = self._extract_emotion_hints(text)
        clean_text = self._strip_emotion_tags(text)
        logger.info(f"Generating speech for: {clean_text[:80]}...")

        # ── Primary: Hume AI Octave ──────────────────────────────────────────
        if self.hume_key and self.hume_key != "your_hume_api_key_here":
            result = self._generate_with_hume(clean_text, output_path, emotion_hints)
            if result:
                return result
            logger.warning("Hume Octave failed — falling back to Kokoro")
        else:
            logger.warning("HUME_API_KEY not set — skipping Hume, using Kokoro")

        # ── Secondary: Kokoro ────────────────────────────────────────────────
        result = self._generate_with_kokoro(clean_text, output_path)
        if result:
            return result

        # ── Last Resort: Edge-TTS ────────────────────────────────────────────
        logger.warning("Kokoro failed — falling back to Edge-TTS")
        result = self._generate_with_edge_tts(clean_text, output_path)
        if result:
            return result

        logger.error("All TTS methods failed")
        return None

    @staticmethod
    def _extract_emotion_hints(text: str) -> str:
        """
        Pull out the bracketed emotion/delivery cues (e.g. [whispers], [trembling voice])
        and return them as a comma-separated hint string for use in Hume acting instructions.
        """
        tags = re.findall(r'\[([^\]]+)\]', text)
        return ", ".join(tags) if tags else ""

    @staticmethod
    def _strip_emotion_tags(text: str) -> str:
        """
        Remove ElevenLabs-style bracketed emotion/delivery tags from text.
        e.g. [whispers], [slow pacing], [trembling voice] → stripped out.
        Also collapses any double-spaces left behind.
        """
        cleaned = re.sub(r'\[.*?\]', '', text)
        cleaned = re.sub(r'  +', ' ', cleaned)
        return cleaned.strip()

    # ─────────────────────────────────────────────
    # PRIVATE: Hume AI Octave TTS (primary)
    # ─────────────────────────────────────────────

    def _generate_with_hume(self, text: str, output_path: str,
                             emotion_hints: str = "") -> dict | None:
        """
        Generate expressive horror narration via Hume AI Octave v2.

        Octave is a speech-language model that understands context and emotion.
        Unlike standard TTS engines, it can follow natural-language acting
        instructions — making it ideal for cinematic horror narration.

        Returns: {"audio_path": str, "words": [{text, start, end}], "duration": float}
        """
        try:
            from hume import HumeClient
            from hume.tts import PostedUtterance, PostedUtteranceVoiceWithId

            client = HumeClient(api_key=self.hume_key)

            # Build enriched acting instructions — merge base horror direction
            # with any emotion cues extracted from the script tags
            acting = HUME_ACTING_INSTRUCTIONS
            if emotion_hints:
                acting += f" Additional emotional cues for this passage: {emotion_hints}."

            # Build utterance
            voice_kwargs = {}
            if HUME_HORROR_VOICE_ID:
                voice_kwargs["voice"] = PostedUtteranceVoiceWithId(id=HUME_HORROR_VOICE_ID)

            utterance = PostedUtterance(
                text=text,
                description=acting,
                **voice_kwargs,
            )

            logger.info("Calling Hume Octave TTS (v2, word timestamps)...")

            # Use the synchronous TTS endpoint with word-level timestamps
            response = client.tts.synthesize_json(
                utterances=[utterance],
                format="mp3",
                include_timestamp_types=["word"],
            )

            if not response or not response.generations:
                logger.warning("Hume returned empty generations")
                return None

            generation = response.generations[0]

            # ── Save audio ─────────────────────────────────────────────────
            os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

            # audio is base64-encoded in the response
            import base64
            audio_bytes = base64.b64decode(generation.audio)
            with open(output_path, 'wb') as f:
                f.write(audio_bytes)

            # ── Extract word-level timestamps ──────────────────────────────
            words = []
            if hasattr(generation, 'timestamps') and generation.timestamps:
                for ts in generation.timestamps:
                    if hasattr(ts, 'type') and ts.type == 'word':
                        words.append({
                            "text":  ts.value,
                            "start": round(ts.start_time, 3),
                            "end":   round(ts.end_time,   3),
                        })

            if not words:
                logger.warning("Hume returned no word timestamps — estimating from duration")
                words = self._estimate_word_timestamps(text, generation.duration_secs or 30.0)

            duration = words[-1]['end'] if words else (generation.duration_secs or 30.0)
            logger.success(
                f"Hume Octave: {len(words)} words, {duration:.1f}s → {output_path}"
            )
            return {"audio_path": output_path, "words": words, "duration": duration}

        except ImportError:
            logger.warning("hume SDK not installed — run: pip install hume>=0.8.0")
            return None
        except Exception as e:
            logger.error(f"Hume Octave generation failed: {e}")
            return None

    @staticmethod
    def _estimate_word_timestamps(text: str, total_duration: float) -> list[dict]:
        """
        Fallback: uniformly distribute word timestamps across the full audio duration.
        Used only when Hume returns audio but no timestamp data.
        """
        words = [w.strip() for w in text.split() if w.strip()]
        if not words:
            return []
        time_per_word = total_duration / len(words)
        result = []
        for i, word in enumerate(words):
            clean = re.sub(r"[^\w'']", '', word)
            if clean:
                result.append({
                    "text":  clean,
                    "start": round(i * time_per_word, 3),
                    "end":   round((i + 1) * time_per_word, 3),
                })
        return result

    # ─────────────────────────────────────────────
    # PRIVATE: Kokoro TTS (secondary fallback)
    # ─────────────────────────────────────────────

    def _get_kokoro_pipeline(self):
        if self._kokoro_pipeline is None:
            try:
                from kokoro import KPipeline
                self._kokoro_pipeline = KPipeline(lang_code='a')  # American English
                logger.info("Kokoro pipeline ready")
            except Exception as e:
                logger.warning(f"Kokoro init failed: {e}")
                return None
        return self._kokoro_pipeline

    def _generate_with_kokoro(self, text: str, output_path: str):
        pipeline = self._get_kokoro_pipeline()
        if not pipeline:
            return None

        try:
            import soundfile as sf

            # Split into sentences so we can track timing per sentence
            sentences = re.split(r'(?<=[.!?…])\s+', text.strip())
            sentences = [s.strip() for s in sentences if s.strip()]

            all_audio_chunks = []
            all_words = []
            current_time = 0.0

            for sentence in sentences:
                sent_chunks = []
                try:
                    generator = pipeline(sentence, voice='am_fenrir', speed=0.85)
                    for _gs, _ps, audio_chunk in generator:
                        sent_chunks.append(audio_chunk)
                except Exception as e:
                    logger.warning(f"Kokoro chunk failed: {e}")
                    continue

                if not sent_chunks:
                    continue

                sent_audio = np.concatenate(sent_chunks)
                sent_duration = len(sent_audio) / SAMPLE_RATE

                # Distribute duration proportionally across words in the sentence
                words = [w.strip() for w in sentence.split() if w.strip()]
                if words:
                    time_per_word = sent_duration / len(words)
                    for i, word in enumerate(words):
                        clean = re.sub(r"[^\w'']", '', word)
                        if clean:
                            all_words.append({
                                "text":  clean,
                                "start": round(current_time + i * time_per_word, 3),
                                "end":   round(current_time + (i + 1) * time_per_word, 3),
                            })

                all_audio_chunks.append(sent_audio)
                current_time += sent_duration

                # Add a small natural gap between sentences (0.35s)
                # so the caption chunker can detect the sentence boundary
                gap_samples = int(0.35 * SAMPLE_RATE)
                all_audio_chunks.append(np.zeros(gap_samples))
                current_time += 0.35

            if not all_audio_chunks or not all_words:
                return None

            final_audio = np.concatenate(all_audio_chunks)
            os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
            sf.write(output_path, final_audio, SAMPLE_RATE)

            logger.success(
                f"Kokoro TTS: {len(all_words)} words, {current_time:.1f}s → {output_path}"
            )
            return {
                "audio_path": output_path,
                "words": all_words,
                "duration": current_time,
            }

        except Exception as e:
            logger.error(f"Kokoro generation failed: {e}")
            return None

    # ─────────────────────────────────────────────
    # PRIVATE: Edge-TTS fallback (last resort)
    # ─────────────────────────────────────────────

    def _generate_with_edge_tts(self, text: str, output_path: str):
        try:
            import edge_tts

            async def _run():
                communicate = edge_tts.Communicate(
                    text,
                    voice="en-US-DavisNeural",   # Deepest, most dramatic male voice
                    rate="-15%",                 # Slower delivery for horror
                    pitch="-8Hz",                # Lower pitch = more menacing
                )
                word_boundaries = []
                os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

                with open(output_path, 'wb') as f:
                    async for chunk in communicate.stream():
                        if chunk['type'] == 'audio':
                            f.write(chunk['data'])
                        elif chunk['type'] == 'WordBoundary':
                            word_boundaries.append(chunk)

                words = []
                for wb in word_boundaries:
                    start = wb['offset'] / 10_000_000       # 100-ns → seconds
                    dur   = wb['duration'] / 10_000_000
                    words.append({
                        "text":  wb['text'],
                        "start": round(start, 3),
                        "end":   round(start + dur, 3),
                    })
                return words

            words = asyncio.run(_run())
            if not words:
                return None

            duration = words[-1]['end']
            logger.success(
                f"Edge-TTS: {len(words)} words, {duration:.1f}s → {output_path}"
            )
            return {"audio_path": output_path, "words": words, "duration": duration}

        except Exception as e:
            logger.error(f"Edge-TTS failed: {e}")
            return None

    # ─────────────────────────────────────────────
    # PUBLIC: generate_sfx — Freesound.org API
    # ─────────────────────────────────────────────

    def generate_sfx(self, prompt: str, output_path: str = "assets/sfx.mp3",
                     duration_seconds: float = None):
        """
        Search Freesound.org for contextually relevant SFX and download its preview.
        Uses a horror-specific keyword map for reliable results.
        Falls back to silence if nothing found.
        """
        try:
            query = self._build_freesound_query(prompt)
            logger.info(f"Freesound SFX search: '{query}' (from prompt: '{prompt}')")

            url = "https://freesound.org/apiv2/search/text/"
            params = {
                "query": query,
                "token": self.freesound_key,
                "fields": "id,name,previews,duration",
                "sort": "rating_desc",
                "page_size": 5,
            }

            resp = requests.get(url, params=params, timeout=20)
            logger.debug(f"Freesound response: {resp.status_code}")

            if resp.status_code == 200:
                data = resp.json()
                results = data.get('results', [])
                if results:
                    sound = results[0]
                    preview_url = sound['previews'].get(
                        'preview-hq-mp3', sound['previews'].get('preview-lq-mp3')
                    )
                    if preview_url:
                        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
                        pr = requests.get(preview_url, timeout=30)
                        if pr.status_code == 200:
                            with open(output_path, 'wb') as f:
                                f.write(pr.content)
                            logger.success(f"SFX '{sound['name']}' → {output_path}")
                            return output_path

            logger.warning(f"No SFX found for '{query}', writing silence")
            self._create_silence(output_path, duration=duration_seconds or 3.0)
            return output_path

        except Exception as e:
            logger.error(f"generate_sfx failed: {e}")
            self._create_silence(output_path, duration=duration_seconds or 3.0)
            return output_path

    @staticmethod
    def _build_freesound_query(prompt: str) -> str:
        """
        Convert a potentially long sfx_prompt into a short, reliable Freesound query.
        Checks the horror keyword map first, then falls back to keyword extraction.
        """
        prompt_lower = prompt.lower()

        # Check horror keyword map — return the mapped term if any key matches
        for key, mapped_query in HORROR_SFX_MAP.items():
            if key in prompt_lower:
                return mapped_query

        # Fallback: strip stop words and take top 3 keywords
        stop_words = {
            'a','an','the','with','in','on','at','for','of','and','or',
            'is','it','its','this','that','to','into','very','old','dark',
            'deep','soft','low','high','loud','distant','sudden','slowly',
        }
        raw_words = re.findall(r'\w+', prompt_lower)
        keywords = [w for w in raw_words if w not in stop_words and len(w) > 2]
        return ' '.join(keywords[:3]) if keywords else "horror ambient"

    # ─────────────────────────────────────────────
    # PUBLIC: generate_music — HuggingFace MusicGen
    # ─────────────────────────────────────────────

    def generate_music(self, mood_prompt: str,
                       output_path: str = "assets/music.wav",
                       duration_seconds: int = 30):
        """
        Generate slow, atmospheric background music via HuggingFace MusicGen.
        The music MUST be slow, dim, and never upbeat — it plays quietly under narration.
        Falls back to Freesound ambient drone search.
        """
        try:
            from huggingface_hub import InferenceClient

            client = InferenceClient(token=self.hf_token)

            # Very specific slow-horror prompt — avoids fast/upbeat generation
            music_prompt = (
                f"slow dark horror ambient drone, {mood_prompt}, "
                "40 BPM, deep sustained bass tones, eerie silence with texture, "
                "minimal, no percussion, no melody, no rhythm, no beat, "
                "cinematic tension, long slow notes, dark atmospheric sound design, "
                "whisper-quiet background, spine-chilling, sub-bass rumble"
            )
            logger.info(f"MusicGen: {music_prompt[:90]}...")

            audio_bytes = client.text_to_audio(
                music_prompt,
                model="facebook/musicgen-small",
            )

            os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(audio_bytes)

            logger.success(f"MusicGen music → {output_path}")
            return output_path

        except Exception as e:
            logger.warning(f"MusicGen failed ({e}) — falling back to Freesound ambient")
            return self._music_freesound_fallback(mood_prompt, output_path)

    def _music_freesound_fallback(self, mood_prompt: str, output_path: str) -> str:
        """
        Multi-tier Freesound fallback for background music.
        Tries increasingly generic slow-horror ambient queries until one succeeds.
        """
        queries = [
            f"slow horror ambient {mood_prompt[:20]}",
            "dark ambient drone horror",
            "horror atmosphere ambient",
            "dark drone slow ambient",
            "horror ambient",
        ]
        for query in queries:
            result = self._try_freesound_download(query, output_path)
            if result:
                return result

        logger.warning("All Freesound music fallbacks failed — using silence")
        self._create_silence(output_path, duration=30.0)
        return output_path

    def _try_freesound_download(self, query: str, output_path: str):
        """Attempt a single Freesound query and download the top result."""
        try:
            url = "https://freesound.org/apiv2/search/text/"
            params = {
                "query": query,
                "token": self.freesound_key,
                "fields": "id,name,previews,duration",
                "sort": "rating_desc",
                "page_size": 3,
            }
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                results = resp.json().get('results', [])
                if results:
                    preview_url = results[0]['previews'].get(
                        'preview-hq-mp3', results[0]['previews'].get('preview-lq-mp3')
                    )
                    if preview_url:
                        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
                        pr = requests.get(preview_url, timeout=30)
                        if pr.status_code == 200:
                            with open(output_path, 'wb') as f:
                                f.write(pr.content)
                            logger.success(
                                f"Music from Freesound '{results[0]['name']}' → {output_path}"
                            )
                            return output_path
        except Exception as e:
            logger.debug(f"Freesound query '{query}' failed: {e}")
        return None

    # ─────────────────────────────────────────────
    # PRIVATE: helpers
    # ─────────────────────────────────────────────

    def _create_silence(self, output_path: str, duration: float = 3.0):
        """Write a silent WAV file as a safe placeholder."""
        try:
            import soundfile as sf
            os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
            silence = np.zeros(int(duration * SAMPLE_RATE))
            sf.write(output_path, silence, SAMPLE_RATE)
            logger.info(f"Silence placeholder → {output_path}")
        except Exception as e:
            logger.error(f"Failed to create silence: {e}")


if __name__ == "__main__":
    gen = AudioGenerator()
    r = gen.generate_speech("In the heart of the whispering woods, something hungry waits.")
    print(r)
