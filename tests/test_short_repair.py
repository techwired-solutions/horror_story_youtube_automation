import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from scripts.story_policy import validate_story, ShortDurationError, NarrationDurationError
from scripts.script_gen import ScriptGenerator
from scripts.video_preparation import prepare_video_parts

FIXTURE = Path(__file__).parent / "fixtures" / "van_meter_overlong.json"


def failed_story(): return json.loads(FIXTURE.read_text(encoding="utf-8"))

def short_story():
    return {"title": "Door", "parts": [{"part_number": 1, "beats": [
        {"text": "The door opened by itself. I had buried its key yesterday.", "pause_after": 1}]}]}


class ShortRepairTests(unittest.TestCase):
    def test_original_failure_reports_real_word_count_and_duration(self):
        with self.assertRaisesRegex(ShortDurationError, "325 words, 183.9s"):
            validate_story(failed_story(), "short")

    def test_original_failure_splits_without_losing_or_reordering_story(self):
        original = failed_story()
        expected = [beat["text"] for part in original["parts"] for beat in part["beats"]]
        result = validate_story(original, "short", allow_short_split=True)
        self.assertEqual(len(result["parts"]), 2)
        actual = [beat["text"] for part in result["parts"] for beat in part["beats"]]
        self.assertEqual(actual, expected)
        for part in result["parts"]:
            self.assertLessEqual(sum(beat["duration_estimate"] for beat in part["beats"]), 175)

    def test_short_complete_story_stays_one_part(self):
        self.assertEqual(len(validate_story(short_story(), "short", allow_short_split=True)["parts"]), 1)

    def test_cannot_split_a_single_huge_beat(self):
        data = short_story()
        data["parts"][0]["beats"][0]["text"] = "word " * 800
        with self.assertRaises(ShortDurationError): validate_story(data, "short", allow_short_split=True)

    def test_generator_rewrites_using_timing_feedback(self):
        generator = ScriptGenerator()
        generator._generate_with_nvidia = Mock(return_value=None)
        generator._generate_with_gemini = Mock(side_effect=[json.dumps(failed_story()), json.dumps(short_story())])
        result = generator.generate_horror_script("Van Meter", mode="short")
        self.assertEqual(len(result["parts"]), 1)
        self.assertEqual(generator._generate_with_gemini.call_count, 2)
        feedback = generator._generate_with_gemini.call_args.args[0]
        self.assertIn("325 words", feedback)
        self.assertIn("183.9s", feedback)
        self.assertIn("Preserve the protagonist", feedback)

    def test_third_attempt_splits_if_rewrites_remain_long(self):
        generator = ScriptGenerator()
        generator._generate_with_nvidia = Mock(return_value=None)
        generator._generate_with_gemini = Mock(return_value=json.dumps(failed_story()))
        result = generator.generate_horror_script("Van Meter", mode="short")
        self.assertEqual(generator._generate_with_gemini.call_count, 3)
        self.assertEqual(len(result["parts"]), 2)

    def test_unrepairable_draft_stops_after_three_attempts(self):
        generator = ScriptGenerator()
        generator._generate_with_nvidia = Mock(return_value=None)
        generator._generate_with_gemini = Mock(return_value="not JSON")
        self.assertIsNone(generator.generate_horror_script("Door"))
        self.assertEqual(generator._generate_with_gemini.call_count, 3)
        self.assertIsNotNone(generator.last_error)

    def test_measured_audio_overrun_rewrites_before_render(self):
        builder = Mock()
        builder.build_props.side_effect = [NarrationDurationError("Measured narration is 190s"), {"duration_in_frames": 3000}]
        rewrite = Mock(return_value=short_story())
        original = short_story(); original["disclosure"] = "Fiction"
        with tempfile.TemporaryDirectory() as directory:
            revised, prepared = prepare_video_parts(original, builder, directory, "short", 10, rewrite)
            self.assertEqual(len(prepared), 1)
            self.assertEqual(revised["disclosure"], "Fiction")
            self.assertEqual(json.loads((Path(directory) / "story.json").read_text())["disclosure"], "Fiction")
        self.assertIn("190s", rewrite.call_args.args[1])
        self.assertEqual(builder.build_props.call_count, 2)

    def test_manual_story_does_not_silently_rewrite(self):
        builder = Mock(); builder.build_props.side_effect = NarrationDurationError("190s")
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(NarrationDurationError):
                prepare_video_parts(short_story(), builder, directory, "short", 10)
        self.assertEqual(builder.build_props.call_count, 1)

    def test_live_catalog_can_skip_retired_nvidia_candidate(self):
        with patch.dict("os.environ", {"NVIDIA_NIM_API_KEY": "test", "NVIDIA_MODEL": ""}):
            generator = ScriptGenerator()
            catalog = Mock(); catalog.json.return_value = {"data": [
                {"id": "qwen/qwen3-next-80b-a3b-instruct"}, {"id": "meta/llama-3.3-70b-instruct"}]}
            success = Mock(status_code=200)
            success.json.return_value = {"choices": [{"message": {"content": "story"}}]}
            with patch("requests.get", return_value=catalog), patch("requests.post", side_effect=[Mock(status_code=410), success]) as post:
                self.assertEqual(generator._generate_with_nvidia("prompt"), "story")
                self.assertEqual(post.call_count, 2)
                self.assertEqual(post.call_args.kwargs["json"]["model"], "meta/llama-3.3-70b-instruct")


if __name__ == "__main__": unittest.main()
