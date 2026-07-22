from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "parity"
PROMPTS_PATH = FIXTURE_DIR / "prompts.jsonl"
EXPECTED_DIR = FIXTURE_DIR / "expected"

HOSTS = ("cli", "vscode", "codex", "claude", "kiro")

CORE_KEYS = ("decision", "should_clarify", "intent", "checks", "question_count")


def load_prompts() -> list[dict[str, str]]:
    """Load fixture prompts.

    Privacy fixtures may use ``prompt_parts`` (joined at load time) so committed
    files do not contain contiguous secret-like tokens that trip scanners.
    """
    rows: list[dict[str, str]] = []
    for line in PROMPTS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if "prompt" not in row:
            parts = row.get("prompt_parts")
            if not isinstance(parts, list) or not parts:
                raise ValueError(f"Fixture {row.get('id')!r} needs prompt or prompt_parts")
            row = {**row, "prompt": "".join(str(part) for part in parts)}
        rows.append(row)
    return rows


def normalize_core(analysis: dict[str, object], *, decision: str | None = None) -> dict[str, object]:
    """Reduce analyzer/CLI JSON (or equivalent) to the cross-host decision core."""
    checks = analysis.get("checks") or []
    questions = analysis.get("questions") or []
    return {
        "decision": decision if decision is not None else analysis["decision"],
        "should_clarify": bool(analysis["should_clarify"]),
        "intent": analysis["intent"],
        "checks": sorted(checks),
        "question_count": len(questions),
    }


def _run_cli_json(prompt: str, *, cwd: str | None = None) -> dict[str, object]:
    """Invoke the CLI the same way the VS Code extension does (`--json`)."""
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "prompt_preflight.py"), "--json", prompt],
        cwd=cwd or str(ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    # Exit 2 means clarification/block; still a successful analysis payload.
    if completed.returncode not in (0, 2):
        raise AssertionError(
            f"CLI failed (exit {completed.returncode}): stderr={completed.stderr!r} "
            f"stdout={completed.stdout!r}"
        )
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise AssertionError(
            f"CLI returned invalid JSON: stdout={completed.stdout!r} stderr={completed.stderr!r}"
        ) from error


def _run_hook_script(
    script_name: str,
    prompt: str,
    *,
    hook_event_name: str,
    cwd: str,
) -> subprocess.CompletedProcess[str]:
    payload = {
        "hook_event_name": hook_event_name,
        "cwd": cwd,
        "prompt": prompt,
    }
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script_name)],
        input=json.dumps(payload),
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=False,
    )


def _decision_from_codex_or_claude(stdout: str) -> str:
    text = stdout.strip()
    if not text:
        return "allow"
    payload = json.loads(text)
    if "decision" in payload:
        return str(payload["decision"])
    if "hookSpecificOutput" in payload:
        return "nudge"
    raise AssertionError(f"Unrecognized hook JSON: {payload!r}")


def _decision_from_kiro(completed: subprocess.CompletedProcess[str]) -> str:
    if completed.returncode == 2:
        return "block"
    if completed.returncode != 0:
        raise AssertionError(
            f"Kiro hook failed (exit {completed.returncode}): "
            f"stdout={completed.stdout!r} stderr={completed.stderr!r}"
        )
    if completed.stdout.strip():
        return "nudge"
    return "allow"


def run_host(host: str, prompt: str, *, isolated_cwd: str) -> dict[str, object]:
    """Run one host adapter and return the normalized decision core.

    CLI and VS Code both use ``scripts/prompt_preflight.py --json``. Codex, Claude,
    and Kiro expose decision via host-specific formats; analyzer fields come from
    the shared CLI JSON so the normalized core can be compared across hosts.
    """
    if host not in HOSTS:
        raise ValueError(f"Unknown host: {host}")

    analysis = _run_cli_json(prompt, cwd=isolated_cwd)

    if host in ("cli", "vscode"):
        return normalize_core(analysis)

    if host == "codex":
        completed = _run_hook_script(
            "prompt_preflight_hook.py",
            prompt,
            hook_event_name="UserPromptSubmit",
            cwd=isolated_cwd,
        )
        if completed.returncode != 0:
            raise AssertionError(
                f"Codex hook failed (exit {completed.returncode}): "
                f"stderr={completed.stderr!r}"
            )
        decision = _decision_from_codex_or_claude(completed.stdout)
        return normalize_core(analysis, decision=decision)

    if host == "claude":
        completed = _run_hook_script(
            "prompt_preflight_claude_hook.py",
            prompt,
            hook_event_name="UserPromptSubmit",
            cwd=isolated_cwd,
        )
        if completed.returncode != 0:
            raise AssertionError(
                f"Claude hook failed (exit {completed.returncode}): "
                f"stderr={completed.stderr!r}"
            )
        decision = _decision_from_codex_or_claude(completed.stdout)
        return normalize_core(analysis, decision=decision)

    # kiro
    completed = _run_hook_script(
        "prompt_preflight_kiro_hook.py",
        prompt,
        hook_event_name="userPromptSubmit",
        cwd=isolated_cwd,
    )
    decision = _decision_from_kiro(completed)
    return normalize_core(analysis, decision=decision)


