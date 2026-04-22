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
        
        The script should be structured for a 50-60 second video.
        
        CRITICAL INSTRUCTIONS FOR SCARINESS:
        1. Narrative Style: Use ElevenLabs emotional tags like [whispers], [sighs], [giggles], [trembling], [excited], and [slow pacing] directly in the narration text. These tags MUST be in lowercase and in square brackets.
        2. Realism & Folklore: Focus on "True" stories. Use hooks like "Did you know that in [Culture]..." or "This historical incident in [City/Year] still haunts...". Pull from real urban legends, documented paranormal cases, or eerie cultural facts (e.g. Japanese legends like Okiku, or modern creepy encounters like Black Eyed Children).
        3. Character Consistency: If there is a protagonist, provide a detailed 'character_description' (e.g., "a 10-year-old boy with messy blonde hair and a striped blue shirt").
        3. Visuals: For each scene, provide a highly detailed 'image_prompt' suitable for AI generation. Always include the 'character_description' if the character is in the scene.
        4. SFX: Suggest a specific 'sfx_prompt' for each scene (e.g., "heavy breathing and distant floorboard creak").
        5. Animations: For each scene, specify an 'animation_type' from: [zoom, pop, slide_up, slide_down, fade].
        
        Format the output as a JSON object:
        {{
            "title": "Viral Story Title",
            "character_description": "detailed visual description for consistency",
            "scenes": [
                {{
                    "text": "Narration text with [Tags] here...",
                    "image_prompt": "Cinematic horror style image of...",
                    "sfx_prompt": "sound effect description",
                    "animation_type": "zoom",
                    "duration_estimate": 8
                }},
                ...
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
