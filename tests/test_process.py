"""Safety and end-to-end tests with generated, disposable audio."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import process_podcast_audio as tool


class SafetyTests(unittest.TestCase):
    def test_names(self):
        self.assertEqual(tool.slug("PT_creators Dilemma_v1"), "pt-creators-dilemma-v1")

    def test_end_to_end_and_refusals(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tone = root / "Test Tone.wav"
            silence = root / "silence.wav"
            for path, signal in [(tone, "sine=frequency=440:duration=4"),
                                 (silence, "anullsrc=r=44100:cl=stereo")]:
                subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", signal,
                                "-t", "4", "-metadata", "comment=private-edit-history",
                                str(path)], check=True)
            original_hash = tool.digest(tone)
            out = root / "export"
            out.mkdir()
            result = tool.process(tone, out / "tone.mp3")
            self.assertEqual(result["status"], "passed")
            self.assertNotIn("private-edit-history", str(tool.probe(out / "tone.mp3")))
            self.assertEqual(tool.digest(tone), original_hash)
            with self.assertRaises(FileExistsError):
                tool.process(tone, out / "tone.mp3")
            with self.assertRaises(ValueError):
                tool.process(silence, out / "silence.mp3")
            self.assertFalse((out / "silence.mp3").exists())
            bad = root / "bad.wav"
            bad.write_bytes(b"not audio")
            with self.assertRaises(ValueError):
                tool.process(bad, out / "bad.mp3")
            command = [sys.executable, str(Path(tool.__file__)), str(root),
                       "--output", str(root / "nested")]
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            same_name = root / "test-tone.wav"
            same_name.write_bytes(tone.read_bytes())
            command = [sys.executable, str(Path(tool.__file__)), str(tone), str(same_name),
                       "--output", str(root / "collision")]
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertFalse((root / "collision").exists())
            command = [sys.executable, str(Path(tool.__file__)), str(tone),
                       "--output", str(root / "no-report"), "--no-report"]
            subprocess.run(command, capture_output=True, check=True)
            self.assertEqual([p.name for p in (root / "no-report").iterdir()], ["test-tone.mp3"])


if __name__ == "__main__":
    unittest.main()
