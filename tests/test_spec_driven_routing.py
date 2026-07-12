import unittest

from prompt_preflight.analyzer import analyze_prompt


class TestSpecDrivenRouting(unittest.TestCase):
    def test_blocking_cases(self) -> None:
        """Assert broad feature build prompts are blocked/nudged and routed to spec templates."""
        prompts = [
            "build auth",
            "create billing",
            "add a dashboard",
            "make onboarding",
            "implement notifications",
            "set up user management"
        ]
        for prompt in prompts:
            with self.subTest(prompt=prompt):
                analysis = analyze_prompt(prompt)
                self.assertTrue(analysis.should_clarify)
                self.assertIn("plan_first", analysis.checks)
                self.assertIn("broad feature build should start with a spec", analysis.reasons)
                
                # Should recommend a spec template
                self.assertIsNotNone(analysis.suggested_prompt)
                
                # Depending on the prompt, it could be feature_spec by default
                self.assertTrue(
                    any(spec in analysis.suggested_prompt for spec in ("feature_spec", "requirements_spec", "technical_design_spec")),
                    f"Expected a spec template recommendation, got: {analysis.suggested_prompt}"
                )

    def test_routing_cases(self) -> None:
        """Assert architecture/requirements signals route to specific spec templates."""
        # Architecture-flavored
        analysis_arch = analyze_prompt("design a scalable notifications system")
        self.assertTrue(analysis_arch.should_clarify)
        self.assertIn("plan_first", analysis_arch.checks)
        self.assertIn("technical_design_spec", analysis_arch.suggested_prompt)
        
        # Requirements-flavored
        analysis_req = analyze_prompt("gather requirements and build the billing feature")
        self.assertTrue(analysis_req.should_clarify)
        self.assertIn("plan_first", analysis_req.checks)
        self.assertIn("requirements_spec", analysis_req.suggested_prompt)

    def test_passing_cases(self) -> None:
        """Assert specific prompts are NOT routed to spec templates and pass normally."""
        prompts = [
            "add a logout button to Navbar.tsx",
            "create a POST /api/users endpoint that validates email and returns 201 with the created id",
            "implement a debounce(fn, wait=300) utility in utils/debounce.ts",
            "add a unit test for formatCurrency in format.test.ts",
            "fix the off-by-one in pagination.ts line 42"
        ]
        for prompt in prompts:
            with self.subTest(prompt=prompt):
                analysis = analyze_prompt(prompt)
                # Specificity checks should allow this to pass without blocking for spec template
                self.assertFalse(
                    analysis.should_clarify and "plan_first" in analysis.checks and "broad feature build should start with a spec" in analysis.reasons,
                    f"Prompt '{prompt}' should not be flagged as a broad feature build."
                )


if __name__ == "__main__":
    unittest.main()
