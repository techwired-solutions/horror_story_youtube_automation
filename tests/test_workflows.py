import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock
from scripts.story_policy import validate_story, check_render_duration
from scripts.asset_fetcher import AssetFetcher
from scripts.social import prepare_post, MetaPublisher


def story():
    return {"title": "The Empty Room", "disclosure": "An original fictional horror story.", "parts": [{"beats": [
        {"text": "Every night I heard my own voice behind the locked door.", "pause_after": 1.5},
        {"text": "Every night I heard my own voice behind the locked door.", "pause_after": 1.5}]}]}


class WorkflowTests(unittest.TestCase):
    def test_repetition_and_consistent_narrator(self):
        data = validate_story(story(), "short")
        self.assertEqual(len(data["parts"][0]["beats"]), 2)
        self.assertEqual(data["parts"][0]["beats"][0]["voice"], "male")

    def test_limits_include_tail(self):
        check_render_duration(179, "short")
        for duration in [179.1, 180, float("nan"), -1]:
            with self.assertRaises(ValueError):
                check_render_duration(duration, "short")
        check_render_duration(600, "long", 10)
        with self.assertRaises(ValueError):
            check_render_duration(200, "long", 10)

    def test_parts_and_estimate(self):
        data = story()
        data["parts"] *= 3
        with self.assertRaises(ValueError): validate_story(data, "short")
        data = story()
        data["parts"][0]["beats"][0]["text"] = "word " * 400
        with self.assertRaises(ValueError): validate_story(data, "short")

    def test_stock_fallback(self):
        with patch.dict("os.environ", {"PEXELS_API_KEY": "test", "PIXABAY_API_KEY": "test"}):
            fetcher = AssetFetcher()
            first = Mock(); first.json.return_value = {"photos": []}
            second = Mock(); second.json.return_value = {"hits": [{"largeImageURL": "https://cdn.example/photo.jpg", "pageURL": "https://pixabay.com/photos/1", "user": "Artist"}]}
            fetcher.session.get = Mock(side_effect=[first, second])
            asset = fetcher.search("fog")
            self.assertEqual(asset["provider"], "pixabay")
            self.assertIn("license_url", asset)

    def test_social_card_and_caption_limit(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as directory:
            post = prepare_post(story(), directory)
            with Image.open(post["image"]) as image:
                self.assertEqual(image.size, (1080, 1350))
                self.assertEqual(image.format, "JPEG")
            self.assertIn("fictional", post["caption"])
            data = story(); data["parts"][0]["beats"][0]["text"] = "a" * 2300
            with self.assertRaises(ValueError): prepare_post(data, directory)

    def test_social_preflight_prevents_partial_publish(self):
        with patch.dict("os.environ", {"META_GRAPH_API_VERSION": "vTEST", "META_ACCESS_TOKEN": "test", "INSTAGRAM_IMAGE_URL": ""}):
            publisher = MetaPublisher(); publisher.request = Mock()
            with tempfile.TemporaryDirectory() as directory:
                with self.assertRaises(ValueError):
                    publisher.publish({"variant": "text", "caption": "story"}, ["facebook", "instagram"], Path(directory) / "receipt.json")
            publisher.request.assert_not_called()

    def test_user_token_resolves_page_and_instagram(self):
        with patch.dict("os.environ", {"META_GRAPH_API_VERSION": "vTEST", "META_ACCESS_TOKEN": "", "META_USER_TOKEN": "user-token", "FACEBOOK_ID": "page123", "FACEBOOK_PAGE_ID": "", "INSTAGRAM_ACCOUNT_ID": ""}):
            publisher = MetaPublisher()
            publisher.request = Mock(return_value={"access_token": "page-token", "instagram_business_account": {"id": "ig123"}})
            publisher.resolve_accounts(["facebook", "instagram"])
            self.assertEqual(publisher.token, "page-token")
            self.assertEqual(publisher.page_id, "page123")
            self.assertEqual(publisher.instagram_id, "ig123")

    def test_facebook_only_requests_no_instagram_fields(self):
        with patch.dict("os.environ", {"META_GRAPH_API_VERSION": "vTEST", "META_ACCESS_TOKEN": "", "META_USER_TOKEN": "user-token", "FACEBOOK_ID": "page123", "FACEBOOK_PAGE_ID": ""}):
            publisher = MetaPublisher()
            publisher.request = Mock(return_value={"access_token": "page-token"})
            publisher.resolve_accounts(["facebook"])
            self.assertEqual(publisher.request.call_args.kwargs["params"]["fields"], "id,access_token")

    def test_receipt_skips_already_published_platform(self):
        with patch.dict("os.environ", {"META_GRAPH_API_VERSION": "vTEST", "META_ACCESS_TOKEN": "test", "FACEBOOK_PAGE_ID": "123"}):
            publisher = MetaPublisher(); publisher.request = Mock(return_value={"id": "post123"})
            with tempfile.TemporaryDirectory() as directory:
                receipt = Path(directory) / "receipt.json"
                post = {"variant": "text", "caption": "story"}
                publisher.publish(post, ["facebook"], receipt)
                publisher.publish(post, ["facebook"], receipt)
                self.assertEqual(publisher.request.call_count, 1)


if __name__ == "__main__": unittest.main()
