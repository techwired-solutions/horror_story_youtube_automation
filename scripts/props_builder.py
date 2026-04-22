import os
import json
from scripts.script_gen import ScriptGenerator
from scripts.audio_gen import AudioGenerator
from scripts.asset_fetcher import AssetFetcher
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

class PropsBuilder:
    def __init__(self):
        self.script_gen = ScriptGenerator()
        self.audio_gen = AudioGenerator()
        self.asset_fetcher = AssetFetcher()

    def align_words(self, characters, start_times, end_times, full_text):
        """
        Groups character-level timestamps into word-level timestamps.
        """
        words_data = []
        current_word = ""
        current_start = 0
        
        for char, start, end in zip(characters, start_times, end_times):
            if char.isspace():
                if current_word:
                    words_data.append({
                        "text": current_word,
                        "start": current_start,
                        "end": end
                    })
                    current_word = ""
            else:
                if not current_word:
                    current_start = start
                current_word += char
        
        if current_word:
            words_data.append({
                "text": current_word,
                "start": current_start,
                "end": end_times[-1]
            })
            
        return words_data

    def build_props(self, topic: str, output_path: str = "remotion-video/public/props.json"):
        script = self.script_gen.generate_horror_script(topic)
        if not script:
            return None

        full_narration = " ".join([scene["text"] for scene in script["scenes"]])
        
        # Generate Audio
        audio_result = self.audio_gen.generate_speech(full_narration, output_path="remotion-video/public/assets/audio/speech.mp3")
        if not audio_result:
            return None

        alignment = audio_result["alignment"]
        words = self.align_words(
            alignment["characters"],
            alignment["character_start_times_seconds"],
            alignment["character_end_times_seconds"],
            full_narration
        )

        # Download Assets and Generate SFX
        scenes_with_assets = []
        for i, scene in enumerate(script["scenes"]):
            # 1. Generate Image
            image_url = self.asset_fetcher.generate_image(scene["image_prompt"])
            image_path = f"assets/images/scene_{i}.png"
            local_image_path = os.path.join("remotion-video/public", image_path)
            self.asset_fetcher.download_asset(image_url, local_image_path)
            scene["image_url"] = image_path
            
            # 2. Generate Scene SFX
            sfx_path = f"assets/audio/sfx_{i}.mp3"
            local_sfx_path = os.path.join("remotion-video/public", sfx_path)
            self.audio_gen.generate_sfx(scene["sfx_prompt"], output_path=local_sfx_path)
            scene["sfx_url"] = sfx_path
            
            scenes_with_assets.append(scene)

        # Generate SFX (Atmosphere)
        sfx_path = "assets/audio/atmosphere.mp3"
        self.audio_gen.generate_sfx("deep creepy horror atmosphere with subtle whispers", 
                                   output_path=os.path.join("remotion-video/public", sfx_path))

        final_props = {
            "title": script["title"],
            "scenes": scenes_with_assets,
            "subtitles": words,
            "audio_url": "assets/audio/speech.mp3",
            "atmosphere_url": sfx_path,
            "fps": 30
        }

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(final_props, f, indent=4)
        
        logger.success(f"Props file generated at {output_path}")
        return final_props

if __name__ == "__main__":
    builder = PropsBuilder()
    builder.build_props("The Shadow in the Mirror")
