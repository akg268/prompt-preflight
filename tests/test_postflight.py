from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from prompt_preflight.postflight import (  # noqa: E402
    PostflightConfig,
    analyze_postflight,
)
from prompt_preflight.postflight_config import load_postflight_config  # noqa: E402
from prompt_preflight.postflight_cli import main as cli_main  # noqa: E402
from prompt_preflight.postflight_claude_hook import (  # noqa: E402
    main as claude_hook_main,
    process_payload as claude_process_payload,
)
from prompt_preflight.telemetry import read_events  # noqa: E402


def _checks(prompt: str, response: str, **kwargs) -> tuple[str, ...]:
    return analyze_postflight(prompt, response, **kwargs).checks


class OutputFormatCheckTests(unittest.TestCase):
    def test_json_requested_and_present_passes(self) -> None:
        result = analyze_postflight("Return the result as JSON", '{"ok": true, "n": 3}')
        self.assertNotIn("output_format", result.checks)

    def test_json_requested_but_prose_is_flagged(self) -> None:
        result = analyze_postflight("Return the result as JSON", "the status is ok, 3 items")
        self.assertIn("output_format", result.checks)
        self.assertTrue(result.needs_attention)

    def test_json_in_fenced_block_passes(self) -> None:
        response = "Here you go:\n```json\n{\"a\": 1}\n```"
        self.assertNotIn("output_format", _checks("give me json", response))

    def test_table_requested_and_present_passes(self) -> None:
        response = "| name | score |\n| --- | --- |\n| a | 1 |"
        self.assertNotIn("output_format", _checks("show a table", response))

    def test_table_requested_but_missing_is_flagged(self) -> None:
        self.assertIn("output_format", _checks("show a comparison table", "a is 1 and b is 2"))

    def test_bullets_requested_but_missing_is_flagged(self) -> None:
        self.assertIn("output_format", _checks("give me a bulleted list", "just one sentence"))

    def test_no_format_requested_is_never_flagged(self) -> None:
        self.assertNotIn("output_format", _checks("explain recursion", "prose answer"))


class TestsPresentCheckTests(unittest.TestCase):
    def test_tests_requested_but_absent_is_flagged(self) -> None:
        result = analyze_postflight("Write a function with unit tests", "def add(a, b): return a + b")
        self.assertIn("tests_present", result.checks)
        self.assertTrue(result.needs_attention)

    def test_tests_requested_and_present_passes(self) -> None:
        response = "def add(a, b): return a + b\n\ndef test_add():\n    assert add(1, 2) == 3"
        self.assertNotIn("tests_present", _checks("add tests too", response))

    def test_no_tests_requested_is_never_flagged(self) -> None:
        self.assertNotIn("tests_present", _checks("write a function", "def add(a, b): return a + b"))


class FileChangeClaimCheckTests(unittest.TestCase):
    def test_claim_with_empty_changeset_is_flagged(self) -> None:
        result = analyze_postflight("update the parser", "I updated src/parser.py.", changed_files=[])
        self.assertIn("file_change_claim", result.checks)
        self.assertTrue(result.needs_attention)

    def test_claim_without_metadata_is_informational_only(self) -> None:
        result = analyze_postflight("update the parser", "I updated src/parser.py.", changed_files=None)
        self.assertIn("file_change_claim", result.checks)
        self.assertFalse(result.needs_attention)
        info = [f for f in result.findings if f.check == "file_change_claim"]
        self.assertTrue(info and info[0].informational)

    def test_claim_with_real_changes_passes(self) -> None:
        result = analyze_postflight("fix it", "I updated the file.", changed_files=["src/a.py"])
        self.assertNotIn("file_change_claim", result.checks)

    def test_no_claim_is_never_flagged(self) -> None:
        result = analyze_postflight("explain the parser", "The parser works like this.", changed_files=[])
        self.assertNotIn("file_change_claim", result.checks)


class ConstraintAdherenceCheckTests(unittest.TestCase):
    def test_violated_avoid_constraint_is_flagged(self) -> None:
        result = analyze_postflight(
            "Parse the string without using regex",
            "Here is a solution using regex to match the pattern.",
        )
        self.assertIn("constraint_adherence", result.checks)

    def test_respected_constraint_passes(self) -> None:
        result = analyze_postflight(
            "Parse the string without using regex",
            "Here is a solution using str.split and a manual scan.",
        )
        self.assertNotIn("constraint_adherence", result.checks)


class PlaceholderCheckTests(unittest.TestCase):
    def test_todo_placeholder_is_flagged(self) -> None:
        result = analyze_postflight("finish the loader", "def load(): return [TODO]")
        self.assertIn("placeholders", result.checks)
        self.assertTrue(result.needs_attention)

    def test_your_key_placeholder_is_flagged(self) -> None:
        self.assertIn("placeholders", _checks("write config", "key = [YOUR_API_KEY]"))

    def test_clean_response_passes(self) -> None:
        self.assertNotIn("placeholders", _checks("write config", "key = load_from_env()"))


