"""Kiro UserPromptSubmit hook adapter."""

from __future__ import annotations

import json
import sys
from typing import Any, TextIO

from .analyzer import analyze_prompt
from .config import load_config
from .hook import clarification_message
from .telemetry import record_analysis_safely


def nudge_message(analysis_prompt: str, suggested_prompt: str, questions: tuple[str, ...]) -> str:
    return (
        "Prompt Preflight detected consequential ambiguity in the submitted prompt.\n"
        "Before doing substantive work, show the user this improved prompt example:\n"
        f"{suggested_prompt}\n\n"
        "Then ask these clarification questions:\n"
        + "\n".join(f"- {question}" for question in questions)
        + "\n\n"
        f"Original prompt: {analysis_prompt}"
    )


def process_payload(payload: dict[str, Any]) -> tuple[int, str, str]:
    """Return ``(exit_code, stdout, stderr)`` for one Kiro hook payload."""

    prompt = payload.get("prompt")
    if not isinstance(prompt, str):
        return 0, "", ""

    config = load_config(payload.get("cwd"))
    if not config.enabled:
        return 0, "", ""

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
        config=config,
        threshold=config.threshold,
        max_questions=config.max_questions,
        cwd=payload.get("cwd"),
        attachments=attachments,
    )
    record_analysis_safely(
        analysis,
        host="kiro",
        mode=config.mode,
        telemetry_path=config.telemetry_path,
        enabled=config.telemetry_enabled,
        timestamp_mode=config.telemetry_timestamp_mode,
        token_observability_enabled=config.token_observability_enabled,
        token_default_max_output_tokens=config.token_default_max_output_tokens,
        token_estimated_retry_output_tokens=config.token_estimated_retry_output_tokens,
    )
    if not analysis.should_clarify:
        return 0, "", ""

    if analysis.decision == "nudge":
        return (
            0,
            nudge_message(
                analysis.redacted_prompt or analysis.prompt,
                analysis.suggested_prompt or prompt,
                analysis.questions,
            ),
            "",
        )

    return 2, "", clarification_message(analysis)


def main(
    stdin: TextIO = sys.stdin,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    """Read one Kiro hook payload and fail open on malformed input."""

    try:
        payload = json.load(stdin)
        if not isinstance(payload, dict):
            return 0
        code, stdout_text, stderr_text = process_payload(payload)
        if stdout_text:
            stdout.write(stdout_text)
            stdout.write("\n")
        if stderr_text:
            stderr.write(stderr_text)
            stderr.write("\n")
        return code
    except Exception:
        # A clarity helper should never make Kiro unusable.
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
