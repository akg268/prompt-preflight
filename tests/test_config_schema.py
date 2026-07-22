from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

SCHEMA_PATH = ROOT / "schemas" / "prompt-preflight.schema.json"
EXAMPLE_PATH = ROOT / ".prompt-preflight.example.json"

try:
    import jsonschema
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover - exercised when jsonschema is missing
    jsonschema = None
    Draft202012Validator = None


@unittest.skipUnless(jsonschema is not None, "jsonschema is required (pip install 'prompt-preflight[dev]' or jsonschema)")
class ConfigSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.validator = Draft202012Validator(cls.schema)

    def _assert_valid(self, instance: object) -> None:
        errors = sorted(self.validator.iter_errors(instance), key=lambda e: e.path)
        self.assertEqual(errors, [], msg="; ".join(e.message for e in errors))

    def _assert_invalid(self, instance: object) -> None:
        errors = list(self.validator.iter_errors(instance))
        self.assertTrue(errors, msg="expected schema validation to fail")

    def test_example_config_validates(self) -> None:
        example = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
        self._assert_valid(example)

    def test_empty_object_validates(self) -> None:
        self._assert_valid({})

    def test_profiles_optional_overlay_validates(self) -> None:
        self._assert_valid(
            {
                "enabled": True,
                "mode": "block",
                "profiles": [
                    {
                        "match": "docs/prompts/research/**",
                        "intent": "research",
                        "mode": "block",
                        "checks": {"output_contract": "block"},
                        "max_questions": 3,
                    }
                ],
            }
        )

    def test_bad_check_policy_value_fails(self) -> None:
        self._assert_invalid({"checks": {"clarity": "warn"}})

    def test_bad_mode_fails(self) -> None:
        self._assert_invalid({"mode": "strict"})

    def test_threshold_out_of_range_fails(self) -> None:
        self._assert_invalid({"threshold": 101})

    def test_unknown_top_level_key_fails(self) -> None:
        self._assert_invalid({"not_a_real_key": True})

    def test_telemetry_boolean_shorthand_validates(self) -> None:
        self._assert_valid({"telemetry": False})

    def test_bad_timestamp_mode_fails(self) -> None:
        self._assert_invalid({"telemetry": {"timestamp_mode": "iso8601"}})


if __name__ == "__main__":
    unittest.main()
