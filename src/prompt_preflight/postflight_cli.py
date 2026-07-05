"""Standalone command-line entry point for postflight checks.

Kept separate from ``cli.py`` so the existing preflight CLI and its tests are
untouched. Reads the agent response from a positional argument or stdin.

Exit codes follow the repo convention: ``0`` when the response is clean (or only
non-blocking findings remain), ``2`` when the result needs attention.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import TextIO

from .postflight import analyze_postflight
from .postflight_config import load_postflight_config


def _parse_changed_files(value: str | None) -> list[str] | None:
    """Distinguish "no metadata" (None) from "supplied but empty" ([])."""

    if value is None:
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run deterministic postflight quality checks on an agent response.",
    )
    parser.add_argument(
        "response",
        nargs="?",
        help="The agent response to check. If omitted, it is read from stdin.",
    )
    parser.add_argument("--prompt", default="", help="The original user prompt for context.")
    parser.add_argument(
        "--changed-files",
        default=None,
        help=(
            "Comma-separated changed file paths (names only). Pass an empty "
            "string to assert nothing changed; omit when metadata is unavailable."
        ),
    )
    parser.add_argument("--cwd", default=None, help="Directory used to locate .prompt-preflight.json.")
    parser.add_argument("--json", action="store_true", help="Emit the full result as JSON.")
    return parser


def _render_text(result) -> str:
    if not result.findings:
        return "Postflight: no issues detected."
    header = (
        "Postflight found issues "
        f"(severity: {result.severity}, "
        f"{'needs attention' if result.needs_attention else 'advisory only'})."
    )
    lines = [header, ""]
    for finding in result.findings:
        tag = f"[{finding.check}/{finding.severity}"
        tag += "/info]" if finding.informational else "]"
        lines.append(f"{tag} {finding.reason}")
        lines.append(f"    fix: {finding.suggestion}")
    return "\n".join(lines)


def main(
    argv: list[str] | None = None,
    stdin: TextIO = sys.stdin,
    stdout: TextIO = sys.stdout,
) -> int:
    args = build_parser().parse_args(argv)

    response = args.response
    if response is None:
        response = stdin.read()

    config = load_postflight_config(args.cwd)
    result = analyze_postflight(
        args.prompt,
        response,
        changed_files=_parse_changed_files(args.changed_files),
        config=config,
    )

    if args.json:
        json.dump(result.to_dict(), stdout, indent=2)
        stdout.write("\n")
    else:
        stdout.write(_render_text(result) + "\n")

    return 2 if result.needs_attention else 0


if __name__ == "__main__":
    raise SystemExit(main())
