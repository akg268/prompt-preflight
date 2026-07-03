from __future__ import annotations

import io
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from prompt_preflight.analyzer import analyze_prompt  # noqa: E402
from prompt_preflight.cli import main as cli_main  # noqa: E402
from prompt_preflight.templates import (  # noqa: E402
    render_template,
    template_profile_names,
    validate_structured_prompt,
)


class TemplateTests(unittest.TestCase):
    def test_template_catalog_exposes_expected_profiles(self) -> None:
        self.assertIn("software", template_profile_names())
        self.assertIn("image", template_profile_names())
        self.assertIn("writing", template_profile_names())
        self.assertIn("research", template_profile_names())
        self.assertIn("data_analysis", template_profile_names())
        self.assertIn("presentation", template_profile_names())

    def test_renders_markdown_xml_and_toml_templates(self) -> None:
        self.assertIn("# Visual Details", render_template("image", "md"))
        self.assertIn("<visual_details>", render_template("image", "xml"))
        self.assertIn('profile = "image"', render_template("image", "toml"))

    def test_incomplete_markdown_image_contract_is_blocked(self) -> None:
        prompt = """# Task
Create a car image

# Visual Details
A red vintage Mustang on a rainy neon street

# Output Format
16:9 PNG
"""
        result = analyze_prompt(prompt)
        self.assertTrue(result.should_clarify, result)
        self.assertIn("template_contract", result.checks)
        self.assertIn("style or mood", result.reasons[0])
        self.assertIn("# Style", result.suggested_prompt)

    def test_complete_markdown_image_contract_validates(self) -> None:
        prompt = """# Task
Create an image of a red 1967 Ford Mustang.

# Visual Details
The car is parked on a rainy Tokyo street with neon reflections and chrome details.

# Style
Photorealistic, cinematic, high contrast night mood.

# Output Format
16:9 landscape PNG.
"""
        validation = validate_structured_prompt(prompt, "image_generation")
        self.assertIsNotNone(validation)
        self.assertEqual(validation.missing_required, ())

    def test_xml_contract_uses_profile_attribute(self) -> None:
        prompt = """<prompt profile="research">
  <research_question>Which SOC 2 alternative is best for a seed-stage SaaS?</research_question>
  <scope>US vendors in 2026, exclude enterprise-only options.</scope>
  <sources>Official docs and vendor pricing pages.</sources>
  <output_format>Markdown table plus recommendation.</output_format>
</prompt>"""
        result = analyze_prompt(prompt)
        self.assertTrue(result.should_clarify, result)
        self.assertIn("template_contract", result.checks)
        self.assertIn("criteria", result.reasons[0])
        self.assertIn("<criteria>", result.suggested_prompt)

    def test_toml_placeholders_do_not_satisfy_required_fields(self) -> None:
        prompt = """profile = "software"
task = "[Build/fix/change/refactor specific thing]"
scope = "src/auth.py"
constraints = "Preserve public API"
output_format = "Patch plus summary"
success_criteria = "[Test or acceptance criterion]"
"""
        result = analyze_prompt(prompt)
        self.assertTrue(result.should_clarify, result)
        self.assertIn("template_contract", result.checks)
        self.assertIn("task", result.reasons[0])
        self.assertIn("success criteria", result.reasons[0])

    def test_cli_can_print_template_without_prompt(self) -> None:
        stdout = io.StringIO()
        original_stdout = sys.stdout
        try:
            sys.stdout = stdout
            code = cli_main(["--template", "data-analysis", "--template-format", "toml"])
        finally:
            sys.stdout = original_stdout
        self.assertEqual(code, 0)
        output = stdout.getvalue()
        self.assertIn('profile = "data_analysis"', output)
        self.assertIn("validation", output)


if __name__ == "__main__":
    unittest.main()
