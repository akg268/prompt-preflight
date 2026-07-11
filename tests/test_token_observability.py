from __future__ import annotations

import unittest

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from prompt_preflight.token_observability import (  # noqa: E402
    observe_prompt,
    observe_response,
    token_observability_payload,
)


class TokenObservabilityTests(unittest.TestCase):
    def test_prompt_observation_counts_without_text(self) -> None:
        prompt = "Create a car image"
        payload = observe_prompt(prompt, max_output_tokens=500, retry_output_tokens=300)

        self.assertEqual(payload["prompt_character_count"], len(prompt))
        self.assertGreater(payload["visible_prompt_tokens_estimate"], 0)
        self.assertEqual(payload["estimated_max_output_tokens"], 500)
        self.assertEqual(payload["estimated_retry_output_tokens"], 300)
        self.assertNotIn("Create", str(payload))
        self.assertNotIn("car", str(payload))

    def test_response_observation_counts_without_text(self) -> None:
        response = "Here is the answer in prose."
        payload = observe_response(response)

        self.assertEqual(payload["response_character_count"], len(response))
        self.assertGreater(payload["response_tokens_estimate"], 0)
        self.assertNotIn("answer", str(payload))

    def test_blocked_prompt_payload_estimates_avoided_retry_tokens(self) -> None:
        payload = token_observability_payload(
            prompt="Fix it",
            decision="blocked",
            max_output_tokens=100,
            retry_output_tokens=50,
        )

        self.assertIn("prompt", payload)
        self.assertGreater(payload["estimated_avoided_retry_tokens"], 50)


if __name__ == "__main__":
    unittest.main()
