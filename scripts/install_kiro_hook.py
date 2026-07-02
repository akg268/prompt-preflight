#!/usr/bin/env python3
"""Install Prompt Preflight as a Kiro IDE UserPromptSubmit hook.

Kiro IDE hooks live in either:

    <workspace>/.kiro/hooks/
    ~/.kiro/hooks/

This installer writes a prompt-preflight.json hook file that points back to the
current Prompt Preflight checkout.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
from typing import Any


HOOK_FILE_NAME = "prompt-preflight.json"
HOOK_NAME = "prompt-preflight"


class InstallerError(RuntimeError):
    """Raised for expected installer failures."""


def plugin_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_user_hooks_dir(home: Path | None = None) -> Path:
    home = home or Path.home()
    return home / ".kiro" / "hooks"


def default_workspace_hooks_dir(workspace: Path | None = None) -> Path:
    workspace = workspace or Path.cwd()
    return workspace / ".kiro" / "hooks"


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise InstallerError(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise InstallerError(f"{path} must contain a JSON object")
    return data


def validate_source(root: Path) -> None:
    required_paths = (
        root / "scripts" / "prompt_preflight_kiro_hook.py",
        root / "src" / "prompt_preflight" / "kiro_hook.py",
        root / "src" / "prompt_preflight" / "analyzer.py",
        root / "src" / "prompt_preflight" / "data" / "vague_prompts.txt",
    )
    missing = [str(path) for path in required_paths if not path.exists()]
    if missing:
        raise InstallerError("Source checkout is incomplete. Missing: " + ", ".join(missing))


def hook_command(root: Path, python_bin: str, target_os: str | None = None) -> str:
    target_os = target_os or os.name
    script = root / "scripts" / "prompt_preflight_kiro_hook.py"
    if target_os == "nt":
        return subprocess.list2cmdline([python_bin, str(script)])
    return f"{shlex.quote(python_bin)} {shlex.quote(str(script))}"


def hook_config(root: Path, python_bin: str, target_os: str | None = None) -> dict[str, Any]:
    return {
        "version": "v1",
        "hooks": [
            {
                "name": HOOK_NAME,
                "description": (
                    "Pause vague, consequential prompts before Kiro spends a model turn."
                ),
                "trigger": "UserPromptSubmit",
                "action": {
                    "type": "command",
                    "command": hook_command(root, python_bin, target_os=target_os),
                },
                "timeout": 5,
                "enabled": True,
            }
        ],
    }


def existing_file_is_prompt_preflight(path: Path) -> bool:
    if not path.exists():
        return True
    try:
        data = read_json(path)
    except InstallerError:
        return False
    hooks = data.get("hooks")
    if not isinstance(hooks, list):
        return False
    return any(isinstance(hook, dict) and hook.get("name") == HOOK_NAME for hook in hooks)


def write_hook_file(
    path: Path,
    config: dict[str, Any],
    *,
    dry_run: bool,
    force: bool,
) -> None:
    if path.exists() and not force and not existing_file_is_prompt_preflight(path):
        raise InstallerError(
            f"Refusing to overwrite {path}; pass --force if you intentionally want to replace it"
        )
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def resolve_hooks_dir(args: argparse.Namespace) -> Path:
    if args.hooks_dir is not None:
        return args.hooks_dir.expanduser()
    if args.scope == "user":
        return default_user_hooks_dir()
    workspace = args.workspace.expanduser().resolve()
    if not workspace.exists():
        raise InstallerError(f"Workspace does not exist: {workspace}")
    if not workspace.is_dir():
        raise InstallerError(f"Workspace is not a directory: {workspace}")
    return default_workspace_hooks_dir(workspace)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Install or update the Prompt Preflight Kiro IDE hook.",
    )
    parser.add_argument(
        "--scope",
        choices=("workspace", "user"),
        default="workspace",
        help="Install into the current workspace or user-level Kiro hooks directory",
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=Path.cwd(),
        help="Workspace root to use when --scope workspace is selected",
    )
    parser.add_argument(
        "--hooks-dir",
        type=Path,
        help="Override the exact Kiro hooks directory",
    )
    parser.add_argument(
        "--python-bin",
        default="python" if sys.platform.startswith("win") else "python3",
        help="Python executable to use in the Kiro hook command",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing prompt-preflight.json hook file even if it does not look like Prompt Preflight",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print intended actions without writing files",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        root = plugin_root().resolve()
        validate_source(root)
        hooks_dir = resolve_hooks_dir(args)
        destination = hooks_dir / HOOK_FILE_NAME
        config = hook_config(root, args.python_bin)

        print("Prompt Preflight Kiro installer")
        print(f"Source: {root}")
        print(f"Scope: {args.scope}")
        print(f"Hook file: {destination}")
        print(f"Command: {config['hooks'][0]['action']['command']}")
        print()

        write_hook_file(destination, config, dry_run=args.dry_run, force=args.force)
        print(("Would write" if args.dry_run else "Wrote") + " Kiro hook file.")
        print()
        print("Next steps:")
        print("1. Restart Kiro IDE, or reload hooks from the Agent Hooks panel.")
        print("2. Confirm the prompt-preflight UserPromptSubmit hook is enabled.")
        print('3. Test with: "Create a car image"')
        return 0
    except InstallerError as exc:
        print(f"Install failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
