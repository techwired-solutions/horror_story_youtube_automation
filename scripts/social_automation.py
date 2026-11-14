"""One command: create the day's story and image, host it, and publish both feeds."""
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from scripts.social import MetaPublisher, prepare_post
from scripts.social_store import SocialStore, verify_public_image

SETTINGS = ["a night-shift nurse and an unused hospital room", "a father hearing his child on a disconnected baby monitor",
            "a bus driver whose last passenger never gets off", "a tenant receiving letters from next week's date",
            "a forest ranger finding the same cabin in different places", "a hotel clerk and a guest with no reflection",
            "a grandmother's familiar voice from an empty locked cellar", "a lighthouse radio calling from beneath the sea",
            "a delivery driver whose own house appears at every address", "an old family photograph changing overnight",
            "a security guard watching tomorrow's footage", "a phone that rings only when its owner is asleep"]


def prepare_daily(directory, day):
    # Lazy imports keep saved-post retries independent of story provider availability.
    from scripts.script_gen import ScriptGenerator
    from scripts.asset_fetcher import AssetFetcher
    setting = SETTINGS[day.toordinal() % len(SETTINGS)]
    generator = ScriptGenerator()
    for attempt in range(3):
        story = generator.generate_horror_script(
            f"An original, resolved micro-story about {setting}. Creative episode seed: {day.isoformat()}. "
            "Use a fresh protagonist and twist. Keep the entire story to 100-150 words and the title under 45 characters.",
            mode="social")
        if not story:
            continue
        story["story_kind"] = "fiction"
        story["disclosure"] = "An original fictional horror story. Visuals are illustrative."
        photo = None
        fetcher = AssetFetcher()
        queries = [story["parts"][0]["beats"][0].get("stock_query") or "foggy forest", "dark forest", "fog"]
        for query in queries:
            try:
                photo = fetcher.fetch_scene(query, directory / "stock", prefer_video=False)
                break
            except (RuntimeError, OSError):
                continue
        # Facebook alternates native text and photo posts; Instagram always gets a card.
        variant = "text" if day.toordinal() % 2 else "photo"
        try:
            post = prepare_post(story, directory, variant, photo)
        except ValueError:
            continue
        (directory / "story.json").write_text(json.dumps(story, indent=2), encoding="utf-8")
        return post
    raise RuntimeError("Could not create a valid social micro-story after three attempts; nothing published")


def run(day=None, store=None, directory=Path("runs/current")):
    day = day or datetime.now(ZoneInfo("Asia/Kathmandu")).date()
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    store = store or SocialStore()
    store.ensure_branch()
    prefix = f"social/{day.isoformat()}"
    saved = store.read(f"{prefix}/post.json")
    receipt_bytes = store.read(f"{prefix}/publication.json")
    receipts = json.loads(receipt_bytes) if receipt_bytes else {}
    if all(platform in receipts for platform in ("facebook", "instagram")):
        print(f"Both social posts already published for {day}; skipping")
        return
    if saved:
        post = json.loads(saved)
        image = store.read(f"{prefix}/post.jpg")
        if image is None:
            raise RuntimeError("Saved daily image is missing; repair media state before retrying")
        (directory / "post.jpg").write_bytes(image)
    else:
        post = prepare_daily(directory, day)
        image = Path(post["image"]).read_bytes()
        post["image_url"] = store.write(f"{prefix}/post.jpg", image)
        store.save_json(f"{prefix}/post.json", post)
        story = json.loads((directory / "story.json").read_text(encoding="utf-8"))
        store.save_json(f"{prefix}/story.json", story)
    post["image"] = str(directory / "post.jpg")
    (directory / "post.json").write_text(json.dumps(post, indent=2), encoding="utf-8")
    (directory / "caption.txt").write_text(post["caption"], encoding="utf-8")
    receipt_path = directory / "publication.json"
    receipt_path.write_text(json.dumps(receipts, indent=2), encoding="utf-8")
    publisher = MetaPublisher()
    # Authenticate both destinations before creating any public feed posts.
    publisher.resolve_accounts(["facebook", "instagram"])
    if "instagram" not in receipts:
        verify_public_image(post["image_url"], image)
    publisher.publish(post, ["facebook", "instagram"], receipt_path,
                      on_receipt=lambda value: store.save_json(f"{prefix}/publication.json", value),
                      accounts_resolved=True)
    print(f"Daily social publication completed for {day}")


if __name__ == "__main__":
    run()
