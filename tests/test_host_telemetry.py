"""Telemetry integration tests for the Claude Code and Kiro hooks.

Addresses prompt-preflight issue #22:
  * Claude Code and Kiro hooks write prompt-free telemetry when enabled.
  * Telemetry failures do not change hook behavior (fail-open).

The hooks are plain scripts that read a JSON event on stdin, so these tests
run them exactly the way each host does: pipe JSON in, set cwd to a throwaway
project that has telemetry turned on, then read the telemetry file back.

No Claude Code subscription and no Kiro IDE are needed. Everything is local
Python + subprocess.

Run from the repo root:
    python3 -m unittest discover -s tests -v
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# tests/ lives directly under the repo root; scripts/ is its sibling.
REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"

CLAUDE_HOOK = SCRIPTS / "prompt_preflight_claude_hook.py"
KIRO_HOOK = SCRIPTS / "prompt_preflight_kiro_hook.py"

# Vague prompts Prompt Preflight should flag, each paired with a distinctive
# word we later prove never leaks into the telemetry file. The words are chosen
# so they cannot collide with any field the telemetry file actually stores
# (host, decision, intent, scores, counts, timestamp).
VAGUE_PROMPTS = (
    ("Make the dashboard better", "dashboard"),
    ("Create a car image", "car"),
    ("Rewrite the whole project", "whole"),
)

TELEMETRY_FILE = ".prompt-preflight-telemetry.jsonl"


def write_config(project_dir, *, telemetry_enabled, telemetry_path=TELEMETRY_FILE):
    """Write a .prompt-preflight.json into the throwaway project."""
    config = {
        "enabled": True,
        "mode": "block",
        "telemetry": {
            "enabled": telemetry_enabled,
            "path": telemetry_path,
        },
    }
    (Path(project_dir) / ".prompt-preflight.json").write_text(
        json.dumps(config), encoding="utf-8"
    )


def run_hook(hook_path, project_dir, payload):
    """Run a hook the way its host does: JSON on stdin, cwd = the project."""
    return subprocess.run(
        [sys.executable, str(hook_path)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=project_dir,
    )


def read_telemetry(project_dir, telemetry_path=TELEMETRY_FILE):
    """Return (raw_text, [parsed_events]) for the telemetry file, if any."""
    path = Path(project_dir) / telemetry_path
    if not path.exists():
        return "", []
    raw = path.read_text(encoding="utf-8")
    events = [json.loads(line) for line in raw.splitlines() if line.strip()]
    return raw, events


class _HookTelemetryMixin:
    """Shared tests; concrete classes set HOST / HOOK / EVENT_NAME below."""

    HOST = None
    HOOK = None
    EVENT_NAME = "UserPromptSubmit"

    def _payload(self, project_dir, prompt):
        return {
            "hook_event_name": self.EVENT_NAME,
            "cwd": project_dir,
            "prompt": prompt,
        }

    def setUp(self):
        if self.HOOK is None or not self.HOOK.exists():
            self.skipTest(f"hook script not found: {self.HOOK}")

    def test_writes_prompt_free_telemetry_when_enabled(self):
        for prompt, distinctive_word in VAGUE_PROMPTS:
            with self.subTest(prompt=prompt):
                with tempfile.TemporaryDirectory() as project_dir:
                    write_config(project_dir, telemetry_enabled=True)
                    run_hook(self.HOOK, project_dir, self._payload(project_dir, prompt))

                    raw, events = read_telemetry(project_dir)

                    # An event was recorded, tagged with this host.
                    self.assertTrue(events, "telemetry should record at least one event")
                    self.assertEqual(events[-1].get("host"), self.HOST)

                    # Neither the prompt nor its distinctive word reached telemetry.
                    self.assertNotIn(prompt, raw)
                    self.assertNotIn(distinctive_word, raw.lower())

    def test_telemetry_failure_does_not_change_behavior(self):
        for prompt, _ in VAGUE_PROMPTS:
            with self.subTest(prompt=prompt):
                with tempfile.TemporaryDirectory() as project_dir:
                    payload = self._payload(project_dir, prompt)

                    # Baseline: telemetry disabled.
                    write_config(project_dir, telemetry_enabled=False)
                    baseline = run_hook(self.HOOK, project_dir, payload)

                    # Point telemetry at a directory so every write attempt fails.
                    # (If the hook auto-creates parent dirs, make this path
                    # read-only instead.)
                    broken_path = "telemetry_is_a_dir"
                    os.makedirs(Path(project_dir) / broken_path, exist_ok=True)
                    write_config(
                        project_dir,
                        telemetry_enabled=True,
                        telemetry_path=broken_path,
                    )
                    with_failure = run_hook(self.HOOK, project_dir, payload)

                    # User-visible behavior is identical whether telemetry blew up
                    # or not.
                    self.assertEqual(with_failure.returncode, baseline.returncode)
                    self.assertEqual(with_failure.stdout, baseline.stdout)
                    self.assertEqual(with_failure.stderr, baseline.stderr)


class ClaudeHookTelemetryTests(_HookTelemetryMixin, unittest.TestCase):
    HOST = "claude-code"
    HOOK = CLAUDE_HOOK
    EVENT_NAME = "UserPromptSubmit"


class KiroHookTelemetryTests(_HookTelemetryMixin, unittest.TestCase):
    HOST = "kiro"
    HOOK = KIRO_HOOK
    EVENT_NAME = "userPromptSubmit"  # Kiro uses the lowercase event name.

    def test_kiro_blocks_vague_prompts_with_exit_2(self):
        # Kiro's distinct output behavior: block via exit code 2.
        for prompt, _ in VAGUE_PROMPTS:
            with self.subTest(prompt=prompt):
                with tempfile.TemporaryDirectory() as project_dir:
                    write_config(project_dir, telemetry_enabled=True)
                    result = run_hook(self.HOOK, project_dir, self._payload(project_dir, prompt))
                    self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
