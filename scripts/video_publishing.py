"""Independent YouTube/Facebook publication, with automatic Instagram readiness."""
import json
import os
import subprocess
import time
from pathlib import Path
from scripts.social import MetaPublisher


def upload_facebook_video(publisher, path, title, description, published=True):
    with open(path, "rb") as video:
        result = publisher.request("POST", f"{publisher.page_id}/videos", timeout=900,
                                   data={"title": title[:255], "description": description,
                                         "published": "true" if published else "false"},
                                   files={"source": video})
    if not result.get("id"):
        raise RuntimeError("Facebook did not return a video ID")
    return result


def facebook_video_source(publisher, video_id):
    for _ in range(60):
        result = publisher.request("GET", video_id, params={"fields": "source,status"})
        if result.get("source", "").startswith("https://"):
            return result["source"]
        status = result.get("status", {}).get("video_status")
        if status == "error":
            raise RuntimeError("Facebook video processing failed")
        time.sleep(5)
    raise RuntimeError("Facebook video source is still processing; saved upload ID can be retried")


def instagram_segments(video, props):
    duration = props["duration_in_frames"] / props.get("fps", 30)
    if duration <= 840:
        return [Path(video)]
    # Keep Instagram segments under 15 minutes, cutting at caption/sentence boundaries.
    words = props.get("subtitles", [])
    cuts = [0.0]
    while duration - cuts[-1] > 840:
        candidates = [word for word in words if cuts[-1] + 60 <= word["end"] <= cuts[-1] + 840]
        if not candidates:
            raise RuntimeError("Long Instagram video needs caption timestamps for safe splitting")
        sentences = [word for word in candidates if word["text"].endswith((".", "?", "!"))]
        cuts.append(float((sentences or candidates)[-1]["end"]))
    cuts.append(duration)
    segments = []
    for index, (start, end) in enumerate(zip(cuts, cuts[1:]), 1):
        target = Path(video).with_name(Path(video).stem + f"-instagram-{index}.mp4")
        if not target.exists():
            subprocess.run(["ffmpeg", "-y", "-i", str(video), "-ss", str(start), "-t", str(end - start),
                            "-c:v", "libx264", "-preset", "fast", "-crf", "22", "-c:a", "aac", "-movflags", "+faststart", str(target)],
                           check=True, capture_output=True)
        segments.append(target)
    return segments


def publish_instagram_video(publisher, source, caption, state, save):
    if not state.get("container_id"):
        container = publisher.request("POST", f"{publisher.instagram_id}/media", data={
            "media_type": "REELS", "video_url": source, "caption": caption[:2200], "share_to_feed": "true"})
        state["container_id"] = container["id"]
        save()
    container_id = state["container_id"]
    for _ in range(60):
        status = publisher.request("GET", container_id, params={"fields": "status_code"}).get("status_code")
        if status == "PUBLISHED":
            state["published"] = True
            save()
            return
        if status == "FINISHED":
            break
        if status in {"ERROR", "EXPIRED"}:
            raise RuntimeError(f"Instagram video container {status}; inspect before retrying")
        time.sleep(5)
    else:
        raise RuntimeError("Instagram video is still processing; container receipt saved")
    result = publisher.request("POST", f"{publisher.instagram_id}/media_publish", data={"creation_id": container_id})
    state.update(result=result, published=True)
    save()


def publish_videos(prepared, story, directory, privacy="private", platforms=None, youtube_factory=None, meta_factory=None):
    platforms = platforms or ["youtube", "facebook", "instagram"]
    receipt_path = Path(directory) / "publication.json"
    receipts = json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
    # Preserve receipts created by the original YouTube-only pipeline.
    receipts = {key: ({"youtube": value} if isinstance(value, str) else value) for key, value in receipts.items()}
    def save():
        receipt_path.write_text(json.dumps(receipts, indent=2), encoding="utf-8")
    save()
    if youtube_factory is None:
        from scripts.uploader import YouTubeUploader
        youtube_factory = YouTubeUploader
    meta_factory = meta_factory or MetaPublisher
    failures = []
    youtube = None
    for number, (title, props, video, _) in enumerate(prepared, 1):
        state = receipts.setdefault(str(number), {})
        credits = "\n".join(f"{item['creator']} / {item['provider']}: {item['page_url']}" for item in props.get("credits", []))
        description = story["disclosure"] + "\n\nStock visuals (illustrative):\n" + credits
        for platform in platforms:
            if platform in state and platform != "instagram":
                continue
            try:
                if platform == "youtube":
                    youtube = youtube or youtube_factory()
                    result = youtube.upload_video(str(video), title, description[:5000], tags=["horror", "scary stories"], privacy_status=privacy)
                    if not result:
                        raise RuntimeError("YouTube did not return a video ID")
                    state[platform] = result
                    save()
                elif platform == "facebook":
                    publisher = meta_factory()
                    publisher.check_permissions(["facebook"])
                    publisher.resolve_accounts(["facebook"])
                    state[platform] = upload_facebook_video(publisher, video, title, description)
                    save()
                elif platform == "instagram":
                    publisher = meta_factory()
                    if not publisher.instagram_available():
                        continue
                    segments = instagram_segments(video, props)
                    ig_states = state.setdefault("instagram", {})
                    for index, segment in enumerate(segments, 1):
                        item = ig_states.setdefault(str(index), {})
                        if item.get("published"):
                            continue
                        if not item.get("facebook_source_id"):
                            if len(segments) == 1 and state.get("facebook"):
                                item["facebook_source_id"] = state["facebook"]["id"]
                            else:
                                # Staging upload is not published to the Facebook feed.
                                upload = upload_facebook_video(publisher, segment, title, description, published=False)
                                item["facebook_source_id"] = upload["id"]
                            save()
                        source = facebook_video_source(publisher, item["facebook_source_id"])
                        caption = title + (f" - Part {index}/{len(segments)}" if len(segments) > 1 else "") + "\n\n" + description
                        publish_instagram_video(publisher, source, caption, item, save)
            except Exception as error:
                failures.append(f"part {number} {platform}: {error}")
    if failures:
        raise RuntimeError("Video publication incomplete; confirmed uploads were saved. " + " | ".join(failures))
    return receipts
