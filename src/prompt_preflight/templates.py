"""Structured prompt contract templates and validation.

The template catalog is data-driven so Codex, Claude Code, Kiro, and the CLI
share the same required fields and examples.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
import json
import re
from typing import Any
from xml.etree import ElementTree


SUPPORTED_TEMPLATE_FORMATS = ("md", "xml", "toml")

FIELD_ALIASES = {
    "action": "task",
    "ask": "task",
    "request": "task",
    "goal": "goal",
    "objective": "goal",
    "purpose": "purpose",
    "background": "context",
    "context_source_material": "context",
    "context_source": "context",
    "problem": "problem_statement",
    "problem_context": "context",
    "problem_statement": "problem_statement",
    "goals": "goals",
    "objectives": "goals",
    "users": "target_users",
    "target_user": "target_users",
    "target_users": "target_users",
    "personas": "target_users",
    "source": "source_material",
    "source_material": "source_material",
    "source_materials": "source_material",
    "source_spec": "source_spec",
    "spec": "source_spec",
    "specification": "source_spec",
    "task_scope": "task",
    "scope_context": "scope",
    "files": "files_components",
    "files_components": "files_components",
    "files_or_components": "files_components",
    "components": "files_components",
    "affected_components": "files_components",
    "affected_files": "files_components",
    "architecture": "architecture",
    "data_changes": "data_changes",
    "api_changes": "api_changes",
    "data_api_changes": "api_changes",
    "data_or_api_changes": "api_changes",
    "tradeoffs": "tradeoffs",
    "trade_offs": "tradeoffs",
    "compatibility": "compatibility",
    "backward_compatibility": "compatibility",
    "migration_plan": "migration_plan",
    "rollout_plan": "rollout_plan",
    "rollback_plan": "rollback_plan",
    "verification_plan": "verification_plan",
    "test_plan": "verification_plan",
    "functional_requirements": "functional_requirements",
    "non_functional_requirements": "non_functional_requirements",
    "user_stories": "user_stories",
    "edge_cases": "edge_cases",
    "open_questions": "open_questions",
    "dependencies": "dependencies",
    "phases": "phases",
    "steps": "implementation_steps",
    "implementation_steps": "implementation_steps",
    "implementation_plan": "implementation_plan",
    "risks": "risks",
    "risk_checks": "risk_checks",
    "missing_information": "missing_information",
    "review_criteria": "criteria",
    "decision": "decision",
    "platform": "platform_stack",
    "stack": "platform_stack",
    "platform_stack": "platform_stack",
    "requirements": "constraints",
    "boundaries": "constraints",
    "include_exclude": "exclusions",
    "includeexclude": "exclusions",
    "out_of_scope": "non_goals",
    "non_goals": "non_goals",
    "output": "output_format",
    "outputs": "output_format",
    "deliverable": "output_format",
    "deliverables": "output_format",
    "output_contract": "output_format",
    "output_format": "output_format",
    "format": "output_format",
    "success": "success_criteria",
    "success_criteria": "success_criteria",
    "acceptance_criteria": "success_criteria",
    "definition_of_done": "success_criteria",
    "done_when": "success_criteria",
    "self_check": "success_criteria",
    "selfcheck": "success_criteria",
    "verify": "success_criteria",
    "verify_with": "success_criteria",
    "validation": "validation",
    "quality_bar": "success_criteria",
    "visual_details": "visual_details",
    "visual_detail": "visual_details",
    "image_details": "visual_details",
    "details": "visual_details",
    "style_mood": "style",
    "style": "style",
    "mood": "style",
    "avoid": "avoid",
    "negative_prompt": "avoid",
    "example": "examples",
    "examples": "examples",
    "example_style_reference": "examples",
    "style_reference": "examples",
    "audience": "audience",
    "reader": "audience",
    "readers": "audience",
    "tone": "tone",
    "voice": "tone",
    "length": "length",
    "research_question": "research_question",
    "question": "question",
    "research_sources": "sources",
    "sources": "sources",
    "criteria": "criteria",
    "comparison_criteria": "criteria",
    "date_range": "date_range",
    "geography": "geography",
    "citation_style": "citation_style",
    "uncertainty_rule": "uncertainty_rule",
    "data": "data_source",
    "data_context": "data_source",
    "data_source": "data_source",
    "dataset": "data_source",
    "metrics": "metrics",
    "metric": "metrics",
    "segments": "segments",
    "filters": "filters",
    "assumptions": "assumptions",
    "story": "storyline",
    "storyline": "storyline",
    "narrative": "storyline",
    "visual_style": "visual_style",
    "speaker_notes": "speaker_notes",
    "privacy": "privacy_notes",
    "privacy_notes": "privacy_notes",
    "plan_first": "plan_first",
    "profile": "profile",
}

PROFILE_ALIASES = {
    "code": "software",
    "coding": "software",
    "developer": "software",
    "development": "software",
    "software_build": "software",
    "bug_fix": "software",
    "image_generation": "image",
    "image-generation": "image",
    "images": "image",
    "data": "data_analysis",
    "data-analysis": "data_analysis",
    "analytics": "data_analysis",
    "slides": "presentation",
    "deck": "presentation",
    "presentations": "presentation",
    "feature": "feature_spec",
    "feature_specification": "feature_spec",
    "feature_spec": "feature_spec",
    "requirements": "requirements_spec",
    "requirements_specification": "requirements_spec",
    "requirements_spec": "requirements_spec",
    "tech_design": "technical_design_spec",
    "technical_design": "technical_design_spec",
    "technical_design_spec": "technical_design_spec",
    "design_spec": "technical_design_spec",
    "implementation": "implementation_plan",
    "implementation_plan": "implementation_plan",
    "execution_prompt": "agent_execution_prompt",
    "agent_prompt": "agent_execution_prompt",
    "agent_execution": "agent_execution_prompt",
    "agent_execution_prompt": "agent_execution_prompt",
    "review_checklist": "spec_review_checklist",
    "spec_review": "spec_review_checklist",
    "spec_review_checklist": "spec_review_checklist",
}

PLACEHOLDER_RE = re.compile(
    r"^(?:\[.*?\]|<.*?>|\{.*?\}|todo|tbd|n/?a|none|optional|example|sample|\.\.\.)$",
    re.IGNORECASE | re.DOTALL,
)
ONLY_PLACEHOLDERS_RE = re.compile(
    r"^(?:[-*]\s*)?(?:\[.*?\]|<.*?>|\{.*?\})(?:\s*(?:,|and|or)?\s*(?:\[.*?\]|<.*?>|\{.*?\}))*\.?$",
    re.IGNORECASE | re.DOTALL,
)
MARKDOWN_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*$")
MARKDOWN_LABEL_RE = re.compile(r"^\s*(?:[-*]\s*)?([A-Za-z][A-Za-z0-9 /_-]{1,48})\s*:\s*(.*)$")
MARKDOWN_PROFILE_COMMENT_RE = re.compile(r"^\s*<!--\s*profile\s*:\s*([A-Za-z0-9_-]+)\s*-->\s*$", re.IGNORECASE)
TOML_KEY_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_-]*)\s*=\s*(.*)$")
CONCRETE_SIGNAL_RE = re.compile(
    r"`[^`]+`|https?://\S+|(?:[\w.-]+/)*[\w.-]+\.[A-Za-z0-9]{1,8}\b|#\d+|\d"
)
FILLER_TOKENS = frozenset(
    {
        "any",
        "anything",
        "asdf",
        "bar",
        "baz",
        "blah",
        "blabla",
        "dummy",
        "foo",
        "ipsum",
        "lorem",
        "random",
        "some",
        "someone",
        "something",
        "someth",
        "somewhere",
        "stuff",
        "thing",
        "things",
        "whatever",
    }
)
GENERIC_FIELD_TOKENS = frozenset(
    {
        "constraint",
        "constraints",
        "content",
        "context",
        "criteria",
        "data",
        "detail",
        "details",
        "example",
        "examples",
        "field",
        "format",
        "info",
        "information",
        "input",
        "material",
        "output",
        "prompt",
        "request",
        "rule",
        "rules",
        "section",
        "source",
        "success",
        "task",
        "text",
    }
)


@dataclass(frozen=True)
class TemplateRequirement:
    label: str
    fields: tuple[str, ...]


@dataclass(frozen=True)
class TemplateProfile:
    name: str
    display_name: str
    intents: tuple[str, ...]
    required: tuple[TemplateRequirement, ...]
    optional: tuple[str, ...]
    templates: dict[str, str]


@dataclass(frozen=True)
class TemplateValidation:
    format: str
    profile: str
    profile_display_name: str
    fields: tuple[str, ...]
    missing_required: tuple[str, ...]
    suggested_template: str

    @property
    def is_complete(self) -> bool:
        return not self.missing_required


def _normalize_name(name: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
    return FIELD_ALIASES.get(normalized, normalized)


def _normalize_profile_name(name: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
    return PROFILE_ALIASES.get(normalized, normalized)


@lru_cache(maxsize=1)
def load_template_profiles() -> dict[str, TemplateProfile]:
    """Load prompt contract profiles from package data."""

    catalog_path = resources.files("prompt_preflight.data").joinpath("prompt_templates.json")
    raw = json.loads(catalog_path.read_text(encoding="utf-8"))
    profiles: dict[str, TemplateProfile] = {}
    for name, payload in raw["profiles"].items():
        required = tuple(
            TemplateRequirement(
                label=str(item["label"]),
                fields=tuple(_normalize_name(field) for field in item["fields"]),
            )
            for item in payload["required"]
        )
        templates = {
            str(template_format): "\n".join(lines).rstrip()
            for template_format, lines in payload["templates"].items()
        }
        profiles[name] = TemplateProfile(
            name=name,
            display_name=str(payload["display_name"]),
            intents=tuple(str(intent) for intent in payload.get("intents", ())),
            required=required,
            optional=tuple(_normalize_name(field) for field in payload.get("optional", ())),
            templates=templates,
        )
    return profiles


def template_profile_for_intent(intent: str | None) -> TemplateProfile:
    """Return the best prompt contract profile for an analyzer intent."""

    profiles = load_template_profiles()
    normalized_intent = _normalize_profile_name(intent or "general")
    if normalized_intent in profiles:
        return profiles[normalized_intent]
    for profile in profiles.values():
        if intent in profile.intents or normalized_intent in profile.intents:
            return profile
    return profiles["general"]


def template_profile_names() -> tuple[str, ...]:
    """Return stable profile names for CLI choices."""

    return tuple(load_template_profiles().keys())


def render_template(profile: str = "general", template_format: str = "md") -> str:
    """Render a copy-pasteable prompt contract template."""

    profiles = load_template_profiles()
    profile_name = _normalize_profile_name(profile)
    if profile_name not in profiles:
        raise ValueError(f"unknown template profile: {profile}")
    if template_format not in SUPPORTED_TEMPLATE_FORMATS:
        raise ValueError(f"unknown template format: {template_format}")
    return profiles[profile_name].templates[template_format]


def _is_meaningful_value(value: str) -> bool:
    stripped = value.strip()
    if not stripped:
        return False
    compact = re.sub(r"\s+", " ", stripped).strip(" .,:;`\"'")
    if not compact:
        return False
    if PLACEHOLDER_RE.fullmatch(compact):
        return False
    if ONLY_PLACEHOLDERS_RE.fullmatch(compact):
        return False
    if is_low_information_value(compact):
        return False
    without_markers = re.sub(r"[-*#>\s`\"'.,:;()]+", "", compact)
    if not without_markers:
        return False
    return True


def is_low_information_value(value: str) -> bool:
    """Return true when text is just filler rather than usable prompt detail."""

    compact = re.sub(r"\s+", " ", value.strip()).strip(" .,:;`\"'")
    if not compact:
        return False
    if CONCRETE_SIGNAL_RE.search(compact):
        return False

    tokens = re.findall(r"[a-z]+", compact.lower())
    if not tokens:
        return False
    if all(token in FILLER_TOKENS for token in tokens):
        return True
    if (
        len(tokens) <= 5
        and any(token in FILLER_TOKENS for token in tokens)
        and all(token in FILLER_TOKENS or token in GENERIC_FIELD_TOKENS for token in tokens)
    ):
        return True
    return False


def _canonical_field(label: str) -> str | None:
    field = _normalize_name(label)
    known_fields = {"profile"}
    for profile in load_template_profiles().values():
        for requirement in profile.required:
            known_fields.update(requirement.fields)
        known_fields.update(profile.optional)
    return field if field in known_fields else None


def _collapse_field_values(fields: dict[str, list[str]]) -> dict[str, str]:
    return {field: "\n".join(parts).strip() for field, parts in fields.items()}


def _parse_markdown_fields(prompt: str) -> dict[str, str]:
    fields: dict[str, list[str]] = {}
    current: str | None = None
    markers = 0

    for line in prompt.splitlines():
        profile_comment = MARKDOWN_PROFILE_COMMENT_RE.match(line)
        if profile_comment:
            fields.setdefault("profile", []).append(profile_comment.group(1))
            markers += 1
            continue

        heading = MARKDOWN_HEADING_RE.match(line)
        if heading:
            field = _canonical_field(heading.group(1))
            current = field
            if field:
                fields.setdefault(field, [])
                markers += 1
            continue

        label = MARKDOWN_LABEL_RE.match(line)
        if label:
            field = _canonical_field(label.group(1))
            if field:
                current = field
                fields.setdefault(field, []).append(label.group(2).strip())
                markers += 1
                continue

        if current:
            fields.setdefault(current, []).append(line)

    if markers < 2:
        return {}
    return _collapse_field_values(fields)


def _parse_xml_fields(prompt: str) -> dict[str, str]:
    stripped = prompt.strip()
    if not stripped.startswith("<"):
        return {}
    try:
        root = ElementTree.fromstring(stripped)
    except ElementTree.ParseError:
        return {}

    fields: dict[str, list[str]] = {}
    profile_attr = root.attrib.get("profile")
    if profile_attr:
        fields.setdefault("profile", []).append(profile_attr)

    root_field = _canonical_field(root.tag)
    if root_field and root_field != "profile":
        fields.setdefault(root_field, []).append(" ".join(root.itertext()))

    for element in root.iter():
        field = _canonical_field(element.tag)
        if not field or field == "profile":
            continue
        value = " ".join(part.strip() for part in element.itertext() if part.strip())
        fields.setdefault(field, []).append(value)

    if len(fields) < 2 and root.tag.lower() not in {"prompt", "structured_prompt"}:
        return {}
    return _collapse_field_values(fields)


def _parse_toml_fields(prompt: str) -> dict[str, str]:
    fields: dict[str, list[str]] = {}
    key_markers = 0
    current_key: str | None = None
    current_parts: list[str] = []

    def flush_current() -> None:
        nonlocal current_key, current_parts
        if current_key:
            fields.setdefault(current_key, []).append("\n".join(current_parts))
        current_key = None
        current_parts = []

    for raw_line in prompt.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            continue
        if current_key:
            current_parts.append(line)
            if "]" in line:
                flush_current()
            continue
        match = TOML_KEY_RE.match(line)
        if not match:
            continue
        field = _canonical_field(match.group(1))
        if not field:
            continue
        value = match.group(2).strip()
        key_markers += 1
        if value.startswith("[") and "]" not in value:
            current_key = field
            current_parts = [value]
        else:
            fields.setdefault(field, []).append(value)

    flush_current()
    if key_markers < 2:
        return {}
    return _collapse_field_values(fields)


def _detect_structured_fields(prompt: str) -> tuple[str, dict[str, str]] | None:
    parsers = (
        ("xml", _parse_xml_fields),
        ("toml", _parse_toml_fields),
        ("md", _parse_markdown_fields),
    )
    for template_format, parser in parsers:
        fields = parser(prompt)
        if fields:
            return template_format, fields
    return None


def _profile_from_fields(fields: dict[str, str], fallback_intent: str | None) -> TemplateProfile:
    profiles = load_template_profiles()
    profile_value = fields.get("profile", "")
    if _is_meaningful_value(profile_value):
        profile_name = _normalize_profile_name(profile_value.strip("\"' "))
        if profile_name in profiles:
            return profiles[profile_name]
    return template_profile_for_intent(fallback_intent)


def validate_structured_prompt(prompt: str, intent: str | None = None) -> TemplateValidation | None:
    """Validate Markdown/XML/TOML prompt contracts when the user provides one.

    Returns ``None`` when the prompt does not look like a supported structured
    prompt. Placeholder-only values such as ``[specific task]`` do not satisfy a
    required field.
    """

    detected = _detect_structured_fields(prompt)
    if not detected:
        return None

    template_format, raw_fields = detected
    profile = _profile_from_fields(raw_fields, intent)
    meaningful_fields = {
        field
        for field, value in raw_fields.items()
        if field != "profile" and _is_meaningful_value(value)
    }
    missing = tuple(
        requirement.label
        for requirement in profile.required
        if not any(field in meaningful_fields for field in requirement.fields)
    )
    return TemplateValidation(
        format=template_format,
        profile=profile.name,
        profile_display_name=profile.display_name,
        fields=tuple(sorted(meaningful_fields)),
        missing_required=missing,
        suggested_template=profile.templates[template_format],
    )


def questions_for_missing_fields(missing_fields: tuple[str, ...]) -> tuple[str, ...]:
    """Turn missing template fields into direct clarification questions."""

    return tuple(f"Fill the required {field} section with concrete details." for field in missing_fields)
