import json
import os
import types
import unittest
from unittest.mock import Mock, MagicMock, patch
from scripts.social import MetaPublisher
from scripts.script_gen import ScriptGenerator


class ProviderDiagnosticsTests(unittest.TestCase):
    def test_meta_error_preserves_diagnosis_but_redacts_credentials(self):
        with patch.dict(os.environ, {"META_GRAPH_API_VERSION": "vTEST", "META_ACCESS_TOKEN": "page-secret", "META_USER_TOKEN": "user-secret"}):
            publisher = MetaPublisher()
            response = Mock(ok=False, status_code=400)
            response.json.return_value = {"error": {"code": 100, "error_subcode": 33,
                "message": "Unsupported request page-secret user-secret https://host/image?access_token=other-secret",
                "fbtrace_id": "trace123"}}
            with patch("scripts.social.requests.request", return_value=response):
                with self.assertRaises(RuntimeError) as caught:
                    publisher.request("POST", "account/media")
            message = str(caught.exception)
            self.assertIn("Unsupported request", message)
            self.assertIn("33", message)
            self.assertIn("trace123", message)
            for secret in ("page-secret", "user-secret", "other-secret"):
                self.assertNotIn(secret, message)

    def test_missing_instagram_permission_is_actionable(self):
        with patch.dict(os.environ, {"META_GRAPH_API_VERSION": "vTEST", "META_ACCESS_TOKEN": "", "META_USER_TOKEN": "user-secret"}):
            publisher = MetaPublisher()
            publisher.request = Mock(return_value={"data": [
                {"permission": "instagram_basic", "status": "granted"},
                {"permission": "pages_read_engagement", "status": "granted"},
                {"permission": "instagram_content_publish", "status": "declined"}]})
            with self.assertRaisesRegex(ValueError, "instagram_content_publish"):
                publisher.check_permissions(["instagram"])
            publisher.request.assert_called_once_with("GET", "me/permissions")

    def test_retired_nvidia_model_is_not_retried(self):
        with patch.dict(os.environ, {"NVIDIA_NIM_API_KEY": "test", "NVIDIA_MODEL": "retired-model"}):
            generator = ScriptGenerator()
            with patch("requests.post", return_value=Mock(status_code=410)) as request:
                self.assertIsNone(generator._generate_with_nvidia("prompt"))
                self.assertIsNone(generator._generate_with_nvidia("prompt"))
                self.assertEqual(request.call_count, 1)

    def test_gemini_uses_new_sdk_and_configured_model(self):
        story = {"title": "Door", "parts": [{"beats": [{"text": "The door opened by itself.", "pause_after": 1}]}]}
        client = Mock()
        client.models.generate_content.return_value.text = json.dumps(story)
        context = MagicMock()
        context.__enter__.return_value = client
        sdk = types.ModuleType("google.genai")
        sdk.Client = Mock(return_value=context)
        with patch.dict(os.environ, {"NVIDIA_NIM_API_KEY": "", "GEMINI_API_KEY": "test", "GEMINI_MODEL": "configured-model"}), patch.dict("sys.modules", {"google.genai": sdk}):
            result = ScriptGenerator().generate_horror_script("Door", mode="social")
        self.assertEqual(result["title"], "Door")
        self.assertEqual(client.models.generate_content.call_args.kwargs["model"], "configured-model")
        self.assertEqual(client.models.generate_content.call_args.kwargs["config"]["response_mime_type"], "application/json")


if __name__ == "__main__": unittest.main()
