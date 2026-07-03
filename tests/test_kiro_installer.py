from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
import unittest.mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _load_installer_module():
    module_path = ROOT / "scripts" / "install_kiro_hook.py"
    spec = importlib.util.spec_from_file_location("install_kiro_hook", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class KiroInstallerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.installer = _load_installer_module()

    def test_default_workspace_hooks_dir(self) -> None:
        workspace = Path("/tmp/example-workspace")
        self.assertEqual(
            self.installer.default_workspace_hooks_dir(workspace),
            workspace / ".kiro" / "hooks",
        )

    def test_default_user_hooks_dir(self) -> None:
        home = Path("/tmp/example-home")
        self.assertEqual(
            self.installer.default_user_hooks_dir(home),
            home / ".kiro" / "hooks",
        )

    def test_hook_config_uses_user_prompt_submit_trigger(self) -> None:
        config = self.installer.hook_config(ROOT, "python3")
        hook = config["hooks"][0]
        self.assertEqual(config["version"], "v1")
        self.assertEqual(hook["name"], "prompt-preflight")
        self.assertEqual(hook["trigger"], "UserPromptSubmit")
        self.assertEqual(hook["action"]["type"], "command")
        self.assertIn("prompt_preflight_kiro_hook.py", hook["action"]["command"])

    def test_existing_file_safety_requires_prompt_preflight_hook(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "prompt-preflight.json"
            path.write_text(
                json.dumps({"version": "v1", "hooks": [{"name": "other"}]}),
                encoding="utf-8",
            )
            self.assertFalse(self.installer.existing_file_is_prompt_preflight(path))

    def test_write_hook_file_dry_run_does_not_create_destination(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".kiro" / "hooks" / "prompt-preflight.json"
            config = self.installer.hook_config(ROOT, "python3")
            self.installer.write_hook_file(path, config, dry_run=True, force=False)
            self.assertFalse(path.exists())

    def test_hook_command_posix(self) -> None:
        cmd = self.installer.hook_command(Path("/test/path"), "python3", target_os="posix")
        self.assertEqual(cmd, "python3 /test/path/scripts/prompt_preflight_kiro_hook.py")

    def test_hook_command_posix_with_spaces(self) -> None:
        cmd = self.installer.hook_command(Path("/test/some path"), "python3", target_os="posix")
        self.assertEqual(cmd, "python3 '/test/some path/scripts/prompt_preflight_kiro_hook.py'")

    def test_hook_command_windows(self) -> None:
        cmd = self.installer.hook_command(Path("C:/test/path"), "python", target_os="nt")
        self.assertEqual(cmd, "python C:/test/path/scripts/prompt_preflight_kiro_hook.py")

    def test_hook_command_windows_with_spaces(self) -> None:
        cmd = self.installer.hook_command(Path("C:/test/some path"), "python", target_os="nt")
        self.assertEqual(cmd, 'python "C:/test/some path/scripts/prompt_preflight_kiro_hook.py"')

    @unittest.mock.patch("sys.platform", "linux")
    def test_parser_default_python_posix(self) -> None:
        parser = self.installer.build_parser()
        args = parser.parse_args([])
        self.assertEqual(args.python_bin, "python3")

    @unittest.mock.patch("sys.platform", "win32")
    def test_parser_default_python_windows(self) -> None:
        parser = self.installer.build_parser()
        args = parser.parse_args([])
        self.assertEqual(args.python_bin, "python")


if __name__ == "__main__":
    unittest.main()
