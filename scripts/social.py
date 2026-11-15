"""Facebook Page posts and Instagram photo/text-card publishing (Facebook Login)."""
import json
import os
import textwrap
from pathlib import Path
import requests


def prepare_post(story, directory, variant="text", photo=None):
    from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageEnhance
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    caption = story["title"] + "\n\n" + "\n\n".join(b["text"] for p in story["parts"] for b in p["beats"])
    caption += "\n\n" + story["disclosure"]
    if photo:
        caption += f"\nPhoto: {photo['creator']} / {photo['provider']} â€” {photo['page_url']}"
    if len(caption) > 2200:
        raise ValueError("Social caption exceeds Instagram's 2200-character limit; shorten the story")
    image = Image.new("RGB", (1080, 1350), "#0c1018")
    if photo:
        with Image.open(photo["local_path"]) as source:
            image = ImageEnhance.Brightness(ImageOps.fit(source.convert("RGB"), image.size)).enhance(0.35)
    draw = ImageDraw.Draw(image)
    font = None
    for name in (os.getenv("SOCIAL_FONT", ""), "DejaVuSans.ttf", "C:/Windows/Fonts/arial.ttf"):
        try:
            font = ImageFont.truetype(name, 48)
            break
        except OSError:
            pass
    font = font or ImageFont.load_default()
    card_text = story["title"] + "\n\n" + story["parts"][0]["beats"][0]["text"] + "\n\nRead the story in the caption."
    lines = []
    for paragraph in card_text.split("\n"):
        line = ""
        for word in paragraph.split():
            candidate = (line + " " + word).strip()
            if line and draw.textlength(candidate, font=font) > 920:
                lines.append(line)
                line = word
            else:
                line = candidate
        lines.append(line)
    lines = "\n".join(lines)
    box = draw.multiline_textbbox((0, 0), lines, font=font, spacing=18)
    if box[2] > 920 or box[3] > 1100:
        raise ValueError("Text card overflows; shorten the title/opening beat")
    draw.multiline_text((80, 120), lines, font=font, fill="#f0e9df", spacing=18)
    image.save(directory / "post.jpg", quality=95)
    post = {"caption": caption, "variant": variant, "image": str(directory / "post.jpg")}
    (directory / "post.json").write_text(json.dumps(post, indent=2), encoding="utf-8")
    (directory / "caption.txt").write_text(caption, encoding="utf-8")
    return post


