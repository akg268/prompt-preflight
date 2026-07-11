"""Configuration loading for Prompt Preflight."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .telemetry import DEFAULT_TELEMETRY_FILE
from .token_observability import DEFAULT_MAX_OUTPUT_TOKENS, DEFAULT_RETRY_OUTPUT_TOKENS


@dataclass(frozen=True)
class Config:
    enabled: bool = True
    mode: str = "block"
    threshold: int = 45
    max_questions: int = 3
    telemetry_enabled: bool = False
    telemetry_path: Path | None = None
    telemetry_timestamp_mode: str = "exact"
    token_observability_enabled: bool = True
    token_default_max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS
    token_estimated_retry_output_tokens: int = DEFAULT_RETRY_OUTPUT_TOKENS
    checks: dict[str, str] | None = None
    severity_thresholds: dict[str, str] | None = None

    def policy_for(self, category: str) -> str:
        if self.checks is not None:
            return self.checks.get(category, "disable")
        if category == "privacy":
            return "block"
        return self.mode

    def threshold_for(self, mode: str) -> str:
        defaults = {"block": "high", "nudge": "medium"}
        if self.severity_thresholds is not None:
            return self.severity_thresholds.get(mode, defaults.get(mode, "high"))
        return defaults.get(mode, "high")


def _telemetry_path_from_raw(raw: dict[str, Any], directory: Path) -> Path:
    telemetry = raw.get("telemetry", False)
    if isinstance(telemetry, dict):
        path_value = telemetry.get("path", DEFAULT_TELEMETRY_FILE)
    else:
        path_value = DEFAULT_TELEMETRY_FILE

    path = Path(str(path_value)).expanduser()
    if not path.is_absolute():
        path = directory / path
    return path


def _telemetry_settings(
    raw: dict[str, Any], directory: Path
) -> tuple[bool, Path | None, str]:
    telemetry = raw.get("telemetry", False)
    timestamp_mode = "exact"
    if isinstance(telemetry, dict):
        enabled = bool(telemetry.get("enabled", False))
        mode_val = telemetry.get("timestamp_mode", "exact")
        if mode_val in ("exact", "date", "none"):
            timestamp_mode = mode_val
    else:
        enabled = bool(telemetry)

    if not enabled:
        return False, None, timestamp_mode

    return True, _telemetry_path_from_raw(raw, directory), timestamp_mode


def _bounded_int(value: Any, default: int, *, minimum: int = 0, maximum: int = 1_000_000) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, parsed))


def _token_observability_settings(raw: dict[str, Any]) -> tuple[bool, int, int]:
    section = raw.get("token_observability", True)
    if isinstance(section, dict):
        enabled = bool(section.get("enabled", True))
        max_output = _bounded_int(
            section.get("default_max_output_tokens"),
            DEFAULT_MAX_OUTPUT_TOKENS,
        )
        retry_output = _bounded_int(
            section.get("estimated_retry_output_tokens"),
            DEFAULT_RETRY_OUTPUT_TOKENS,
        )
        return enabled, max_output, retry_output
    return bool(section), DEFAULT_MAX_OUTPUT_TOKENS, DEFAULT_RETRY_OUTPUT_TOKENS


def resolve_telemetry_report_path(cwd: str | Path | None = None) -> Path:
    """Return the telemetry file path for reporting from project config."""

    start = Path(cwd or Path.cwd()).resolve()
    for directory in [start, *start.parents]:
        config_path = directory / ".prompt-preflight.json"
        if not config_path.is_file():
            continue
        try:
            raw: dict[str, Any] = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            break
        return _telemetry_path_from_raw(raw, directory)
    return start / DEFAULT_TELEMETRY_FILE


def load_config(cwd: str | Path | None = None) -> Config:
    start = Path(cwd or Path.cwd()).resolve()
    candidates = [start, *start.parents]
    for directory in candidates:
        path = directory / ".prompt-preflight.json"
        if path.is_file():
            try:
                raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
                telemetry_enabled, telemetry_path, telemetry_timestamp_mode = _telemetry_settings(raw, directory)
                (
                    token_observability_enabled,
                    token_default_max_output_tokens,
                    token_estimated_retry_output_tokens,
                ) = _token_observability_settings(raw)
                raw_mode = raw.get("mode")
                mode = raw_mode if raw_mode in {"block", "nudge"} else "block"

                checks = None
                raw_checks = raw.get("checks")
                if raw_checks is not None and isinstance(raw_checks, dict):
                    checks = {}
                    for category in [
                        "clarity",
                        "context",
                        "output_contract",
                        "template_contract",
                        "risk",
                        "plan_first",
                        "privacy",
                    ]:
                        if category in raw_checks:
                            val = raw_checks[category]
                            if val in ("block", "nudge", "disable", "off"):
                                checks[category] = "disable" if val == "off" else val
                            else:
                                checks[category] = (
                                    "block"
                                    if category == "privacy"
                                    else (
                                        mode
                                        if raw_mode in ("block", "nudge")
                                        else "nudge"
                                    )
                                )
                        else:
                            checks[category] = (
                                "block"
                                if category == "privacy"
                                else (
                                    mode if raw_mode in ("block", "nudge") else "nudge"
                                )
                            )

                severity_thresholds = None
                raw_sev = raw.get("severity_thresholds")
                if raw_sev is not None and isinstance(raw_sev, dict):
                    severity_thresholds = {}
                    for m in ["block", "nudge"]:
                        val = raw_sev.get(m)
                        if val in ("low", "medium", "high"):
                            severity_thresholds[m] = val
                        else:
                            severity_thresholds[m] = (
                                "high" if m == "block" else "medium"
                            )
                elif raw_sev is not None:
                    severity_thresholds = {"block": "high", "nudge": "medium"}

                return Config(
                    enabled=bool(raw.get("enabled", True)),
                    mode=mode,
                    threshold=max(0, min(100, int(raw.get("threshold", 45)))),
                    max_questions=max(1, min(5, int(raw.get("max_questions", 3)))),
                    telemetry_enabled=telemetry_enabled,
                    telemetry_path=telemetry_path,
                    telemetry_timestamp_mode=telemetry_timestamp_mode,
                    token_observability_enabled=token_observability_enabled,
                    token_default_max_output_tokens=token_default_max_output_tokens,
                    token_estimated_retry_output_tokens=token_estimated_retry_output_tokens,
                    checks=checks,
                    severity_thresholds=severity_thresholds,
                )
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                return Config()
    return Config()
