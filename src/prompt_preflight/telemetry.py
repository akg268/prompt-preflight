"""Local-only opt-in telemetry for Prompt Preflight.

Telemetry records aggregate counts and scores only. It never stores prompt text,
suggested rewrites, clarification questions, or reason strings.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
from typing import Any, Iterable

from .analyzer import Analysis
from .token_observability import (
    DEFAULT_MAX_OUTPUT_TOKENS,
    DEFAULT_RETRY_OUTPUT_TOKENS,
    token_observability_payload,
)


DEFAULT_TELEMETRY_FILE = ".prompt-preflight-telemetry.jsonl"
TELEMETRY_VERSION = 1


def telemetry_event(
    analysis: Analysis,
    *,
    host: str,
    decision: str,
    timestamp_mode: str = "exact",
    token_observability_enabled: bool = True,
    token_default_max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    token_estimated_retry_output_tokens: int = DEFAULT_RETRY_OUTPUT_TOKENS,
) -> dict[str, Any]:
    """Build a prompt-free telemetry event from an analysis result."""

    event: dict[str, Any] = {
        "version": TELEMETRY_VERSION,
        "phase": "preflight",
        "host": host,
        "decision": decision,
        "intent": analysis.intent,
        "score": analysis.score,
        "ambiguity": analysis.ambiguity,
        "impact": analysis.impact,
        "reason_count": len(analysis.reasons),
        "question_count": len(analysis.questions),
        "checks": analysis.checks,
        "bypassed": analysis.bypassed,
    }
    if token_observability_enabled:
        event["token_observability"] = token_observability_payload(
            prompt=analysis.prompt,
            decision=decision,
            max_output_tokens=token_default_max_output_tokens,
            retry_output_tokens=token_estimated_retry_output_tokens,
        )

    if timestamp_mode == "exact":
        event["timestamp"] = datetime.now(timezone.utc).isoformat()
    elif timestamp_mode == "date":
        event["timestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    return event


def postflight_telemetry_event(
    result: Any,
    *,
    host: str,
    token_observability_enabled: bool = True,
    token_default_max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    token_estimated_retry_output_tokens: int = DEFAULT_RETRY_OUTPUT_TOKENS,
) -> dict[str, Any]:
    """Build a prompt-free telemetry event from a postflight result."""

    decision = "postflight_blocked" if getattr(result, "needs_attention", False) else "postflight_allowed"
    event: dict[str, Any] = {
        "version": TELEMETRY_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "phase": "postflight",
        "host": host,
        "decision": decision,
        "severity": getattr(result, "severity", "low"),
        "finding_count": len(getattr(result, "findings", ())),
        "checks": tuple(getattr(result, "checks", ())),
    }
    if token_observability_enabled:
        event["token_observability"] = token_observability_payload(
            prompt=getattr(result, "prompt", ""),
            response=getattr(result, "response", ""),
            max_output_tokens=token_default_max_output_tokens,
            retry_output_tokens=token_estimated_retry_output_tokens,
        )
    return event


    return event


def decision_for_analysis(analysis: Analysis, *, mode: str) -> str:
    if analysis.bypassed:
        return "bypassed"
    if analysis.should_clarify:
        return "nudged" if mode == "nudge" else "blocked"
    if "conversational follow-up" in analysis.reasons:
        return "followup_accepted"
    return "allowed"


def record_event(
    path: Path, 
    event: dict[str, Any],
    *,
    max_events: int | None = None,
    max_bytes: int | None = None,
    retention_days: int | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    
    if max_events is None and max_bytes is None and retention_days is None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True, separators=(",", ":")))
            handle.write("\n")
        return

    events = read_events(path)
    events.append(event)

    if retention_days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        pruned_events = []
        for e in events:
            ts_str = e.get("timestamp")
            if not ts_str:
                pruned_events.append(e)
                continue
            
            try:
                if ts_str.endswith('Z'):
                    ts_str = ts_str[:-1] + '+00:00'
                ts = datetime.fromisoformat(ts_str)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if ts >= cutoff:
                    pruned_events.append(e)
            except (ValueError, TypeError):
                pruned_events.append(e)
        events = pruned_events

    if max_events is not None:
        if len(events) > max_events:
            events = events[-max_events:]

    lines = [json.dumps(e, sort_keys=True, separators=(",", ":")) + "\n" for e in events]

    if max_bytes is not None:
        total_size = sum(len(line.encode("utf-8")) for line in lines)
        while total_size > max_bytes and lines:
            total_size -= len(lines[0].encode("utf-8"))
            lines.pop(0)

    temp_path = path.with_suffix(".tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        for line in lines:
            handle.write(line)
    temp_path.replace(path)


def record_analysis(
    analysis: Analysis,
    *,
    host: str,
    mode: str,
    telemetry_path: Path | None,
    enabled: bool,
    max_events: int | None = None,
    max_bytes: int | None = None,
    retention_days: int | None = None,
    timestamp_mode: str = "exact",
    token_observability_enabled: bool = True,
    token_default_max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    token_estimated_retry_output_tokens: int = DEFAULT_RETRY_OUTPUT_TOKENS,
) -> None:
    if not enabled or telemetry_path is None:
        return
    record_event(
        telemetry_path,
        telemetry_event(
            analysis,
            host=host,
            decision=decision_for_analysis(analysis, mode=mode),
            timestamp_mode=timestamp_mode,
            token_observability_enabled=token_observability_enabled,
            token_default_max_output_tokens=token_default_max_output_tokens,
            token_estimated_retry_output_tokens=token_estimated_retry_output_tokens,
        ),
        max_events=max_events,
        max_bytes=max_bytes,
        retention_days=retention_days,
    )


def record_analysis_safely(
    analysis: Analysis,
    *,
    host: str,
    mode: str,
    telemetry_path: Path | None,
    enabled: bool,
    max_events: int | None = None,
    max_bytes: int | None = None,
    retention_days: int | None = None,
    timestamp_mode: str = "exact",
    token_observability_enabled: bool = True,
    token_default_max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    token_estimated_retry_output_tokens: int = DEFAULT_RETRY_OUTPUT_TOKENS,
) -> None:
    try:
        record_analysis(
            analysis,
            host=host,
            mode=mode,
            telemetry_path=telemetry_path,
            enabled=enabled,
            max_events=max_events,
            max_bytes=max_bytes,
            retention_days=retention_days,
            timestamp_mode=timestamp_mode,
            token_observability_enabled=token_observability_enabled,
            token_default_max_output_tokens=token_default_max_output_tokens,
            token_estimated_retry_output_tokens=token_estimated_retry_output_tokens,
        )
    except OSError:
        # Telemetry must never make a host hook unusable.
        return


def record_postflight(
    result: Any,
    *,
    host: str,
    telemetry_path: Path | None,
    enabled: bool,
    token_observability_enabled: bool = True,
    token_default_max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    token_estimated_retry_output_tokens: int = DEFAULT_RETRY_OUTPUT_TOKENS,
) -> None:
    """Record one postflight telemetry event."""

    if not enabled or telemetry_path is None:
        return
    record_event(
        telemetry_path,
        postflight_telemetry_event(
            result,
            host=host,
            token_observability_enabled=token_observability_enabled,
            token_default_max_output_tokens=token_default_max_output_tokens,
            token_estimated_retry_output_tokens=token_estimated_retry_output_tokens,
        ),
    )


def record_postflight_safely(
    result: Any,
    *,
    host: str,
    telemetry_path: Path | None,
    enabled: bool,
    token_observability_enabled: bool = True,
    token_default_max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    token_estimated_retry_output_tokens: int = DEFAULT_RETRY_OUTPUT_TOKENS,
) -> None:
    """Record postflight telemetry without affecting host behavior on failure."""

    try:
        record_postflight(
            result,
            host=host,
            telemetry_path=telemetry_path,
            enabled=enabled,
            token_observability_enabled=token_observability_enabled,
            token_default_max_output_tokens=token_default_max_output_tokens,
            token_estimated_retry_output_tokens=token_estimated_retry_output_tokens,
        )
    except OSError:
        return


def read_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if not path.exists():
        return events
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


def summarize_events(events: Iterable[dict[str, Any]]) -> dict[str, Any]:
    event_list = list(events)
    preflight_events = [
        event for event in event_list if str(event.get("phase", "preflight")) == "preflight"
    ]
    postflight_events = [
        event for event in event_list if str(event.get("phase", "preflight")) == "postflight"
    ]
    decisions = Counter(str(event.get("decision", "unknown")) for event in preflight_events)
    hosts = Counter(str(event.get("host", "unknown")) for event in event_list)
    intents = Counter(str(event.get("intent", "unknown")) for event in preflight_events)
    scores = [int(event.get("score", 0)) for event in preflight_events if isinstance(event.get("score"), int)]

    prompts_checked = len(preflight_events)
    blocked = decisions.get("blocked", 0)
    nudged = decisions.get("nudged", 0)
    bypassed = decisions.get("bypassed", 0)
    followups = decisions.get("followup_accepted", 0)

    blocked_by_check = Counter()
    for event in preflight_events:
        if event.get("decision") == "blocked":
            for check in event.get("checks", []):
                blocked_by_check[str(check)] += 1

    postflight_by_check = Counter()
    for event in postflight_events:
        if event.get("decision") == "postflight_blocked":
            for check in event.get("checks", []):
                postflight_by_check[str(check)] += 1

    token_events = 0
    prompt_token_total = 0
    request_token_total = 0
    response_token_total = 0
    avoided_retry_token_total = 0
    prompt_risks = Counter()
    response_risks = Counter()

    for event in event_list:
        token_payload = event.get("token_observability")
        if not isinstance(token_payload, dict):
            continue
        token_events += 1
        prompt_payload = token_payload.get("prompt")
        if isinstance(prompt_payload, dict):
            prompt_token_total += int(prompt_payload.get("visible_prompt_tokens_estimate", 0) or 0)
            request_token_total += int(prompt_payload.get("estimated_total_request_tokens", 0) or 0)
            prompt_risks[str(prompt_payload.get("token_risk", "unknown"))] += 1
        response_payload = token_payload.get("response")
        if isinstance(response_payload, dict):
            response_token_total += int(response_payload.get("response_tokens_estimate", 0) or 0)
            response_risks[str(response_payload.get("token_risk", "unknown"))] += 1
        avoided_retry_token_total += int(
            token_payload.get("estimated_avoided_retry_tokens", 0) or 0
        )

    return {
        "prompts_checked": prompts_checked,
        "prompts_blocked": blocked,
        "prompts_nudged": nudged,
        "prompts_bypassed": bypassed,
        "followup_accepted": followups,
        "prompts_allowed": decisions.get("allowed", 0),
        "clarification_opportunities": blocked + nudged,
        "estimated_avoided_retry_turns": blocked,
        "average_score": round(sum(scores) / len(scores), 2) if scores else 0,
        "blocked_by_check": dict(sorted(blocked_by_check.items())),
        "decisions": dict(sorted(decisions.items())),
        "hosts": dict(sorted(hosts.items())),
        "intents": dict(sorted(intents.items())),
        "postflight_responses_checked": len(postflight_events),
        "postflight_responses_blocked": sum(
            1 for event in postflight_events if event.get("decision") == "postflight_blocked"
        ),
        "postflight_blocked_by_check": dict(sorted(postflight_by_check.items())),
        "token_observability_events": token_events,
        "visible_prompt_tokens_estimate_total": prompt_token_total,
        "estimated_total_request_tokens": request_token_total,
        "response_tokens_estimate_total": response_token_total,
        "estimated_avoided_retry_tokens": avoided_retry_token_total,
        "prompt_token_risk": dict(sorted(prompt_risks.items())),
        "response_token_risk": dict(sorted(response_risks.items())),
        "average_visible_prompt_tokens_estimate": round(prompt_token_total / token_events, 2)
        if token_events
        else 0,
    }


def render_report(summary: dict[str, Any], *, path: Path) -> str:
    lines = [
        "Prompt Preflight telemetry report",
        f"Path: {path}",
        "",
        f"Prompts checked: {summary['prompts_checked']}",
        f"Blocked before model work: {summary['prompts_blocked']}",
    ]
    
    for check, count in summary.get("blocked_by_check", {}).items():
        lines.append(f"  - {check}: {count}")
        
    lines.extend(
        [
            f"Nudged: {summary['prompts_nudged']}",
            f"Allowed: {summary['prompts_allowed']}",
            f"Bypassed: {summary['prompts_bypassed']}",
            f"Follow-up prompts accepted: {summary['followup_accepted']}",
            "",
            f"Clarification opportunities: {summary['clarification_opportunities']}",
            f"Estimated avoided retry turns: {summary['estimated_avoided_retry_turns']}",
            f"Average clarification score: {summary['average_score']}/100",
        ]
    )

    if summary.get("postflight_responses_checked", 0):
        lines.extend(
            [
                "",
                "Postflight",
                f"Responses checked: {summary['postflight_responses_checked']}",
                f"Responses needing attention: {summary['postflight_responses_blocked']}",
            ]
        )
        for check, count in summary.get("postflight_blocked_by_check", {}).items():
            lines.append(f"  - {check}: {count}")

    if summary.get("token_observability_events", 0):
        lines.extend(
            [
                "",
                "Token observability",
                f"Events with token estimates: {summary['token_observability_events']}",
                (
                    "Visible prompt tokens estimated: "
                    f"{summary['visible_prompt_tokens_estimate_total']}"
                ),
                (
                    "Estimated request tokens reserved: "
                    f"{summary['estimated_total_request_tokens']}"
                ),
                (
                    "Estimated response tokens observed: "
                    f"{summary['response_tokens_estimate_total']}"
                ),
                (
                    "Estimated avoided retry token opportunity: "
                    f"{summary['estimated_avoided_retry_tokens']}"
                ),
            ]
        )
        if summary.get("prompt_token_risk"):
            lines.append("Prompt token risk:")
            for risk, count in summary["prompt_token_risk"].items():
                lines.append(f"  - {risk}: {count}")
        if summary.get("response_token_risk"):
            lines.append("Response token risk:")
            for risk, count in summary["response_token_risk"].items():
                lines.append(f"  - {risk}: {count}")

    lines.extend(
        [
            "",
            "Privacy: this file stores counts, decisions, hosts, intents, check categories, scores, and token estimates only.",
            "It does not store prompt text, suggested rewrites, questions, or reason strings.",
        ]
    )
    return "\n".join(lines)
