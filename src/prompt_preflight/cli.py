"""Command-line interface for inspecting prompts outside Codex."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .analyzer import analyze_prompt
from .config import resolve_telemetry_report_path
from .hook import clarification_message
from .templates import SUPPORTED_TEMPLATE_FORMATS, render_template, template_profile_names
from .telemetry import (
    DEFAULT_TELEMETRY_FILE,
    read_events,
    record_analysis_safely,
    render_report,
    summarize_events,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="prompt-preflight",
        description="Check a prompt locally before spending a model turn.",
    )
    parser.add_argument("prompt", nargs="*", help="Prompt text; reads stdin when omitted")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Emit structured JSON")
    parser.add_argument("--threshold", type=int, default=45, help="Clarification threshold (default: 45)")
    parser.add_argument("--max-questions", type=int, default=3, help="Maximum questions to ask")
    parser.add_argument(
        "--template",
        metavar="PROFILE",
        help=(
            "Print a structured prompt template and exit. Profiles: "
            + ", ".join(template_profile_names())
        ),
    )
    parser.add_argument(
        "--template-format",
        choices=SUPPORTED_TEMPLATE_FORMATS,
        default="md",
        help="Template format for --template (default: md)",
    )
    parser.add_argument(
        "--record-telemetry",
        action="store_true",
        help="Record prompt-free local telemetry for this CLI check",
    )
    parser.add_argument(
        "--telemetry-path",
        type=Path,
        help=f"Telemetry JSONL path (default: {DEFAULT_TELEMETRY_FILE})",
    )
    parser.add_argument(
        "--cwd",
        type=Path,
        help="Project directory for config lookup (telemetry report)",
    )
    parser.add_argument(
        "--telemetry-report",
        nargs="?",
        const="",
        metavar="PATH",
        help="Print a local telemetry report and exit; discovers path from .prompt-preflight.json when omitted",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.template:
        try:
            print(render_template(args.template, args.template_format))
        except ValueError as error:
            parser.error(str(error))
        return 0

    if args.telemetry_report is not None:
        if args.telemetry_report:
            report_path = Path(args.telemetry_report)
        else:
            report_path = resolve_telemetry_report_path(args.cwd)
        summary = summarize_events(read_events(report_path))
        if args.as_json:
            print(json.dumps(summary, indent=2))
        else:
            print(render_report(summary, path=report_path))
        return 0

    prompt = " ".join(args.prompt).strip() if args.prompt else sys.stdin.read().strip()
    # Load config to support per-check policies in CLI
    from .config import load_config
    config = load_config(args.cwd or Path.cwd())
    
    analysis = analyze_prompt(
        prompt,
        config=config,
        threshold=max(0, min(100, args.threshold)),
        max_questions=max(1, min(5, args.max_questions)),
        cwd=args.cwd or Path.cwd(),
    )
    if args.record_telemetry or args.telemetry_path is not None:
        record_analysis_safely(
            analysis,
            host="cli",
            mode="block",
            telemetry_path=args.telemetry_path or config.telemetry_path or Path(DEFAULT_TELEMETRY_FILE),
            enabled=True,
            timestamp_mode=config.telemetry_timestamp_mode,
            token_observability_enabled=config.token_observability_enabled,
            token_default_max_output_tokens=config.token_default_max_output_tokens,
            token_estimated_retry_output_tokens=config.token_estimated_retry_output_tokens,
        )
    if args.as_json:
        print(json.dumps(analysis.to_dict(), indent=2))
    elif analysis.should_clarify:
        print(clarification_message(analysis))
    else:
        print(f"Clear to send (clarification score {analysis.score}/100).")
    return 2 if analysis.should_clarify else 0


if __name__ == "__main__":
    raise SystemExit(main())
