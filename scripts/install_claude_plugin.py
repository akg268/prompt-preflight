#!/usr/bin/env python3
"""Install Prompt Preflight as a personal Claude Code skills-directory plugin.

This installer copies the current plugin directory to:

    ~/.claude/skills/prompt-preflight

Claude Code automatically loads folders in that location when they contain a
.claude-plugin/plugin.json manifest. No marketplace setup is required.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys
from typing import Any


PLUGIN_NAME = "prompt-preflight"
IGNORE_PATTERNS = (
    ".git",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "*.pyc",
    "*.pyo",
    "build",
    "dist",
    "*.egg-info",
    "benchmark-results*.json",
)


class InstallerError(RuntimeError):
    """Raised for expected installer failures."""


def default_skills_dir(home: Path | None = None) -> Path:
    home = home or Path.home()
    return home / ".claude" / "skills"


def plugin_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise InstallerError(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise InstallerError(f"{path} must contain a JSON object")
    return data


def validate_source_plugin(root: Path) -> dict[str, Any]:
    manifest_path = root / ".claude-plugin" / "plugin.json"
    required_paths = (
        manifest_path,
        root / "hooks" / "claude-hooks.json",
        root / "scripts" / "prompt_preflight_claude_hook.py",
        root / "src" / "prompt_preflight" / "claude_hook.py",
        root / "src" / "prompt_preflight" / "analyzer.py",
    )
    missing = [str(path) for path in required_paths if not path.exists()]
    if missing:
        raise InstallerError("Source plugin is incomplete. Missing: " + ", ".join(missing))

    manifest = read_json(manifest_path)
    if manifest.get("name") != PLUGIN_NAME:
        raise InstallerError(
            f"Expected Claude plugin manifest name {PLUGIN_NAME!r}, "
            f"found {manifest.get('name')!r}"
        )
    if manifest.get("hooks") != "./hooks/claude-hooks.json":
        raise InstallerError("Claude plugin manifest must point to ./hooks/claude-hooks.json")
    return manifest


def destination_is_safe_to_clean(destination: Path) -> bool:
    if not destination.exists():
        return True
    manifest_path = destination / ".claude-plugin" / "plugin.json"
    if not manifest_path.exists():
        return False
    try:
        manifest = read_json(manifest_path)
    except InstallerError:
        return False
    return manifest.get("name") == PLUGIN_NAME


def copy_plugin(source_root: Path, destination: Path, *, clean: bool, dry_run: bool) -> None:
    source_root = source_root.resolve()
    destination = destination.expanduser().resolve()

    if source_root == destination:
        raise InstallerError("Source and destination are the same directory")
    if source_root in destination.parents:
        raise InstallerError("Destination cannot be inside the source plugin directory")

    if clean and destination.exists():
        if not destination_is_safe_to_clean(destination):
            raise InstallerError(
                f"Refusing to clean {destination}; it does not look like a {PLUGIN_NAME} install"
            )
        if not dry_run:
            shutil.rmtree(destination)

    if dry_run:
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        source_root,
        destination,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns(*IGNORE_PATTERNS),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Install or update Prompt Preflight for Claude Code.",
    )
    parser.add_argument(
        "--skills-dir",
        type=Path,
        default=default_skills_dir(),
        help="Claude skills directory that should contain prompt-preflight",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove the existing installed prompt-preflight directory before copying",
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
        source_root = plugin_root()
        destination = args.skills_dir.expanduser() / PLUGIN_NAME

        validate_source_plugin(source_root)

        print("Prompt Preflight Claude Code installer")
        print(f"Source: {source_root}")
        print(f"Destination: {destination.expanduser()}")
        print()

        copy_plugin(source_root, destination, clean=args.clean, dry_run=args.dry_run)
        print(("Would copy" if args.dry_run else "Copied") + " plugin files.")
        print()
        print("Next steps:")
        print("1. Restart Claude Code, or run /reload-plugins inside an open session.")
        print("2. Run /plugin list and confirm prompt-preflight@skills-dir is enabled.")
        print("3. Run /hooks and review the Prompt Preflight UserPromptSubmit hook.")
        print('4. Test with: "Create a car image"')
        print()
        print("Development shortcut without installing:")
        print(f"claude --plugin-dir {source_root}")
        return 0
    except InstallerError as exc:
        print(f"Install failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
