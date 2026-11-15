"""Three explicit production paths; generation never implies publication."""
import argparse
import base64
import json
import os
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description="Atmospheric horror production")
    parser.add_argument("--workflow", choices=["long", "short", "social"], default="short")
    parser.add_argument("--topic")
    parser.add_argument("--minutes", type=int, default=10, choices=[5, *range(8, 21)])
    parser.add_argument("--source-file", help="Reviewed factual source notes")
    parser.add_argument("--source-url", help="Attribution URL, required with source-file")
    parser.add_argument("--script-file", help="Reuse an edited story JSON")
    parser.add_argument("--post-file", help="Publish reviewed social post.json without regeneration")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--upload", action="store_true")
    parser.add_argument("--video-platforms", nargs="+", choices=["youtube", "facebook", "instagram"], default=["youtube", "facebook", "instagram"])
    parser.add_argument("--privacy", choices=["private", "unlisted", "public"], default="private")
    parser.add_argument("--variant", choices=["text", "photo"], default="text")
    parser.add_argument("--platforms", nargs="+", choices=["facebook", "instagram"], default=["facebook"])
    parser.add_argument("--output-dir", default="runs/current")
    args = parser.parse_args()
    if bool(args.source_file) != bool(args.source_url):
        parser.error("Supply both --source-file and --source-url")
    if args.post_file:
        if args.workflow != "social" or not args.upload:
            parser.error("--post-file requires --workflow social --upload")
        from scripts.social import MetaPublisher
        path = Path(args.post_file)
        post = json.loads(path.read_text(encoding="utf-8"))
        post["image"] = str(path.parent / "post.jpg")
        MetaPublisher().publish(post, args.platforms, path.parent / "publication.json")
        return
    from scripts.story_policy import validate_story
    directory = Path(args.output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    if args.script_file:
        story = json.loads(Path(args.script_file).read_text(encoding="utf-8"))
        validate_story(story, args.workflow, args.minutes)
    else:
        topic = args.topic
        if not topic:
            from scripts.daily_topic_selector import DailyTopicSelector
            topic = DailyTopicSelector().get_daily_topic()
        from scripts.script_gen import ScriptGenerator
        source = Path(args.source_file).read_text(encoding="utf-8") if args.source_file else ""
        generator = ScriptGenerator()
        story = generator.generate_horror_script(topic, args.workflow, args.minutes, source)
        if not story:
            raise RuntimeError(f"Story generation failed after automatic repair: {generator.last_error}; nothing published")
    story["story_kind"] = "dramatized_source" if args.source_file else "fiction"
    story["disclosure"] = (f"Dramatized account based on supplied source notes. Paranormal claims are unverified. Source: {args.source_url}"
                           if args.source_file else "An original fictional horror story.")
    (directory / "story.json").write_text(json.dumps(story, indent=2), encoding="utf-8")
    if args.workflow == "social":
        from scripts.social import prepare_post, MetaPublisher
        photo = None
        if args.variant == "photo":
            from scripts.asset_fetcher import AssetFetcher
            photo = AssetFetcher().fetch_scene(story["parts"][0]["beats"][0].get("stock_query", "foggy forest"), directory / "stock", prefer_video=False)
        post = prepare_post(story, directory, args.variant, photo)
        if args.upload:
            MetaPublisher().publish(post, args.platforms, directory / "publication.json")
        return
    from scripts.props_builder import PropsBuilder
    builder = PropsBuilder()
    from scripts.video_preparation import prepare_video_parts
    rewrite = None
    if not args.script_file and args.workflow == "short":
        def rewrite(previous, timing_error):
            return generator.generate_horror_script(
                topic, args.workflow, args.minutes, source,
                repair_feedback=("\nActual synthesized narration failed timing: " + timing_error +
                                 "\nRewrite the same plot more concisely, preserving all essential events and the ending. "
                                 "Target 160-220 words per part to allow this narrator's deliberate pauses. "
                                 "Use two parts only if needed. Previous story:\n" + json.dumps(previous)))
    story, prepared = prepare_video_parts(story, builder, directory, args.workflow, args.minutes, rewrite)
    # Render only after every part has passed the actual narration duration check.
    for title, props, video, props_path in prepared:
        if args.render or args.upload:
            subprocess.run(["npx.cmd" if os.name == "nt" else "npx", "remotion", "render",
                            "LongForm" if args.workflow == "long" else "Shorts", str(video),
                            "--props", str(props_path.resolve())], cwd="remotion-video", check=True)
    if args.upload:
        if os.getenv("YOUTUBE_TOKEN_PICKLE_BASE64"):
            Path("token.pickle").write_bytes(base64.b64decode(os.environ["YOUTUBE_TOKEN_PICKLE_BASE64"]))
        if os.getenv("YOUTUBE_CLIENT_SECRET"):
            Path("client_secret.json").write_text(os.environ["YOUTUBE_CLIENT_SECRET"])
        from scripts.video_publishing import publish_videos
        publish_videos(prepared, story, directory, args.privacy, args.video_platforms)



if __name__ == "__main__":
    main()
