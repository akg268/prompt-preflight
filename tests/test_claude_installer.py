from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _load_installer_module():
    module_path = ROOT / "scripts" / "install_claude_plugin.py"
    spec = importlib.util.spec_from_file_location("install_claude_plugin", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ClaudeInstallerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.installer = _load_installer_module()

    def test_default_skills_dir(self) -> None:
        home = Path("/tmp/example-home")
        self.assertEqual(
            self.installer.default_skills_dir(home),
            home / ".claude" / "skills",
        )

    def test_source_plugin_validates_current_repo(self) -> None:
        manifest = self.installer.validate_source_plugin(ROOT)
        self.assertEqual(manifest["name"], "prompt-preflight")
        self.assertEqual(manifest["hooks"], "./hooks/claude-hooks.json")

    def test_destination_clean_requires_prompt_preflight_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "prompt-preflight"
            destination.mkdir()
            self.assertFalse(self.installer.destination_is_safe_to_clean(destination))

    def test_copy_plugin_dry_run_does_not_create_destination(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "prompt-preflight"
            self.installer.copy_plugin(ROOT, destination, clean=False, dry_run=True)
            self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
