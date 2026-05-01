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
        
        Target Audience: American viewers (Focus on real scary incidents, true paranormal cases, ancient cultural folklore, or terrifying facts).
        
        The script should be broken into "parts" if the story is long. Each part MUST be under 1 minute of narration.
        
        CRITICAL RULES FOR PERFORMANCE NARRATION (BEAT-BASED):
        1. SINGLE NARRATOR ONLY: No character voice switching. One late-night paranormal storyteller. Style: Mr Nightmare / Lighthouse Horror.
        2. BEAT-BASED NARRATION: Do NOT write prose paragraphs. Write short, punchy performance beats.
           - Bad: "He looked behind him and saw something standing there in the trees."
           - Good: "He looked behind him...", "And then he saw it—", "Something standing...", "In the trees."
           - Max 3-8 words per beat when possible. One dramatic idea per beat. One breath per beat.
        3. NO ADJECTIVE-HEAVY PROSE: Use concrete imagery.
        4. EMOTIONAL ARC: calm unease → dread → reveal → panic → haunted ending.
        5. PUNCTUATION SHAPING:
           - comma = short pause
           - period = medium pause
           - ellipsis = suspense
           - dash = abrupt realization
        6. NO BRACKET TAGS: Do not write [whispers] in the text. Use the 'delivery' field instead.
        7. DELIVERY MODES: Must be exactly one of: calm, unease, dread, whisper, reveal, panic, terror, ending.
        8. PACING: hook within 2 seconds, open loop curiosity, escalating dread, cliffhanger if multipart.
        
        Format the output as a JSON object:
        {{
            "title": "Viral Story Title",
            "character_description": "detailed visual description",
            "parts": [
                {{
                    "part_number": 1,
                    "music_mood": "e.g. slow creeping dread with building paranoia",
                    "beats": [
                        {{
                            "text": "Something was standing there—",
                            "delivery": "reveal",
                            "pause_after": 0.6,
                            "emphasis_word": "Something",
                            "image_prompt": "Cinematic shot of dark trees...",
                            "sfx_prompt": "creaking wood",
                            "animation_type": "zoom",
                            "duration_estimate": 2
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
