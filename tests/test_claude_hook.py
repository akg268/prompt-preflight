from __future__ import annotations

import io
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from prompt_preflight.claude_hook import main as claude_hook_main, process_payload
from prompt_preflight.hook import EXAMPLES_URL


class ClaudeHookTests(unittest.TestCase):
    def test_claude_hook_blocks_vague_prompt(self) -> None:
        result = process_payload({"prompt": "Create a car image"})
        self.assertEqual(result["decision"], "block")
        self.assertTrue(result["suppressOriginalPrompt"])
        self.assertIn("Your prompt:", result["reason"])
        self.assertIn('"Create a car image"', result["reason"])
        self.assertIn("aspect ratio", result["reason"])
        self.assertIn(EXAMPLES_URL, result["reason"])

    def test_claude_hook_allows_clear_prompt_without_output(self) -> None:
        result = process_payload(
            {
                "prompt": (
                    "Create a photorealistic image of a red 1967 Ford Mustang on a wet "
                    "Tokyo street at night, low camera angle, cinematic lighting, 16:9."
                )
            }
        )
        self.assertIsNone(result)

    def test_claude_hook_with_attachment_metadata_bypasses_missing_file(self) -> None:
        result = process_payload(
            {
                "prompt": "Summarize the attached report.pdf",
                "attachments": [{"name": "report.pdf"}]
            }
        )
        self.assertIsNone(result)

    def test_claude_hook_nudge_mode_adds_context(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, ".prompt-preflight.json").write_text(
                json.dumps({"mode": "nudge"}), encoding="utf-8"
            )
            result = process_payload({"prompt": "Fix it", "cwd": directory})
        self.assertIn("hookSpecificOutput", result)
        self.assertNotIn("decision", result)
        self.assertEqual(
            result["hookSpecificOutput"]["hookEventName"],
            "UserPromptSubmit",
        )
        self.assertIn(
            "Prompt Preflight detected consequential ambiguity",
            result["hookSpecificOutput"]["additionalContext"],
        )

    def test_claude_hook_main_emits_valid_json(self) -> None:
        stdout = io.StringIO()
        code = claude_hook_main(io.StringIO('{"prompt":"Make the dashboard better"}'), stdout)
        self.assertEqual(code, 0)
        result = json.loads(stdout.getvalue())
        self.assertEqual(result["decision"], "block")

    def test_claude_hook_fails_open_on_bad_json(self) -> None:
        stdout = io.StringIO()
        code = claude_hook_main(io.StringIO("not json"), stdout)
        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
