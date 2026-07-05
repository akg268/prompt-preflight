"""Claude Code Stop-hook adapter for postflight checks.

Claude Code fires a ``Stop`` hook when the main agent finishes responding. This
adapter reads the transcript, extracts the last assistant message, runs the
deterministic postflight checks, and -- when a blocking issue is found -- asks
the agent to keep going and fix it.

NOTE: The exact Stop-hook payload and output contract is a Claude Code platform
detail. This adapter follows the documented shape (a transcript path on stdin,
and a ``decision: "block"`` + ``reason`` to continue the agent), but the fields
should be confirmed against current Claude Code hooks documentation. Like every
other adapter in this package, it fails open: any error returns exit 0 so the
hook can never make Claude Code unusable.

``changed_files`` is not generally available from a Stop payload, so the
file-change check degrades to an informational, non-blocking finding here.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any, TextIO

from .postflight import analyze_postflight
from .postflight_config import load_postflight_config


def _message_text(content: Any) -> str:
    """Flatten a transcript message's ``content`` to plain text."""

    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and isinstance(block.get("text"), str):
                parts.append(block["text"])
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return ""


def _read_transcript(path: str) -> tuple[str, str]:
    """Return ``(last_user_prompt, last_assistant_response)`` from a JSONL transcript."""

    last_user = ""
    last_assistant = ""
    transcript_path = Path(path).expanduser()
    if not transcript_path.is_file():
        return last_user, last_assistant
    for line in transcript_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict):
            continue
        message = record.get("message") if isinstance(record.get("message"), dict) else record
        role = message.get("role")
        text = _message_text(message.get("content"))
        if role == "user" and text:
            last_user = text
        elif role == "assistant" and text:
            last_assistant = text
    return last_user, last_assistant


def process_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Return Stop-hook output for one payload, or ``None`` to allow the stop."""

    transcript_path = payload.get("transcript_path")
    if not isinstance(transcript_path, str):
        return None

    # Avoid an infinite loop if the agent is already responding to our block.
    if payload.get("stop_hook_active"):
        return None

    config = load_postflight_config(payload.get("cwd"))
    if not config.enabled:
        return None

    prompt, response = _read_transcript(transcript_path)
    if not response.strip():
        return None

    result = analyze_postflight(prompt, response, changed_files=None, config=config)
    if not result.needs_attention:
        return None

    reason_lines = [
        "Prompt Preflight postflight checks flagged this response before it was finalized:",
        "",
    ]
    for finding in result.findings:
        if finding.informational:
            continue
        reason_lines.append(f"- [{finding.check}] {finding.reason} -> {finding.suggestion}")
    reason_lines.append("")
    reason_lines.append("Please address these points and update the response.")

    return {"decision": "block", "reason": "\n".join(reason_lines)}


def main(stdin: TextIO = sys.stdin, stdout: TextIO = sys.stdout) -> int:
    """Read one Stop-hook payload and fail open on malformed input."""

    try:
        payload = json.load(stdin)
        if not isinstance(payload, dict):
            return 0
        result = process_payload(payload)
        if result is not None:
            json.dump(result, stdout, separators=(",", ":"))
            stdout.write("\n")
    except Exception:
        # A quality helper should never make Claude Code unusable.
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
