import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from scripts.audio_gen import AudioGenerator


class AudioFallbackTests(unittest.TestCase):
    def test_missing_hume_sdk_does_not_abort(self):
        with patch.dict("sys.modules", {"hume": None}):
            self.assertIsNone(AudioGenerator()._generate_with_hume([{"text": "The door opened."}], "unused.mp3"))

    def test_unavailable_hume_uses_kokoro_and_preserves_duration(self):
        generator = AudioGenerator()
        generator._generate_with_hume = Mock(return_value=None)
        generator._generate_with_kokoro = Mock(return_value={"words": [{"text": "Door", "start": 0, "end": 1}], "duration": 1})
        generator._generate_with_edge_tts = Mock()
        generator._master_audio = Mock()
        with tempfile.TemporaryDirectory() as directory, patch("scripts.audio_gen.AudioSegment.from_file") as load:
            load.return_value.__len__.return_value = 2500
            result = generator.generate_speech([{"text": "Door", "voice": "female"}], str(Path(directory) / "speech.mp3"))
        generator._generate_with_kokoro.assert_called_once()
        generator._generate_with_edge_tts.assert_not_called()
        self.assertEqual(result["duration"], 2.5)
        self.assertEqual(generator._generate_with_kokoro.call_args.args[0][0]["voice"], "male")


if __name__ == "__main__": unittest.main()