class CitationCheckTests(unittest.TestCase):
    def test_citations_requested_but_absent_is_flagged(self) -> None:
        result = analyze_postflight(
            "Research vector databases with citations",
            "Pinecone and Weaviate are both popular choices.",
        )
        self.assertIn("citations", result.checks)

    def test_citations_present_passes(self) -> None:
        response = "Pinecone is popular [1].\n\nReferences:\n[1] https://example.com"
        self.assertNotIn("citations", _checks("research this with citations", response))


class PrivacyCheckTests(unittest.TestCase):
    def test_leaked_secret_is_flagged_and_redacted(self) -> None:
        secret = "sk-abcdefghijklmnopqrstuvwxyz0123456789"
        result = analyze_postflight("show the key", f"the key is {secret}")
        self.assertIn("privacy", result.checks)
        self.assertEqual(result.severity, "high")
        self.assertTrue(result.needs_attention)
        self.assertIsNotNone(result.redacted_response)
        self.assertNotIn(secret, result.redacted_response)
        # to_dict swaps the redacted text into the response field.
        self.assertNotIn(secret, json.dumps(result.to_dict()))


class ResultShapeTests(unittest.TestCase):
    def test_clean_response_needs_no_attention(self) -> None:
        result = analyze_postflight("explain X", "Here is a clear explanation of X.")
        self.assertFalse(result.needs_attention)
        self.assertEqual(result.findings, ())
        self.assertEqual(result.severity, "low")

    def test_empty_response_is_clean(self) -> None:
        self.assertFalse(analyze_postflight("do a thing", "").needs_attention)

    def test_non_string_inputs_do_not_raise(self) -> None:
        result = analyze_postflight(None, None)  # type: ignore[arg-type]
        self.assertFalse(result.needs_attention)

    def test_nudge_policy_surfaces_finding_without_blocking(self) -> None:
        config = PostflightConfig(policies={"placeholders": "nudge"})
        result = analyze_postflight("finish it", "return [TODO]", config=config)
        self.assertIn("placeholders", result.checks)
        self.assertFalse(result.needs_attention)

    def test_off_policy_disables_a_check(self) -> None:
        config = PostflightConfig(policies={"placeholders": "off"})
        result = analyze_postflight("finish it", "return [TODO]", config=config)
        self.assertNotIn("placeholders", result.checks)


BENCHMARK_CASES: tuple[tuple[str, str, list[str] | None, set[str]], ...] = (
    ("Return JSON", "the answer is 42", None, {"output_format"}),
    ("Return JSON", '{"answer": 42}', None, set()),
    ("Write code with unit tests", "def f(): pass", None, {"tests_present"}),
    ("Refactor without using eval", "I rewrote it using eval() again.", None, {"constraint_adherence"}),
    ("Finish the module", "def go(): return [TODO]", None, {"placeholders"}),
    ("Research this with citations", "It is widely known to be good.", None, {"citations"}),
    ("Update the config", "I updated config.py.", [], {"file_change_claim"}),
    ("Explain the design", "Here is the design rationale in prose.", None, set()),
)


class PostflightBenchmarkTests(unittest.TestCase):
    def test_benchmark_cases_match_expected_checks(self) -> None:
        for prompt, response, changed, expected in BENCHMARK_CASES:
            with self.subTest(prompt=prompt):
                checks = set(analyze_postflight(prompt, response, changed_files=changed).checks)
                self.assertEqual(checks, expected)


class PostflightConfigTests(unittest.TestCase):
    def test_defaults_are_strict(self) -> None:
        config = load_postflight_config(None)
        self.assertTrue(config.enabled)
        self.assertEqual(config.policy_for("privacy"), "block")
        self.assertEqual(config.policy_for("output_format"), "block")

    def test_config_block_softens_checks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".prompt-preflight.json").write_text(
                json.dumps({"postflight": {"checks": {"citations": "off", "placeholders": "nudge"}}}),
                encoding="utf-8",
            )
            config = load_postflight_config(root)
        self.assertEqual(config.policy_for("citations"), "off")
        self.assertEqual(config.policy_for("placeholders"), "nudge")
        self.assertEqual(config.policy_for("output_format"), "block")

    def test_global_disable_turns_postflight_off(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".prompt-preflight.json").write_text(
                json.dumps({"enabled": False}), encoding="utf-8"
            )
            config = load_postflight_config(root)
        self.assertFalse(config.enabled)


