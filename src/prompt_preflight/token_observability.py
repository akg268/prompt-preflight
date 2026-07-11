"""Prompt-free token observability estimates.

These helpers intentionally use local deterministic estimates instead of a
provider tokenizer. That keeps Prompt Preflight usable without API keys,
network calls, or model-specific dependencies. The estimates are not billing
truth; they are risk signals that help users understand whether a prompt or
response is likely to create a costly model turn or retry loop.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from math import ceil


DEFAULT_MAX_OUTPUT_TOKENS = 1000
DEFAULT_RETRY_OUTPUT_TOKENS = 800


@dataclass(frozen=True)
class TextTokenEstimate:
    """Stores prompt-free size estimates for one text blob."""

    character_count: int
    line_count: int
    token_estimate: int
    token_risk: str

    def to_dict(self) -> dict[str, int | str]:
        """Return a JSON-friendly estimate payload."""

        return asdict(self)


def estimate_text_tokens(text: str) -> int:
    """Estimate tokens from characters using a common 4 chars/token heuristic."""

    if not text:
        return 0
    return max(1, ceil(len(text) / 4))


def count_lines(text: str) -> int:
    """Count visible text lines without storing any line content."""

    if not text:
        return 0
    return text.count("\n") + 1


def token_risk(token_count: int) -> str:
    """Bucket token size into a simple risk level for reports."""

    if token_count >= 8000:
        return "high"
    if token_count >= 2000:
        return "medium"
    return "low"


def estimate_text(text: str) -> TextTokenEstimate:
    """Estimate the size of text without retaining the text itself."""

    token_count = estimate_text_tokens(text)
    return TextTokenEstimate(
        character_count=len(text or ""),
        line_count=count_lines(text or ""),
        token_estimate=token_count,
        token_risk=token_risk(token_count),
    )


def observe_prompt(
    prompt: str,
    *,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    retry_output_tokens: int = DEFAULT_RETRY_OUTPUT_TOKENS,
) -> dict[str, int | str]:
    """Build prompt token observability fields for preflight telemetry."""

    estimate = estimate_text(prompt)
    safe_max_output = max(0, int(max_output_tokens))
    safe_retry_output = max(0, int(retry_output_tokens))
    estimated_total_request_tokens = estimate.token_estimate + safe_max_output
    payload = {
        "prompt_character_count": estimate.character_count,
        "prompt_line_count": estimate.line_count,
        "visible_prompt_tokens_estimate": estimate.token_estimate,
        "estimated_max_output_tokens": safe_max_output,
        "estimated_total_request_tokens": estimated_total_request_tokens,
        "estimated_retry_output_tokens": safe_retry_output,
        "token_risk": token_risk(estimated_total_request_tokens),
    }
    return payload


def observe_response(response: str) -> dict[str, int | str]:
    """Build response token observability fields for postflight telemetry."""

    estimate = estimate_text(response)
    return {
        "response_character_count": estimate.character_count,
        "response_line_count": estimate.line_count,
        "response_tokens_estimate": estimate.token_estimate,
        "token_risk": estimate.token_risk,
    }


def token_observability_payload(
    *,
    prompt: str | None = None,
    response: str | None = None,
    decision: str | None = None,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    retry_output_tokens: int = DEFAULT_RETRY_OUTPUT_TOKENS,
) -> dict[str, object]:
    """Combine prompt/response estimates into one prompt-free telemetry object."""

    payload: dict[str, object] = {}
    prompt_observation: dict[str, int | str] | None = None
    if prompt is not None:
        prompt_observation = observe_prompt(
            prompt,
            max_output_tokens=max_output_tokens,
            retry_output_tokens=retry_output_tokens,
        )
        payload["prompt"] = prompt_observation
    if response is not None:
        payload["response"] = observe_response(response)
    if decision == "blocked" and prompt_observation is not None:
        payload["estimated_avoided_retry_tokens"] = (
            int(prompt_observation["visible_prompt_tokens_estimate"])
            + int(prompt_observation["estimated_retry_output_tokens"])
        )
    return payload


__all__ = [
    "DEFAULT_MAX_OUTPUT_TOKENS",
    "DEFAULT_RETRY_OUTPUT_TOKENS",
    "TextTokenEstimate",
    "count_lines",
    "estimate_text",
    "estimate_text_tokens",
    "observe_prompt",
    "observe_response",
    "token_observability_payload",
    "token_risk",
]