class MetaPublisher:
    def __init__(self):
        version = os.getenv("META_GRAPH_API_VERSION", "")
        if not version:
            raise ValueError("Set META_GRAPH_API_VERSION to a supported Meta Graph API version")
        self.base = f"https://graph.facebook.com/{version}"
        self.token = os.getenv("META_ACCESS_TOKEN") or os.getenv("META_USER_TOKEN")
        if not self.token:
            raise ValueError("Set META_USER_TOKEN or META_ACCESS_TOKEN")
        self.page_id = os.getenv("FACEBOOK_PAGE_ID") or os.getenv("FACEBOOK_ID")
        self.instagram_id = os.getenv("INSTAGRAM_ACCOUNT_ID")

    def request(self, method, path, **kwargs):
        response = requests.request(method, f"{self.base}/{path}",
                                    headers={"Authorization": f"Bearer {self.token}"}, timeout=60, **kwargs)
        if not response.ok:
            try:
                error = response.json().get("error", {})
            except ValueError:
                error = {}
            import re
            details = {key: error[key] for key in (
                "code", "error_subcode", "type", "message", "error_user_title", "error_user_msg", "fbtrace_id") if key in error}
            safe = json.dumps(details, ensure_ascii=False)
            for secret in (self.token, os.getenv("META_USER_TOKEN"), os.getenv("META_ACCESS_TOKEN")):
                if secret:
                    safe = safe.replace(secret, "<redacted>")
            safe = re.sub(r'https?://[^\s"<>]+', '<url>', safe)
            raise RuntimeError(f"Meta request failed: HTTP {response.status_code}, {safe}")
        return response.json()

    def check_permissions(self, platforms):
        # User grants can be inspected before exchanging for a Page token.
        if not os.getenv("META_USER_TOKEN") or os.getenv("META_ACCESS_TOKEN"):
            return
        result = self.request("GET", "me/permissions")
        granted = {item["permission"] for item in result.get("data", []) if item.get("status") == "granted"}
        required = set()
        if "facebook" in platforms:
            required.add("pages_manage_posts")
        if "instagram" in platforms:
            required.update({"instagram_basic", "instagram_content_publish", "pages_read_engagement"})
        missing = sorted(required - granted)
        if missing:
            raise ValueError("META_USER_TOKEN is missing granted permissions: " + ", ".join(missing) +
                             ". Regenerate the user token in the same Meta app with these permissions and update the GitHub secret.")

    def resolve_accounts(self, platforms):
        if not self.page_id:
            raise ValueError("FACEBOOK_ID must be the Facebook Page ID, not a personal profile ID")
        if not os.getenv("META_ACCESS_TOKEN"):
            # A user token must first resolve the Page-scoped publishing token.
            page = self.request("GET", self.page_id, params={
                "fields": "id,access_token" + (",instagram_business_account" if "instagram" in platforms else "")})
            if not page.get("access_token"):
                raise ValueError("Cannot obtain Page token; check Page access and pages_show_list/pages_read_engagement permissions")
            self.token = page["access_token"]
            self.instagram_id = self.instagram_id or (page.get("instagram_business_account") or {}).get("id")
        elif "instagram" in platforms and not self.instagram_id:
            page = self.request("GET", self.page_id, params={"fields": "instagram_business_account"})
            self.instagram_id = (page.get("instagram_business_account") or {}).get("id")
        if "instagram" in platforms and not self.instagram_id:
            raise ValueError("Connect an Instagram Business/Creator account to this Page, or set INSTAGRAM_ACCOUNT_ID")

    def publish(self, post, platforms, receipt_path, on_receipt=None, accounts_resolved=False):
        import time
        receipt_path = Path(receipt_path)
        receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
        def save_receipt():
            receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
            if on_receipt:
                on_receipt(receipt)

        platforms = [platform for platform in platforms if platform not in receipt]
        if not platforms:
            return receipt
        # Validate everything before the first external write.
        image_url = post.get("image_url") or os.getenv("INSTAGRAM_IMAGE_URL")
        if "instagram" in platforms and (not image_url or not image_url.startswith("https://")):
            raise ValueError("Instagram needs INSTAGRAM_IMAGE_URL: a public HTTPS URL serving this exact post.jpg")
        if not accounts_resolved:
            self.resolve_accounts(platforms)
        for platform in platforms:
            if platform in receipt:
                continue
            if platform == "facebook":
                page = self.page_id
                if post["variant"] == "text":
                    result = self.request("POST", f"{page}/feed", data={"message": post["caption"]})
                else:
                    with open(post["image"], "rb") as photo:
                        result = self.request("POST", f"{page}/photos", data={"caption": post["caption"]}, files={"source": photo})
            else:
                account = self.instagram_id
                container_key = "instagram_container"
                if container_key not in receipt:
                    container = self.request("POST", f"{account}/media", data={"image_url": image_url, "caption": post["caption"]})
                    receipt[container_key] = container["id"]
                    save_receipt()
                container_id = receipt[container_key]
                for _ in range(24):
                    status = self.request("GET", container_id, params={"fields": "status_code"}).get("status_code")
                    if status == "FINISHED":
                        break
                    if status in {"ERROR", "EXPIRED"}:
                        raise RuntimeError(f"Instagram container {status}")
                    time.sleep(5)
                else:
                    raise RuntimeError("Instagram container not ready; receipt saved")
                result = self.request("POST", f"{account}/media_publish", data={"creation_id": container_id})
            receipt[platform] = result
            save_receipt()
        return receipt
