#!/usr/bin/env python3
"""Run postflight checks manually from a checkout or plugin install."""

from pathlib import Path
import sys


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT / "src"))

from prompt_preflight.postflight_cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
