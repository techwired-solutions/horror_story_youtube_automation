import os
import google.generativeai as genai
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

class DailyTopicSelector:
    def __init__(self, model_name="gemini-3-flash-preview"):
        self.model = genai.GenerativeModel(model_name)

    def get_daily_topic(self):
        prompt = """
        Suggest a single, specific, and highly engaging "Real Horror" topic for a YouTube Short.
        It should be one of these:
        1. A documented true paranormal incident (e.g. skinwalkers, specific haunted places).
        2. A terrifying cultural legend (e.g. Japanese folklore, European urban legends).
        3. A "Did You Know" style scary fact from history or culture.
        
        Focus on topics that are popular in American culture or trending urban legends.
        Return ONLY the topic name as a string, no other text.
        Example output: The legend of the Black Eyed Children
        """
        try:
            logger.info("Fetching daily horror topic from Gemini...")
            response = self.model.generate_content(prompt)
            topic = response.text.strip()
            logger.success(f"Selected Daily Topic: {topic}")
            return topic
        except Exception as e:
            logger.error(f"Failed to fetch daily topic: {e}")
            return "The Shadow in the Window" # Fallback

if __name__ == "__main__":
    selector = DailyTopicSelector()
    print(selector.get_daily_topic())
