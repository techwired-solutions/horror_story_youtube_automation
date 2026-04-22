import os
import argparse
from scripts.props_builder import PropsBuilder
from loguru import logger

def main():
    parser = argparse.ArgumentParser(description="Horror Video Automation Orchestrator")
    parser.add_argument("--topic", type=str, help="Topic for the horror story (optional, defaults to daily selection)")
    parser.add_argument("--render", action="store_true", help="Whether to trigger remotion render")
    parser.add_argument("--upload", action="store_true", help="Whether to upload to YouTube")
    args = parser.parse_args()

    # 0. Auth Restoration (For GitHub Actions)
    if os.getenv("YOUTUBE_TOKEN_PICKLE_BASE64"):
        import base64
        logger.info("Restoring token.pickle from environment variable...")
        token_data = base64.b64decode(os.getenv("YOUTUBE_TOKEN_PICKLE_BASE64"))
        with open("token.pickle", "wb") as f:
            f.write(token_data)
    
    if os.getenv("YOUTUBE_CLIENT_SECRET"):
        logger.info("Restoring client_secret.json from environment variable...")
        with open("client_secret.json", "w") as f:
            f.write(os.getenv("YOUTUBE_CLIENT_SECRET"))

    # 1. Topic Selection
    topic = args.topic
    if not topic:
        from scripts.daily_topic_selector import DailyTopicSelector
        selector = DailyTopicSelector()
        topic = selector.get_daily_topic()

    # 2. Build Props and Fetch Assets
    logger.info(f"Starting automation for topic: {topic}")
    builder = PropsBuilder()
    props = builder.build_props(topic)

    if not props:
        logger.error("Failed to build props. Aborting.")
        return

    # Generate Thumbnail Image (Square or 16:9 for YouTube, but portrait for Shorts)
    from scripts.asset_fetcher import AssetFetcher
    fetcher = AssetFetcher()
    thumbnail_prompt = f"Scary, cinematic, high-contrast horror thumbnail for: {topic}. Dark, eerie, highly detailed, sharp focus."
    thumbnail_url = fetcher.generate_image(thumbnail_prompt, width=1280, height=720) # YouTube standard
    thumbnail_path = os.path.abspath("remotion-video/public/assets/images/thumbnail.png")
    fetcher.download_asset(thumbnail_url, thumbnail_path)

    logger.success("Assets fetched and props.json generated.")

    # 3. Render
    output_file = os.path.abspath("remotion-video/out.mp4")
    if args.render or args.upload:
        logger.info("Triggering Remotion render...")
        render_cmd = f"cd remotion-video && npx remotion render Shorts {output_file} --props public/props.json"
        os.system(render_cmd)

    # 4. Upload
    if args.upload:
        from scripts.uploader import YouTubeUploader
        logger.info("Starting YouTube upload...")
        uploader = YouTubeUploader()
        
        # Build optimized title and description
        title = f"{props['title']} | Scary Horror Story #shorts #horror"
        description = f"{props['title']}\n\n"
        description += "Prepare for a chilling journey into the unknown. This horror story will keep you on the edge of your seat.\n\n"
        description += "#horror #scarystories #scary #creepy #paranormal #shorts #americanhorror"
        
        tags = ["horror", "scary stories", "creepy", "ghost stories", "urban legends", "horror shorts", "american horror"]
        
        video_id = uploader.upload_video(
            file_path=output_file,
            title=title,
            description=description,
            tags=tags,
            privacy_status="public"
        )

        if video_id:
            uploader.set_thumbnail(video_id, thumbnail_path)

if __name__ == "__main__":
    main()
