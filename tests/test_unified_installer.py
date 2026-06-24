from __future__ import annotations

import importlib.util
import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _load_installer_module():
    module_path = ROOT / "scripts" / "install_prompt_preflight.py"
    spec = importlib.util.spec_from_file_location("install_prompt_preflight", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class UnifiedInstallerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.installer = _load_installer_module()

    def test_unified_dry_run_for_both_hosts_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            codex_plugins_dir = root / "codex-plugins"
            codex_marketplace_path = root / "marketplace.json"
            claude_skills_dir = root / "claude-skills"

            with contextlib.redirect_stdout(io.StringIO()):
                code = self.installer.main(
                    [
                        "--target",
                        "both",
                        "--dry-run",
                        "--skip-codex-add",
                        "--codex-plugins-dir",
                        str(codex_plugins_dir),
                        "--codex-marketplace-path",
                        str(codex_marketplace_path),
                        "--claude-skills-dir",
                        str(claude_skills_dir),
                    ]
                )

            self.assertEqual(code, 0)
            self.assertFalse(codex_plugins_dir.exists())
            self.assertFalse(codex_marketplace_path.exists())
            self.assertFalse(claude_skills_dir.exists())

    def test_target_claude_only_accepts_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            claude_skills_dir = Path(directory) / "claude-skills"
            with contextlib.redirect_stdout(io.StringIO()):
                code = self.installer.main(
                    [
                        "--target",
                        "claude",
                        "--dry-run",
                        "--claude-skills-dir",
                        str(claude_skills_dir),
                    ]
                )
            self.assertEqual(code, 0)
            self.assertFalse(claude_skills_dir.exists())


if __name__ == "__main__":
    unittest.main()
