"""Generic UserPromptSubmit hook adapter."""

from __future__ import annotations

import json
import sys
from typing import Any, TextIO

from .analyzer import Analysis, analyze_prompt
from .config import load_config
from .telemetry import record_analysis_safely


EXAMPLES_URL = "https://github.com/akg268/prompt-preflight/blob/main/docs/EXAMPLES.md"


def clarification_message(analysis: Analysis) -> str:
    display_prompt = analysis.redacted_prompt or analysis.prompt
    lines = [
        (
            f"Prompt Preflight paused this request "
            f"(clarification score {analysis.score}/100, severity: {analysis.severity})."
        ),
    ]
    if analysis.checks:
        lines.extend(["", "Checks triggered:", "  " + ", ".join(analysis.checks)])
    lines.extend(
        [
            "",
            "Your prompt:",
            f'  "{display_prompt}"',
            "",
            "Try asking:",
            f'  "{analysis.suggested_prompt}"',
            "",
            "Fill in the brackets by answering:",
        ]
    )
    lines.extend(f"{index}. {question}" for index, question in enumerate(analysis.questions, 1))
    lines.extend(
        [
            "",
            f"Examples and templates: {EXAMPLES_URL}",
            "",
            "To intentionally send the original prompt once, add [preflight:skip].",
        ]
    )
    return "\n".join(lines)


def process_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    prompt = payload.get("prompt")
    if not isinstance(prompt, str):
        return None

    config = load_config(payload.get("cwd"))
    if not config.enabled:
        return None

    raw_attachments = payload.get("attachments")
    attachments: list[str] = []
    if isinstance(raw_attachments, list):
        for att in raw_attachments:
            if isinstance(att, dict):
                val = att.get("name") or att.get("path")
                if isinstance(val, str):
                    attachments.append(val)
            elif isinstance(att, str):
                attachments.append(att)

    analysis = analyze_prompt(
        prompt,
        threshold=config.threshold,
        max_questions=config.max_questions,
        cwd=payload.get("cwd"),
        attachments=attachments,
    )
    record_analysis_safely(
        analysis,
        host="codex",
        mode=config.mode,
        telemetry_path=config.telemetry_path,
        enabled=config.telemetry_enabled,
    )
    if not analysis.should_clarify:
        return None

    message = clarification_message(analysis)
    if config.mode == "nudge":
        return {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": (
                    "Before doing substantive work, show the user this improved prompt example:\n"
                    f"{analysis.suggested_prompt}\n\n"
                    "Then ask these clarification questions:\n"
                    + "\n".join(f"- {q}" for q in analysis.questions)
                ),
            }
        }
    return {"decision": "block", "reason": message}


def main(stdin: TextIO = sys.stdin, stdout: TextIO = sys.stdout) -> int:
    """Read one hook payload and fail open if the payload is malformed."""
    try:
        payload = json.load(stdin)
        if not isinstance(payload, dict):
            return 0
        result = process_payload(payload)
        if result is not None:
            json.dump(result, stdout, separators=(",", ":"))
            stdout.write("\n")
    except Exception:
        # A clarity helper should never make the host unusable.
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
