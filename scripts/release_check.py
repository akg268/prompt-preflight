#!/usr/bin/env python3
"""Run the repeatable Prompt Preflight release readiness gates.

This script intentionally stays dependency-free. It runs the same checks a
maintainer would otherwise do by hand before cutting a public VS Code extension
release or announcing a broad public beta.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
VSCODE_DIR = REPO_ROOT / "vscode-extension"
EXTENSION_ID = "arunkumar-ganesan.prompt-preflight-vscode"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line flags that make release gates practical locally and in CI."""
    parser = argparse.ArgumentParser(
        description="Run Prompt Preflight release readiness checks."
    )
    parser.add_argument(
        "--skip-vscode",
        action="store_true",
        help="Skip VS Code extension tests, packaging, audit, and clean install.",
    )
    parser.add_argument(
        "--skip-clean-install",
        action="store_true",
        help="Skip installing the generated VSIX into a temporary VS Code profile.",
    )
    parser.add_argument(
        "--min-block-rate",
        default="0.90",
        help="Minimum vague-prompt benchmark block rate. Default: 0.90.",
    )
    parser.add_argument(
        "--benchmark-output",
        default=str(Path(tempfile.gettempdir()) / "prompt-preflight-release-benchmark.json"),
        help="Where to write benchmark JSON output. Default: a temp-file path.",
    )
    return parser.parse_args(argv)


def command_text(command: Sequence[str]) -> str:
    """Return a copy-pasteable representation of a subprocess command."""
    return " ".join(shlex.quote(part) for part in command)


def print_header(title: str) -> None:
    """Print a visible section header so release output is easy to skim."""
    print(f"\n== {title} ==", flush=True)


