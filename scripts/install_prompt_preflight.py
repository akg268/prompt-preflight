#!/usr/bin/env python3
"""Install Prompt Preflight for Codex, Claude Code, or both.

This is the friendly setup entry point for users. It delegates to the
host-specific installers so advanced Codex and Claude Code options remain
available in one place.
"""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import sys
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"


def load_installer(script_name: str) -> ModuleType:
    module_path = SCRIPTS_DIR / script_name
    spec = importlib.util.spec_from_file_location(module_path.stem, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def path_arg(path: Path | None) -> str | None:
    return str(path.expanduser()) if path is not None else None


def build_codex_args(args: argparse.Namespace) -> list[str]:
    codex_args: list[str] = []
    if args.dry_run:
        codex_args.append("--dry-run")
    if args.clean:
        codex_args.append("--clean")
    if args.skip_codex_add:
        codex_args.append("--skip-codex-add")
    if args.require_codex_cli:
        codex_args.append("--require-codex-cli")
    if args.no_codex_reinstall:
        codex_args.append("--no-reinstall")
    if args.codex_bin:
        codex_args.extend(["--codex-bin", args.codex_bin])
    if args.codex_plugins_dir:
        codex_args.extend(["--plugins-dir", path_arg(args.codex_plugins_dir) or ""])
    if args.codex_marketplace_path:
        codex_args.extend(["--marketplace-path", path_arg(args.codex_marketplace_path) or ""])
    if args.codex_marketplace_name:
        codex_args.extend(["--marketplace-name", args.codex_marketplace_name])
    return codex_args


def build_claude_args(args: argparse.Namespace) -> list[str]:
    claude_args: list[str] = []
    if args.dry_run:
        claude_args.append("--dry-run")
    if args.clean:
        claude_args.append("--clean")
    if args.claude_skills_dir:
        claude_args.extend(["--skills-dir", path_arg(args.claude_skills_dir) or ""])
    return claude_args


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Install Prompt Preflight for Codex, Claude Code, or both.",
    )
    parser.add_argument(
        "--target",
        choices=("both", "codex", "claude"),
        default="both",
        help="Which host integration to install",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print intended actions without writing files or running host install commands",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Refresh existing installed copies when they look like Prompt Preflight installs",
    )

    codex = parser.add_argument_group("Codex options")
    codex.add_argument(
        "--skip-codex-add",
        action="store_true",
        help="Copy files and update Codex marketplace.json, but skip codex plugin add",
    )
    codex.add_argument(
        "--require-codex-cli",
        action="store_true",
        help="Fail when installing for Codex and the codex CLI is not available",
    )
    codex.add_argument(
        "--no-codex-reinstall",
        action="store_true",
        help="Do not run codex plugin remove before codex plugin add",
    )
    codex.add_argument("--codex-bin", default="codex", help="Codex CLI executable name or path")
    codex.add_argument(
        "--codex-plugins-dir",
        type=Path,
        help="Directory that should contain the installed Codex plugin",
    )
    codex.add_argument(
        "--codex-marketplace-path",
        type=Path,
        help="Path to the Codex personal marketplace.json file",
    )
    codex.add_argument(
        "--codex-marketplace-name",
        help="Marketplace name to use when creating a Codex marketplace file",
    )

    claude = parser.add_argument_group("Claude Code options")
    claude.add_argument(
        "--claude-skills-dir",
        type=Path,
        help="Claude Code skills directory that should contain prompt-preflight",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    failures = 0
    if args.target in {"both", "codex"}:
        print("== Codex setup ==")
        codex_installer = load_installer("install_codex_plugin.py")
        failures += 1 if codex_installer.main(build_codex_args(args)) else 0
        print()

    if args.target in {"both", "claude"}:
        print("== Claude Code setup ==")
        claude_installer = load_installer("install_claude_plugin.py")
        failures += 1 if claude_installer.main(build_claude_args(args)) else 0

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
