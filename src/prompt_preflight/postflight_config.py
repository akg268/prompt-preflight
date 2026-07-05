"""Configuration for postflight checks.

Postflight owns its own optional ``postflight`` block inside
``.prompt-preflight.json`` rather than coupling to preflight's ``Config``. This
keeps the analysis core (``postflight.py``) free of any file I/O, mirroring how
the repository keeps ``load_config`` in ``config.py`` and out of ``analyzer.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path


POSTFLIGHT_CHECKS: tuple[str, ...] = (
    "output_format",
    "tests_present",
    "file_change_claim",
    "constraint_adherence",
    "placeholders",
    "citations",
    "privacy",
)

# Strict-by-default so the CLI exit code is a meaningful gate. Users can soften
# any check to "nudge" (surfaced but non-blocking) or turn it "off".
DEFAULT_POLICY: dict[str, str] = {check: "block" for check in POSTFLIGHT_CHECKS}

VALID_POLICIES = frozenset({"block", "nudge", "off", "disable"})


@dataclass(frozen=True)
class PostflightConfig:
    enabled: bool = True
    policies: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_POLICY))

    def policy_for(self, check: str) -> str:
        return self.policies.get(check, DEFAULT_POLICY.get(check, "block"))


def _find_config_file(cwd: str | Path | None) -> Path | None:
    if cwd is None:
        return None
    current = Path(cwd).expanduser().resolve()
    for directory in (current, *current.parents):
        candidate = directory / ".prompt-preflight.json"
        if candidate.is_file():
            return candidate
    return None


def load_postflight_config(cwd: str | Path | None = None) -> PostflightConfig:
    """Load the optional ``postflight`` block from ``.prompt-preflight.json``.

    Falls back to strict defaults (every check blocks) when no config is found.
    A top-level ``"enabled": false`` disables postflight too, matching how the
    global switch disables preflight.
    """

    config_file = _find_config_file(cwd)
    if config_file is None:
        return PostflightConfig()
    try:
        raw = json.loads(config_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return PostflightConfig()
    if not isinstance(raw, dict):
        return PostflightConfig()

    global_enabled = raw.get("enabled", True)
    section = raw.get("postflight", {})
    if not isinstance(section, dict):
        section = {}

    enabled = bool(global_enabled) and bool(section.get("enabled", True))
    policies = dict(DEFAULT_POLICY)
    raw_checks = section.get("checks", {})
    if isinstance(raw_checks, dict):
        for check, policy in raw_checks.items():
            if check in DEFAULT_POLICY and isinstance(policy, str) and policy in VALID_POLICIES:
                policies[check] = policy
    return PostflightConfig(enabled=enabled, policies=policies)
