#!/usr/bin/env python3
"""Executable adapter for the bundled Claude Code hook."""

from pathlib import Path
import sys


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT / "src"))

from prompt_preflight.claude_hook import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