def run_command(label: str, command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run a release-gate command and fail immediately if it exits non-zero."""
    print_header(label)
    print(f"$ {command_text(command)}", flush=True)
    result = subprocess.run(command, cwd=cwd, text=True, check=False)
    if result.returncode != 0:
        raise SystemExit(f"\nRelease check failed: {label}")
    return result


def run_captured_command(
    label: str, command: Sequence[str], cwd: Path
) -> subprocess.CompletedProcess[str]:
    """Run a command whose output must be inspected by this script."""
    print_header(label)
    print(f"$ {command_text(command)}", flush=True)
    result = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    print(result.stdout, end="")
    if result.returncode != 0:
        raise SystemExit(f"\nRelease check failed: {label}")
    return result


def parse_node_major(version_text: str) -> int | None:
    """Extract the major version from strings such as `v20.11.1`."""
    cleaned = version_text.strip()
    if cleaned.startswith("v"):
        cleaned = cleaned[1:]
    major_text = cleaned.split(".", maxsplit=1)[0]
    if not major_text.isdigit():
        return None
    return int(major_text)


def ensure_node_20_or_newer() -> None:
    """Fail with a clear message when VSIX packaging would hit Node 16 runtime errors."""
    node_path = shutil.which("node")
    if not node_path:
        raise SystemExit("Release check failed: Node.js was not found on PATH.")

    result = subprocess.run(
        ["node", "--version"],
        text=True,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    major = parse_node_major(result.stdout)
    if major is None or major < 20:
        raise SystemExit(
            "Release check failed: VSIX packaging requires Node.js 20 or newer.\n"
            f"Found: {result.stdout.strip() or 'unknown'} at {node_path}\n"
            "Update Node or run this script with a PATH that points to Node 20+."
        )

    print_header("Node version")
    print(f"Using {result.stdout.strip()} at {node_path}")


def read_extension_version() -> str:
    """Read the VS Code extension version from package.json."""
    package_json = json.loads((VSCODE_DIR / "package.json").read_text(encoding="utf-8"))
    return str(package_json["version"])


def expected_extension_line(version: str) -> str:
    """Return the extension listing line expected after a clean VSIX install."""
    return f"{EXTENSION_ID}@{version}"


def run_python_gates(args: argparse.Namespace) -> None:
    """Run release gates for the shared Python analyzer and documentation."""
    run_command(
        "Python unit tests",
        ["python3", "-m", "unittest", "discover", "-s", "tests", "-q"],
        REPO_ROOT,
    )
    run_command(
        "Structured template docs are current",
        ["python3", "scripts/generate_template_docs.py", "--check"],
        REPO_ROOT,
    )
    run_command(
        "Vague prompt benchmark",
        [
            "python3",
            "scripts/benchmark_vague_prompts.py",
            "--min-block-rate",
            args.min_block_rate,
            "--json-output",
            args.benchmark_output,
        ],
        REPO_ROOT,
    )


def package_vsix(vsix_path: Path) -> None:
    """Compile and package the VS Code extension into the requested VSIX path."""
    run_command(
        "VS Code extension tests",
        ["npm", "test"],
        VSCODE_DIR,
    )
    run_command(
        "Build fresh VSIX",
        ["npm", "run", "package:vsix", "--", "--out", str(vsix_path)],
        VSCODE_DIR,
    )
    if not vsix_path.exists():
        raise SystemExit(f"Release check failed: VSIX was not created at {vsix_path}")


def audit_vsix(vsix_path: Path) -> None:
    """Verify the generated VSIX contains only intended public extension files."""
    run_command(
        "Audit VSIX contents",
        ["node", "scripts/auditVsix.js", str(vsix_path)],
        VSCODE_DIR,
    )


def smoke_test_bundled_analyzer(vsix_path: Path) -> None:
    """Extract the VSIX and run the packaged Python analyzer without repoPath."""
    print_header("Smoke-test bundled Python analyzer")
    with tempfile.TemporaryDirectory(prefix="prompt-preflight-vsix-smoke-") as extract_dir:
        extract_path = Path(extract_dir)
        with zipfile.ZipFile(vsix_path) as archive:
            archive.extractall(extract_path)

        bundled_cli = (
            extract_path
            / "extension"
            / "bundled-analyzer"
            / "scripts"
            / "prompt_preflight.py"
        )
        command = ["python3", str(bundled_cli), "--json", "Create a car image"]
        print(f"$ {command_text(command)}", flush=True)
        result = subprocess.run(
            command,
            cwd=extract_path,
            text=True,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        print(result.stdout, end="")
        if result.returncode != 2:
            raise SystemExit(
                "\nRelease check failed: bundled analyzer smoke test should exit 2 "
                f"for a vague prompt, got {result.returncode}."
            )
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as error:
            raise SystemExit(
                f"\nRelease check failed: bundled analyzer returned invalid JSON: {error}"
            ) from error
        if not payload.get("should_clarify"):
            raise SystemExit(
                "\nRelease check failed: bundled analyzer did not clarify a vague smoke-test prompt."
            )


def verify_clean_install(vsix_path: Path, version: str) -> None:
    """Install the VSIX into temporary VS Code dirs and verify the expected extension ID."""
    code_path = shutil.which("code")
    if not code_path:
        raise SystemExit(
            "Release check failed: VS Code CLI `code` was not found on PATH.\n"
            "Install the VS Code shell command or rerun with --skip-clean-install."
        )

    expected_line = expected_extension_line(version)
    with tempfile.TemporaryDirectory(prefix="prompt-preflight-vscode-user-") as user_dir:
        with tempfile.TemporaryDirectory(prefix="prompt-preflight-vscode-ext-") as ext_dir:
            run_command(
                "Clean temporary VSIX install",
                [
                    "code",
                    "--user-data-dir",
                    user_dir,
                    "--extensions-dir",
                    ext_dir,
                    "--install-extension",
                    str(vsix_path),
                    "--force",
                ],
                REPO_ROOT,
            )
            result = run_captured_command(
                "Verify clean install extension list",
                [
                    "code",
                    "--user-data-dir",
                    user_dir,
                    "--extensions-dir",
                    ext_dir,
                    "--list-extensions",
                    "--show-versions",
                ],
                REPO_ROOT,
            )

    if expected_line not in result.stdout.splitlines():
        raise SystemExit(
            "Release check failed: temporary VS Code profile did not list "
            f"{expected_line}."
        )


def run_vscode_gates(args: argparse.Namespace) -> None:
    """Run release gates for the VS Code extension package."""
    ensure_node_20_or_newer()
    version = read_extension_version()
    with tempfile.TemporaryDirectory(prefix="prompt-preflight-vsix-") as package_dir:
        vsix_path = Path(package_dir) / f"prompt-preflight-vscode-{version}.vsix"
        package_vsix(vsix_path)
        audit_vsix(vsix_path)
        smoke_test_bundled_analyzer(vsix_path)
        if args.skip_clean_install:
            print_header("Clean temporary VSIX install")
            print("Skipped by --skip-clean-install.")
        else:
            verify_clean_install(vsix_path, version)


def print_manual_gates() -> None:
    """Print release checks that still require human eyes or credentials."""
    print_header("Manual release gates still required")
    print(
        "- Run `Prompt Preflight: Run Setup Doctor` in an Extension Development Host.\n"
        "- Run `Prompt Preflight: Open Telemetry Dashboard` after recording one local check.\n"
        "- Confirm README/demo GIF/screenshots still match the latest UI.\n"
        "- Smoke-test an installed VSIX without promptPreflight.repoPath to verify the bundled analyzer path.\n"
        "- Keep marketplace publisher tokens and GitHub credentials outside the repo.\n"
        "- Review `git status` and remove local scratch files before tagging or publishing."
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run all selected release checks and return a process exit code."""
    args = parse_args(argv)
    run_python_gates(args)
    if args.skip_vscode:
        print_header("VS Code release gates")
        print("Skipped by --skip-vscode.")
    else:
        run_vscode_gates(args)
    print_manual_gates()
    print_header("Release check result")
    print("Automated release checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
