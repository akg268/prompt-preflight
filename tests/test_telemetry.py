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

from prompt_preflight.analyzer import analyze_prompt
from prompt_preflight.cli import main
from prompt_preflight.config import load_config, resolve_telemetry_report_path
from prompt_preflight.telemetry import (
    postflight_telemetry_event,
    read_events,
    record_analysis,
    record_postflight,
    render_report,
    summarize_events,
    telemetry_event,
)
from prompt_preflight.postflight import analyze_postflight


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
        self.assertIn("token_observability", event)
        self.assertNotIn("car", json.dumps(event["token_observability"]).lower())

    def test_telemetry_event_can_disable_token_observability(self) -> None:
        analysis = analyze_prompt("Create a car image")
        event = telemetry_event(
            analysis,
            host="test",
            decision="blocked",
            token_observability_enabled=False,
        )

        self.assertNotIn("token_observability", event)

    def test_telemetry_event_timestamp_modes(self) -> None:
        analysis = analyze_prompt("Create a car image")

        event_exact = telemetry_event(analysis, host="test", decision="blocked", timestamp_mode="exact")
        self.assertIn("T", event_exact["timestamp"])

        event_date = telemetry_event(analysis, host="test", decision="blocked", timestamp_mode="date")
        self.assertNotIn("T", event_date["timestamp"])
        self.assertEqual(len(event_date["timestamp"]), 10)

        event_none = telemetry_event(analysis, host="test", decision="blocked", timestamp_mode="none")
        self.assertNotIn("timestamp", event_none)

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
            [telemetry_event(analyze_prompt("Create a car image"), host="codex", decision="blocked")]
        )
        report = render_report(summary, path=Path("telemetry.jsonl"))
        self.assertIn("Prompts checked: 1", report)
        self.assertIn("Estimated avoided retry turns: 1", report)
        self.assertIn("does not store prompt text", report)
        self.assertIn("Token observability", report)

    def test_postflight_event_and_report_are_prompt_free(self) -> None:
        result = analyze_postflight("Return JSON", "the answer is 42")
        event = postflight_telemetry_event(result, host="claude-code-postflight")
        encoded = json.dumps(event)

        self.assertEqual(event["phase"], "postflight")
        self.assertEqual(event["decision"], "postflight_blocked")
        self.assertIn("token_observability", event)
        self.assertNotIn("Return JSON", encoded)
        self.assertNotIn("answer is 42", encoded)

        summary = summarize_events([event])
        report = render_report(summary, path=Path("telemetry.jsonl"))
        self.assertIn("Postflight", report)
        self.assertIn("Responses checked: 1", report)
        self.assertIn("Estimated response tokens observed", report)

    def test_record_postflight_writes_prompt_free_event(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "telemetry.jsonl"
            result = analyze_postflight("Return JSON", "the answer is 42")
            record_postflight(
                result,
                host="cli-postflight",
                telemetry_path=path,
                enabled=True,
            )
            raw = path.read_text(encoding="utf-8")
            events = read_events(path)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["phase"], "postflight")
        self.assertNotIn("Return JSON", raw)
        self.assertNotIn("answer is 42", raw)

    def test_record_and_render_structured_prompt_block(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "telemetry.jsonl"
            prompt = """# Task
Create a car image

# Visual Details
A red vintage Mustang on a rainy neon street

# Output Format
16:9 PNG
"""
            analysis = analyze_prompt(prompt)
            record_analysis(
                analysis,
                host="codex",
                mode="block",
                telemetry_path=path,
                enabled=True,
            )

            events = read_events(path)
            summary = summarize_events(events)
            report = render_report(summary, path=path)

        self.assertEqual(len(events), 1)
        self.assertIn("template_contract", events[0]["checks"])
        self.assertEqual(summary["prompts_blocked"], 1)
        self.assertEqual(summary["blocked_by_check"]["template_contract"], 1)
        self.assertIn("Blocked before model work: 1", report)
        self.assertIn("  - template_contract: 1", report)

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
        self.assertEqual(config.telemetry_timestamp_mode, "exact")

    def test_config_invalid_timestamp_mode_falls_back_to_exact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Path(root, ".prompt-preflight.json").write_text(
                json.dumps({"telemetry": {"enabled": True, "timestamp_mode": "invalid"}}),
                encoding="utf-8",
            )
            config = load_config(root)
        self.assertTrue(config.telemetry_enabled)
        self.assertEqual(config.telemetry_timestamp_mode, "exact")

    def test_config_valid_timestamp_modes(self) -> None:
        for mode in ("exact", "date", "none"):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                Path(root, ".prompt-preflight.json").write_text(
                    json.dumps({"telemetry": {"enabled": True, "timestamp_mode": mode}}),
                    encoding="utf-8",
                )
                config = load_config(root)
            self.assertEqual(config.telemetry_timestamp_mode, mode)

    def test_config_token_observability_settings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Path(root, ".prompt-preflight.json").write_text(
                json.dumps(
                    {
                        "token_observability": {
                            "enabled": False,
                            "default_max_output_tokens": 123,
                            "estimated_retry_output_tokens": 456,
                        }
                    }
                ),
                encoding="utf-8",
            )
            config = load_config(root)
        self.assertFalse(config.token_observability_enabled)
        self.assertEqual(config.token_default_max_output_tokens, 123)
        self.assertEqual(config.token_estimated_retry_output_tokens, 456)

    def test_resolve_telemetry_report_path_uses_configured_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Path(root, ".prompt-preflight.json").write_text(
                json.dumps({"telemetry": {"enabled": True, "path": "local-telemetry.jsonl"}}),
                encoding="utf-8",
            )
            self.assertEqual(
                resolve_telemetry_report_path(root),
                root.resolve() / "local-telemetry.jsonl",
            )

    def test_resolve_telemetry_report_path_when_telemetry_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Path(root, ".prompt-preflight.json").write_text(
                json.dumps(
                    {
                        "telemetry": {
                            "enabled": False,
                            "path": "archived-telemetry.jsonl",
                        }
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(
                resolve_telemetry_report_path(root),
                root.resolve() / "archived-telemetry.jsonl",
            )

    def test_resolve_telemetry_report_path_falls_back_to_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(
                resolve_telemetry_report_path(root),
                root.resolve() / ".prompt-preflight-telemetry.jsonl",
            )


class TelemetryReportCliTests(unittest.TestCase):
    def _write_event(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "decision": "blocked",
                    "host": "codex",
                    "intent": "software_build",
                    "score": 60,
                }
            )
            + "\n",
            encoding="utf-8",
        )

    def test_telemetry_report_default_path_without_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            telemetry_path = root / ".prompt-preflight-telemetry.jsonl"
            self._write_event(telemetry_path)
            stdout = StringIO()
            with patch("sys.stdout", stdout):
                code = main(["--cwd", str(root), "--telemetry-report"])
            self.assertEqual(code, 0)
            self.assertIn("Prompts checked: 1", stdout.getvalue())
            self.assertIn(str(telemetry_path.resolve()), stdout.getvalue())

    def test_telemetry_report_discovers_path_from_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            telemetry_path = root / "project-telemetry.jsonl"
            Path(root, ".prompt-preflight.json").write_text(
                json.dumps({"telemetry": {"enabled": True, "path": "project-telemetry.jsonl"}}),
                encoding="utf-8",
            )
            self._write_event(telemetry_path)
            stdout = StringIO()
            with patch("sys.stdout", stdout):
                code = main(["--cwd", str(root), "--telemetry-report"])
            self.assertEqual(code, 0)
            self.assertIn("Prompts checked: 1", stdout.getvalue())
            self.assertIn(str(telemetry_path.resolve()), stdout.getvalue())

    def test_telemetry_report_uses_explicit_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            configured_path = root / "configured.jsonl"
            explicit_path = root / "explicit.jsonl"
            Path(root, ".prompt-preflight.json").write_text(
                json.dumps({"telemetry": {"enabled": True, "path": "configured.jsonl"}}),
                encoding="utf-8",
            )
            self._write_event(configured_path)
            self._write_event(explicit_path)
            stdout = StringIO()
            with patch("sys.stdout", stdout):
                code = main(["--cwd", str(root), "--telemetry-report", str(explicit_path)])
            self.assertEqual(code, 0)
            report = stdout.getvalue()
            self.assertIn("Prompts checked: 1", report)
            self.assertIn(explicit_path.name, report)
            self.assertNotIn(configured_path.name, report)

    def test_telemetry_report_resolves_config_with_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "my-project"
            project.mkdir()
            telemetry_path = project / "project-telemetry.jsonl"
            Path(project, ".prompt-preflight.json").write_text(
                json.dumps({"telemetry": {"enabled": True, "path": "project-telemetry.jsonl"}}),
                encoding="utf-8",
            )
            self._write_event(telemetry_path)
            stdout = StringIO()
            with patch("sys.stdout", stdout):
                code = main(["--cwd", str(project), "--telemetry-report"])
            self.assertEqual(code, 0)
            self.assertIn(str(telemetry_path.resolve()), stdout.getvalue())

    def test_record_telemetry_uses_configured_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            telemetry_path = root / "project-telemetry.jsonl"
            default_path = root / ".prompt-preflight-telemetry.jsonl"
            Path(root, ".prompt-preflight.json").write_text(
                json.dumps({"telemetry": {"enabled": True, "path": "project-telemetry.jsonl"}}),
                encoding="utf-8",
            )
            stdout = StringIO()
            with patch("sys.stdout", stdout):
                code = main(["--cwd", str(root), "--record-telemetry", "Create a car image"])

            self.assertEqual(code, 2)
            self.assertTrue(telemetry_path.is_file())
            self.assertFalse(default_path.exists())


if __name__ == "__main__":
    unittest.main()
