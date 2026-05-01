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

        Target Audience: American viewers (real scary incidents, true paranormal cases, ancient cultural folklore, or terrifying facts).

        The script MUST be broken into "parts" if the story is long. Each part MUST be at least 45 seconds of narration (approx. 100-130 words).
        You MUST generate at least 25-30 beats per part to ensure the duration exceeds 40 seconds.
        If the story cannot be completed within 1 minute, break it into multiple parts (e.g., Part 1, Part 2).
        At the end of EVERY part except the final one, you MUST end on a cliffhanger and the very last beat MUST explicitly say "Like and follow for Part [Next Number]!" or similar.

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
           - ellipsis (...) = heavy suspense, let it hang
           - dash (—) = abrupt, shocking realization
        6. NO BRACKET TAGS: Do not write [whispers] in the text. Use the 'delivery' field instead.
        7. DELIVERY MODES: Must be exactly one of: calm, unease, dread, whisper, reveal, panic, terror, ending.
        8. PACING: hook within 2 seconds, open loop curiosity, escalating dread, cliffhanger if multipart.

        CRITICAL — PAUSE RULES (pause_after in seconds):
        Each beat is spoken as its own breath. The pause_after value controls the SILENCE after the narrator
        finishes that beat before the next line begins. You MUST follow these ranges per delivery type to
        create real horror pacing — do NOT flatten all beats to the same value:
          - calm:    0.3 – 0.6   (steady, slow opening)
          - unease:  0.5 – 0.8   (slight tension building)
          - dread:   0.8 – 1.2   (heavy, uncomfortable silence)
          - whisper: 1.0 – 1.5   (haunting — let the whisper linger)
          - reveal:  1.2 – 2.0   (the big moment — maximum silence for impact)
          - panic:   0.4 – 0.6   (fast, breathless, but still spaced)
          - terror:  0.8 – 1.2   (raw fear — pause to let it sink in)
          - ending:  1.5 – 2.5   (haunted close — longest silence of all)
        A reveal beat with pause_after: 0.3 is WRONG. A whisper with pause_after: 0.2 is WRONG.
        Think of pause_after as: how many seconds of dead air follow this line on a horror podcast?

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
                            "pause_after": 1.5,
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
