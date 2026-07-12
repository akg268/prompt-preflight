"""Deterministic prompt analysis with no model or network calls."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re
from typing import Iterable, TYPE_CHECKING

if TYPE_CHECKING:
    from .config import Config

from .templates import (
    is_low_information_value,
    questions_for_missing_fields,
    template_profile_for_intent,
    validate_structured_prompt,
)


BYPASS_MARKERS = ("[preflight:skip]", "#preflight-ignore", "/preflight-skip")

ACTION_RE = re.compile(
    r"\b(add|analy[sz]e|answer|brainstorm|build|calculate|change|clean(?:\s*up)?|compare|convert|create|"
    r"delete|deploy|design|destroy|draft|draw|drop|edit|evaluate|find|fix|generate|help|illustrate|implement|"
    r"improve|integrate|investigate|list|look\s+(?:at|into)|make|migrate|modernize|optimi[sz]e|outline|paint|"
    r"plan|polish|prepare|prioritize|proofread|purge|redesign|refactor|remove|rename|render|replace|reply|research|reset|resolve|respond|rewrite|"
    r"ship|summari[sz]e|troubleshoot|truncate|update|upgrade|visuali[sz]e|write)\b",
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
PRODUCTION_RE = re.compile(r"\b(prod(?:uction)?|live|customer[- ]facing)\b", re.IGNORECASE)
DESTRUCTIVE_RE = re.compile(
    r"\b(delete|destroy|drop|purge|remove|reset|truncate)\b", re.IGNORECASE
)
ROLLBACK_RE = re.compile(
    r"\b(backup|canary|dry[- ]run|feature flag|health checks?|rollback|roll back|smoke tests?)\b",
    re.IGNORECASE,
)
PLAN_FIRST_RE = re.compile(
    r"\b(ask before|confirm before|do not (?:change|deploy|edit|run)|dry[- ]run|"
    r"plan first|propose (?:a )?plan|review before|wait for confirmation)\b",
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
STORY_REQUEST_RE = re.compile(
    r"\b(?:create|draft|make|tell|write)\b.*\b(?:bedtime story|children'?s story|"
    r"kids'? story|short story|story|storybook)\b|\bstory\s+(?:about|for|with)\b",
    re.IGNORECASE,
)
STORY_AGE_RANGE_RE = re.compile(
    r"\b(?:ages?\s*\d|age\s+range|reading level|grade\s+\d|"
    r"\d+\s*(?:-|to)\s*\d+\s*(?:year|yr)?s?\s*old|"
    r"\d+\s*(?:year|yr)s?\s*old|toddlers?|preschoolers?|kindergarten|"
    r"early readers?|middle grade|young adults?)\b",
    re.IGNORECASE,
)
STORY_ELEMENT_RE = re.compile(
    r"\b(?:character|characters|conflict|ending|hero|lesson|moral|plot|"
    r"protagonist|setting|theme|villain)\b|"
    r"\babout\s+[A-Za-z0-9][A-Za-z0-9' -]{3,}",
    re.IGNORECASE,
)
NEW_BUILD_RE = re.compile(r"\b(build|create|design|implement)\b", re.IGNORECASE)
BROAD_BUILD_VERB_RE = re.compile(
    r"\b(build|create|add|make|implement|develop|set up|setup|scaffold|introduce|stand up|design)\b",
    re.IGNORECASE,
)
BROAD_FEATURE_DOMAIN_RE = re.compile(
    r"\b(auth(?:entication)?|login|signup|sign-in|sso|oauth|billing|payments?|checkout|"
    r"subscriptions?|invoicing|dashboard|onboarding|notifications?|admin(?: panel)?|"
    r"user management|accounts?|profiles?|search|chat|messaging|reporting|analytics|"
    r"settings|api|backend|service|cms|marketplace|feed|permissions?|roles?|rbac)\b",
    re.IGNORECASE,
)
ARCH_SPEC_RE = re.compile(
    r"\b(design|architecture|architect|integrate|scalable|distributed|migrate|rearchitect|system)\b",
    re.IGNORECASE,
)
REQ_SPEC_RE = re.compile(
    r"\b(requirements|stakeholders|acceptance criteria|compliance|prd|product spec)\b",
    re.IGNORECASE,
)
CONCRETE_INTERFACE_RE = re.compile(
    r"\b(?:GET|POST|PUT|DELETE|PATCH)\s+/[^\s]*|\b\w+\([^)]*\)|\b(?:return|status)\s+(?:code\s+)?[2-5]\d{2}\b",
    re.IGNORECASE,
)
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
    r"press release|proposal|readme|report|summary|tone|writing)\b|\bmake\s+this\s+sound\b|"
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
PURPOSE_RE = re.compile(
    r"\b(?:announce|clarify|convince|drive|educate|edit|explain(?:ing)?|help|"
    r"inform|onboard(?:ing)?|persuade|proofread|sell|summari[sz]e|teach|rewrite)\b",
    re.IGNORECASE,
)
SOURCE_RE = re.compile(r"\b(?:attached|based on|provided|source|include|exclude|from|using|according to|dataset|csv|spreadsheet|table)\b", re.IGNORECASE)
TONE_RE = re.compile(r"\b(?:tone|voice|professional|casual|friendly|formal|concise|persuasive|technical)\b", re.IGNORECASE)
LENGTH_RE = re.compile(r"\b(?:words?|pages?|paragraphs?|slides?|minutes?|short|brief|one-page|long-form)\b|\b\d+\s*(?:words?|pages?|slides?|minutes?)\b", re.IGNORECASE)
RESEARCH_SOURCE_RE = re.compile(r"\b(?:sources?|citations?|recent|latest|peer[- ]reviewed|official|date range|from|exclude|include)\b", re.IGNORECASE)
CRITERIA_RE = re.compile(r"\b(?:criteria|compare|pros|cons|tradeoffs?|cost|pricing|features?|requirements?|scorecard)\b", re.IGNORECASE)
DATASET_RE = re.compile(r"\b(?:csv|dataset|spreadsheet|table|columns?|rows?|file|database|query|data source)\b|`[^`]+`", re.IGNORECASE)
METRIC_RE = re.compile(r"\b(?:metric|kpi|revenue|churn|conversion|retention|sales|latency|count|average|median|p95|trend)\b", re.IGNORECASE)
PRESENTATION_STORY_RE = re.compile(r"\b(?:story|narrative|outline|agenda|sections?|key message|takeaway|thesis)\b", re.IGNORECASE)
PRESENTATION_FORMAT_RE = re.compile(r"\b(?:slides?|deck|speaker notes|talk track|minutes?|template|brand|visual style)\b|\b\d+\s*slides?\b", re.IGNORECASE)
ATTACHMENT_CUE_RE = re.compile(
    r"\b(?:attached|attachment|uploaded|provided|this|that|the)\s+"
    r"(?:csv|data(?:set)?|deck|doc(?:ument)?|file|image|pdf|photo|screenshot|spreadsheet|transcript)\b|"
    r"\b(?:attached|uploaded|provided)\b",
    re.IGNORECASE,
)
FILE_REFERENCE_RE = re.compile(
    r"(?<![\w:/.-])(?:[\w.-]+/)*[\w.-]+\."
    r"(?:csv|docx?|json|md|pdf|png|jpe?g|pptx?|sql|tsv|txt|xlsx?)(?![\w.-])",
    re.IGNORECASE,
)
INPUT_FILE_CUE_RE = re.compile(
    r"\b(?:analy[sz]e|based on|compare|from|import|load|open|read|review|summari[sz]e|"
    r"use|using|visuali[sz]e)\b",
    re.IGNORECASE,
)
OUTPUT_FILE_PREFIX_RE = re.compile(r"\b(?:create|generate|output|save|write)\s+`?$", re.IGNORECASE)
OUTPUT_ARTIFACT_RE = re.compile(
    r"\b(?:create|generate|output|save|write)\s+`?(?:[\w.-]+/)*[\w.-]+\."
    r"(?:csv|docx?|html|json|md|pdf|pptx?|toml|txt|xlsx?|ya?ml)\b",
    re.IGNORECASE,
)
SENSITIVE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "private key",
        re.compile(r"(?P<secret>-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----)", re.DOTALL),
    ),
    ("OpenAI-style API key", re.compile(r"\b(?P<secret>sk-[A-Za-z0-9_-]{20,})\b")),
    ("Anthropic-style API key", re.compile(r"\b(?P<secret>sk-ant-[A-Za-z0-9_-]{20,})\b")),
    ("GitHub token", re.compile(r"\b(?P<secret>(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,})\b")),
    ("GitHub fine-grained token", re.compile(r"\b(?P<secret>github_pat_[A-Za-z0-9_]{20,})\b")),
    ("AWS access key", re.compile(r"\b(?P<secret>AKIA[0-9A-Z]{16})\b")),
    ("Google API key", re.compile(r"\b(?P<secret>AIza[0-9A-Za-z_-]{30,})\b")),
    ("Slack token", re.compile(r"\b(?P<secret>xox[baprs]-[A-Za-z0-9-]{20,})\b")),
    (
        "credential assignment",
        re.compile(
            r"\b(?:api[_-]?key|auth[_-]?token|password|secret|token)\s*[:=]\s*"
            r"[\"']?(?P<secret>[A-Za-z0-9_./+=:@%-]{8,})[\"']?",
            re.IGNORECASE,
        ),
    ),
    ("Stripe key", re.compile(r"\b(?P<secret>(?:sk|rk)_(?:live|test)_[A-Za-z0-9]+|whsec_[A-Za-z0-9]+)\b")),
    ("Twilio token", re.compile(r"\b(?P<secret>(?:AC|SK)[0-9a-fA-F]{32})\b")),
    ("Azure token", re.compile(r"\b(?:AccountKey|sig)=(?P<secret>[A-Za-z0-9%+/=]+)\b")),
    ("npm token", re.compile(r"\b(?P<secret>npm_[A-Za-z0-9]{36})\b")),
    ("Docker Hub PAT", re.compile(r"\b(?P<secret>dckr_pat_[A-Za-z0-9_-]{20,})\b")),
    (
        "Vercel / Netlify token",
        re.compile(r"\b(?:VERCEL_TOKEN|NETLIFY_AUTH_TOKEN)\s*=\s*[\"']?(?P<secret>[A-Za-z0-9_-]+)[\"']?")
    ),
    (
        "database URL",
        re.compile(r"\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|amqps?)://[^:\s]+:(?P<secret>[^@\s]+)@[^\s/]+\b", re.IGNORECASE)
    ),
    ("JWT", re.compile(r"\b(?P<secret>eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)\b")),
    (
        ".env block assignment",
        re.compile(r"\b[A-Z0-9_]*(?:SECRET|TOKEN|KEY|PASSWORD|PASS|CREDENTIAL|API)[A-Z0-9_]*\s*=\s*[\"']?(?P<secret>[^\s\"']+)[\"']?")
    ),
)


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
    checks: tuple[str, ...] = ()
    severity: str = "low"
    redacted_prompt: str | None = None
    decision: str = "allow"

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        if self.redacted_prompt:
            data["prompt"] = self.redacted_prompt
        return data


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def _words(prompt: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9_'-]+", prompt)


def _unique(items: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(items))


def _get_secret_value(match: re.Match[str]) -> str:
    return match.group("secret") if "secret" in match.groupdict() else match.group(0)


def is_placeholder(value: str) -> bool:
    val = value.lower()
    if val == "akiaiosfodnn7example":
        return True
    if any(x in val for x in ("example", "changeme", "redacted", "dummy", "placeholder", "insert")):
        return True
    if val.startswith("xxx") or val.startswith("your-"):
        return True
    if (val.startswith("<") and val.endswith(">")) or \
       (val.startswith("${") and val.endswith("}")) or \
       (val.startswith("{{") and val.endswith("}}")):
        return True
    if "process.env" in val or "os.environ" in val or "env." in val:
        return True
    if val in {"password", "pass", "user"}:
        return True
    if len(val) > 0 and len(set(val)) == 1:
        return True
    return False


def sensitive_findings(prompt: str) -> tuple[str, ...]:
    """Return names of likely secrets present in prompt text."""

    findings: list[str] = []
    for label, pattern in SENSITIVE_PATTERNS:
        for match in pattern.finditer(prompt):
            if not is_placeholder(_get_secret_value(match)):
                findings.append(label)
                break
    return _unique(findings)


def redact_sensitive(prompt: str) -> str:
    """Redact likely secrets before rendering user-facing preflight output."""

    redacted = prompt
    for _, pattern in SENSITIVE_PATTERNS:
        def repl(m: re.Match[str]) -> str:
            if is_placeholder(_get_secret_value(m)):
                return m.group(0)
            if "secret" in m.groupdict():
                return m.group(0).replace(m.group("secret"), "[REDACTED_SECRET]")
            return "[REDACTED_SECRET]"
        redacted = pattern.sub(repl, redacted)
    return redacted


def _referenced_files(prompt: str) -> tuple[str, ...]:
    files: list[str] = []
    for match in FILE_REFERENCE_RE.finditer(prompt):
        value = match.group(0).strip("`'\".,;:()[]{}")
        prefix = prompt[max(0, match.start() - 24) : match.start()]
        if OUTPUT_FILE_PREFIX_RE.search(prefix):
            continue
        files.append(value)
    return _unique(files)


def _missing_referenced_files(prompt: str, cwd: str | Path | None) -> tuple[str, ...]:
    if cwd is None or not INPUT_FILE_CUE_RE.search(prompt):
        return ()

    root = Path(cwd).expanduser()
    missing: list[str] = []
    for file_name in _referenced_files(prompt):
        candidate = Path(file_name)
        if candidate.is_absolute():
            exists = candidate.exists()
        else:
            exists = (root / candidate).exists()
        if not exists:
            missing.append(file_name)
    return _unique(missing)


def classify_intent(prompt: str) -> str:
    """Route a prompt to a feedback domain before choosing questions."""
    raw_prompt = (prompt or "").strip()
    text = " ".join(raw_prompt.split())
    if IMAGE_REQUEST_RE.search(text) and not IMAGE_SOFTWARE_RE.search(text):
        return "image_generation"
    if PRESENTATION_REQUEST_RE.search(text):
        return "presentation"
    if DATA_ANALYSIS_REQUEST_RE.search(text):
        return "data_analysis"
    if RESEARCH_REQUEST_RE.search(text):
        return "research"
    if STORY_REQUEST_RE.search(text):
        return "writing"
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


def _template_suggestion_for_intent(intent: str) -> str:
    """Return the Markdown prompt-contract template that best matches intent."""

    return template_profile_for_intent(intent).templates["md"]


def _append_template_suggestion(base_prompt: str, intent: str) -> str:
    """Attach a structured template so vague prompts point users to a contract."""

    return (
        f"{base_prompt}\n\n"
        "Use this structured template to fill the missing fields:\n"
        f"{_template_suggestion_for_intent(intent)}"
    )


def suggest_rewrite(prompt: str, intent: str | None = None) -> str:
    """Create a prompt-shaped example that preserves the user's likely intent."""
    raw_prompt = (prompt or "").strip()
    text = " ".join(raw_prompt.split())
    def _is_enabled(cat: str) -> bool:
        return config.policy_for(cat) != "disable" if config else True

    intent = intent or classify_intent(text)

    if intent == "privacy":
        return (
            "Task: Re-submit this request without secrets or private data. Context: replace any "
            "API keys, tokens, passwords, customer data, or private keys with placeholders such as "
            "[REDACTED_SECRET]. Output format: describe the goal and the safe placeholder values. "
            "Self-check: rotate any real credential that was pasted into a chat or log."
        )

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
        if STORY_REQUEST_RE.search(text):
            return (
                f"Task: {text.rstrip('.!?')}. Audience/reading level: [specific age range, "
                "grade, or reading level]. Story elements: [main character, setting, simple "
                "plot/conflict, ending, and lesson or theme]. Tone/song details: [mood, number "
                "of songs, chorus/refrain style, and any words to include or avoid]. Output "
                "format: [word count, sections, rhyme/no rhyme, plain text, or markdown]. "
                "Self-check: verify it is age-appropriate, coherent, joyful, and easy to read aloud."
            )
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
            "[plan, commands, migration script, or checklist]. Plan-first: propose the rollout and "
            "wait for confirmation before changing production systems. Self-check: verify with "
            "[health checks or acceptance criteria]."
        )

    if action in {"delete", "destroy", "drop", "purge", "remove", "reset", "truncate"}:
        return (
            f"Task: {action.capitalize()} {target} in [specific environment/scope]. Context: "
            "[why it is safe, backups, affected data, and owner approval]. Constraints: preserve "
            "[data, behavior, or users that must not be affected]. Output format: [plan/checklist "
            "first, then commands only after confirmation]. Self-check: verify with [dry run, "
            "backup, rollback, and audit trail]."
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
    config: Config | None = None,
    threshold: int = 45,
    max_questions: int = 3,
    cwd: str | Path | None = None,
    attachments: list[str] | None = None,
) -> Analysis:
    """Score a prompt and return targeted clarification questions.

    ``score`` estimates the expected cost of acting while requirements are unclear.
    A prompt is paused only when it looks actionable, ambiguous, and impactful.
    """

    raw_prompt = (prompt or "").strip()
    text = " ".join(raw_prompt.split())
    def _is_enabled(cat: str) -> bool:
        return config.policy_for(cat) != "disable" if config else True

    lowered = text.lower()
    words = _words(text)
    def _is_enabled(cat: str) -> bool:
        return config.policy_for(cat) != "disable" if config else True


    if not text:
        return Analysis(text, False, 0, 0, 0, (), ())

    secret_findings = sensitive_findings(text)
    redacted_text = redact_sensitive(text) if secret_findings else None
    if secret_findings and (not config or config.policy_for("privacy") != "disable"):
        return Analysis(
            text,
            True,
            100,
            100,
            100,
            ("possible secret or credential in prompt",),
            (
                "Can you remove the secret and replace it with a placeholder such as [REDACTED_SECRET]?",
                "Was this a real credential that should be rotated before continuing?",
            )[: max(1, max_questions)],
            intent="privacy",
            suggested_prompt=suggest_rewrite("[REDACTED_SECRET]", "privacy"),
            checks=("privacy",),
            severity="high",
            redacted_prompt=redacted_text,
            decision="block",
        )

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
            decision="allow",
        )

    is_followup = bool(FOLLOWUP_RE.fullmatch(text))
    is_question = text.endswith("?") or bool(QUESTION_RE.match(text))
    is_creative = bool(CREATIVE_RE.search(text))
    intent = classify_intent(text)
    is_story_request = bool(STORY_REQUEST_RE.search(text))

    template_validation = validate_structured_prompt(raw_prompt, intent)
    if template_validation and template_validation.missing_required and (_is_enabled("template_contract") or _is_enabled("output_contract")):
        missing = template_validation.missing_required
        ambiguity = _clamp(48 + 7 * len(missing))
        impact = 55 if ACTION_RE.search(text) else 45
        score = _clamp(round((ambiguity * impact) ** 0.5))
        ret = Analysis(
            text,
            True,
            score,
            ambiguity,
            impact,
            (
                "structured prompt is missing required fields: "
                + ", ".join(missing),
            ),
            questions_for_missing_fields(missing)[: max(1, max_questions)],
            intent=intent,
            suggested_prompt=template_validation.suggested_template,
            checks=("template_contract", "output_contract"),
            severity="medium" if len(missing) >= 2 or score >= threshold else "low",
            redacted_prompt=redacted_text,
        )
        if not config or config.checks is None:
            decision = config.mode if config else "block"
            d = ret.to_dict()
            d["decision"] = decision
            if ret.redacted_prompt:
                d["prompt"] = text
            return Analysis(**d)
        else:
            sev_val = {"low": 1, "medium": 2, "high": 3, "critical": 4}.get(ret.severity, 1)
            has_block = False
            has_nudge = False
            for chk in ret.checks:
                policy = config.policy_for(chk)
                block_thresh_val = {"low": 1, "medium": 2, "high": 3, "critical": 4}.get(config.threshold_for("block"), 3)
                nudge_thresh_val = {"low": 1, "medium": 2, "high": 3, "critical": 4}.get(config.threshold_for("nudge"), 2)
                if policy == "block" and sev_val >= block_thresh_val:
                    has_block = True
                elif policy == "nudge" and sev_val >= nudge_thresh_val:
                    has_nudge = True
            
            if has_block:
                decision = "block"
            elif has_nudge:
                decision = "nudge"
            else:
                decision = "allow"
            
            d = ret.to_dict()
            if decision == "allow":
                d["should_clarify"] = False
            d["decision"] = decision
            if ret.redacted_prompt:
                d["prompt"] = text
            return Analysis(**d)

    is_image_request = intent == "image_generation"
    is_writing_request = intent == "writing"
    is_research_request = intent == "research"
    is_data_request = intent == "data_analysis"
    is_presentation_request = intent == "presentation"
    is_content_request = intent in {"writing", "research", "data_analysis", "presentation"}
    action_matches = ACTION_RE.findall(text)
    is_action = bool(action_matches)

    def _is_enabled(cat: str) -> bool:
        return config.policy_for(cat) != "disable" if config else True

    if is_followup:
        return Analysis(text, False, 0, 0, 0, ("conversational follow-up",), ())

    if is_low_information_value(text) and (_is_enabled("clarity") or _is_enabled("template_contract")):
        enabled_checks = tuple(
            check for check in ("clarity", "template_contract") if _is_enabled(check)
        )
        decision = config.mode if config and config.checks is None else "block"
        if config and config.checks is not None:
            policies = tuple(config.policy_for(check) for check in enabled_checks)
            if "block" in policies:
                decision = "block"
            elif "nudge" in policies:
                decision = "nudge"
            else:
                decision = "allow"
        should_clarify = decision != "allow"
        return Analysis(
            text,
            should_clarify,
            55 if should_clarify else 0,
            72 if should_clarify else 0,
            42 if should_clarify else 0,
            ("low-information filler text",),
            (
                "Can you replace filler words with the actual task, context, output format, and success criteria?",
            )[: max(1, max_questions)] if should_clarify else (),
            intent=intent,
            suggested_prompt=_append_template_suggestion(suggest_rewrite(text, intent), intent)
            if should_clarify
            else None,
            checks=enabled_checks,
            severity="medium" if should_clarify else "low",
            redacted_prompt=redacted_text,
            decision=decision,
        )

    # Do not interrupt conversation, explanations, confirmations, or lightweight prose.
    if (is_question and not is_action) or (is_creative and not is_story_request and not HIGH_IMPACT_RE.search(text)):
        return Analysis(text, False, 0, 0, 0, ("low-risk informational request",), ())

    ambiguity = 0
    impact = 0
    reasons: list[str] = []
    questions: list[str] = []
    checks: list[str] = []
    needs_prompt_contract_template = False

    vague_terms = _unique(match.group(0).lower() for match in VAGUE_RE.finditer(text))
    has_anchor = bool(ANCHOR_RE.search(text))
    has_constraint = bool(CONSTRAINT_RE.search(text))
    has_success = bool(SUCCESS_RE.search(text))
    has_format = bool(FORMAT_RE.search(text))
    has_broad_scope = bool(BROAD_RE.search(text))
    has_high_impact = bool(HIGH_IMPACT_RE.search(text))
    has_production = bool(PRODUCTION_RE.search(text))
    has_destructive_action = bool(DESTRUCTIVE_RE.search(text))
    has_rollback = bool(ROLLBACK_RE.search(text))
    has_plan_first = bool(PLAN_FIRST_RE.search(text))
    references_attachment = bool(ATTACHMENT_CUE_RE.search(text))
    
    provided_attachments = set(a.lower() for a in (attachments or []))
    provided_attachment_names = set(Path(a).name.lower() for a in (attachments or []))
    missing_files = tuple(
        f for f in _missing_referenced_files(text, cwd)
        if f.lower() not in provided_attachments and Path(f).name.lower() not in provided_attachment_names
    )

    requires_plan_first = bool(
        is_action
        and (
            intent in {"deployment", "migration"}
            or has_production
            or has_destructive_action
            or (has_broad_scope and re.search(r"\b(rewrite|refactor|remove|replace|upgrade)\b", text, re.IGNORECASE))
        )
    )
    is_new_build = intent == "software_build"
    is_bugfix = bool(re.search(r"\bfix\b", text, re.IGNORECASE))

    broad_build_spec_template = None
    if (
        bool(BROAD_BUILD_VERB_RE.search(text))
        and bool(BROAD_FEATURE_DOMAIN_RE.search(text))
        and not has_anchor
        and not has_success
        and not is_bugfix
        and not bool(CONCRETE_INTERFACE_RE.search(text))
    ):
        is_action = True
        needs_prompt_contract_template = True
        if ARCH_SPEC_RE.search(text):
            broad_build_spec_template = "technical_design_spec"
        elif REQ_SPEC_RE.search(text):
            broad_build_spec_template = "requirements_spec"
        else:
            broad_build_spec_template = "feature_spec"
            
        if _is_enabled('plan_first'):
            checks.append("plan_first")
        if _is_enabled('context'):
            checks.append("context")
        ambiguity += 40
        impact += 50
        reasons.append("broad feature build should start with a spec")
        questions.append(f"Consider starting with a spec. Print one using: prompt-preflight --template {broad_build_spec_template}")

    if len(words) <= 4:
        ambiguity += 24
        reasons.append("very short request")
    elif len(words) <= 10:
        ambiguity += 14
        reasons.append("short request")

    if vague_terms and _is_enabled('clarity'):
        checks.append("clarity")
        ambiguity += min(28, 12 + 4 * len(vague_terms))
        reasons.append("subjective or vague language: " + ", ".join(vague_terms[:4]))
        if not is_image_request and not is_content_request:
            questions.append("What observable result would count as the desired improvement?")

    if is_action and not has_anchor and not is_image_request and not is_content_request and _is_enabled('context'):
        checks.append("context")
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
        and _is_enabled('output_contract')
    ):
        checks.append("output_contract")
        ambiguity += 12
        reasons.append("output format is underspecified")
        questions.append(
            "What should the final output look like—patch, plan, table, JSON, docs, screenshots, or another format?"
        )

    if references_attachment and not has_anchor and len(words) <= 6 and not provided_attachments and _is_enabled('context'):
        checks.append("context")
        ambiguity += 16
        reasons.append("referenced attachment or source material is missing")
        questions.append("Can you attach the referenced file, paste the relevant excerpt, or point to the exact path/URL?")

    if missing_files and _is_enabled('context'):
        checks.append("context")
        ambiguity += 18
        reasons.append("referenced file not found: " + ", ".join(missing_files[:3]))
        questions.append("Can you add the referenced file to the workspace or provide the correct path?")

    if requires_plan_first and (_is_enabled('risk') or _is_enabled('plan_first')):
        checks.append("risk")
        checks.append("plan_first")
        impact += 25
        if not has_rollback or not has_plan_first:
            ambiguity += 16
            reasons.append("high-risk change needs rollback or plan-first confirmation")
            questions.insert(
                0,
                "What is the rollback plan, approval boundary, and should the agent produce a plan before making changes?"
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

        if not has_subject_detail and _is_enabled('context'):
            checks.append("context")
            ambiguity += 8
            reasons.append("subject lacks defining visual details")
            questions.append(
                f"What should the {subject_label} look like—type, color, materials, condition, and distinctive details?"
            )
        if not has_image_style and _is_enabled('output_contract'):
            checks.append("output_contract")
            ambiguity += 8
            reasons.append("no visual style or mood")
            questions.append(
                "What visual style and mood do you want—photorealistic, illustrated, cinematic, 3D, or something else?"
            )
        if (not has_image_scene or not has_image_format) and _is_enabled('output_contract'):
            checks.append("output_contract")
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
        has_story_age_range = bool(STORY_AGE_RANGE_RE.search(text))
        has_story_elements = bool(STORY_ELEMENT_RE.search(text))
        has_story_length = bool(LENGTH_RE.search(text))

        if not has_audience and _is_enabled('context'):
            checks.append("context")
            ambiguity += 10
            reasons.append("no writing audience")
            questions.append("Who is the audience, and what should they do or understand after reading it?")
        if is_story_request and not has_story_age_range and _is_enabled('context'):
            checks.append("context")
            ambiguity += 8
            reasons.append("children's story age range or reading level is underspecified")
            questions.append("What exact age range or reading level should the story target?")
        if is_story_request and not has_story_elements and _is_enabled('context'):
            checks.append("context")
            ambiguity += 14
            reasons.append("story characters, setting, plot, or lesson are underspecified")
            questions.append("Who are the main characters, what is the setting, and what simple plot or lesson should the story include?")
        if is_story_request and not has_story_length and _is_enabled('output_contract'):
            checks.append("output_contract")
            ambiguity += 10
            reasons.append("story length or structure is underspecified")
            questions.append("How long should the story be, and should songs be full lyrics, short choruses, or simple placeholders?")
        if (not has_goal or not has_source) and _is_enabled('context'):
            checks.append("context")
            ambiguity += 12
            reasons.append("writing purpose or source material is underspecified")
            questions.append("What key points, source material, and boundaries should be included or excluded?")
        if not has_tone_or_length and _is_enabled('output_contract'):
            checks.append("output_contract")
            ambiguity += 10
            reasons.append("writing tone, length, or format is underspecified")
            questions.append("What tone, length, output format, and example style should the writing use?")

    if is_research_request:
        has_goal = bool(GOAL_RE.search(text) or QUESTION_RE.match(text))
        has_sources = bool(RESEARCH_SOURCE_RE.search(text))
        has_criteria = bool(CRITERIA_RE.search(text) or has_format)

        if not has_goal and _is_enabled('context'):
            checks.append("context")
            ambiguity += 10
            reasons.append("no specific research question")
            questions.append("What decision or question should the research answer?")
        if not has_sources and _is_enabled('context'):
            checks.append("context")
            ambiguity += 10
            reasons.append("research sources or scope are underspecified")
            questions.append("What sources, date range, geography, and exclusions should be used?")
        if not has_criteria and _is_enabled('output_contract'):
            checks.append("output_contract")
            ambiguity += 10
            reasons.append("research criteria or output format is underspecified")
            questions.append("What comparison criteria, output format, citation needs, and uncertainty rules do you want?")

    if is_data_request:
        has_dataset = bool(DATASET_RE.search(text) or has_anchor)
        has_metric = bool(METRIC_RE.search(text))
        has_output = bool(has_format or re.search(r"\b(chart|graph|dashboard|summary|report|table)\b", text, re.IGNORECASE))

        if not has_dataset and _is_enabled('context'):
            checks.append("context")
            ambiguity += 12
            reasons.append("no dataset or data source")
            questions.append("What dataset, file, table, or columns should be analyzed?")
        if not has_metric and _is_enabled('context'):
            checks.append("context")
            ambiguity += 10
            reasons.append("analysis question or metric is underspecified")
            questions.append("What question, metric, segment, or trend should the analysis answer?")
        if not has_output and _is_enabled('output_contract'):
            checks.append("output_contract")
            ambiguity += 8
            reasons.append("analysis output format is underspecified")
            questions.append("What output do you want—chart, table, summary, JSON, dashboard, or code—and how should it be validated?")

    if is_presentation_request:
        has_audience = bool(AUDIENCE_RE.search(text))
        has_goal = bool(GOAL_RE.search(text))
        has_story = bool(PRESENTATION_STORY_RE.search(text))
        has_deck_format = bool(PRESENTATION_FORMAT_RE.search(text) or has_format)

        if not has_audience and _is_enabled('context'):
            checks.append("context")
            ambiguity += 12
            reasons.append("no presentation audience")
            questions.append("Who is the audience, and what decision or takeaway should the presentation drive?")
        if (not has_goal or not has_story) and _is_enabled('context'):
            checks.append("context")
            ambiguity += 14
            reasons.append("presentation goal or storyline is underspecified")
            questions.append("What key message, sections, and takeaways should the deck include?")
        if not has_deck_format and _is_enabled('output_contract'):
            checks.append("output_contract")
            ambiguity += 8
            reasons.append("presentation format is underspecified")
            questions.append("How many slides, what visual style, speaker notes, timing, and example deck/style should it follow?")

    if has_broad_scope and not is_image_request and not is_content_request and _is_enabled('risk'):
        checks.append("risk")
        ambiguity += 14
        impact += 20
        reasons.append("broad scope")

    if is_action and not is_image_request and not is_content_request and (has_broad_scope or has_high_impact) and not has_constraint and _is_enabled('risk'):
        checks.append("risk")
        ambiguity += 10
        reasons.append("no boundaries or invariants")
        questions.append("What must remain unchanged, and are there technical or product constraints?")

    if is_action and not is_image_request and not is_content_request and (has_broad_scope or has_high_impact or vague_terms) and not has_success and _is_enabled('output_contract'):
        checks.append("output_contract")
        ambiguity += 8
        reasons.append("no verification or success criteria")
        questions.append("How should completion be verified—tests, examples, or acceptance criteria?")

    first_action = action_matches[0] if action_matches else ""
    task_target = _action_target(text, first_action) if first_action else "[specific target]"
    has_contract_task = bool(is_action and task_target != "[specific target]")
    has_contract_intent = bool(GOAL_RE.search(text) or PURPOSE_RE.search(text) or has_success)
    if is_story_request:
        has_contract_context = bool(STORY_ELEMENT_RE.search(text))
    elif is_writing_request:
        has_contract_context = bool(SOURCE_RE.search(text) or AUDIENCE_RE.search(text))
    elif is_image_request:
        has_contract_context = bool(IMAGE_SCENE_RE.search(text))
    elif is_research_request:
        has_contract_context = bool(RESEARCH_SOURCE_RE.search(text) or SOURCE_RE.search(text))
    elif is_data_request:
        has_contract_context = bool(DATASET_RE.search(text) or has_anchor)
    elif is_presentation_request:
        has_contract_context = bool(PRESENTATION_STORY_RE.search(text) or SOURCE_RE.search(text))
    else:
        has_contract_context = bool(has_anchor or references_attachment or SOURCE_RE.search(text))
    has_contract_rules = bool(
        has_constraint
        or has_plan_first
        or has_rollback
        or TONE_RE.search(text)
        or CRITERIA_RE.search(text)
    )
    has_contract_output = bool(
        has_format
        or has_success
        or LENGTH_RE.search(text)
        or IMAGE_FORMAT_RE.search(text)
        or PRESENTATION_FORMAT_RE.search(text)
        or OUTPUT_ARTIFACT_RE.search(text)
    )
    missing_contract_fields: list[str] = []
    if not has_contract_task:
        missing_contract_fields.append("task")
    if not has_contract_intent:
        missing_contract_fields.append("intent/purpose")
    if not has_contract_context:
        missing_contract_fields.append("context")
    if not has_contract_rules:
        missing_contract_fields.append("rules/constraints")
    if not has_contract_output:
        missing_contract_fields.append("output format")

    if (
        len(missing_contract_fields) >= 3
        and (is_action or is_content_request or is_image_request)
        and (_is_enabled("template_contract") or _is_enabled("risk") or _is_enabled("output_contract"))
    ):
        needs_prompt_contract_template = True
        if _is_enabled("template_contract"):
            checks.append("template_contract")
        if _is_enabled("risk"):
            checks.append("risk")
        ambiguity += min(28, 10 + 4 * len(missing_contract_fields))
        impact += 20
        reasons.append("missing prompt contract fields: " + ", ".join(missing_contract_fields))
        if not questions:
            questions.append(
                "Can you rewrite this using a structured template with task, intent/purpose, context, rules/constraints, and output format?"
            )

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
        checks.append("risk")
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
    should_clarify = bool(
        needs_prompt_contract_template
        or (is_action and ambiguity >= 30 and impact >= 35 and score >= threshold)
    )

    if should_clarify and not questions:
        if is_image_request:
            questions.append("What subject, visual style, composition, and output format do you want?")
        else:
            questions.append("What exact outcome should be produced, and where should the change be made?")
    if should_clarify and has_broad_scope and not has_anchor:
        questions.insert(0, "Which part should we start with instead of changing the entire project at once?")

    suggested_prompt = suggest_rewrite(text, intent) if should_clarify else None
    if should_clarify and broad_build_spec_template:
        from .templates import load_template_profiles
        profiles = load_template_profiles()
        if broad_build_spec_template in profiles:
            suggested_prompt = (
                f"{suggested_prompt or text}\n\n"
                "Use this structured template to fill the missing fields:\n"
                f"{profiles[broad_build_spec_template].templates['md']}"
            )
    elif should_clarify and needs_prompt_contract_template and suggested_prompt:
        suggested_prompt = _append_template_suggestion(suggested_prompt, intent)
    if should_clarify and requires_plan_first and suggested_prompt and "Plan-first:" not in suggested_prompt:
        suggested_prompt += (
            " Plan-first: inspect the relevant context, propose a safe plan, and wait for "
            "confirmation before making irreversible changes."
        )

    severity = "low"
    if should_clarify:
        if needs_prompt_contract_template or "risk" in checks or (impact >= 80 and not is_content_request and not is_image_request):
            severity = "high"
        elif score >= 55:
            severity = "medium"

    # Per-check decision engine
    decision = "allow"
    if should_clarify:
        if not config or config.checks is None:
            decision = config.mode if config else "block"
        else:
            sev_val = {"low": 1, "medium": 2, "high": 3, "critical": 4}.get(severity, 1)
            
            has_block = False
            has_nudge = False
            for chk in _unique(checks):
                policy = config.policy_for(chk)
                
                block_thresh = config.threshold_for("block")
                block_thresh_val = {"low": 1, "medium": 2, "high": 3, "critical": 4}.get(block_thresh, 3)
                
                nudge_thresh = config.threshold_for("nudge")
                nudge_thresh_val = {"low": 1, "medium": 2, "high": 3, "critical": 4}.get(nudge_thresh, 2)

                if policy == "block" and sev_val >= block_thresh_val:
                    has_block = True
                elif policy == "nudge" and sev_val >= nudge_thresh_val:
                    has_nudge = True

            if has_block:
                decision = "block"
            elif has_nudge:
                decision = "nudge"
            else:
                decision = "allow"
                should_clarify = False
        
    return Analysis(
        prompt=text,
        should_clarify=should_clarify,
        score=score,
        ambiguity=ambiguity,
        impact=impact,
        reasons=_unique(reasons),
        questions=_unique(questions)[: max(1, max_questions)],
        intent=intent,
        suggested_prompt=suggested_prompt,
        checks=_unique(checks),
        severity=severity,
        redacted_prompt=redacted_text,
        decision=decision,
    )
