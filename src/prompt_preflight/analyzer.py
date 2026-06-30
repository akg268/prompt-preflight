"""Deterministic prompt analysis with no model or network calls."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Iterable


BYPASS_MARKERS = ("[preflight:skip]", "#preflight-ignore", "/preflight-skip")

ACTION_RE = re.compile(
    r"\b(add|analy[sz]e|build|calculate|change|clean(?:\s*up)?|compare|convert|create|"
    r"deploy|design|draft|draw|edit|evaluate|find|fix|generate|illustrate|implement|"
    r"improve|integrate|investigate|look\s+into|make|migrate|modernize|optimi[sz]e|outline|paint|"
    r"polish|prepare|proofread|refactor|remove|rename|render|replace|research|rewrite|"
    r"ship|summari[sz]e|update|upgrade|visuali[sz]e|write)\b",
    re.IGNORECASE,
)
VAGUE_RE = re.compile(
    r"\b(better|best|clean(?:er)?|fast(?:er)?|good|great|improve(?:d)?|modern|nice|"
    r"optimi[sz]e(?:d)?|polish(?:ed)?|proper(?:ly)?|robust|scalable|simple|somehow|"
    r"stuff|thing|this|that|it|user[ -]?friendly|work(?:ing)?)\b",
    re.IGNORECASE,
)
BROAD_RE = re.compile(
    r"\b(all|architecture|codebase|entire|everything|everywhere|full|overall|"
    r"production[- ]ready|project|repo(?:sitory)?|system|whole)\b",
    re.IGNORECASE,
)
HIGH_IMPACT_RE = re.compile(
    r"\b(auth(?:entication|orization)?|billing|database|deploy|infrastructure|"
    r"migration|payments?|permissions?|production|security|schema)\b",
    re.IGNORECASE,
)
CONSTRAINT_RE = re.compile(
    r"\b(avoid|constraint|do not|don't|except|keep|limit|must|only|preserve|"
    r"requirement|should not|without)\b",
    re.IGNORECASE,
)
SUCCESS_RE = re.compile(
    r"\b(acceptance|assert|benchmark|done when|expected|pass(?:es|ing)?|test(?:s|ed|ing)?|"
    r"verify|success criteria|should return|should show)\b",
    re.IGNORECASE,
)
FORMAT_RE = re.compile(
    r"\b(as (?:a|an)|bullets?|csv|deck|diff|diagram|doc(?:ument)?|email|html|json|"
    r"markdown|memo|outline|patch|pdf|plan|prd|report|slides?|table|yaml)\b",
    re.IGNORECASE,
)
ANCHOR_RE = re.compile(
    r"(?:[\w.-]+/[\w./-]+|[\w.-]+\.(?:py|js|jsx|ts|tsx|go|rs|java|rb|php|md|json|"
    r"ya?ml|toml|sql|html|css)|https?://\S+|`[^`]+`|#[0-9]+|\b[A-Z][A-Za-z0-9]+(?:[A-Z][A-Za-z0-9]+)+\b)"
)
FOLLOWUP_RE = re.compile(
    r"^(?:yes|no|ok(?:ay)?|sure|continue|go ahead|do it|proceed|approved?|looks good|"
    r"run (?:it|the tests?|tests?)|try again|use (?:that|this)|option \w+)[.!\s]*$",
    re.IGNORECASE,
)
QUESTION_RE = re.compile(
    r"^(?:can|could|do|does|explain|how|is|tell|teach|what|when|where|which|who|why|would)\b",
    re.IGNORECASE,
)
CREATIVE_RE = re.compile(
    r"\b(haiku|joke|poem|story|tagline|translate|translation)\b",
    re.IGNORECASE,
)
NEW_BUILD_RE = re.compile(r"\b(build|create|design|implement)\b", re.IGNORECASE)
IMAGE_REQUEST_RE = re.compile(
    r"\b(?:create|generate|draw|illustrate|make|paint|render)\b.*\b(?:artwork|graphic|"
    r"icon|image|illustration|logo|photo(?:graph)?|picture|portrait|poster|render|"
    r"wallpaper)\b|\b(?:draw|illustrate|paint)\b|"
    r"\brender\s+(?:a|an|the)?\s*(?:building|car|character|house|landscape|product|"
    r"room|scene|vehicle)\b",
    re.IGNORECASE,
)
IMAGE_SOFTWARE_RE = re.compile(
    r"\b(?:image|photo|video)\s+(?:editing|generation|processing|upload)\s+"
    r"(?:api|app|component|feature|pipeline|service)\b",
    re.IGNORECASE,
)
IMAGE_STYLE_RE = re.compile(
    r"\b(?:3d|anime|cinematic|digital art|editorial|illustration|oil painting|"
    r"photorealistic|pixel art|sketch|studio photography|vector|watercolor)\b",
    re.IGNORECASE,
)
IMAGE_SCENE_RE = re.compile(
    r"\b(?:angle|background|beach|bokeh|city|close[- ]up|composition|day|forest|"
    r"lighting|night|overhead|scene|setting|street|studio|sunrise|sunset|wide shot|view)\b",
    re.IGNORECASE,
)
IMAGE_FORMAT_RE = re.compile(
    r"\b(?:aspect ratio|landscape|portrait|resolution|square|transparent background)\b|"
    r"\b\d{1,2}:\d{1,2}\b",
    re.IGNORECASE,
)
WRITING_REQUEST_RE = re.compile(
    r"\b(?:create|draft|edit|improve|rewrite|write|proofread|polish|summari[sz]e|make)\b.*\b(?:announcement|"
    r"article|blog|case study|copy|doc(?:ument)?|draft|email|essay|intro(?:duction)?|memo|message|newsletter|"
    r"proposal|readme|report|summary|tone|writing)\b|\bmake\s+this\s+sound\b|"
    r"\bedit\s+this\s+for\s+clarity\b|\bsummari[sz]e\s+(?:it|this|the)\b",
    re.IGNORECASE,
)
RESEARCH_REQUEST_RE = re.compile(
    r"\b(?:research|compare|investigate|evaluate|find|look\s+into)\b.*\b(?:alternatives?|"
    r"competitors?|market|options?|pricing|sources?|tools?|vendors?)\b|"
    r"\b(?:research|compare|investigate|evaluate|find|look\s+into)\s+(?:it|this|that|the\s+topic)\b",
    re.IGNORECASE,
)
DATA_ANALYSIS_REQUEST_RE = re.compile(
    r"\b(?:analy[sz]e|calculate|clean|explore|find|generate|summari[sz]e|visuali[sz]e|"
    r"make|create)\b.*\b(?:chart|churn|cohort|conversion|csv|data|dataset|"
    r"funnel|insights?|metrics?|numbers?|report|retention|revenue|sales|spreadsheet|"
    r"table|trends?)\b",
    re.IGNORECASE,
)
PRESENTATION_REQUEST_RE = re.compile(
    r"\b(?:build|create|design|draft|make|polish|prepare|summari[sz]e|turn)\b.*\b(?:deck|"
    r"presentation|slides?|webinar)\b|\b(?:pitch|investor|quarterly)\s+deck\b",
    re.IGNORECASE,
)
AUDIENCE_RE = re.compile(r"\b(?:audience|for|to)\s+(?:[A-Za-z][\w-]+|the\s+\w+)", re.IGNORECASE)
GOAL_RE = re.compile(r"\b(?:goal|purpose|so that|to help|decision|objective|call to action|cta)\b", re.IGNORECASE)
SOURCE_RE = re.compile(r"\b(?:based on|source|include|exclude|from|using|according to|dataset|csv|spreadsheet|table)\b", re.IGNORECASE)
TONE_RE = re.compile(r"\b(?:tone|voice|professional|casual|friendly|formal|concise|persuasive|technical)\b", re.IGNORECASE)
LENGTH_RE = re.compile(r"\b(?:words?|pages?|paragraphs?|slides?|minutes?|short|brief|one-page|long-form)\b|\b\d+\s*(?:words?|pages?|slides?|minutes?)\b", re.IGNORECASE)
RESEARCH_SOURCE_RE = re.compile(r"\b(?:sources?|citations?|recent|latest|peer[- ]reviewed|official|date range|from|exclude|include)\b", re.IGNORECASE)
CRITERIA_RE = re.compile(r"\b(?:criteria|compare|pros|cons|tradeoffs?|cost|pricing|features?|requirements?|scorecard)\b", re.IGNORECASE)
DATASET_RE = re.compile(r"\b(?:csv|dataset|spreadsheet|table|columns?|rows?|file|database|query|data source)\b|`[^`]+`", re.IGNORECASE)
METRIC_RE = re.compile(r"\b(?:metric|kpi|revenue|churn|conversion|retention|sales|latency|count|average|median|p95|trend)\b", re.IGNORECASE)
PRESENTATION_STORY_RE = re.compile(r"\b(?:story|narrative|outline|agenda|sections?|key message|takeaway|thesis)\b", re.IGNORECASE)
PRESENTATION_FORMAT_RE = re.compile(r"\b(?:slides?|deck|speaker notes|talk track|minutes?|template|brand|visual style)\b|\b\d+\s*slides?\b", re.IGNORECASE)


@dataclass(frozen=True)
class Analysis:
    prompt: str
    should_clarify: bool
    score: int
    ambiguity: int
    impact: int
    reasons: tuple[str, ...]
    questions: tuple[str, ...]
    intent: str = "general"
    suggested_prompt: str | None = None
    bypassed: bool = False

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def _words(prompt: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9_'-]+", prompt)


def _unique(items: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(items))


def classify_intent(prompt: str) -> str:
    """Route a prompt to a feedback domain before choosing questions."""
    text = " ".join((prompt or "").strip().split())
    if IMAGE_REQUEST_RE.search(text) and not IMAGE_SOFTWARE_RE.search(text):
        return "image_generation"
    if PRESENTATION_REQUEST_RE.search(text):
        return "presentation"
    if DATA_ANALYSIS_REQUEST_RE.search(text):
        return "data_analysis"
    if RESEARCH_REQUEST_RE.search(text):
        return "research"
    if WRITING_REQUEST_RE.search(text):
        return "writing"
    if re.search(r"\bfix\b", text, re.IGNORECASE):
        return "bug_fix"
    if re.search(r"\bdeploy\b", text, re.IGNORECASE):
        return "deployment"
    if re.search(r"\bmigrate\b", text, re.IGNORECASE):
        return "migration"
    if re.search(r"\boptimi[sz]e\b", text, re.IGNORECASE):
        return "optimization"
    if NEW_BUILD_RE.search(text):
        return "software_build"
    if ACTION_RE.search(text):
        return "general_action"
    return "general"


def _image_subject(prompt: str) -> str:
    patterns = (
        r"\b(?:create|generate|make|render)\s+(.+?)\s+(?:artwork|image|illustration|photo|picture|poster|render|wallpaper)\b",
        r"\b(?:artwork|image|illustration|photo|picture|portrait|render)\s+of\s+(.+?)(?:\s+(?:at|in|on|with)\b|[.!?]|$)",
        r"\b(?:draw|illustrate|paint|render)\s+(.+?)(?:[.!?]|$)",
    )
    for pattern in patterns:
        match = re.search(pattern, prompt, re.IGNORECASE)
        if match:
            subject = match.group(1).strip(" .?!")
            if subject:
                return subject
    return "[specific subject]"


def _subject_label(subject: str) -> str:
    label = re.sub(r"^(?:a|an|the)\s+", "", subject, flags=re.IGNORECASE)
    return label if label and not label.startswith("[") else "subject"


def _subject_phrase(subject: str) -> str:
    if subject.startswith("[") or re.match(r"^(?:a|an|the)\s+", subject, re.IGNORECASE):
        return subject
    if subject.lower().endswith("s"):
        return subject
    article = "an" if subject[:1].lower() in "aeiou" else "a"
    return f"{article} {subject}"


def _action_target(prompt: str, action: str) -> str:
    match = re.search(rf"\b{re.escape(action)}\b\s+(.*)", prompt, re.IGNORECASE)
    target = match.group(1).strip(" .?!") if match else ""
    if not target or target.lower() in {"it", "this", "that", "things", "stuff"}:
        return "[specific target]"
    return target


def suggest_rewrite(prompt: str, intent: str | None = None) -> str:
    """Create a prompt-shaped example that preserves the user's likely intent."""
    text = " ".join((prompt or "").strip().split())
    intent = intent or classify_intent(text)

    if intent == "image_generation":
        subject = _subject_phrase(_image_subject(text))
        return (
            f"Task: Create a [photorealistic/illustrated/3D] image of {subject} with "
            "[key colors, materials, and distinctive details]. Context: [setting/background], "
            "[camera angle/composition], and [lighting/mood]. Output format: [aspect ratio, "
            "resolution, file type, or transparent background]. Example/style reference: "
            "[optional image, brand, or style sample]."
        )

    if intent == "writing":
        return (
            f"Task: {text.rstrip('.!?')}. Audience: [who will read it]. "
            "Purpose: [what the writing should accomplish]. Context/source material: "
            "[text, notes, links, transcript, or outline]. Include/exclude: [key points and "
            "boundaries]. Output format: [tone, word count, headings, bullets, email, memo, etc.]. "
            "Example/style reference: [optional sample to imitate]. Self-check: verify the output "
            "matches the requested tone, length, and format."
        )

    if intent == "research":
        return (
            f"Task: {text.rstrip('.!?')}. Research question: [specific decision or question to answer]. "
            "Context/scope: [sources, date range, geography, and exclusions]. Criteria: "
            "[cost, features, tradeoffs, risks, etc.]. Output format: [summary/table/recommendation] "
            "with [citation needs]. Uncertainty rule: mark unknowns instead of guessing."
        )

    if intent == "data_analysis":
        return (
            f"Task: {text.rstrip('.!?')}. Data/context: [file/table/source and relevant columns]. "
            "Question: [metric, segment, or trend to analyze]. Output format: "
            "[chart/table/summary/JSON/dashboard]. Self-check: [totals, row counts, "
            "expected ranges, or comparison method]."
        )

    if intent == "presentation":
        return (
            f"Task: {text.rstrip('.!?')}. Audience: [who will see it]. Goal: "
            "[decision, update, pitch, or teaching outcome]. Context/source material: "
            "[notes, metrics, transcript, or document]. Storyline: [key sections and takeaways]. "
            "Output format: [slide count, visual style, speaker notes, timing, and constraints]. "
            "Example/style reference: [optional deck or brand sample]."
        )

    make_better = re.fullmatch(r"make\s+(.+?)\s+better[.!?]?", text, re.IGNORECASE)
    if make_better:
        target = make_better.group(1).strip()
        return (
            f"Task: Improve {target} in [specific page/component] so [observable outcome]. "
            "Context: [current behavior, screenshots, logs, or examples]. Constraints: keep "
            "[important behavior or design constraints] unchanged. Output format: [patch, plan, "
            "diff summary, screenshots, or docs]. Self-check: verify with [tests or acceptance criteria]."
        )

    action_match = ACTION_RE.search(text)
    if not action_match:
        return (
            f"Task: {text.rstrip('.!?')}. Context: [relevant background or source material]. "
            "Desired outcome: [observable result]. Scope: [specific area]. Constraints: "
            "[important boundaries]. Output format: [exact structure expected]."
        )

    action = re.sub(r"\s+", " ", action_match.group(0).lower())
    target = _action_target(text, action)

    if action == "fix":
        if target == "[specific target]":
            target = "[specific bug]"
        return (
            f"Task: Fix {target} in [file/component]. Current behavior: [what happens]. "
            "Expected behavior: [what should happen]. Context: [reproduction steps, logs, URL, "
            "or failing test]. Constraints: preserve [important behavior]. Output format: "
            "[patch plus brief summary]. Self-check: verify with [test or reproduction steps]."
        )

    if action in {"build", "create", "design", "implement"}:
        return (
            f"Task: {action.capitalize()} {target} for [target users/use case] using "
            "[platform or stack]. Context: [existing code, API, data, or design constraints]. "
            "Include [minimum required features]. Output format: [patch, files changed, plan, "
            "or demo notes]. Self-check: success means [acceptance criteria]."
        )

    if action in {"deploy", "migrate", "upgrade"}:
        if target == "[specific target]":
            target = "[service/application]"
        return (
            f"Task: {action.capitalize()} {target} in [target environment/scope]. "
            "Context: [current version, dependencies, infra, or data shape]. Preserve "
            "[critical behavior or data]. Follow [rollout/rollback constraints]. Output format: "
            "[plan, commands, migration script, or checklist]. Self-check: verify with "
            "[health checks or acceptance criteria]."
        )

    if action in {"optimize", "optimise"}:
        return (
            f"Task: Optimize {target} to achieve [measurable latency/throughput/cost target]. "
            "Context: [baseline metric, traces, query plan, or workload]. Constraints: keep "
            "[behavior or compatibility constraints] unchanged. Output format: [patch plus "
            "before/after measurements]. Self-check: verify with [benchmark]."
        )

    if action in {"improve", "make", "modernize", "polish", "refactor", "rewrite", "clean up"}:
        return (
            f"Task: {action.capitalize()} {target}. Context: [current behavior, examples, "
            "or source material]. Scope: limit to [specific files/components] and achieve "
            "[observable outcome]. Constraints: preserve [constraints]. Output format: "
            "[patch, plan, table, docs, or screenshots]. Self-check: verify with "
            "[tests or acceptance criteria]."
        )

    return (
        f"Task: {text.rstrip('.!?')}. Context: [relevant background, files, data, or examples]. "
        "Scope: [specific files/components]. Desired outcome: [observable result]. Constraints: "
        "[what must remain unchanged]. Output format: [exact structure expected]. Self-check: "
        "verify with [tests or acceptance criteria]."
    )


