from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from prompt_preflight.analyzer import analyze_prompt
from prompt_preflight.config import load_config
from prompt_preflight.telemetry import (
    read_events,
    record_analysis,
    render_report,
    summarize_events,
    telemetry_event,
)


class TelemetryTests(unittest.TestCase):
    def test_telemetry_event_does_not_store_prompt_text(self) -> None:
        analysis = analyze_prompt("Create a car image")
        event = telemetry_event(analysis, host="test", decision="blocked")
        encoded = json.dumps(event)

        self.assertNotIn("Create a car image", encoded)
        self.assertNotIn("photorealistic", encoded)
        self.assertNotIn("What should the car look like", encoded)
        self.assertEqual(event["decision"], "blocked")
        self.assertEqual(event["intent"], "image_generation")
        self.assertEqual(event["question_count"], 3)

    def test_record_and_summarize_counts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "telemetry.jsonl"
            record_analysis(
                analyze_prompt("Create a car image"),
                host="codex",
                mode="block",
                telemetry_path=path,
                enabled=True,
            )
            record_analysis(
                analyze_prompt("Create a car image [preflight:skip]"),
                host="codex",
                mode="block",
                telemetry_path=path,
                enabled=True,
            )
            record_analysis(
                analyze_prompt("go ahead"),
                host="codex",
                mode="block",
                telemetry_path=path,
                enabled=True,
            )

            events = read_events(path)
            summary = summarize_events(events)

        self.assertEqual(len(events), 3)
        self.assertEqual(summary["prompts_checked"], 3)
        self.assertEqual(summary["prompts_blocked"], 1)
        self.assertEqual(summary["prompts_bypassed"], 1)
        self.assertEqual(summary["followup_accepted"], 1)
        self.assertEqual(summary["estimated_avoided_retry_turns"], 1)

    def test_render_report_explains_privacy(self) -> None:
        summary = summarize_events(
            [
                {
                    "decision": "blocked",
                    "host": "codex",
                    "intent": "software_build",
                    "score": 60,
                }
            ]
        )
        report = render_report(summary, path=Path("telemetry.jsonl"))
        self.assertIn("Prompts checked: 1", report)
        self.assertIn("Estimated avoided retry turns: 1", report)
        self.assertIn("does not store prompt text", report)

    def test_config_telemetry_is_disabled_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = load_config(directory)
        self.assertFalse(config.telemetry_enabled)
        self.assertIsNone(config.telemetry_path)

    def test_config_telemetry_path_is_relative_to_config_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Path(root, ".prompt-preflight.json").write_text(
                json.dumps({"telemetry": {"enabled": True, "path": "local-telemetry.jsonl"}}),
                encoding="utf-8",
            )
            config = load_config(root)
        self.assertTrue(config.telemetry_enabled)
        self.assertEqual(config.telemetry_path, root.resolve() / "local-telemetry.jsonl")


if __name__ == "__main__":
    unittest.main()
