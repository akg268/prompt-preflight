#!/usr/bin/env python3
"""Regenerate cross-host parity expected snapshots from live analyzer/host output.

Usage:
  python3 scripts/update_parity_fixtures.py

Equivalent:
  UPDATE_PARITY_FIXTURES=1 python3 -m unittest tests.test_parity_fixtures -v

See docs/PARITY_FIXTURES.md.
"""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

from test_parity_fixtures import regenerate_expected_fixtures  # noqa: E402


def main() -> int:
    ids = regenerate_expected_fixtures()
    print("Updated parity expected snapshots for:", ", ".join(ids))
    print(f"Wrote under {ROOT / 'tests' / 'fixtures' / 'parity' / 'expected'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
