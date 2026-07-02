from __future__ import annotations

import io
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from prompt_preflight.kiro_hook import main as kiro_hook_main, process_payload
from prompt_preflight.hook import EXAMPLES_URL


class KiroHookTests(unittest.TestCase):
    def test_kiro_hook_blocks_vague_prompt_with_exit_two(self) -> None:
        code, stdout, stderr = process_payload({"prompt": "Create a car image"})
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("Your prompt:", stderr)
        self.assertIn('"Create a car image"', stderr)
        self.assertIn("aspect ratio", stderr)
        self.assertIn(EXAMPLES_URL, stderr)

    def test_kiro_hook_allows_clear_prompt(self) -> None:
        code, stdout, stderr = process_payload(
            {
                "prompt": (
                    "Create a photorealistic image of a red 1967 Ford Mustang on a wet "
                    "Tokyo street at night, low camera angle, cinematic lighting, 16:9."
                )
            }
        )
        self.assertEqual((code, stdout, stderr), (0, "", ""))

    def test_kiro_hook_with_attachment_metadata_bypasses_missing_file(self) -> None:
        code, stdout, stderr = process_payload(
            {
                "prompt": "Summarize the attached report.pdf",
                "attachments": [{"name": "report.pdf"}]
            }
        )
        self.assertEqual((code, stdout, stderr), (0, "", ""))

    def test_kiro_hook_nudge_mode_writes_context_to_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, ".prompt-preflight.json").write_text(
                json.dumps({"mode": "nudge"}), encoding="utf-8"
            )
            code, stdout, stderr = process_payload({"prompt": "Fix it", "cwd": directory})
        self.assertEqual(code, 0)
        self.assertIn("Prompt Preflight detected consequential ambiguity", stdout)
        self.assertIn("Then ask these clarification questions:", stdout)
        self.assertEqual(stderr, "")

    def test_kiro_hook_main_writes_stderr_and_returns_two(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        code = kiro_hook_main(
            io.StringIO('{"hook_event_name":"userPromptSubmit","prompt":"Make the dashboard better"}'),
            stdout,
            stderr,
        )
        self.assertEqual(code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("Prompt Preflight paused this request", stderr.getvalue())

    def test_kiro_hook_fails_open_on_bad_json(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        code = kiro_hook_main(io.StringIO("not json"), stdout, stderr)
        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
