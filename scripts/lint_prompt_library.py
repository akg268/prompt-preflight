#!/usr/bin/env python3
"""Lint opted-in Markdown prompt library files with Prompt Preflight.

Deterministic and local: no network or model calls. Files must include the
opt-in marker ``prompt-preflight: check`` near the top (Markdown form:
``<!-- prompt-preflight: check -->``). Files without the marker are skipped.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from prompt_preflight.analyzer import analyze_prompt  # noqa: E402


MARKER = "prompt-preflight: check"
MARKER_SCAN_LIMIT = 800
HTML_MARKER_RE = re.compile(r"<!--\s*prompt-preflight:\s*check\s*-->", re.IGNORECASE)
HASH_MARKER_RE = re.compile(r"(?m)^\s*#\s*prompt-preflight:\s*check\s*$", re.IGNORECASE)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Lint Markdown prompt files that opt into Prompt Preflight checks."
    )
    parser.add_argument(
        "--cwd",
        default=".",
        help="Directory to search (default: current working directory).",
    )
    parser.add_argument(
        "--include",
        action="append",
        default=[],
        metavar="GLOB",
        help='Glob relative to --cwd (repeatable). Example: "docs/prompts/**/*.md"',
    )
    return parser.parse_args(argv)


def _has_opt_in_marker(text: str) -> bool:
    """Require a real opt-in comment near the top (not prose that merely names it)."""
    head = text[:MARKER_SCAN_LIMIT]
    return bool(HTML_MARKER_RE.search(head) or HASH_MARKER_RE.search(head))


def _strip_opt_in_marker(text: str) -> str:
    stripped = HTML_MARKER_RE.sub("", text, count=1)
    stripped = HASH_MARKER_RE.sub("", stripped, count=1)
    return stripped.strip()


def _iter_matching_files(cwd: Path, includes: Iterable[str]) -> list[Path]:
    patterns = list(includes) or ["docs/prompts/**/*.md"]
    found: set[Path] = set()
    for pattern in patterns:
        for path in sorted(cwd.glob(pattern)):
            if path.is_file() and path.suffix.lower() == ".md":
                found.add(path.resolve())
    return sorted(found, key=lambda p: str(p.relative_to(cwd)).lower())


def _rel(path: Path, cwd: Path) -> str:
    try:
        return str(path.relative_to(cwd))
    except ValueError:
        return str(path)


def lint_prompt_library(cwd: Path, includes: list[str]) -> int:
    """Lint matching Markdown files. Return process exit code (0 = all pass)."""
    files = _iter_matching_files(cwd, includes)
    if not files:
        print(f"No Markdown files matched under {cwd} for includes={includes or ['docs/prompts/**/*.md']}")
        return 0

    checked = 0
    failed = 0
    skipped = 0

    print("Prompt Preflight prompt-library lint")
    print(f"cwd: {cwd}")
    print(f"Opt-in marker required: {MARKER}")
    print()

    for path in files:
        rel = _rel(path, cwd)
        text = path.read_text(encoding="utf-8")
        if not _has_opt_in_marker(text):
            skipped += 1
            print(f"SKIP {rel} — Opt-in marker required: {MARKER}")
            continue

        prompt = _strip_opt_in_marker(text)
        analysis = analyze_prompt(prompt)
        checked += 1
        reasons = "; ".join(analysis.reasons) if analysis.reasons else "(none)"
        if analysis.should_clarify:
            failed += 1
            print(
                f"FAIL {rel} — should_clarify=true score={analysis.score} "
                f"intent={analysis.intent} severity={analysis.severity} reasons={reasons}"
            )
        else:
            print(
                f"PASS {rel} — should_clarify=false score={analysis.score} "
                f"intent={analysis.intent} reasons={reasons}"
            )

    print()
    print(f"Files matched: {len(files)}")
    print(f"Files checked: {checked}")
    print(f"Files skipped: {skipped}")
    print(f"Needs clarification: {failed}")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    cwd = Path(args.cwd).expanduser().resolve()
    if not cwd.is_dir():
        print(f"error: --cwd is not a directory: {cwd}", file=sys.stderr)
        return 2
    return lint_prompt_library(cwd, list(args.include))


if __name__ == "__main__":
    raise SystemExit(main())
