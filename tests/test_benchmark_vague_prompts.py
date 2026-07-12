from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from prompt_preflight.vague_prompt_library import load_vague_prompts, parse_vague_prompts


def _load_benchmark_module():
    module_path = ROOT / "scripts" / "benchmark_vague_prompts.py"
    spec = importlib.util.spec_from_file_location("benchmark_vague_prompts", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BenchmarkVaguePromptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.benchmark = _load_benchmark_module()

    def test_benchmark_has_214_unique_prompts(self) -> None:
        prompts = self.benchmark.VAGUE_PROMPTS
        self.assertEqual(len(prompts), 214)
        self.assertEqual(len(set(prompts)), 214)

    def test_benchmark_uses_shared_vague_prompt_library(self) -> None:
        self.assertEqual(self.benchmark.VAGUE_PROMPTS, load_vague_prompts())

    def test_prompt_library_parser_ignores_comments_and_rejects_duplicates(self) -> None:
        self.assertEqual(
            parse_vague_prompts("# Software\nFix it\n\n# Writing\nWrite a blog post\n"),
            ("Fix it", "Write a blog post"),
        )
        with self.assertRaises(ValueError):
            parse_vague_prompts("Fix it\nFix it\n")

    def test_benchmark_covers_content_domains(self) -> None:
        summary = self.benchmark.run_benchmark()
        for intent in ("writing", "research", "data_analysis", "presentation"):
            with self.subTest(intent=intent):
                self.assertIn(intent, summary["by_intent"])
                self.assertGreaterEqual(summary["by_intent"][intent]["total"], 8)

    def test_vague_prompt_benchmark_catches_at_least_90_percent(self) -> None:
        summary = self.benchmark.run_benchmark()
        self.assertGreaterEqual(
            summary["block_rate"],
            0.90,
            f"Missed prompts: {[row['prompt'] for row in summary['missed']]}",
        )


if __name__ == "__main__":
    unittest.main()
