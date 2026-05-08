import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

class ScriptGenerator:
    def __init__(self, model_name="gemini-3-flash-preview"):
        self.model = genai.GenerativeModel(model_name)
        self.nvidia_api_key = os.getenv("NVIDIA_NIM_API_KEY")

    def _generate_with_nvidia(self, prompt: str):
        import requests
        import json
        if not self.nvidia_api_key:
            return None
            
        logger.info("Generating script with NVIDIA NIM (Llama 3.1 70B)...")
        url = "https://integrate.api.nvidia.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.nvidia_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        payload = {
            "model": "meta/llama-3.1-70b-instruct",
            "messages": [
                {"role": "system", "content": "You are a master horror storyteller and scriptwriter."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 4096,
        }
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=90)
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            else:
                logger.error(f"NVIDIA LLM Error: {resp.status_code} {resp.text}")
                return None
        except Exception as e:
            logger.error(f"NVIDIA LLM Exception: {e}")
            return None

    def generate_horror_script(self, topic: str):
        prompt = f"""
        Write a high-detail, cinematic horror story script for a YouTube Short about: {topic}.

        Target Audience: American viewers (real scary incidents, true paranormal cases, ancient cultural folklore, or terrifying facts).

        CRITICAL RULES FOR SCRIPT STRUCTURE:
        1. IF the story can be told concisely and beautifully within 60 seconds (approx. 100-150 words), generate ONLY ONE part. Do NOT artificially stretch it.
        2. IF the story genuinely requires more time (e.g. 80+ seconds), break it into logical parts (e.g., Part 1: 50 seconds, Part 2: 30 seconds).
        3. DO NOT repeat dialogue or artificially loop just to create a second part.
        4. If generating a single part, do not use cliffhangers.
        5. If generating multiple parts:
           - Part 1 must end on a cliffhanger, and the very last beat MUST be explicitly "Like and subscribe for Part 2!" (or similar).
           - Part 2 must start with a beat announcing the title and part (e.g. "The Whispering Well, Part 2").
           - Part 2 must end with a beat explicitly saying "Subscribe for more terrifying stories!" (or similar).

        CRITICAL RULES FOR PERFORMANCE NARRATION (BEAT-BASED):
        1. DUAL-VOICE NARRATION:
           - Use the "male" voice exclusively for the deep, unsettling horror storytelling.
           - Use the "female" voice exclusively for introductory title reveals, "Subscribe for Part X" calls to action, and standard non-story branding.
        2. BEAT-BASED NARRATION: Do NOT write prose paragraphs. Write short, punchy performance beats.
           - Max 3-8 words per beat when possible. One dramatic idea per beat. One breath per beat.
        3. NO ADJECTIVE-HEAVY PROSE: Use concrete imagery.
        4. PUNCTUATION SHAPING:
           - comma = short pause
           - period = medium pause
           - ellipsis (...) = heavy suspense, let it hang
           - dash (—) = abrupt, shocking realization
        5. NO BRACKET TAGS OR ASTERISKS: Do not write [whispers] or *sighs* in the text.
        6. DELIVERY MODES: Must be exactly one of: calm, unease, dread, whisper, reveal, panic, terror, ending.
        7. PACING: hook within 2 seconds, open loop curiosity, escalating dread.

        CRITICAL — PAUSE RULES (pause_after in seconds):
        Each beat is spoken as its own breath. Follow these ranges per delivery type:
          - calm:    0.3 – 0.6
          - unease:  0.5 – 0.8
          - dread:   0.8 – 1.2
          - whisper: 1.0 – 1.5
          - reveal:  1.2 – 2.0
          - panic:   0.4 – 0.6
          - terror:  0.8 – 1.2
          - ending:  1.5 – 2.5

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
                            "text": "The Whispering Well, Part 1",
                            "voice": "female",
                            "delivery": "calm",
                            "pause_after": 0.5,
                            "emphasis_word": "Well",
                            "image_prompt": "Cinematic shot of dark trees...",
                            "sfx_prompt": "ambient wind",
                            "animation_type": "zoom",
                            "duration_estimate": 2
                        }},
                        {{
                            "text": "Something was standing there—",
                            "voice": "male",
                            "delivery": "reveal",
                            "pause_after": 1.5,
                            "emphasis_word": "Something",
                            "image_prompt": "Cinematic shot of dark trees...",
                            "sfx_prompt": "creaking wood",
                            "animation_type": "pan",
                            "duration_estimate": 2
                        }}
                    ]
                }}
            ]
        }}
        """
        logger.info(f"Generating horror script for topic: {topic}")
        
        # 1. Try NVIDIA NIM (Primary)
        text = self._generate_with_nvidia(prompt)
        
        # 2. Try Gemini (Fallback)
        if not text:
            logger.warning("NVIDIA NIM script generation failed or skipped. Falling back to Gemini...")
            try:
                response = self.model.generate_content(prompt)
                text = response.text
            except Exception as e:
                logger.error(f"Gemini generation failed: {e}")
                return None
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
