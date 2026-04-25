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
        history_path = "assets/used_topics.txt"
        used_topics = []
        if os.path.exists(history_path):
            with open(history_path, "r") as f:
                used_topics = [line.strip() for line in f.readlines() if line.strip()]

        history_str = "\n".join(used_topics[-50:]) # Send last 50 topics for context
        
        prompt = f"""
        Suggest a single, specific, and highly engaging "Real Horror" topic for a YouTube Short.
        
        CRITICAL: Do NOT suggest any of the following previously used topics:
        {history_str}
        
        It should be one of these:
        1. A documented true paranormal incident (e.g. skinwalkers, specific haunted places).
        2. A terrifying cultural legend (e.g. Japanese folklore, European urban legends).
        3. A "Did You Know" style scary fact from history or culture.
        
        Focus on fresh, unique, and terrifying topics that are popular in American culture or trending urban legends. 
        Think outside the box (e.g. avoid overused ones like generic skinwalkers unless it's a very specific documented case).
        
        Return ONLY the topic name as a string, no other text.
        Example output: The legend of the Black Eyed Children
        """
        try:
            logger.info("Fetching daily horror topic from Gemini with history context...")
            response = self.model.generate_content(prompt)
            topic = response.text.strip()
            
            # Save to history
            with open(history_path, "a") as f:
                f.write(f"{topic}\n")
                
            logger.success(f"Selected and saved Daily Topic: {topic}")
            return topic
        except Exception as e:
            logger.error(f"Failed to fetch daily topic: {e}")
            return "The Shadow in the Window" # Fallback

if __name__ == "__main__":
    selector = DailyTopicSelector()
    print(selector.get_daily_topic())
