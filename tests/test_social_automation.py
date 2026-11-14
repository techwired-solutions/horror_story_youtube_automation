import base64
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.social import MetaPublisher
from scripts.social_automation import run
from scripts.social_store import SocialStore, verify_public_image


class MemoryStore:
    def __init__(self): self.files = {}
    def ensure_branch(self): pass
    def read(self, path): return self.files.get(path)
    def write(self, path, content):
        self.files[path] = content
        return "https://raw.githubusercontent.com/owner/repo/commit/" + path
    def save_json(self, path, data): return self.write(path, json.dumps(data).encode())


class AutomationTests(unittest.TestCase):
    def test_first_run_saves_image_and_receipts_then_rerun_skips(self):
        store = MemoryStore()
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            def prepare(folder, day):
                (folder / "post.jpg").write_bytes(b"jpeg")
                (folder / "story.json").write_text('{"title":"Story"}')
                return {"caption": "Story", "variant": "photo", "image": str(folder / "post.jpg")}
            publisher = Mock()
            def publish(post, platforms, path, on_receipt, accounts_resolved):
                self.assertTrue(accounts_resolved)
                on_receipt({"facebook": {"id": "fb"}})
                on_receipt({"facebook": {"id": "fb"}, "instagram": {"id": "ig"}})
            publisher.publish.side_effect = publish
            with patch("scripts.social_automation.prepare_daily", side_effect=prepare) as generate, patch("scripts.social_automation.verify_public_image") as verify, patch("scripts.social_automation.MetaPublisher", return_value=publisher) as factory:
                run(date(2026, 11, 15), store, directory)
                run(date(2026, 11, 15), store, directory)
                self.assertEqual(generate.call_count, 1)
                self.assertEqual(factory.call_count, 1)
                self.assertEqual(publisher.publish.call_count, 1)
                self.assertEqual(verify.call_count, 1)
        self.assertIn("social/2026-11-15/post.jpg", store.files)
        self.assertIn("instagram", json.loads(store.files["social/2026-11-15/publication.json"]))

    def test_partial_publication_reuses_exact_saved_image(self):
        store = MemoryStore()
        prefix = "social/2026-11-15/"
        post = {"caption": "Original caption", "variant": "text", "image_url": "https://example.org/exact.jpg"}
        store.save_json(prefix + "post.json", post)
        store.write(prefix + "post.jpg", b"original-image")
        store.save_json(prefix + "publication.json", {"facebook": {"id": "already-published"}})
        with tempfile.TemporaryDirectory() as temp, patch("scripts.social_automation.prepare_daily") as generate, patch("scripts.social_automation.verify_public_image") as verify, patch("scripts.social_automation.MetaPublisher") as factory:
            run(date(2026, 11, 15), store, Path(temp))
            generate.assert_not_called()
            verify.assert_called_once_with(post["image_url"], b"original-image")
            args = factory.return_value.publish.call_args.args
            self.assertIn("facebook", json.loads(Path(args[2]).read_text()))
            self.assertEqual(args[0]["caption"], "Original caption")

    def test_completed_receipt_needs_no_meta_credentials(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict("os.environ", {"META_GRAPH_API_VERSION": "vTEST", "META_ACCESS_TOKEN": "test"}):
            publisher = MetaPublisher()
            publisher.resolve_accounts = Mock()
            path = Path(temp) / "receipt.json"
            path.write_text('{"facebook":{"id":"fb"},"instagram":{"id":"ig"}}')
            publisher.publish({}, ["facebook", "instagram"], path)
            publisher.resolve_accounts.assert_not_called()

    def test_instagram_uses_generated_url_and_persists_container_and_post(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict("os.environ", {"META_GRAPH_API_VERSION": "vTEST", "META_ACCESS_TOKEN": "test"}):
            publisher = MetaPublisher(); publisher.instagram_id = "ig-account"
            publisher.request = Mock(side_effect=[{"id": "container"}, {"status_code": "FINISHED"}, {"id": "post"}])
            saved = []
            publisher.publish({"image_url": "https://example.org/generated.jpg", "caption": "caption"}, ["instagram"], Path(temp) / "receipt.json",
                              on_receipt=lambda value: saved.append(json.loads(json.dumps(value))), accounts_resolved=True)
            self.assertEqual(publisher.request.call_args_list[0].kwargs["data"]["image_url"], "https://example.org/generated.jpg")
            self.assertEqual(saved[0], {"instagram_container": "container"})
            self.assertEqual(saved[1]["instagram"], {"id": "post"})

    def test_image_verification_requires_exact_bytes_without_auth(self):
        response = Mock(ok=True, content=b"jpeg")
        with patch("scripts.social_store.requests.get", return_value=response) as get:
            verify_public_image("https://example.org/image.jpg", b"jpeg")
            get.assert_called_once_with("https://example.org/image.jpg", timeout=20)

    def test_store_write_uses_separate_branch_and_immutable_url(self):
        store = SocialStore("owner/repo", "test-token")
        store.request = Mock(side_effect=[None, {"commit": {"sha": "commit123"}}])
        url = store.write("social/day/post.jpg", b"jpeg")
        payload = store.request.call_args.kwargs["json"]
        self.assertEqual(payload["branch"], "automation/social-media")
        self.assertEqual(base64.b64decode(payload["content"]), b"jpeg")
        self.assertEqual(url, "https://raw.githubusercontent.com/owner/repo/commit123/social/day/post.jpg")
        self.assertNotIn("test-token", json.dumps(payload))

    def test_private_repository_rejected_before_writes(self):
        store = SocialStore("owner/repo", "test-token")
        store.request = Mock(return_value={"private": True})
        with self.assertRaises(ValueError): store.ensure_branch()
        self.assertEqual(store.request.call_count, 1)


if __name__ == "__main__": unittest.main()