class PostflightCliTests(unittest.TestCase):
    def _run(self, argv: list[str], stdin_text: str = "") -> tuple[int, str]:
        stdout = StringIO()
        code = cli_main(argv, stdin=StringIO(stdin_text), stdout=stdout)
        return code, stdout.getvalue()

    def test_clean_response_exits_zero(self) -> None:
        code, out = self._run(["--prompt", "Return JSON", '{"ok": true}'])
        self.assertEqual(code, 0)
        self.assertIn("no issues", out.lower())

    def test_bad_response_exits_two(self) -> None:
        code, _ = self._run(["--prompt", "Return JSON", "the answer is 42"])
        self.assertEqual(code, 2)

    def test_reads_response_from_stdin(self) -> None:
        code, _ = self._run(["--prompt", "Return JSON"], stdin_text="the answer is 42")
        self.assertEqual(code, 2)

    def test_json_output_shape(self) -> None:
        _, out = self._run(["--json", "--prompt", "Return JSON", "the answer is 42"])
        data = json.loads(out)
        self.assertEqual(set(data), {
            "prompt", "response", "needs_attention", "findings", "checks",
            "severity", "redacted_response",
        })
        self.assertIn("output_format", data["checks"])

    def test_changed_files_empty_string_flags_but_absent_does_not(self) -> None:
        absent_code, _ = self._run(["--prompt", "update it", "I updated parser.py."])
        empty_code, _ = self._run(["--prompt", "update it", "--changed-files", "", "I updated parser.py."])
        self.assertEqual(absent_code, 0)
        self.assertEqual(empty_code, 2)

    def test_records_postflight_telemetry_without_response_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "telemetry.jsonl"
            code, _ = self._run(
                [
                    "--prompt",
                    "Return JSON",
                    "--record-telemetry",
                    "--telemetry-path",
                    str(path),
                    "the answer is 42",
                ]
            )
            raw = path.read_text(encoding="utf-8")
            events = read_events(path)

        self.assertEqual(code, 2)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["phase"], "postflight")
        self.assertIn("token_observability", events[0])
        self.assertNotIn("Return JSON", raw)
        self.assertNotIn("answer is 42", raw)


class PostflightClaudeHookTests(unittest.TestCase):
    def _write_transcript(self, directory: Path, assistant: str, user: str = "Return JSON") -> Path:
        path = directory / "transcript.jsonl"
        path.write_text(
            "\n".join(
                [
                    json.dumps({"role": "user", "content": user}),
                    json.dumps({"role": "assistant", "content": assistant}),
                ]
            ),
            encoding="utf-8",
        )
        return path

    def test_stop_hook_blocks_on_bad_response(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            transcript = self._write_transcript(Path(directory), "the answer is 42")
            result = claude_process_payload(
                {"hook_event_name": "Stop", "transcript_path": str(transcript), "cwd": directory}
            )
        self.assertIsNotNone(result)
        self.assertEqual(result["decision"], "block")
        self.assertIn("output_format", result["reason"])

    def test_stop_hook_allows_clean_response(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            transcript = self._write_transcript(Path(directory), '{"ok": true}')
            result = claude_process_payload(
                {"hook_event_name": "Stop", "transcript_path": str(transcript), "cwd": directory}
            )
        self.assertIsNone(result)

    def test_stop_hook_respects_stop_hook_active(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            transcript = self._write_transcript(Path(directory), "the answer is 42")
            result = claude_process_payload(
                {"transcript_path": str(transcript), "cwd": directory, "stop_hook_active": True}
            )
        self.assertIsNone(result)

    def test_stop_hook_main_emits_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            transcript = self._write_transcript(Path(directory), "the answer is 42")
            payload = json.dumps(
                {"hook_event_name": "Stop", "transcript_path": str(transcript), "cwd": directory}
            )
            stdout = StringIO()
            code = claude_hook_main(stdin=StringIO(payload), stdout=stdout)
        self.assertEqual(code, 0)
        json.loads(stdout.getvalue())  # must be valid JSON

    def test_stop_hook_records_postflight_telemetry_when_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".prompt-preflight.json").write_text(
                json.dumps(
                    {
                        "telemetry": {
                            "enabled": True,
                            "path": "telemetry.jsonl",
                        }
                    }
                ),
                encoding="utf-8",
            )
            transcript = self._write_transcript(root, "the answer is 42")
            result = claude_process_payload(
                {"hook_event_name": "Stop", "transcript_path": str(transcript), "cwd": directory}
            )
            telemetry_path = root / "telemetry.jsonl"
            raw = telemetry_path.read_text(encoding="utf-8")
            events = read_events(telemetry_path)

        self.assertIsNotNone(result)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["host"], "claude-code-postflight")
        self.assertEqual(events[0]["phase"], "postflight")
        self.assertIn("token_observability", events[0])
        self.assertNotIn("Return JSON", raw)
        self.assertNotIn("answer is 42", raw)

    def test_stop_hook_fails_open_on_bad_json(self) -> None:
        stdout = StringIO()
        code = claude_hook_main(stdin=StringIO("not json"), stdout=stdout)
        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
