/**
 * Structured form data collected by the Prompt Composer webview.
 */
export interface ComposerForm {
  profile: string;
  task: string;
  context: string;
  outputFormat: string;
  successCriteria: string;
  constraints: string;
  examples: string;
}

/**
 * Describes how the composer should treat a profile-specific prompt contract.
 */
export interface ComposerProfileSpec {
  value: string;
  label: string;
  constraintsRequired: boolean;
}

/**
 * Profile metadata shared by the prompt builder and the webview UI.
 */
export const COMPOSER_PROFILE_SPECS: readonly ComposerProfileSpec[] = [
  { value: "general", label: "General", constraintsRequired: false },
  { value: "software", label: "Software / agent work", constraintsRequired: true },
  { value: "image", label: "Image generation", constraintsRequired: false },
  { value: "writing", label: "Writing", constraintsRequired: false },
  { value: "research", label: "Research", constraintsRequired: false },
  { value: "data_analysis", label: "Data analysis", constraintsRequired: false },
  { value: "presentation", label: "Presentation", constraintsRequired: false }
];

/**
 * Default composer form values used when the webview first opens.
 */
export const DEFAULT_COMPOSER_FORM: ComposerForm = {
  profile: "general",
  task: "",
  context: "",
  outputFormat: "",
  successCriteria: "",
  constraints: "",
  examples: ""
};

/**
 * Marker that opts generated prompt files into workspace prompt linting.
 */
export const PROMPT_CHECK_MARKER = "<!-- prompt-preflight: check -->";

/**
 * Builds a Markdown prompt from composer form fields.
 */
export function buildComposedPrompt(form: ComposerForm): string {
  const profile = sanitizeInline(form.profile || "general");
  const sections = [
    PROMPT_CHECK_MARKER,
    "",
    `<!-- profile: ${profile} -->`,
    "",
    "# Task",
    fieldOrPlaceholder(form.task, "[What should the AI agent do?]"),
    "",
    "# Context",
    fieldOrPlaceholder(form.context, "[Relevant background, files, source material, or links]")
  ];

  if (composerProfileRequiresConstraints(profile)) {
    sections.push(
      "",
      "# Constraints",
      bulletLinesOrPlaceholder(
        form.constraints,
        "- [Required boundaries, things to preserve, and out-of-scope areas]"
      )
    );
  }

  sections.push(
    "",
    "# Output Format",
    fieldOrPlaceholder(form.outputFormat, "[Exact structure: bullets, table, JSON, patch, image specs, etc.]"),
    "",
    "# Success Criteria",
    bulletLinesOrPlaceholder(form.successCriteria, "- [How should the result be verified?]")
  );

  const optionalLines = optionalPromptLines(form, profile);
  if (optionalLines.length) {
    sections.push("", "# Optional", ...optionalLines);
  }

  return `${sections.join("\n").trimEnd()}\n`;
}

/**
 * Returns true when a selected profile requires constraints as part of the
 * prompt contract.
 */
export function composerProfileRequiresConstraints(profile: string): boolean {
  return composerProfileSpec(profile).constraintsRequired;
}

/**
 * Finds composer metadata for a profile, falling back to general behavior.
 */
export function composerProfileSpec(profile: string): ComposerProfileSpec {
  const normalized = sanitizeInline(profile);
  return (
    COMPOSER_PROFILE_SPECS.find((spec) => spec.value === normalized) ??
    COMPOSER_PROFILE_SPECS[0]
  );
}

/**
 * Builds the optional Markdown bullets without emitting empty placeholder
 * values that could be mistaken for user intent.
 */
function optionalPromptLines(form: ComposerForm, profile: string): string[] {
  const lines: string[] = [];
  if (!composerProfileRequiresConstraints(profile) && form.constraints.trim()) {
    lines.push(`- Constraints: ${inlineValue(form.constraints)}`);
  }
  if (form.examples.trim()) {
    lines.push(`- Examples: ${inlineValue(form.examples)}`);
  }
  return lines;
}

/**
 * Returns true when the composer form has enough required information to be
 * worth creating or checking as a prompt.
 */
export function composerFormHasRequiredFields(form: ComposerForm): boolean {
  return Boolean(
    form.task.trim() &&
      form.context.trim() &&
      form.outputFormat.trim() &&
      form.successCriteria.trim() &&
      (!composerProfileRequiresConstraints(form.profile) || form.constraints.trim())
  );
}

/**
 * Prevents comment-breaking characters from leaking into inline metadata.
 */
function sanitizeInline(value: string): string {
  return value.replace(/-->/g, "").trim() || "general";
}

/**
 * Renders a multiline field or placeholder text.
 */
function fieldOrPlaceholder(value: string, placeholder: string): string {
  return value.trim() || placeholder;
}

/**
 * Renders success criteria as bullet lines when users type plain newline text.
 */
function bulletLinesOrPlaceholder(value: string, placeholder: string): string {
  const lines = value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  if (!lines.length) {
    return placeholder;
  }
  return lines.map((line) => (line.startsWith("-") ? line : `- ${line}`)).join("\n");
}

/**
 * Renders a single-line optional field value.
 */
function inlineValue(value: string): string {
  return value.trim().replace(/\s+/g, " ");
}
