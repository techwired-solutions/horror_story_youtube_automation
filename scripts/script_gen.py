import os
import google.generativeai as genai
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

class ScriptGenerator:
    def __init__(self, model_name="gemini-3-flash-preview"):
        self.model = genai.GenerativeModel(model_name)

    def generate_horror_script(self, topic: str):
        prompt = f"""
        Write a high-detail, cinematic horror story script for a YouTube Short about: {topic}.
        
        Target Audience: American viewers (Focus on real scary incidents, true paranormal cases, ancient cultural folklore, or terrifying "did you know" facts).
        
        The script should be broken into "parts" if the story is long. Each part MUST be under 1 minute of narration (approx. 130-150 words).
        If the story fits in one part, only return one part.
        
        CRITICAL INSTRUCTIONS FOR SCARINESS & STRUCTURE:
        1. Narrative Style: Write in an expressive, emotionally charged style — use dramatic pauses (...), vivid sensory language, and vary sentence rhythm to build tension. Do NOT include any bracketed tags like [whispers] or [slow pacing] in the narration text — they must not appear in the script at all.
        2. Realism & Folklore: Focus on "True" stories, urban legends, or documented cases.
        3. Multi-Part Hooks: If there is a next part, the narration MUST end with a cliffhanger followed by "Subscribe for Part [Next Part Number]".
        4. Part Intro: If it's Part 2 or higher, start with "Part [Number] of [Title]".
        5. Visuals: Provide a 'character_description' for consistency and 'image_prompt' for each scene.
        6. SFX Prompts: The 'sfx_prompt' for each scene must be a SHORT 2-3 word Freesound.org search query (e.g. "creaking door", "wind howling", "heartbeat suspense", "ghost whisper", "thunder storm"). Do NOT write long sentences.
        
        Format the output as a JSON object:
        {{
            "title": "Viral Story Title",
            "character_description": "detailed visual description",
            "parts": [
                {{
                    "part_number": 1,
                    "music_mood": "A 5-10 word description of the emotional pace for background music, e.g. 'slow creeping dread with building paranoia' or 'sudden terror and panic'. Must reflect the PACE and TONE of the narration — never upbeat.",
                    "scenes": [
                        {{
                            "text": "Narration text...",
                            "image_prompt": "Prompt...",
                            "sfx_prompt": "sound effect",
                            "animation_type": "zoom",
                            "duration_estimate": 8
                        }}
                    ]
                }}
            ]
        }}
        """
        logger.info(f"Generating horror script for topic: {topic}")
        response = self.model.generate_content(prompt)
        
        # Simple JSON extraction from response text
        import json
        text = response.text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        
        try:
            script_data = json.loads(text.strip())
            logger.success("Script generated successfully")
            return script_data
        except Exception as e:
            logger.error(f"Failed to parse script JSON: {e}")
            logger.debug(f"Raw response: {text}")
            return None

if __name__ == "__main__":
    gen = ScriptGenerator()
    test_script = gen.generate_horror_script("The Whispering Well")
    print(test_script)
