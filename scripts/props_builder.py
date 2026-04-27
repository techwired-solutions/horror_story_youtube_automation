import os
import json
from scripts.audio_gen import AudioGenerator
from scripts.asset_fetcher import AssetFetcher
from loguru import logger
from dotenv import load_dotenv

load_dotenv()


class PropsBuilder:
    def __init__(self):
        self.audio_gen = AudioGenerator()
        self.asset_fetcher = AssetFetcher()

    def build_props(self, part_data, title, part_number=1,
                    output_path="remotion-video/public/props.json"):
        """
        Builds Remotion props for a specific story part.
        Handles TTS narration, SFX, background music, and image assets.
        """
        scenes = part_data["scenes"]
        full_narration = " ".join([scene["text"] for scene in scenes])

        # ── 1. Generate Narration Audio ──────────────────────────────────────
        audio_filename = f"assets/audio/speech_part_{part_number}.mp3"
        audio_output_path = os.path.join("remotion-video/public", audio_filename)

        audio_result = self.audio_gen.generate_speech(
            full_narration, output_path=audio_output_path
        )
        if not audio_result:
            logger.error("Speech generation failed — aborting props build.")
            return None

        # word-level timestamps come directly from Kokoro / Edge-TTS
        # Also strip any residual [tags] from word text (safety net)
        import re
        words = [
            w for w in audio_result["words"]
            if re.sub(r'[^\w]', '', w.get('text', '')).strip()
            and not re.match(r'^\[.*\]$', w.get('text', '').strip())
        ]
        total_duration_seconds = audio_result["duration"]

        # ── 2. Generate Background Music ─────────────────────────────────────
        # Build a mood prompt from the title/topic for contextual music
        mood_keywords = title.replace(" - Part", "").strip()
        atmosphere_filename = f"assets/audio/music_part_{part_number}.wav"
        atmosphere_output_path = os.path.join(
            "remotion-video/public", atmosphere_filename
        )
        self.audio_gen.generate_music(
            mood_prompt=mood_keywords,
            output_path=atmosphere_output_path,
            duration_seconds=int(total_duration_seconds) + 10,
        )

        # ── 3. Download Scene Images + SFX ───────────────────────────────────
        scenes_with_assets = []
        for i, scene in enumerate(scenes):
            # Image
            image_url = self.asset_fetcher.generate_image(scene["image_prompt"])
            image_path = f"assets/images/part_{part_number}_scene_{i}.png"
            local_image_path = os.path.join("remotion-video/public", image_path)
            self.asset_fetcher.download_asset(image_url, local_image_path)
            scene["image_url"] = image_path

            # SFX
            sfx_path = f"assets/audio/part_{part_number}_sfx_{i}.mp3"
            local_sfx_path = os.path.join("remotion-video/public", sfx_path)
            sfx_prompt = scene.get("sfx_prompt", "horror ambient atmosphere")
            self.audio_gen.generate_sfx(sfx_prompt, output_path=local_sfx_path)
            scene["sfx_url"] = sfx_path

            scenes_with_assets.append(scene)

        # ── 4. Build Final Props JSON ─────────────────────────────────────────
        duration_in_frames = int(total_duration_seconds * 30) + 30  # 1s buffer

        final_props = {
            "title": title if part_number == 1 else f"{title} - Part {part_number}",
            "scenes": scenes_with_assets,
            "subtitles": words,          # word-level: [{text, start, end}, ...]
            "audio_url": audio_filename,
            "atmosphere_url": atmosphere_filename,
            "duration_in_frames": duration_in_frames,
            "fps": 30,
        }

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(final_props, f, indent=4)

        logger.success(
            f"Props built for Part {part_number}: "
            f"{len(words)} words, {total_duration_seconds:.1f}s, {duration_in_frames} frames"
        )
        return final_props


if __name__ == "__main__":
    builder = PropsBuilder()
