import importlib.util
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "release_check.py"


def load_release_check_module():
    """Load the release-check script as a module without running its main function."""
    spec = importlib.util.spec_from_file_location("release_check", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ReleaseCheckTests(unittest.TestCase):
    """Protect the small helper logic used by the release-check CLI."""

    @classmethod
    def setUpClass(cls):
        """Load the script once for this test class."""
        cls.release_check = load_release_check_module()

    def test_parse_node_major(self):
        """Node version parsing should handle common `node --version` output."""
        self.assertEqual(self.release_check.parse_node_major("v20.11.1\n"), 20)
        self.assertEqual(self.release_check.parse_node_major("24.14.0"), 24)
        self.assertEqual(self.release_check.parse_node_major("v16"), 16)
        self.assertIsNone(self.release_check.parse_node_major("not-a-version"))

    def test_expected_extension_line(self):
        """Clean-install verification should look for the public publisher ID."""
        self.assertEqual(
            self.release_check.expected_extension_line("0.0.1"),
            "arunkumar-ganesan.prompt-preflight-vscode@0.0.1",
        )

    def test_command_text_quotes_spaces(self):
        """Printed commands should be safe to copy when paths include spaces."""
        command = self.release_check.command_text(["python3", "path with space/script.py"])
        self.assertEqual(command, "python3 'path with space/script.py'")


if __name__ == "__main__":
    unittest.main()
