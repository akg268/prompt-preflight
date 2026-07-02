"""Claude Code UserPromptSubmit hook adapter."""

from __future__ import annotations

import json
import sys
from typing import Any, TextIO

from .analyzer import analyze_prompt
from .config import load_config
from .hook import clarification_message
from .telemetry import record_analysis_safely


def process_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Return Claude Code hook output for one UserPromptSubmit payload.

    Claude Code sends the submitted prompt on stdin before the model sees it.
    When a prompt needs clarification, this adapter returns a top-level block
    decision. In nudge mode it lets the prompt continue while injecting context
    that tells Claude to clarify before doing substantive work.
    """

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
        host="claude-code",
        mode=config.mode,
        telemetry_path=config.telemetry_path,
        enabled=config.telemetry_enabled,
    )
    if not analysis.should_clarify:
        return None

    if config.mode == "nudge":
        return {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": (
                    "Prompt Preflight detected consequential ambiguity. "
                    "Before doing substantive work, show the user this improved prompt example:\n"
                    f"{analysis.suggested_prompt}\n\n"
                    "Then ask these clarification questions:\n"
                    + "\n".join(f"- {question}" for question in analysis.questions)
                ),
            }
        }

    return {
        "decision": "block",
        "reason": clarification_message(analysis),
        "suppressOriginalPrompt": True,
    }


def main(stdin: TextIO = sys.stdin, stdout: TextIO = sys.stdout) -> int:
    """Read one Claude hook payload and fail open on malformed input."""

    try:
        payload = json.load(stdin)
        if not isinstance(payload, dict):
            return 0
        result = process_payload(payload)
        if result is not None:
            json.dump(result, stdout, separators=(",", ":"))
            stdout.write("\n")
    except Exception:
        # A clarity helper should never make Claude Code unusable.
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
