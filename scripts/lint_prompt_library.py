#!/usr/bin/env python3
"""Run Prompt Preflight against a prompt library for CI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from prompt_preflight.prompt_lint import (
    DEFAULT_LINT_PATTERNS,
    lint_prompt_library,
    render_lint_report,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the prompt-library lint CLI parser."""

    parser = argparse.ArgumentParser(
        prog="lint-prompt-library",
        description="Check checked-in prompt files before they reach AI agents.",
    )
    parser.add_argument("--cwd", type=Path, default=Path.cwd(), help="Project root to scan")
    parser.add_argument(
        "--include",
        action="append",
        dest="patterns",
        help="Glob to include. Repeat for multiple globs. Defaults to Markdown/XML/TOML files.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Check all matching files instead of requiring the prompt-preflight: check marker.",
    )
    parser.add_argument("--json", action="store_true", dest="as_json", help="Emit JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run prompt-library lint and return a CI-friendly exit code."""

    args = build_parser().parse_args(argv)
    summary = lint_prompt_library(
        args.cwd,
        patterns=tuple(args.patterns) if args.patterns else DEFAULT_LINT_PATTERNS,
        require_marker=not args.all,
    )

    if args.as_json:
        print(json.dumps(summary.to_dict(), indent=2))
    else:
        print(render_lint_report(summary))
    return 2 if not summary.passed else 0


if __name__ == "__main__":
    raise SystemExit(main())
