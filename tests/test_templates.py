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
        self.assertIn("customer_support", template_profile_names())
        self.assertIn("prd", template_profile_names())
        self.assertIn("incident_response", template_profile_names())
        self.assertIn("sql", template_profile_names())
        self.assertIn("design_critique", template_profile_names())
        self.assertIn("meeting_notes", template_profile_names())

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



    def test_complete_customer_support_contract_validates(self) -> None:
        prompt = """# Task
Draft a reply to a frustrated user.
# Customer Issue
User cannot log in after password reset.
# Prior Interactions
User emailed us twice yesterday.
# Desired Tone
Empathetic and apologetic.
# Policy or Constraints
Do not offer refunds yet.
# Resolution
Ask them to try an incognito window.
# Channel
Email.
# Output Format
Draft email.
"""
        validation = validate_structured_prompt(prompt, "customer_support")
        self.assertIsNotNone(validation)
        self.assertEqual(validation.missing_required, ())

    def test_incomplete_customer_support_contract_is_blocked(self) -> None:
        prompt = """<prompt profile="customer_support">
  <task>Draft a reply</task>
  <customer_issue>Cannot login</customer_issue>
  <prior_interactions>None</prior_interactions>
  <desired_tone>[Desired tone]</desired_tone>
  <policy>No refunds</policy>
  <resolution>Ask to reset again</resolution>
  <channel>Email</channel>
  <output_format>Email</output_format>
</prompt>"""
        result = analyze_prompt(prompt)
        self.assertTrue(result.should_clarify, result)
        self.assertIn("template_contract", result.checks)
        self.assertIn("tone", result.reasons[0])

    def test_complete_prd_contract_validates(self) -> None:
        prompt = """profile = "prd"
task = "Write PRD"
problem_statement = "Hard to use"
target_users = "Admins"
functional_requirements = "SSO login"
non_functional_requirements = "Fast"
scope = "Web only"
success_metrics = "100 users"
output_format = "Markdown"
"""
        validation = validate_structured_prompt(prompt, "prd")
        self.assertIsNotNone(validation)
        self.assertEqual(validation.missing_required, ())

    def test_incomplete_prd_contract_is_blocked(self) -> None:
        prompt = """profile = "prd"
task = "Write PRD"
problem_statement = "Hard to use"
target_users = "Admins"
functional_requirements = "SSO login"
non_functional_requirements = "Fast"
scope = "Web only"
success_metrics = "[Success metrics]"
output_format = "Markdown"
"""
        result = analyze_prompt(prompt)
        self.assertTrue(result.should_clarify, result)
        self.assertIn("template_contract", result.checks)
        self.assertIn("success metrics", result.reasons[0])

    def test_complete_incident_response_contract_validates(self) -> None:
        prompt = """# Task
Write postmortem
# Incident Summary
Site went down
# Severity
SEV-1
# Timeline
10am to 11am
# Impact
100 users affected
# Root Cause
Database crash
# Remediation
Upgrade database
# Output Format
Doc
"""
        validation = validate_structured_prompt(prompt, "incident_response")
        self.assertIsNotNone(validation)
        self.assertEqual(validation.missing_required, ())

    def test_incomplete_incident_response_contract_is_blocked(self) -> None:
        prompt = """<prompt profile="incident_response">
  <task>Write postmortem</task>
  <incident_summary>Site went down</incident_summary>
  <severity>SEV-1</severity>
  <timeline>10am to 11am</timeline>
  <impact>100 users</impact>
  <root_cause>DB crash</root_cause>
  <output_format>Doc</output_format>
</prompt>"""
        result = analyze_prompt(prompt)
        self.assertTrue(result.should_clarify, result)
        self.assertIn("template_contract", result.checks)
        self.assertIn("remediation", result.reasons[0])

    def test_complete_sql_contract_validates(self) -> None:
        prompt = """profile = "sql"
query_goal = "Get active users"
schema = "users table"
dialect = "Postgres"
filters = "created > 2023"
performance_constraints = "Index scan"
expected_output = "user_id, email"
success_criteria = "Returns 10 rows"
"""
        validation = validate_structured_prompt(prompt, "sql")
        self.assertIsNotNone(validation)
        self.assertEqual(validation.missing_required, ())

    def test_incomplete_sql_contract_is_blocked(self) -> None:
        prompt = """profile = "sql"
query_goal = "Get active users"
schema = "users table"
dialect = "Postgres"
filters = "created > 2023"
performance_constraints = "Index scan"
expected_output = "[Expected output columns/shape]"
success_criteria = "Returns 10 rows"
"""
        result = analyze_prompt(prompt)
        self.assertTrue(result.should_clarify, result)
        self.assertIn("template_contract", result.checks)
        self.assertIn("expected output", result.reasons[0])

    def test_complete_design_critique_contract_validates(self) -> None:
        prompt = """# Task
Review design
# Artifact
Figma link
# Design Goals
Look modern
# Target Users
Teens
# Evaluation Criteria
Accessibility
# Severity
High
# Deliverable Format
Bullets
"""
        validation = validate_structured_prompt(prompt, "design_critique")
        self.assertIsNotNone(validation)
        self.assertEqual(validation.missing_required, ())

    def test_incomplete_design_critique_contract_is_blocked(self) -> None:
        prompt = """<prompt profile="design_critique">
  <task>Review design</task>
  <artifact>Figma link</artifact>
  <design_goals>Look modern</design_goals>
  <target_users>Teens</target_users>
  <severity>High</severity>
  <deliverable_format>Bullets</deliverable_format>
</prompt>"""
        result = analyze_prompt(prompt)
        self.assertTrue(result.should_clarify, result)
        self.assertIn("template_contract", result.checks)
        self.assertIn("evaluation criteria", result.reasons[0])

    def test_complete_meeting_notes_contract_validates(self) -> None:
        prompt = """profile = "meeting_notes"
task = "Summarize"
meeting_purpose = "Sync"
attendees = "Alice, Bob"
source_transcript = "Alice said hi"
decisions = "We decided to launch."
action_items = "Alice to email"
output_format = "Email"
"""
        validation = validate_structured_prompt(prompt, "meeting_notes")
        self.assertIsNotNone(validation)
        self.assertEqual(validation.missing_required, ())

    def test_incomplete_meeting_notes_contract_is_blocked(self) -> None:
        prompt = """profile = "meeting_notes"
task = "Summarize"
meeting_purpose = "Sync"
attendees = "Alice, Bob"
source_transcript = "Alice said hi"
decisions = "We decided to launch."
output_format = "Email"
"""
        result = analyze_prompt(prompt)
        self.assertTrue(result.should_clarify, result)
        self.assertIn("template_contract", result.checks)
        self.assertIn("action items", result.reasons[0])

if __name__ == "__main__":
    unittest.main()
