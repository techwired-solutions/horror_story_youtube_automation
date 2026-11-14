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
                    output_path="remotion-video/public/props.json", mode="short", minutes=10):
        """
        Builds Remotion props for a specific story part.
        Handles TTS narration, SFX, background music, and image assets.
        """
        beats = part_data.get("beats", part_data.get("scenes", []))

        # ── 1. Generate Narration Audio ──────────────────────────────────────
        audio_filename = f"assets/audio/speech_part_{part_number}.mp3"
        audio_output_path = os.path.join("remotion-video/public", audio_filename)

        audio_result = self.audio_gen.generate_speech(
            beats, output_path=audio_output_path
        )
        if not audio_result:
            logger.error("Speech generation failed — aborting props build.")
            return None

        import re
        words = [
            w for w in audio_result["words"]
            if re.sub(r'[^\w]', '', w.get('text', '')).strip()
        ]
        total_duration_seconds = audio_result["duration"]
        from scripts.story_policy import check_render_duration
        check_render_duration(total_duration_seconds, mode, minutes)

        # ── 2. Generate Background Music ─────────────────────────────────────
        music_mood = part_data.get(
            "music_mood",
            f"slow creeping dread, {title.replace(' - Part', '').strip()}"
        )
        atmosphere_filename = f"assets/audio/music_part_{part_number}.wav"
        atmosphere_output_path = os.path.join(
            "remotion-video/public", atmosphere_filename
        )
        self.audio_gen.generate_music(
            mood_prompt=music_mood,
            output_path=atmosphere_output_path,
            duration_seconds=int(total_duration_seconds) + 10,
        )

        # ── 3. Download Scene Images + SFX ───────────────────────────────────
        beats_with_assets = []
        current_image_url = None
        
        credits = []
        held_seconds = 999
        current_kind = "photo"
        video_frames = None
        for i, original in enumerate(beats):
            beat = dict(original)
            # Hold scenery for at least 18 seconds; do not cut on every sentence.
            if held_seconds >= 18:
                asset = self.asset_fetcher.fetch_scene(
                    beat.get("stock_query") or "dark forest fog",
                    f"remotion-video/public/assets/images/part_{part_number}_scene_{i}",
                    orientation="landscape" if mode == "long" else "portrait",
                )
                current_image_url = os.path.relpath(asset["local_path"], "remotion-video/public").replace(os.sep, "/")
                current_kind = asset["kind"]
                if current_kind == "video":
                    import subprocess
                    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", asset["local_path"]], check=True, capture_output=True, text=True)
                    video_frames = max(1, int(float(probe.stdout.strip()) * 30))
                else:
                    video_frames = None
                credits.append(asset)
                held_seconds = 0
            beat["image_url"] = current_image_url
            beat["media_type"] = current_kind
            beat["video_frames"] = video_frames
            beat["animation_type"] = "zoom"
            beat.pop("sfx_url", None)
            held_seconds += beat.get("duration_estimate", 8)
            beats_with_assets.append(beat)

        # ── 4. Build Final Props JSON ─────────────────────────────────────────
        duration_in_frames = int(total_duration_seconds * 30) + 30  # 1s buffer

        final_props = {
            "title": title,
            "beats": beats_with_assets,
            "subtitles": words,
            "audio_url": audio_filename,
            "atmosphere_url": atmosphere_filename,
            "duration_in_frames": duration_in_frames,
            "fps": 30,
            "credits": credits,
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