def analyze_prompt(
    prompt: str,
    *,
    threshold: int = 45,
    max_questions: int = 3,
) -> Analysis:
    """Score a prompt and return targeted clarification questions.

    ``score`` estimates the expected cost of acting while requirements are unclear.
    A prompt is paused only when it looks actionable, ambiguous, and impactful.
    """

    text = " ".join((prompt or "").strip().split())
    lowered = text.lower()
    words = _words(text)

    if not text:
        return Analysis(text, False, 0, 0, 0, (), ())

    if any(marker in lowered for marker in BYPASS_MARKERS):
        return Analysis(
            text,
            False,
            0,
            0,
            0,
            ("one-time bypass marker",),
            (),
            bypassed=True,
        )

    is_followup = bool(FOLLOWUP_RE.fullmatch(text))
    is_question = text.endswith("?") or bool(QUESTION_RE.match(text))
    is_creative = bool(CREATIVE_RE.search(text))
    intent = classify_intent(text)
    is_image_request = intent == "image_generation"
    is_writing_request = intent == "writing"
    is_research_request = intent == "research"
    is_data_request = intent == "data_analysis"
    is_presentation_request = intent == "presentation"
    is_content_request = intent in {"writing", "research", "data_analysis", "presentation"}
    action_matches = ACTION_RE.findall(text)
    is_action = bool(action_matches)

    # Do not interrupt conversation, explanations, confirmations, or lightweight prose.
    if is_followup or (is_question and not is_action) or (is_creative and not HIGH_IMPACT_RE.search(text)):
        reason = "conversational follow-up" if is_followup else "low-risk informational request"
        return Analysis(text, False, 0, 0, 0, (reason,), ())

    ambiguity = 0
    impact = 0
    reasons: list[str] = []
    questions: list[str] = []

    vague_terms = _unique(match.group(0).lower() for match in VAGUE_RE.finditer(text))
    has_anchor = bool(ANCHOR_RE.search(text))
    has_constraint = bool(CONSTRAINT_RE.search(text))
    has_success = bool(SUCCESS_RE.search(text))
    has_format = bool(FORMAT_RE.search(text))
    has_broad_scope = bool(BROAD_RE.search(text))
    has_high_impact = bool(HIGH_IMPACT_RE.search(text))
    is_new_build = intent == "software_build"

    if len(words) <= 4:
        ambiguity += 24
        reasons.append("very short request")
    elif len(words) <= 10:
        ambiguity += 14
        reasons.append("short request")

    if vague_terms:
        ambiguity += min(28, 12 + 4 * len(vague_terms))
        reasons.append("subjective or vague language: " + ", ".join(vague_terms[:4]))
        if not is_image_request and not is_content_request:
            questions.append("What observable result would count as the desired improvement?")

    if is_action and not has_anchor and not is_image_request and not is_content_request:
        ambiguity += 18
        reasons.append("no concrete file, component, URL, issue, or identifier")
        questions.append("What should this apply to—specific files/components, or the whole project?")

    if is_new_build and len(words) <= 10 and not has_constraint and not has_anchor:
        ambiguity += 8
        reasons.append("new build without platform or feature boundaries")
        questions.append("What platform or stack should it use, and what are the minimum required features?")

    if (
        is_action
        and not has_format
        and not has_anchor
        and not is_image_request
        and not is_content_request
        and (vague_terms or len(words) <= 10 or has_broad_scope)
    ):
        ambiguity += 12
        reasons.append("output format is underspecified")
        questions.append(
            "What should the final output look like—patch, plan, table, JSON, docs, screenshots, or another format?"
        )

    if is_image_request:
        subject = _image_subject(text)
        subject_label = _subject_label(subject)
        subject_without_article = re.sub(
            r"^(?:a|an|the)\s+", "", subject, flags=re.IGNORECASE
        )
        subject_words = _words(subject_without_article)
        has_subject_detail = subject != "[specific subject]" and len(subject_words) >= 3
        has_image_style = bool(IMAGE_STYLE_RE.search(text))
        has_image_scene = bool(IMAGE_SCENE_RE.search(text))
        has_image_format = bool(IMAGE_FORMAT_RE.search(text))

        if not has_subject_detail:
            ambiguity += 8
            reasons.append("subject lacks defining visual details")
            questions.append(
                f"What should the {subject_label} look like—type, color, materials, condition, and distinctive details?"
            )
        if not has_image_style:
            ambiguity += 8
            reasons.append("no visual style or mood")
            questions.append(
                "What visual style and mood do you want—photorealistic, illustrated, cinematic, 3D, or something else?"
            )
        if not has_image_scene or not has_image_format:
            ambiguity += 12
            reasons.append("scene, composition, or output format is underspecified")
            questions.append(
                "What setting, camera angle/composition, lighting, and aspect ratio should the image use?"
            )

    if is_writing_request:
        has_audience = bool(AUDIENCE_RE.search(text))
        has_goal = bool(GOAL_RE.search(text))
        has_source = bool(SOURCE_RE.search(text))
        has_tone_or_length = bool(TONE_RE.search(text) or LENGTH_RE.search(text) or has_format)

        if not has_audience:
            ambiguity += 10
            reasons.append("no writing audience")
            questions.append("Who is the audience, and what should they do or understand after reading it?")
        if not has_goal or not has_source:
            ambiguity += 12
            reasons.append("writing purpose or source material is underspecified")
            questions.append("What key points, source material, and boundaries should be included or excluded?")
        if not has_tone_or_length:
            ambiguity += 10
            reasons.append("writing tone, length, or format is underspecified")
            questions.append("What tone, length, output format, and example style should the writing use?")

    if is_research_request:
        has_goal = bool(GOAL_RE.search(text) or QUESTION_RE.match(text))
        has_sources = bool(RESEARCH_SOURCE_RE.search(text))
        has_criteria = bool(CRITERIA_RE.search(text) or has_format)

        if not has_goal:
            ambiguity += 10
            reasons.append("no specific research question")
            questions.append("What decision or question should the research answer?")
        if not has_sources:
            ambiguity += 10
            reasons.append("research sources or scope are underspecified")
            questions.append("What sources, date range, geography, and exclusions should be used?")
        if not has_criteria:
            ambiguity += 10
            reasons.append("research criteria or output format is underspecified")
            questions.append("What comparison criteria, output format, citation needs, and uncertainty rules do you want?")

    if is_data_request:
        has_dataset = bool(DATASET_RE.search(text) or has_anchor)
        has_metric = bool(METRIC_RE.search(text))
        has_output = bool(has_format or re.search(r"\b(chart|graph|dashboard|summary|report|table)\b", text, re.IGNORECASE))

        if not has_dataset:
            ambiguity += 12
            reasons.append("no dataset or data source")
            questions.append("What dataset, file, table, or columns should be analyzed?")
        if not has_metric:
            ambiguity += 10
            reasons.append("analysis question or metric is underspecified")
            questions.append("What question, metric, segment, or trend should the analysis answer?")
        if not has_output:
            ambiguity += 8
            reasons.append("analysis output format is underspecified")
            questions.append("What output do you want—chart, table, summary, JSON, dashboard, or code—and how should it be validated?")

    if is_presentation_request:
        has_audience = bool(AUDIENCE_RE.search(text))
        has_goal = bool(GOAL_RE.search(text))
        has_story = bool(PRESENTATION_STORY_RE.search(text))
        has_deck_format = bool(PRESENTATION_FORMAT_RE.search(text) or has_format)

        if not has_audience:
            ambiguity += 12
            reasons.append("no presentation audience")
            questions.append("Who is the audience, and what decision or takeaway should the presentation drive?")
        if not has_goal or not has_story:
            ambiguity += 14
            reasons.append("presentation goal or storyline is underspecified")
            questions.append("What key message, sections, and takeaways should the deck include?")
        if not has_deck_format:
            ambiguity += 8
            reasons.append("presentation format is underspecified")
            questions.append("How many slides, what visual style, speaker notes, timing, and example deck/style should it follow?")

    if has_broad_scope and not is_image_request and not is_content_request:
        ambiguity += 14
        impact += 20
        reasons.append("broad scope")

    if is_action and not is_image_request and not is_content_request and (has_broad_scope or has_high_impact) and not has_constraint:
        ambiguity += 10
        reasons.append("no boundaries or invariants")
        questions.append("What must remain unchanged, and are there technical or product constraints?")

    if is_action and not is_image_request and not is_content_request and (has_broad_scope or has_high_impact or vague_terms) and not has_success:
        ambiguity += 8
        reasons.append("no verification or success criteria")
        questions.append("How should completion be verified—tests, examples, or acceptance criteria?")

    if has_anchor:
        ambiguity -= 18
    if has_constraint:
        ambiguity -= 10
    if has_success:
        ambiguity -= 12
    if has_format:
        ambiguity -= 8
    if len(words) >= 24:
        ambiguity -= 10
    if "\n- " in prompt or "\n* " in prompt or re.search(r"\n\d+[.)]\s", prompt):
        ambiguity -= 8

    if is_action:
        impact += 35
    if is_image_request:
        impact += 20
    if is_content_request:
        impact += 25
    if is_action and not has_anchor and intent in {"bug_fix", "software_build", "general_action"}:
        impact += 15
    if re.search(r"\b(build|create|deploy|migrate|redesign|rewrite)\b", text, re.IGNORECASE):
        impact += 20
    if has_high_impact:
        impact += 25
        reasons.append("high-impact area")
    if len(action_matches) >= 2:
        impact += 10
    if vague_terms and is_action:
        impact += 10

    ambiguity = _clamp(ambiguity)
    impact = _clamp(impact)
    # The geometric-style blend keeps low-impact chatter and clear high-impact work moving.
    score = _clamp(round((ambiguity * impact) ** 0.5)) if ambiguity and impact else 0

    # A clear target plus explicit verification is sufficient even for costly work.
    should_clarify = bool(is_action and ambiguity >= 30 and impact >= 35 and score >= threshold)

    if should_clarify and not questions:
        if is_image_request:
            questions.append("What subject, visual style, composition, and output format do you want?")
        else:
            questions.append("What exact outcome should be produced, and where should the change be made?")
    if should_clarify and has_broad_scope and not has_anchor:
        questions.insert(0, "Which part should we start with instead of changing the entire project at once?")

    return Analysis(
        prompt=text,
        should_clarify=should_clarify,
        score=score,
        ambiguity=ambiguity,
        impact=impact,
        reasons=_unique(reasons),
        questions=_unique(questions)[: max(1, max_questions)],
        intent=intent,
        suggested_prompt=suggest_rewrite(text, intent) if should_clarify else None,
    )
