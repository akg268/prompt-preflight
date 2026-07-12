from __future__ import annotations

import io
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from prompt_preflight.analyzer import analyze_prompt, classify_intent, suggest_rewrite
from prompt_preflight.hook import EXAMPLES_URL, clarification_message, main as hook_main, process_payload
from prompt_preflight.telemetry import read_events


class AnalyzerTests(unittest.TestCase):
    def assertClarifies(self, prompt: str) -> None:
        result = analyze_prompt(prompt)
        self.assertTrue(result.should_clarify, result)
        self.assertGreaterEqual(len(result.questions), 1)

    def assertPasses(self, prompt: str) -> None:
        result = analyze_prompt(prompt)
        self.assertFalse(result.should_clarify, result)

    def test_pauses_vague_change(self) -> None:
        result = analyze_prompt("Make the dashboard better")
        self.assertTrue(result.should_clarify)
        self.assertIn("dashboard", result.suggested_prompt)
        self.assertIn("observable outcome", result.suggested_prompt)

    def test_pauses_pronoun_only_fix(self) -> None:
        self.assertClarifies("Fix it")

    def test_pauses_low_information_filler_prompts(self) -> None:
        for prompt in ("blah blah", "something", "some task", "random thing"):
            with self.subTest(prompt=prompt):
                result = analyze_prompt(prompt)
                self.assertTrue(result.should_clarify, result)
                self.assertGreater(result.score, 0)
                self.assertIn("low-information filler text", result.reasons)
                self.assertIn("clarity", result.checks)

    def test_pauses_broad_rewrite(self) -> None:
        self.assertClarifies("Rewrite the whole project to be production ready")

    def test_new_build_asks_for_platform_and_features(self) -> None:
        result = analyze_prompt("Build a todo app")
        self.assertTrue(result.should_clarify)
        self.assertTrue(any("platform" in question for question in result.questions))

    def test_passes_specific_change(self) -> None:
        self.assertPasses(
            "Fix the null handling in `src/auth.py`; preserve the public API and add a regression test."
        )

    def test_passes_informational_question(self) -> None:
        self.assertPasses("How does OAuth PKCE work?")

    def test_passes_followup(self) -> None:
        self.assertPasses("go ahead")

    def test_passes_one_time_bypass(self) -> None:
        result = analyze_prompt("Fix it [preflight:skip]")
        self.assertFalse(result.should_clarify)
        self.assertTrue(result.bypassed)

    def test_fix_rewrite_is_specific_to_bug_work(self) -> None:
        rewrite = suggest_rewrite("Fix it")
        self.assertIn("Current behavior", rewrite)
        self.assertIn("Expected behavior", rewrite)

    def test_build_rewrite_asks_for_users_stack_and_features(self) -> None:
        rewrite = suggest_rewrite("Build a todo app")
        self.assertIn("target users", rewrite)
        self.assertIn("platform or stack", rewrite)
        self.assertIn("minimum required features", rewrite)

    def test_vague_image_request_uses_visual_feedback(self) -> None:
        result = analyze_prompt("Create a car image")
        self.assertTrue(result.should_clarify)
        self.assertEqual(result.intent, "image_generation")
        self.assertIn("image of a car", result.suggested_prompt)
        feedback = " ".join(result.questions).lower()
        self.assertIn("visual style", feedback)
        self.assertIn("camera angle", feedback)
        self.assertNotIn("file", feedback)
        self.assertNotIn("component", feedback)
        self.assertNotIn("platform", feedback)
        self.assertNotIn("stack", feedback)

    def test_detailed_image_request_passes(self) -> None:
        prompt = (
            "Create a photorealistic image of a red 1967 Ford Mustang on a wet Tokyo "
            "street at night, low camera angle, cinematic lighting, 16:9."
        )
        result = analyze_prompt(prompt)
        self.assertEqual(result.intent, "image_generation")
        self.assertFalse(result.should_clarify, result)

    def test_image_processing_app_stays_software(self) -> None:
        self.assertEqual(classify_intent("Create an image processing app"), "software_build")

    def test_image_intent_routing_matrix(self) -> None:
        cases = {
            "Generate an image of a sports car": "image_generation",
            "Draw a cat in a garden": "image_generation",
            "Create a logo for my bakery": "image_generation",
            "Render a product photo": "image_generation",
            "Render a house": "image_generation",
            "Create an image generation API": "software_build",
            "Build an image upload component": "software_build",
        }
        for prompt, expected in cases.items():
            with self.subTest(prompt=prompt):
                self.assertEqual(classify_intent(prompt), expected)

    def test_content_domain_intent_routing_matrix(self) -> None:
        cases = {
            "Write a better intro": "writing",
            "Make this sound professional": "writing",
            "Summarize it": "writing",
            "Create a story for kids": "writing",
            "Research this topic": "research",
            "Compare vendor options": "research",
            "Look into pricing": "research",
            "Analyze the data": "data_analysis",
            "Make a chart": "data_analysis",
            "Analyze churn": "data_analysis",
            "Create a presentation": "presentation",
            "Make a slide deck": "presentation",
            "Create investor slides": "presentation",
        }
        for prompt, expected in cases.items():
            with self.subTest(prompt=prompt):
                self.assertEqual(classify_intent(prompt), expected)

    def test_vague_content_domains_use_domain_specific_feedback(self) -> None:
        cases = {
            "Write a better intro": ("writing", "audience", "tone"),
            "Research this topic": ("research", "sources", "criteria"),
            "Analyze the data": ("data_analysis", "dataset", "metric"),
            "Create a presentation": ("presentation", "audience", "slide"),
        }
        for prompt, (intent, expected_question_word, expected_rewrite_word) in cases.items():
            with self.subTest(prompt=prompt):
                result = analyze_prompt(prompt)
                self.assertTrue(result.should_clarify, result)
                self.assertEqual(result.intent, intent)
                self.assertIn(expected_question_word, " ".join(result.questions).lower())
                self.assertIn(expected_rewrite_word, result.suggested_prompt.lower())
                self.assertNotIn("files/components", " ".join(result.questions).lower())
                self.assertNotIn("platform or stack", " ".join(result.questions).lower())

    def test_detailed_content_domain_prompts_pass(self) -> None:
        prompts = [
            "Write a 500-word blog post for startup founders explaining how Prompt Preflight reduces AI-agent retry loops, using a practical tone and three examples.",
            "Write a 700-word bedtime story for children ages 4 to 6 about a shy turtle learning to sing, with two short chorus songs, a joyful read-aloud tone, and a happy ending.",
            "Research current SOC 2 alternatives for a seed-stage SaaS and compare cost, implementation effort, and audit readiness in a markdown table with links to official sources.",
            "Analyze sales.csv by month and region, calculate revenue and conversion rate, and output a table plus a short summary of trends.",
            "Create a 10-slide investor deck for seed-stage AI developer tool buyers with problem, market, product, traction, GTM, and ask sections.",
        ]
        for prompt in prompts:
            with self.subTest(prompt=prompt):
                self.assertPasses(prompt)

    def test_suggested_rewrites_use_contract_style_structure(self) -> None:
        prompts = [
            "Fix it",
            "Write a better intro",
            "Research this topic",
            "Analyze the data",
            "Create a presentation",
            "Create a car image",
        ]
        for prompt in prompts:
            with self.subTest(prompt=prompt):
                result = analyze_prompt(prompt)
                self.assertTrue(result.should_clarify, result)
                self.assertIn("Task:", result.suggested_prompt)
                self.assertIn("Output format:", result.suggested_prompt)
                self.assertTrue(
                    any(
                        marker in result.suggested_prompt
                        for marker in ("Self-check:", "Uncertainty rule:", "Example/style reference:")
                    ),
                    result.suggested_prompt,
                )

    def test_vague_story_prompt_gets_writing_feedback(self) -> None:
        result = analyze_prompt("Create a story for kids. Story should be joyful with songs")
        self.assertTrue(result.should_clarify, result)
        self.assertEqual(result.intent, "writing")
        self.assertGreater(result.score, 0)
        self.assertEqual(result.severity, "high")
        self.assertIn("context", result.checks)
        self.assertIn("output_contract", result.checks)
        self.assertIn("template_contract", result.checks)
        self.assertIn("risk", result.checks)
        feedback = " ".join(result.questions).lower()
        self.assertIn("age range", feedback)
        self.assertIn("characters", feedback)
        self.assertIn("songs", feedback)
        self.assertIn("Story elements:", result.suggested_prompt)
        self.assertIn("Use this structured template", result.suggested_prompt)
        self.assertIn("# Task", result.suggested_prompt)
        self.assertIn("# Output Format", result.suggested_prompt)

    def test_missing_prompt_contract_fields_are_high_risk_and_template_backed(self) -> None:
        result = analyze_prompt("Make the button better")
        self.assertTrue(result.should_clarify, result)
        self.assertEqual(result.severity, "high")
        self.assertIn("template_contract", result.checks)
        self.assertIn("risk", result.checks)
        self.assertTrue(
            any("missing prompt contract fields" in reason for reason in result.reasons),
            result.reasons,
        )
        self.assertIn("Use this structured template", result.suggested_prompt)
        self.assertIn("# Task", result.suggested_prompt)
        self.assertIn("# Constraints", result.suggested_prompt)
        self.assertIn("# Output Format", result.suggested_prompt)

    def test_short_low_risk_haiku_prompt_still_passes(self) -> None:
        self.assertPasses("Write a haiku about rain")

    def test_short_action_without_output_format_gets_clarified(self) -> None:
        result = analyze_prompt("Generate more tests")
        self.assertTrue(result.should_clarify, result)
        self.assertIn("output format is underspecified", result.reasons)
        self.assertIn("final output", " ".join(result.questions).lower())

    def test_privacy_check_blocks_and_redacts_secrets(self) -> None:
        secret = "sk-1234567890abcdef1234567890"
        prompt = f"Use api_key={secret} to debug my request"
        result = analyze_prompt(prompt)
        self.assertTrue(result.should_clarify, result)
        self.assertEqual(result.intent, "privacy")
        self.assertEqual(result.checks, ("privacy",))
        self.assertEqual(result.severity, "high")
        self.assertNotIn(secret, result.to_dict()["prompt"])
        self.assertIn("[REDACTED_SECRET]", result.to_dict()["prompt"])

        message = clarification_message(result)
        self.assertNotIn(secret, message)
        self.assertIn("[REDACTED_SECRET]", message)

    def test_privacy_check_is_not_bypassed_by_skip_marker(self) -> None:
        result = analyze_prompt("Use token=supersecret123456 [preflight:skip]")
        self.assertTrue(result.should_clarify, result)
        self.assertEqual(result.checks, ("privacy",))
        self.assertFalse(result.bypassed)

    def test_high_risk_prompt_requires_plan_first_and_rollback(self) -> None:
        result = analyze_prompt("Deploy this to production")
        self.assertTrue(result.should_clarify, result)
        self.assertIn("risk", result.checks)
        self.assertIn("plan_first", result.checks)
        self.assertEqual(result.severity, "high")
        feedback = " ".join(result.questions).lower()
        self.assertIn("rollback", feedback)
        self.assertIn("plan", feedback)
        self.assertIn("Plan-first:", result.suggested_prompt)

    def test_attachment_reference_requires_context(self) -> None:
        result = analyze_prompt("Summarize the attached PDF")
        self.assertTrue(result.should_clarify, result)
        self.assertIn("context", result.checks)
        self.assertIn("referenced attachment or source material is missing", result.reasons)

    def test_missing_file_reference_blocks_only_when_file_is_source_material(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = analyze_prompt(
                "Analyze missing.csv by month and output a table",
                cwd=directory,
            )
        self.assertTrue(result.should_clarify, result)
        self.assertIn("context", result.checks)
        self.assertTrue(any("referenced file not found" in reason for reason in result.reasons))

    def test_existing_source_file_can_pass_when_prompt_is_specific(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "sales.csv").write_text("month,region,revenue\nJan,West,10\n", encoding="utf-8")
            result = analyze_prompt(
                "Analyze sales.csv by month and region, calculate revenue and conversion rate, and output a table plus a short summary of trends.",
                cwd=directory,
            )
        self.assertFalse(result.should_clarify, result)

    def test_attachment_metadata_satisfies_attached_pdf_reference(self) -> None:
        result = analyze_prompt("Summarize the attached PDF", attachments=["report.pdf"])
        self.assertNotIn("referenced attachment or source material is missing", result.reasons)

    def test_attachment_metadata_satisfies_missing_file_reference(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = analyze_prompt(
                "Analyze missing.csv by month, calculate revenue, and output a table",
                cwd=directory,
                attachments=["missing.csv"]
            )
        self.assertFalse(result.should_clarify, result)

    def test_image_hook_feedback_is_domain_specific(self) -> None:
        result = process_payload({"prompt": "Create a car image"})
        reason = result["reason"].lower()
        self.assertIn("photorealistic/illustrated/3d", reason)
        self.assertIn("aspect ratio", reason)
        self.assertNotIn("platform or stack", reason)
        self.assertNotIn("files/components", reason)

    def test_calibration_set(self) -> None:
        cases = {
            "Optimize the database": True,
            "Deploy this to production": True,
            "Make payments more robust": True,
            "Modernize the entire authentication system": True,
            "Redesign the onboarding flow": True,
            "Reply to the customer": True,
            "Plan the Q3 roadmap": True,
            "Look at the user data": True,
            "Add an aria-label to `LoginButton` and test it": False,
            "Create `docs/API.md` from the existing OpenAPI schema": False,
            "Write a haiku about rain": False,
            "Explain the repository architecture": False,
            "Run the tests": False,
            "approved": False,
        }
        for prompt, expected in cases.items():
            with self.subTest(prompt=prompt):
                self.assertEqual(analyze_prompt(prompt).should_clarify, expected)


class HookTests(unittest.TestCase):
    def test_hook_blocks_vague_prompt(self) -> None:
        result = process_payload({"prompt": "Make the dashboard better"})
        self.assertEqual(result["decision"], "block")
        self.assertIn("Your prompt:", result["reason"])
        self.assertIn('"Make the dashboard better"', result["reason"])
        self.assertIn("Try asking:", result["reason"])
        self.assertIn("Improve the dashboard", result["reason"])
        self.assertIn(EXAMPLES_URL, result["reason"])

    def test_feedback_orders_original_rewrite_then_questions(self) -> None:
        message = clarification_message(analyze_prompt("Fix it"))
        self.assertLess(message.index("Your prompt:"), message.index("Try asking:"))
        self.assertLess(message.index("Try asking:"), message.index("Fill in the brackets"))
        self.assertLess(message.index("Fill in the brackets"), message.index("Examples and templates:"))

    def test_hook_allows_clear_prompt_without_output(self) -> None:
        result = process_payload(
            {"prompt": "Fix `src/auth.py` token expiry handling and add a regression test."}
        )
        self.assertIsNone(result)

    def test_hook_fails_open_on_bad_json(self) -> None:
        stdout = io.StringIO()
        code = hook_main(io.StringIO("not json"), stdout)
        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue(), "")

    def test_nudge_mode_adds_context(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, ".prompt-preflight.json").write_text(
                json.dumps({"mode": "nudge"}), encoding="utf-8"
            )
            result = process_payload({"prompt": "Fix it", "cwd": directory})
        self.assertIn("hookSpecificOutput", result)
        self.assertNotIn("decision", result)
        self.assertIn("improved prompt example", result["hookSpecificOutput"]["additionalContext"])

    def test_hook_records_opt_in_telemetry_without_prompt_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, ".prompt-preflight.json").write_text(
                json.dumps({"telemetry": {"enabled": True, "path": "telemetry.jsonl"}}),
                encoding="utf-8",
            )
            result = process_payload({"prompt": "Create a car image", "cwd": directory})
            events = read_events(Path(directory) / "telemetry.jsonl")
        self.assertEqual(result["decision"], "block")
        self.assertEqual(len(events), 1)
        encoded = json.dumps(events[0])
        self.assertIn('"decision": "blocked"', encoded)
        self.assertNotIn("Create a car image", encoded)


if __name__ == "__main__":
    unittest.main()
