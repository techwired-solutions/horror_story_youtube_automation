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

    # 2. Build Script
    logger.info(f"Starting automation for topic: {topic}")
    builder = PropsBuilder()
    from scripts.script_gen import ScriptGenerator
    script_gen = ScriptGenerator()
    script = script_gen.generate_horror_script(topic)
    
    if not script or "parts" not in script:
        logger.error("Failed to generate script or invalid format. Aborting.")
        return

    # Generate Common Thumbnail
    from scripts.asset_fetcher import AssetFetcher
    fetcher = AssetFetcher()
    thumbnail_prompt = f"Scary, cinematic, high-contrast horror thumbnail for: {topic}. Dark, eerie, highly detailed, sharp focus."
    thumbnail_url = fetcher.generate_image(thumbnail_prompt, width=1280, height=720)
    thumbnail_path = os.path.abspath("remotion-video/public/assets/images/thumbnail.png")
    fetcher.download_asset(thumbnail_url, thumbnail_path)

    # Process Each Part
    for part in script["parts"]:
        part_num = part["part_number"]
        total_parts = len(script["parts"])
        logger.info(f"Processing Part {part_num}/{total_parts}...")

        # Build Props for this part
        props = builder.build_props(part, script["title"], part_number=part_num)
        if not props:
            logger.error(f"Failed to build props for Part {part_num}. Skipping.")
            continue

        # 3. Render
        output_file = os.path.abspath(f"remotion-video/out_part_{part_num}.mp4")
        if args.render or args.upload:
            logger.info(f"Triggering Remotion render for Part {part_num}...")
            render_cmd = f"cd remotion-video && npx remotion render Shorts {output_file} --props public/props.json"
            os.system(render_cmd)

        # 4. Upload
        if args.upload:
            from scripts.uploader import YouTubeUploader
            logger.info(f"Starting YouTube upload for Part {part_num}...")
            uploader = YouTubeUploader()
            
            # Build part-specific title and description
            title = props["title"]
            if total_parts > 1:
                title = f"{script['title']} - Part {part_num} | Scary Horror Story #shorts"
            else:
                title = f"{script['title']} | Scary Horror Story #shorts #horror"

            description = f"{script['title']} - Part {part_num}\n\n"
            if part_num < total_parts:
                description += f"Stay tuned for Part {part_num + 1}! Subscribe and hit the bell.\n\n"
            
            description += "Prepare for a chilling journey into the unknown.\n\n"
            description += "#horror #scarystories #scary #creepy #shorts #part" + str(part_num)
            
            tags = ["horror", "scary stories", "creepy", "ghost stories", "horror shorts", f"part {part_num}"]
            
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
