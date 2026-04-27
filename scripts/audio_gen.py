import os
import re
import asyncio
import numpy as np
import requests
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

FREESOUND_API_KEY = os.getenv("FREESOUND_API_KEY")
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")

SAMPLE_RATE = 24000  # Kokoro native sample rate


class AudioGenerator:
    def __init__(self):
        self.freesound_key = FREESOUND_API_KEY
        self.hf_token = HUGGINGFACE_TOKEN
        self._kokoro_pipeline = None

    # ─────────────────────────────────────────────
    # PUBLIC: generate_speech
    # Returns: {"audio_path": str, "words": [{text, start, end}], "duration": float}
    # ─────────────────────────────────────────────

    def generate_speech(self, text: str, output_path: str = "assets/speech.mp3"):
        """
        Generate narration with word-level timestamps.
        Tries Kokoro TTS first, falls back to Edge-TTS.
        """
        logger.info(f"Generating speech for: {text[:60]}...")

        result = self._generate_with_kokoro(text, output_path)
        if result:
            return result

        logger.warning("Kokoro failed — falling back to Edge-TTS")
        result = self._generate_with_edge_tts(text, output_path)
        if result:
            return result

        logger.error("All TTS methods failed")
        return None

    # ─────────────────────────────────────────────
    # PRIVATE: Kokoro TTS (primary)
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
                    generator = pipeline(sentence, voice='af_heart', speed=0.9)
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
                                "text": clean,
                                "start": round(current_time + i * time_per_word, 3),
                                "end": round(current_time + (i + 1) * time_per_word, 3),
                            })

                all_audio_chunks.append(sent_audio)
                current_time += sent_duration

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
    # PRIVATE: Edge-TTS fallback
    # ─────────────────────────────────────────────

    def _generate_with_edge_tts(self, text: str, output_path: str):
        try:
            import edge_tts

            async def _run():
                communicate = edge_tts.Communicate(
                    text,
                    voice="en-US-ChristopherNeural",
                    rate="-10%",
                    pitch="-5Hz",
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
                        "text": wb['text'],
                        "start": round(start, 3),
                        "end": round(start + dur, 3),
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
        Search Freesound.org for a contextually relevant SFX and download its preview.
        Falls back to silence if nothing found.
        """
        try:
            stop_words = {
                'a','an','the','with','in','on','at','for','of','and','or',
                'is','it','its','this','that','to','into','dark','deep',
            }
            raw_words = re.findall(r'\w+', prompt.lower())
            keywords = [w for w in raw_words if w not in stop_words and len(w) > 2]
            query = ' '.join(keywords[:6])

            url = "https://freesound.org/apiv2/search/text/"
            params = {
                "query": query,
                "token": self.freesound_key,
                "fields": "id,name,previews,duration",
                "filter": "duration:[1 TO 30]",
                "sort": "rating_desc",
                "page_size": 5,
            }

            logger.info(f"Freesound SFX search: '{query}'")
            resp = requests.get(url, params=params, timeout=20)

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

    # ─────────────────────────────────────────────
    # PUBLIC: generate_music — HuggingFace MusicGen
    # ─────────────────────────────────────────────

    def generate_music(self, mood_prompt: str,
                       output_path: str = "assets/music.wav",
                       duration_seconds: int = 30):
        """
        Generate contextual background music using HuggingFace MusicGen (free inference API).
        Falls back to Freesound ambient search.
        """
        try:
            from huggingface_hub import InferenceClient

            client = InferenceClient(token=self.hf_token)
            music_prompt = (
                f"dark cinematic horror ambient music, {mood_prompt}, "
                "ominous tension building, eerie atmosphere, no vocals, "
                "suspenseful soundtrack"
            )
            logger.info(f"MusicGen: {music_prompt[:70]}...")

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
            return self.generate_sfx(
                f"horror ambient music atmosphere {mood_prompt}",
                output_path,
                duration_seconds=duration_seconds,
            )

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