def expected_path(prompt_id: str) -> Path:
    return EXPECTED_DIR / f"{prompt_id}.json"


def load_expected(prompt_id: str) -> dict[str, object]:
    path = expected_path(prompt_id)
    return json.loads(path.read_text(encoding="utf-8"))


def write_expected(prompt_id: str, core: dict[str, object]) -> None:
    EXPECTED_DIR.mkdir(parents=True, exist_ok=True)
    path = expected_path(prompt_id)
    path.write_text(json.dumps(core, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def collect_host_cores(prompt: str) -> dict[str, dict[str, object]]:
    with tempfile.TemporaryDirectory() as directory:
        return {host: run_host(host, prompt, isolated_cwd=directory) for host in HOSTS}


def regenerate_expected_fixtures() -> list[str]:
    """Recompute expected snapshots from live host/analyzer output. Returns ids."""
    updated: list[str] = []
    for row in load_prompts():
        prompt_id = row["id"]
        cores = collect_host_cores(row["prompt"])
        # Prefer CLI as the written baseline; hosts must already agree.
        baseline = cores["cli"]
        for host, core in cores.items():
            if core != baseline:
                raise AssertionError(
                    f"Cannot regenerate {prompt_id}: host {host} core {core!r} "
                    f"differs from cli {baseline!r}"
                )
        write_expected(prompt_id, baseline)
        updated.append(prompt_id)
    return updated


class ParityFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.prompts = load_prompts()
        cls.by_id = {row["id"]: row for row in cls.prompts}

    def test_fixture_catalog_has_required_cases(self) -> None:
        ids = {row["id"] for row in self.prompts}
        self.assertEqual(
            ids,
            {"vague", "clear", "privacy-risk", "structured-template"},
        )

    def test_host_parity_matches_expected_snapshots(self) -> None:
        update = os.environ.get("UPDATE_PARITY_FIXTURES") == "1"
        if update:
            regenerate_expected_fixtures()

        for row in self.prompts:
            prompt_id = row["id"]
            prompt = row["prompt"]
            with self.subTest(id=prompt_id):
                cores = collect_host_cores(prompt)
                baseline = cores["cli"]
                for host, core in cores.items():
                    self.assertEqual(
                        list(core.keys()),
                        list(CORE_KEYS),
                        f"{prompt_id}/{host}: unexpected core keys",
                    )
                    self.assertEqual(
                        core,
                        baseline,
                        f"{prompt_id}: host {host} normalized core differs from cli",
                    )

                expected = load_expected(prompt_id)
                self.assertEqual(
                    baseline,
                    expected,
                    f"{prompt_id}: normalized core differs from expected snapshot "
                    f"({expected_path(prompt_id)}). Re-run with "
                    f"UPDATE_PARITY_FIXTURES=1 or scripts/update_parity_fixtures.py "
                    f"after intentional analyzer changes.",
                )

    def test_vague_case_blocks_image_generation(self) -> None:
        core = collect_host_cores(self.by_id["vague"]["prompt"])["cli"]
        self.assertEqual(core["decision"], "block")
        self.assertTrue(core["should_clarify"])
        self.assertEqual(core["intent"], "image_generation")

    def test_clear_case_allows(self) -> None:
        core = collect_host_cores(self.by_id["clear"]["prompt"])["cli"]
        self.assertEqual(core["decision"], "allow")
        self.assertFalse(core["should_clarify"])

    def test_privacy_case_blocks_privacy(self) -> None:
        core = collect_host_cores(self.by_id["privacy-risk"]["prompt"])["cli"]
        self.assertEqual(core["decision"], "block")
        self.assertEqual(core["intent"], "privacy")
        self.assertIn("privacy", core["checks"])

    def test_structured_template_blocks_template_contract(self) -> None:
        core = collect_host_cores(self.by_id["structured-template"]["prompt"])["cli"]
        self.assertEqual(core["decision"], "block")
        self.assertIn("template_contract", core["checks"])


if __name__ == "__main__":
    if os.environ.get("UPDATE_PARITY_FIXTURES") == "1" and "--update-only" in sys.argv:
        ids = regenerate_expected_fixtures()
        print("Updated parity fixtures:", ", ".join(ids))
        raise SystemExit(0)
    unittest.main()
