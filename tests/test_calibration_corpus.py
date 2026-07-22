"""Data-driven calibration corpus tests.

Loads reviewed examples from tests/data/calibration_corpus.jsonl and asserts
analyzer behavior. New cases are append-only in the JSONL — no new test code
is required for each example.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from prompt_preflight.analyzer import analyze_prompt  # noqa: E402


CORPUS_PATH = Path(__file__).resolve().parent / "data" / "calibration_corpus.jsonl"


def load_corpus(path: Path = CORPUS_PATH) -> list[dict]:
    """Load calibration entries, skipping blanks and comment lines."""
    entries: list[dict] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON on line {line_no} of {path}: {exc}") from exc
        if "id" not in entry or "prompt" not in entry or "should_clarify" not in entry:
            raise ValueError(
                f"Corpus entry on line {line_no} missing required fields "
                f"(id, prompt, should_clarify): {entry!r}"
            )
        entries.append(entry)
    return entries


class CalibrationCorpusTests(unittest.TestCase):
    """Assert analyzer decisions against the append-only JSONL corpus."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.entries = load_corpus()

    def test_corpus_is_nonempty(self) -> None:
        self.assertGreaterEqual(len(self.entries), 1, "calibration corpus has no entries")

    def test_corpus_cases(self) -> None:
        for entry in self.entries:
            case_id = entry["id"]
            with self.subTest(id=case_id):
                result = analyze_prompt(entry["prompt"])
                expected_clarify = entry["should_clarify"]
                self.assertEqual(
                    result.should_clarify,
                    expected_clarify,
                    f"{case_id}: should_clarify={result.should_clarify} "
                    f"(expected {expected_clarify}); decision={result.decision}",
                )
                # decision should agree with should_clarify: block when clarifying.
                if expected_clarify:
                    self.assertEqual(
                        result.decision,
                        "block",
                        f"{case_id}: expected decision='block' when should_clarify=true, "
                        f"got {result.decision!r}",
                    )
                else:
                    self.assertIn(
                        result.decision,
                        ("allow", "nudge"),
                        f"{case_id}: expected decision in ('allow','nudge') when "
                        f"should_clarify=false, got {result.decision!r}",
                    )

                expected_intent = entry.get("expected_intent")
                if expected_intent is not None:
                    self.assertEqual(
                        result.intent,
                        expected_intent,
                        f"{case_id}: intent={result.intent!r} "
                        f"(expected {expected_intent!r})",
                    )

                expected_checks = entry.get("expected_checks")
                if expected_checks is not None:
                    actual = set(result.checks)
                    for check in expected_checks:
                        self.assertIn(
                            check,
                            actual,
                            f"{case_id}: expected check {check!r} in result.checks={list(result.checks)!r}",
                        )


if __name__ == "__main__":
    unittest.main()
