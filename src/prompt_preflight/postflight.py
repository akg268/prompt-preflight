"""Deterministic postflight quality checks for agent responses.

Prompt Preflight's preflight checks run *before* a model turn on the prompt.
These postflight checks run *after* an agent response and flag common failure
modes deterministically: wrong output format, missing tests, hollow file-change
claims, violated negative constraints, leftover placeholders, and missing
citations. Like the rest of the package, this module performs no network I/O,
calls no model, and never reads any file: ``analyze_postflight`` operates purely
on the strings it is given, and ``changed_files`` is a list of names/paths only.

The result object mirrors ``analyzer.Analysis`` conventions: a frozen dataclass
with tuple fields, a ``to_dict()`` that swaps in redacted text when a secret is
present, a ``checks`` tuple of category names, and a ``severity`` string.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import re
from typing import Iterable

from .analyzer import redact_sensitive, sensitive_findings
from .postflight_config import POSTFLIGHT_CHECKS, PostflightConfig


# ---------------------------------------------------------------------------
# Small local helpers (kept local rather than importing analyzer privates).
# ---------------------------------------------------------------------------
def _unique(items: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(items))


_SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2}


def _max_severity(severities: Iterable[str]) -> str:
    best = "low"
    for severity in severities:
        if _SEVERITY_ORDER.get(severity, 0) > _SEVERITY_ORDER[best]:
            best = severity
    return best


_DEFAULT_SEVERITY = {
    "output_format": "medium",
    "tests_present": "medium",
    "file_change_claim": "medium",
    "constraint_adherence": "medium",
    "placeholders": "medium",
    "citations": "medium",
    "privacy": "high",
}


# ---------------------------------------------------------------------------
# Request detectors (what did the prompt ask for?).
# ---------------------------------------------------------------------------
_REQUEST_JSON_RE = re.compile(r"\bjson\b", re.IGNORECASE)
_REQUEST_TABLE_RE = re.compile(r"\btable\b", re.IGNORECASE)
_REQUEST_BULLETS_RE = re.compile(
    r"\b(?:bullet(?:ed)?(?:\s+points?|\s+list)?|as a list|in a list)\b", re.IGNORECASE
)
_REQUEST_NUMBERED_RE = re.compile(r"\bnumbered\s+(?:list|steps?)\b", re.IGNORECASE)
_REQUEST_YAML_RE = re.compile(r"\bya?ml\b", re.IGNORECASE)
_REQUEST_CSV_RE = re.compile(r"\bcsv\b", re.IGNORECASE)

_REQUEST_TESTS_RE = re.compile(
    r"\b(?:unit|integration)\s+tests?\b"
    r"|\b(?:add|include|write|with|and|plus)\s+(?:some\s+|a\s+)?(?:unit|integration)?\s*tests?\b"
    r"|\btest\s+coverage\b",
    re.IGNORECASE,
)

_REQUEST_CITATIONS_RE = re.compile(
    r"\bwith\s+citations?\b"
    r"|\bcite\s+(?:your\s+)?sources?\b"
    r"|\b(?:include|provide|add)\s+(?:references?|citations?|sources?)\b"
    r"|\bresearch\b",
    re.IGNORECASE,
)

# Negative constraints of the form "<verb> <single-token>" that we can literally
# check for in the response. Deliberately narrow to stay high precision.
_NEGATIVE_CONSTRAINT_RE = re.compile(
    r"\b(?:without\s+using|without|don'?t\s+use|do\s+not\s+use|avoid\s+using|avoid|"
    r"must\s+not\s+use|never\s+use|no)\s+([A-Za-z][\w.+#-]{1,30})",
    re.IGNORECASE,
)

# Claims that files were changed.
_CHANGE_CLAIM_RE = re.compile(
    r"\bI(?:'ve| have)?\s+(?:created|added|updated|modified|changed|wrote|written|"
    r"edited|refactored|deleted|removed|renamed|implemented|fixed)\b"
    r"|\bhere'?s\s+the\s+(?:updated|new|modified|revised)\s+\w+"
    r"|\b(?:created|updated|modified|added|wrote)\s+(?:the\s+)?(?:file|`?[\w./-]+\.\w+`?)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Response detectors (does the response satisfy the request?).
# ---------------------------------------------------------------------------
_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", re.DOTALL | re.IGNORECASE)
_JSON_OBJECT_RE = re.compile(r"(\{.*\}|\[.*\])", re.DOTALL)

_TEST_INDICATOR_RE = re.compile(
    r"\bdef\s+test_\w+"
    r"|\bassert\b"
    r"|\bpytest\b"
    r"|\bunittest\b"
    r"|\bdescribe\s*\("
    r"|\bit\s*\("
    r"|\btest_\w+\.py\b"
    r"|\b\w+\.test\.(?:js|ts|tsx|jsx)\b"
    r"|@Test\b",
    re.IGNORECASE,
)

_CITATION_INDICATOR_RE = re.compile(
    r"https?://"
    r"|\[\d+\]"
    r"|\bsources?\s*:"
    r"|\breferences?\b\s*:?"
    r"|\bdoi:\s*\S+"
    r"|\b10\.\d{4,}/\S+"
    r"|\bet al\.",
    re.IGNORECASE,
)

_PLACEHOLDER_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("[TODO]", re.compile(r"\[TODO\]", re.IGNORECASE)),
    ("TODO:", re.compile(r"\bTODO:")),
    ("FIXME", re.compile(r"\bFIXME\b")),
    ("XXX", re.compile(r"\bXXX\b")),
    ("[fill in]", re.compile(r"\[fill[\s_-]?in[^\]]*\]", re.IGNORECASE)),
    ("[placeholder]", re.compile(r"\[placeholder[^\]]*\]", re.IGNORECASE)),
    ("[insert ...]", re.compile(r"\[insert[^\]]*\]", re.IGNORECASE)),
    ("<your ... here>", re.compile(r"<[^>]*your[^>]*here[^>]*>", re.IGNORECASE)),
    ("[REPLACE ...]", re.compile(r"\[REPLACE[^\]]*\]", re.IGNORECASE)),
    ("[YOUR_...]", re.compile(r"\[YOUR_[A-Z0-9_]*\]")),
    ("TBD", re.compile(r"\bTBD\b")),
)


def _contains_json(text: str) -> bool:
    if _JSON_FENCE_RE.search(text):
        return True
    for match in _JSON_OBJECT_RE.finditer(text):
        candidate = match.group(1).strip()
        try:
            json.loads(candidate)
            return True
        except (json.JSONDecodeError, ValueError):
            continue
    return False


def _contains_markdown_table(text: str) -> bool:
    lines = text.splitlines()
    for row, sep in zip(lines, lines[1:]):
        if row.count("|") >= 2 and "|" in sep and re.match(
            r"^\s*\|?[\s:|-]*-{1,}[\s:|-]*\|?\s*$", sep
        ):
            return True
    return False


def _contains_bullets(text: str) -> bool:
    return len(re.findall(r"^\s*[-*+]\s+\S", text, re.MULTILINE)) >= 2


def _contains_numbered(text: str) -> bool:
    return len(re.findall(r"^\s*\d+[.)]\s+\S", text, re.MULTILINE)) >= 2


def _contains_yaml(text: str) -> bool:
    if re.search(r"```ya?ml\b", text, re.IGNORECASE):
        return True
    kv_lines = [
        line
        for line in text.splitlines()
        if re.match(r"^\s*[\w.-]+:\s+\S", line) and "http" not in line.lower()
    ]
    return len(kv_lines) >= 2


def _contains_csv(text: str) -> bool:
    if re.search(r"```csv\b", text, re.IGNORECASE):
        return True
    csv_lines = [
        line for line in text.splitlines() if re.match(r"^[^,\n]+(?:,[^,\n]+){1,}$", line.strip())
    ]
    return len(csv_lines) >= 2


_FORMAT_VERIFIERS = {
    "json": _contains_json,
    "table": _contains_markdown_table,
    "bullet list": _contains_bullets,
    "numbered list": _contains_numbered,
    "yaml": _contains_yaml,
    "csv": _contains_csv,
}


def _requested_formats(prompt: str) -> tuple[str, ...]:
    requested: list[str] = []
    if _REQUEST_JSON_RE.search(prompt):
        requested.append("json")
    if _REQUEST_TABLE_RE.search(prompt):
        requested.append("table")
    if _REQUEST_NUMBERED_RE.search(prompt):
        requested.append("numbered list")
    elif _REQUEST_BULLETS_RE.search(prompt):
        requested.append("bullet list")
    if _REQUEST_YAML_RE.search(prompt):
        requested.append("yaml")
    if _REQUEST_CSV_RE.search(prompt):
        requested.append("csv")
    return _unique(requested)


# ---------------------------------------------------------------------------
# Result model.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PostflightFinding:
    check: str
    severity: str
    reason: str
    suggestion: str
    informational: bool = False


@dataclass(frozen=True)
class PostflightResult:
    prompt: str
    response: str
    needs_attention: bool
    findings: tuple[PostflightFinding, ...]
    checks: tuple[str, ...]
    severity: str
    redacted_response: str | None = None

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        if self.redacted_response:
            data["response"] = self.redacted_response
        return data


# ---------------------------------------------------------------------------
# Individual checks. Each returns a PostflightFinding or None.
# ---------------------------------------------------------------------------
def _check_output_format(prompt: str, response: str) -> PostflightFinding | None:
    requested = _requested_formats(prompt)
    if not requested:
        return None
    missing = [fmt for fmt in requested if not _FORMAT_VERIFIERS[fmt](response)]
    if not missing:
        return None
    return PostflightFinding(
        check="output_format",
        severity=_DEFAULT_SEVERITY["output_format"],
        reason="response does not match requested output format: " + ", ".join(missing),
        suggestion="re-emit the answer in the requested format (" + ", ".join(missing) + ")",
    )


def _check_tests_present(prompt: str, response: str) -> PostflightFinding | None:
    if not _REQUEST_TESTS_RE.search(prompt):
        return None
    if _TEST_INDICATOR_RE.search(response):
        return None
    return PostflightFinding(
        check="tests_present",
        severity=_DEFAULT_SEVERITY["tests_present"],
        reason="tests were requested but the response contains no test code",
        suggestion="add tests (e.g. a test_* function with assertions) covering the change",
    )


def _check_file_change_claim(
    response: str, changed_files: list[str] | None
) -> PostflightFinding | None:
    if not _CHANGE_CLAIM_RE.search(response):
        return None
    if changed_files is None:
        return PostflightFinding(
            check="file_change_claim",
            severity="low",
            reason="response claims file changes but no changed-file metadata was available to verify",
            suggestion="supply the authoritative changed-file list to verify this claim",
            informational=True,
        )
    if len(changed_files) == 0:
        return PostflightFinding(
            check="file_change_claim",
            severity=_DEFAULT_SEVERITY["file_change_claim"],
            reason="response claims file changes but no files were actually changed",
            suggestion="apply the described edits, or correct the response to say nothing changed",
        )
    return None


def _check_constraint_adherence(prompt: str, response: str) -> PostflightFinding | None:
    violated: list[str] = []
    lowered_response = response.lower()
    for match in _NEGATIVE_CONSTRAINT_RE.finditer(prompt):
        token = match.group(1)
        if token.lower() in {"the", "a", "an", "any", "it", "them", "using", "this", "that"}:
            continue
        if re.search(rf"\b{re.escape(token)}\b", lowered_response):
            violated.append(token)
    violated = list(_unique(violated))
    if not violated:
        return None
    return PostflightFinding(
        check="constraint_adherence",
        severity=_DEFAULT_SEVERITY["constraint_adherence"],
        reason="response appears to use terms the prompt asked to avoid: " + ", ".join(violated),
        suggestion="revise to respect the stated constraint, or explain why it was unavoidable",
    )


def _check_placeholders(response: str) -> PostflightFinding | None:
    found = [label for label, pattern in _PLACEHOLDER_PATTERNS if pattern.search(response)]
    found = list(_unique(found))
    if not found:
        return None
    return PostflightFinding(
        check="placeholders",
        severity=_DEFAULT_SEVERITY["placeholders"],
        reason="response left unfilled placeholders: " + ", ".join(found),
        suggestion="replace each placeholder with real content before delivering",
    )


def _check_citations(prompt: str, response: str) -> PostflightFinding | None:
    if not _REQUEST_CITATIONS_RE.search(prompt):
        return None
    if _CITATION_INDICATOR_RE.search(response):
        return None
    return PostflightFinding(
        check="citations",
        severity=_DEFAULT_SEVERITY["citations"],
        reason="citations or references were requested but none are present",
        suggestion="add sources (links, [1]-style markers, or a References section)",
    )


def _check_privacy(response: str) -> tuple[PostflightFinding | None, str | None]:
    findings = sensitive_findings(response)
    if not findings:
        return None, None
    finding = PostflightFinding(
        check="privacy",
        severity="high",
        reason="response appears to contain a secret or credential: " + ", ".join(findings),
        suggestion="remove the secret, rotate it if real, and use a placeholder instead",
    )
    return finding, redact_sensitive(response)


# ---------------------------------------------------------------------------
# Public entry point.
# ---------------------------------------------------------------------------
def analyze_postflight(
    prompt: str,
    response: str,
    *,
    changed_files: list[str] | None = None,
    config: PostflightConfig | None = None,
) -> PostflightResult:
    """Run deterministic postflight checks on an agent response.

    ``changed_files`` is a list of file names/paths (never contents). Pass an
    empty list to assert "nothing changed" (enables the file-change mismatch
    check); pass ``None`` when no such metadata is available (the check then
    degrades to an informational, non-blocking finding).
    """

    prompt = prompt if isinstance(prompt, str) else ""
    response = response if isinstance(response, str) else ""
    config = config or PostflightConfig()

    if not config.enabled or not response.strip():
        return PostflightResult(
            prompt=prompt,
            response=response,
            needs_attention=False,
            findings=(),
            checks=(),
            severity="low",
        )

    # Privacy first, mirroring preflight's precedence.
    privacy_finding, redacted = _check_privacy(response)

    candidates: list[tuple[str, PostflightFinding | None]] = [
        ("privacy", privacy_finding),
        ("output_format", _check_output_format(prompt, response)),
        ("tests_present", _check_tests_present(prompt, response)),
        ("file_change_claim", _check_file_change_claim(response, changed_files)),
        ("constraint_adherence", _check_constraint_adherence(prompt, response)),
        ("placeholders", _check_placeholders(response)),
        ("citations", _check_citations(prompt, response)),
    ]

    findings: list[PostflightFinding] = []
    needs_attention = False
    for check, finding in candidates:
        if finding is None:
            continue
        policy = config.policy_for(check)
        if policy in {"off", "disable"}:
            continue
        findings.append(finding)
        if policy == "block" and not finding.informational:
            needs_attention = True

    severity = _max_severity(f.severity for f in findings) if findings else "low"
    return PostflightResult(
        prompt=prompt,
        response=response,
        needs_attention=needs_attention,
        findings=tuple(findings),
        checks=_unique(f.check for f in findings),
        severity=severity,
        redacted_response=redacted if privacy_finding is not None else None,
    )


__all__ = [
    "POSTFLIGHT_CHECKS",
    "PostflightConfig",
    "PostflightFinding",
    "PostflightResult",
    "analyze_postflight",
]
