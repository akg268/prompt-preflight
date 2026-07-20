from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from io import StringIO
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from prompt_preflight.cli import main as preflight_main
from prompt_preflight.config import load_config
from prompt_preflight.prompt_lint import lint_prompt_library, render_lint_report


class PromptLibraryLintTests(unittest.TestCase):
    def test_config_profiles_match_workspace_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".prompt-preflight.json").write_text(
                json.dumps(
                    {
                        "profiles": {
                            "docs/prompts/research/**": "research",
                            "docs/prompts/specs/**": "feature_spec",
                        }
                    }
                ),
                encoding="utf-8",
            )
            config = load_config(root)

            self.assertEqual(
                config.profile_for_path(root / "docs/prompts/research/vendors.md", root),
                "research",
            )
            self.assertEqual(
                config.profile_for_path("docs/prompts/specs/new-widget.md", root),
                "feature_spec",
            )
            self.assertIsNone(config.profile_for_path("README.md", root))

    def test_lint_prompt_library_uses_marker_and_profile(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prompt_dir = root / "docs" / "prompts" / "research"
            prompt_dir.mkdir(parents=True)
            (root / ".prompt-preflight.json").write_text(
                json.dumps({"profiles": {"docs/prompts/research/**": "research"}}),
                encoding="utf-8",
            )
            (prompt_dir / "vendors.md").write_text(
                "<!-- prompt-preflight: check -->\n# Task\nResearch vendors\n# Output Format\nTable\n",
                encoding="utf-8",
            )
            (root / "README.md").write_text("Unmarked project docs should be skipped.\n", encoding="utf-8")

            summary = lint_prompt_library(root)
            report = render_lint_report(summary)

            self.assertEqual(summary.checked, 1)
            self.assertEqual(summary.skipped, 0)
            self.assertEqual(summary.failed, 1)
            self.assertEqual(summary.results[0].profile, "research")
            self.assertIn("profile=research", report)
            self.assertNotIn("Research vendors", report)

    def test_cli_prompt_file_applies_profile_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prompt_dir = root / "docs" / "prompts" / "research"
            prompt_dir.mkdir(parents=True)
            prompt_path = prompt_dir / "vendors.md"
            prompt_path.write_text(
                "# Task\nResearch vendors\n# Output Format\nTable\n",
                encoding="utf-8",
            )
            (root / ".prompt-preflight.json").write_text(
                json.dumps({"profiles": {"docs/prompts/research/**": "research"}}),
                encoding="utf-8",
            )

            stdout = StringIO()
            with patch("sys.stdout", stdout):
                code = preflight_main([
                    "--cwd",
                    str(root),
                    "--prompt-file",
                    str(prompt_path),
                    "--json",
                ])
            payload = json.loads(stdout.getvalue())

            self.assertEqual(code, 2)
            self.assertEqual(payload["intent"], "research")
            self.assertIn("template_contract", payload["checks"])


if __name__ == "__main__":
    unittest.main()
