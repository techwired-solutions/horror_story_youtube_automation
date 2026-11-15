import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from scripts.video_publishing import publish_videos, upload_facebook_video, instagram_segments
from scripts.social import MetaPublisher


class VideoPublishingTests(unittest.TestCase):
    def prepared(self, directory):
        video = Path(directory) / "part-1.mp4"; video.write_bytes(b"video-bytes")
        return [("Story", {"duration_in_frames": 3000, "fps": 30, "credits": []}, video, Path(directory) / "props.json")]

    def test_youtube_failure_does_not_block_facebook(self):
        youtube = Mock(); youtube.upload_video.side_effect = RuntimeError("Expired OAuth")
        facebook = Mock(page_id="page"); facebook.request.return_value = {"id": "fb-video"}
        instagram = Mock(); instagram.instagram_available.return_value = False
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "youtube: Expired OAuth"):
                publish_videos(self.prepared(directory), {"disclosure": "Fiction"}, directory,
                               youtube_factory=lambda: youtube, meta_factory=Mock(side_effect=[facebook, instagram]))
            receipt = json.loads((Path(directory) / "publication.json").read_text())
            self.assertEqual(receipt["1"]["facebook"]["id"], "fb-video")
            self.assertNotIn("instagram", receipt["1"])
            facebook.request.assert_called_once()

    def test_old_youtube_receipt_is_preserved_and_not_reuploaded(self):
        youtube_factory = Mock()
        facebook = Mock(page_id="page"); facebook.request.return_value = {"id": "fb-video"}
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "publication.json").write_text('{"1":"yt-existing"}')
            result = publish_videos(self.prepared(directory), {"disclosure": "Fiction"}, directory,
                                    platforms=["youtube", "facebook"], youtube_factory=youtube_factory, meta_factory=lambda: facebook)
            self.assertEqual(result["1"]["youtube"], "yt-existing")
            youtube_factory.assert_not_called()

    def test_instagram_starts_after_connection_without_reuploading_other_platforms(self):
        instagram = Mock(page_id="page", instagram_id="ig-account")
        instagram.instagram_available.return_value = True
        instagram.request.side_effect = [{"source": "https://cdn.example/video.mp4"}, {"id": "container"},
                                         {"status_code": "FINISHED"}, {"id": "ig-post"}]
        youtube_factory = Mock()
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "publication.json").write_text('{"1":{"youtube":"yt-existing","facebook":{"id":"fb-existing"}}}')
            result = publish_videos(self.prepared(directory), {"disclosure": "Fiction"}, directory,
                                    youtube_factory=youtube_factory, meta_factory=lambda: instagram)
            youtube_factory.assert_not_called()
            self.assertTrue(result["1"]["instagram"]["1"]["published"])
            self.assertEqual(result["1"]["instagram"]["1"]["facebook_source_id"], "fb-existing")
            self.assertEqual(instagram.request.call_args_list[1].kwargs["data"]["video_url"], "https://cdn.example/video.mp4")

    def test_facebook_upload_attaches_actual_file(self):
        publisher = Mock(page_id="page")
        def request(method, path, **kwargs):
            self.assertEqual(path, "page/videos")
            self.assertEqual(kwargs["files"]["source"].read(), b"video-bytes")
            self.assertEqual(kwargs["data"]["published"], "false")
            return {"id": "staging-video"}
        publisher.request.side_effect = request
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "part.mp4"; video.write_bytes(b"video-bytes")
            self.assertEqual(upload_facebook_video(publisher, video, "Title", "Caption", published=False)["id"], "staging-video")

    def test_twenty_minute_video_splits_at_caption_boundary_for_instagram(self):
        with tempfile.TemporaryDirectory() as directory, patch("scripts.video_publishing.subprocess.run") as run:
            parts = instagram_segments(Path(directory) / "long.mp4", {"duration_in_frames": 36000, "fps": 30,
                                       "subtitles": [{"text": "reveal.", "end": 830}, {"text": "ending.", "end": 1198}]})
            self.assertEqual(len(parts), 2)
            durations = [float(call.args[0][call.args[0].index("-t") + 1]) for call in run.call_args_list]
            self.assertEqual(durations, [830, 370])

    def test_missing_link_is_not_enabled_by_stale_instagram_id(self):
        with patch.dict("os.environ", {"META_GRAPH_API_VERSION": "vTEST", "META_ACCESS_TOKEN": "page-token", "FACEBOOK_ID": "page", "INSTAGRAM_ACCOUNT_ID": "stale"}):
            publisher = MetaPublisher()
            publisher.request = Mock(return_value={})
            publisher.validate_instagram_account = Mock()
            self.assertFalse(publisher.instagram_available())
            publisher.validate_instagram_account.assert_not_called()

    def test_ready_link_enables_instagram_automatically(self):
        with patch.dict("os.environ", {"META_GRAPH_API_VERSION": "vTEST", "META_ACCESS_TOKEN": "page-token", "FACEBOOK_ID": "page"}):
            publisher = MetaPublisher()
            publisher.request = Mock(side_effect=[{"instagram_business_account": {"id": "linked"}}, {"id": "linked", "username": "horror"}])
            self.assertTrue(publisher.instagram_available())
            self.assertEqual(publisher.instagram_id, "linked")


if __name__ == "__main__": unittest.main()
