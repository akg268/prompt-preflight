"""Configuration loading for Prompt Preflight."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .telemetry import DEFAULT_TELEMETRY_FILE


@dataclass(frozen=True)
class Config:
    enabled: bool = True
    mode: str = "block"
    threshold: int = 45
    max_questions: int = 3
    telemetry_enabled: bool = False
    telemetry_path: Path | None = None


def _telemetry_settings(raw: dict[str, Any], directory: Path) -> tuple[bool, Path | None]:
    telemetry = raw.get("telemetry", False)
    if isinstance(telemetry, dict):
        enabled = bool(telemetry.get("enabled", False))
        path_value = telemetry.get("path", DEFAULT_TELEMETRY_FILE)
    else:
        enabled = bool(telemetry)
        path_value = DEFAULT_TELEMETRY_FILE

    if not enabled:
        return False, None

    path = Path(str(path_value)).expanduser()
    if not path.is_absolute():
        path = directory / path
    return True, path


def load_config(cwd: str | Path | None = None) -> Config:
    start = Path(cwd or Path.cwd()).resolve()
    candidates = [start, *start.parents]
    for directory in candidates:
        path = directory / ".prompt-preflight.json"
        if path.is_file():
            try:
                raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
                telemetry_enabled, telemetry_path = _telemetry_settings(raw, directory)
                return Config(
                    enabled=bool(raw.get("enabled", True)),
                    mode=raw.get("mode", "block") if raw.get("mode") in {"block", "nudge"} else "block",
                    threshold=max(0, min(100, int(raw.get("threshold", 45)))),
                    max_questions=max(1, min(5, int(raw.get("max_questions", 3)))),
                    telemetry_enabled=telemetry_enabled,
                    telemetry_path=telemetry_path,
                )
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                return Config()
    return Config()
