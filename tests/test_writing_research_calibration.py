"""Calibration coverage for writing and research prompt domains.

This module documents the expected analyzer behavior for writing and research
prompts. Unlike the canonical vague-prompt library (which only tracks prompts
that should be blocked), this calibration set includes both prompts that should
be clarified and prompts that should pass through, so regressions in either
direction are caught.

Each case is documented with the rationale for its expected outcome.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from prompt_preflight.analyzer import analyze_prompt  # noqa: E402


# Calibration cases for writing and research prompts.
#
# True  = the prompt is vague and should be blocked for clarification.
# False = the prompt is specific enough to act on and should pass through.
#
# Cases are grouped by intent and ordered from vague to specific so that
# maintainers can see the boundary between "should clarify" and "should pass".
CALIBRATION_CASES: dict[str, bool] = {
    # ---- Writing: vague prompts that should clarify ----
    # Missing audience, purpose, source material, tone, length, and format.
    "Write a blog post": True,
    "Write a better intro": True,
    "Make this sound professional": True,
    "Summarize it": True,
    "Rewrite this email": True,
    "Draft the announcement": True,
    "Create website copy": True,
    "Improve the proposal": True,
    "Edit this for clarity": True,
    # ---- Writing: specific prompts that should pass ----
    # These include audience, purpose, scope, tone, length, or format.
    "Write a 500-word blog post for startup founders explaining how Prompt Preflight reduces AI-agent retry loops, using a practical tone and three examples.": False,
    "Proofread the attached press release for AP style and keep it under 400 words.": False,
    "Rewrite the onboarding email sequence for new enterprise trial users in a friendly but professional tone, 5 emails, each under 150 words.": False,
    # ---- Research: vague prompts that should clarify ----
    # Missing research question, scope, sources, criteria, and output format.
    "Research this topic": True,
    "Compare the options": True,
    "Find the best tool": True,
    "Investigate competitors": True,
    "Look into pricing": True,
    "Evaluate vendors": True,
    "Research the market": True,
    "Find sources": True,
    # ---- Research: specific prompts that should pass ----
    # These include question, scope, sources, criteria, and output format.
    "Research current SOC 2 alternatives for a seed-stage SaaS and compare cost, implementation effort, and audit readiness in a markdown table with links to official sources.": False,
    "Compare the top 5 vector databases for RAG workloads using benchmarks from ann-benchmarks.com, output a table with latency, recall, and pricing columns.": False,
}


class WritingResearchCalibrationTests(unittest.TestCase):
    """Validate analyzer behavior on writing and research prompts."""

    def test_calibration_set(self) -> None:
        for prompt, expected in CALIBRATION_CASES.items():
            with self.subTest(prompt=prompt):
                self.assertEqual(analyze_prompt(prompt).should_clarify, expected)

    def test_writing_intent_routing(self) -> None:
        """Vague writing prompts should route to the writing intent."""
        for prompt in (
            "Write a better intro",
            "Make this sound professional",
            "Summarize it",
            "Proofread the attached press release for AP style and keep it under 400 words.",
        ):
            with self.subTest(prompt=prompt):
                self.assertEqual(analyze_prompt(prompt).intent, "writing")

    def test_research_intent_routing(self) -> None:
        """Vague research prompts should route to the research intent."""
        for prompt in (
            "Research this topic",
            "Compare the options",
            "Find the best tool",
        ):
            with self.subTest(prompt=prompt):
                self.assertEqual(analyze_prompt(prompt).intent, "research")


if __name__ == "__main__":
    unittest.main()
