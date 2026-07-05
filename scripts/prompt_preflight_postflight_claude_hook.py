#!/usr/bin/env python3
"""Executable adapter for the Claude Code postflight Stop hook."""

from pathlib import Path
import sys


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT / "src"))

from prompt_preflight.postflight_claude_hook import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
