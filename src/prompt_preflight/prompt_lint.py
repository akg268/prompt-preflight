"""Prompt-library linting for CI and local automation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from .analyzer import analyze_prompt
from .config import Config, load_config


PROMPT_PREFLIGHT_CHECK_MARKER = "prompt-preflight: check"
DEFAULT_LINT_PATTERNS = (
    "docs/prompts/**/*.md",
    "docs/prompts/**/*.xml",
    "docs/prompts/**/*.toml",
    "prompts/**/*.md",
    "prompts/**/*.xml",
    "prompts/**/*.toml",
)
DEFAULT_EXCLUDED_DIRS = frozenset(
    {".git", "node_modules", "out", "dist", "build", ".vscode-test", "coverage", "htmlcov"}
)


@dataclass(frozen=True)
class PromptLintResult:
    """One analyzed prompt-library file."""

    path: str
    profile: str | None
    should_clarify: bool
    score: int
    severity: str
    intent: str
    checks: tuple[str, ...]
    reasons: tuple[str, ...]
    questions: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable result without prompt text."""

        return asdict(self)


@dataclass(frozen=True)
class PromptLintSummary:
    """Summary of one prompt-library lint run."""

    checked: int
    skipped: int
    failed: int
    results: tuple[PromptLintResult, ...]

    @property
    def passed(self) -> bool:
        """Return true when no checked prompt file needs clarification."""

        return self.failed == 0

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable summary without prompt text."""

        return {
            "checked": self.checked,
            "skipped": self.skipped,
            "failed": self.failed,
            "passed": self.passed,
            "results": [result.to_dict() for result in self.results],
        }


def has_lint_marker(text: str) -> bool:
    """Return true when a prompt file explicitly opts into CI/workspace lint."""

    return PROMPT_PREFLIGHT_CHECK_MARKER in text[:800].lower()


def _is_lintable_file(path: Path) -> bool:
    """Return true for Markdown, XML, and TOML prompt files outside build dirs."""

    if path.suffix.lower() not in {".md", ".xml", ".toml"}:
        return False
    return not any(part in DEFAULT_EXCLUDED_DIRS for part in path.parts)


def discover_prompt_files(root: Path, patterns: Iterable[str] = DEFAULT_LINT_PATTERNS) -> tuple[Path, ...]:
    """Find candidate prompt-library files under a project root."""

    found: dict[Path, None] = {}
    for pattern in patterns:
        for path in root.glob(pattern):
            if path.is_file() and _is_lintable_file(path):
                found[path.resolve()] = None
    return tuple(sorted(found))


def lint_prompt_library(
    cwd: str | Path,
    *,
    patterns: Iterable[str] = DEFAULT_LINT_PATTERNS,
    require_marker: bool = True,
    config: Config | None = None,
) -> PromptLintSummary:
    """Analyze a workspace prompt library and return prompt-free results."""

    root = Path(cwd).expanduser().resolve()
    active_config = config or load_config(root)
    results: list[PromptLintResult] = []
    skipped = 0

    if not active_config.enabled:
        return PromptLintSummary(checked=0, skipped=0, failed=0, results=())

    for path in discover_prompt_files(root, patterns):
        text = path.read_text(encoding="utf-8")
        if require_marker and not has_lint_marker(text):
            skipped += 1
            continue

        profile = active_config.profile_for_path(path, root)
        analysis = analyze_prompt(
            text,
            config=active_config,
            profile=profile,
            threshold=active_config.threshold,
            max_questions=active_config.max_questions,
            cwd=root,
        )
        relative = path.relative_to(root).as_posix()
        results.append(
            PromptLintResult(
                path=relative,
                profile=profile,
                should_clarify=analysis.should_clarify,
                score=analysis.score,
                severity=analysis.severity,
                intent=analysis.intent,
                checks=analysis.checks,
                reasons=analysis.reasons,
                questions=analysis.questions,
            )
        )

    failed = sum(1 for result in results if result.should_clarify)
    return PromptLintSummary(
        checked=len(results),
        skipped=skipped,
        failed=failed,
        results=tuple(results),
    )


def render_lint_report(summary: PromptLintSummary) -> str:
    """Render a concise human-readable CI report."""

    lines = [
        "Prompt Preflight prompt-library lint",
        "",
        f"Files checked: {summary.checked}",
        f"Files skipped: {summary.skipped}",
        f"Files needing clarification: {summary.failed}",
        f"Opt-in marker: {PROMPT_PREFLIGHT_CHECK_MARKER}",
        "",
    ]

    if not summary.results:
        lines.append("No prompt files were checked.")
    elif summary.passed:
        lines.append("All checked prompt files are clear to send.")
    else:
        for result in summary.results:
            if not result.should_clarify:
                continue
            profile = f" profile={result.profile}" if result.profile else ""
            reason = result.reasons[0] if result.reasons else "needs clarification"
            question = f" Ask: {result.questions[0]}" if result.questions else ""
            lines.append(
                f"- {result.path}:{profile} Vagueness score {result.score}/100 "
                f"({result.severity}) — {reason}{question}"
            )

    lines.extend(
        [
            "",
            "Privacy: this report does not print prompt text.",
        ]
    )
    return "\n".join(lines)
