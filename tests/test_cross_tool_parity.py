from __future__ import annotations

import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from prompt_preflight.claude_hook import process_payload as claude_process_payload
from prompt_preflight.cli import main as cli_main
from prompt_preflight.hook import process_payload as codex_process_payload
from prompt_preflight.kiro_hook import process_payload as kiro_process_payload


class CrossToolParityTests(unittest.TestCase):
    def test_codex_claude_kiro_and_cli_block_same_vague_prompt(self) -> None:
        prompt = "Create a car image"

        codex = codex_process_payload({"prompt": prompt})
        claude = claude_process_payload({"prompt": prompt})
        kiro_code, _, kiro_stderr = kiro_process_payload({"prompt": prompt})
        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            cli_code = cli_main(["--json", prompt])
        cli_payload = json.loads(stdout.getvalue())

        self.assertEqual(codex["decision"], "block")
        self.assertEqual(claude["decision"], "block")
        self.assertEqual(kiro_code, 2)
        self.assertEqual(cli_code, 2)
        self.assertIn("aspect ratio", codex["reason"])
        self.assertIn("aspect ratio", claude["reason"])
        self.assertIn("aspect ratio", kiro_stderr)
        self.assertEqual(cli_payload["intent"], "image_generation")

    def test_codex_claude_kiro_and_cli_allow_same_clear_prompt(self) -> None:
        prompt = (
            "Create a photorealistic image of a red 1967 Ford Mustang on a wet "
            "Tokyo street at night, low camera angle, cinematic lighting, 16:9."
        )

        self.assertIsNone(codex_process_payload({"prompt": prompt}))
        self.assertIsNone(claude_process_payload({"prompt": prompt}))
        self.assertEqual(kiro_process_payload({"prompt": prompt}), (0, "", ""))
        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            cli_code = cli_main(["--json", prompt])

        self.assertEqual(cli_code, 0)
        self.assertFalse(json.loads(stdout.getvalue())["should_clarify"])

    def test_policy_profile_mapping_reaches_hooks_and_cli(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prompt_path = root / "docs" / "prompts" / "research" / "vendors.md"
            prompt_path.parent.mkdir(parents=True)
            prompt_path.write_text(
                "# Task\nResearch vendors\n# Output Format\nTable\n",
                encoding="utf-8",
            )
            (root / ".prompt-preflight.json").write_text(
                json.dumps({"profiles": {"docs/prompts/research/**": "research"}}),
                encoding="utf-8",
            )
            payload = {
                "prompt": prompt_path.read_text(encoding="utf-8"),
                "cwd": str(root),
                "prompt_path": str(prompt_path),
            }

            codex = codex_process_payload(payload)
            claude = claude_process_payload(payload)
            kiro_code, _, _ = kiro_process_payload(payload)
            stdout = io.StringIO()
            with patch("sys.stdout", stdout):
                cli_code = cli_main([
                    "--cwd",
                    str(root),
                    "--prompt-file",
                    str(prompt_path),
                    "--json",
                ])
            cli_payload = json.loads(stdout.getvalue())

        self.assertEqual(codex["decision"], "block")
        self.assertEqual(claude["decision"], "block")
        self.assertEqual(kiro_code, 2)
        self.assertEqual(cli_code, 2)
        self.assertEqual(cli_payload["intent"], "research")
        self.assertIn("template_contract", cli_payload["checks"])


if __name__ == "__main__":
    unittest.main()
