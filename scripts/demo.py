#!/usr/bin/env python3
"""Self-contained Prompt Preflight demo for screenshots, GIFs, and launch posts.

Runs three steps with no network or model calls:

1. A vague prompt that Prompt Preflight blocks.
2. A detailed prompt that passes through.
3. A short benchmark summary across the bundled 100-prompt set.

Intended for a clean recording or a quick local sanity check. Exits 0 on
success, or non-zero if the analyzer or benchmark behave unexpectedly.
"""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from prompt_preflight.analyzer import analyze_prompt  # noqa: E402
from prompt_preflight.hook import clarification_message  # noqa: E402

sys.path.insert(0, str(ROOT / "scripts"))

from benchmark_vague_prompts import VAGUE_PROMPTS  # noqa: E402


VAGUE_PROMPT = "Make the dashboard better"
DETAILED_PROMPT = (
    "Add an aria-label to the LoginButton in src/components/LoginButton.tsx "
    "so screen readers announce it as 'Log in'. Keep existing styles. "
    "Verify with the existing snapshot tests."
)


def _banner(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def _show_vague() -> bool:
    _banner("1. Vague prompt — Prompt Preflight blocks before any model turn")
    print(f'Prompt: "{VAGUE_PROMPT}"\n')
    analysis = analyze_prompt(VAGUE_PROMPT)
    if not analysis.should_clarify:
        print("Unexpected: vague demo prompt was not flagged.")
        return False
    print(clarification_message(analysis))
    return True


def _show_detailed() -> bool:
    _banner("2. Detailed prompt — passes through with no clarification")
    print(f'Prompt: "{DETAILED_PROMPT}"\n')
    analysis = analyze_prompt(DETAILED_PROMPT)
    if analysis.should_clarify:
        print("Unexpected: detailed demo prompt was flagged.")
        return False
    print(f"Clear to send (clarification score {analysis.score}/100).")
    return True


def _show_benchmark_summary() -> bool:
    _banner("3. Benchmark — 100 vague prompts, zero model calls")
    total = len(VAGUE_PROMPTS)
    blocked = sum(1 for p in VAGUE_PROMPTS if analyze_prompt(p).should_clarify)
    pct = (blocked / total) * 100 if total else 0.0
    print(f"Blocked {blocked}/{total} vague prompts ({pct:.1f}%).")
    print("Run `python3 scripts/benchmark_vague_prompts.py` for the full report.")
    return blocked >= int(total * 0.9)


def main() -> int:
    ok = _show_vague()
    ok = _show_detailed() and ok
    ok = _show_benchmark_summary() and ok
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
