/**
 * Public GitHub issue where users can report VS Code extension feedback.
 */
export const BETA_FEEDBACK_ISSUE_URL =
  "https://github.com/akg268/prompt-preflight/issues/69";

/**
 * GitHub new-issue URL used for calibration cases with a concrete example.
 */
export const CALIBRATION_ISSUE_URL =
  "https://github.com/akg268/prompt-preflight/issues/new";

/**
 * Returns the canonical feedback issue URL for commands, docs, and tests.
 */
export function betaFeedbackIssueUrl(): string {
  return BETA_FEEDBACK_ISSUE_URL;
}

/**
 * Prompt-free metadata plus redacted example text used to prefill a calibration
 * GitHub issue only after the user explicitly clicks an issue action.
 */
export interface CalibrationIssueInput {
  kind: "false_positive" | "missed_vagueness" | "open_issue";
  prompt: string;
  intent: string;
  score: number;
  severity: string;
  decision: string;
  checks: string[];
}

/**
 * Returns a prefilled GitHub issue URL for a user-reviewed calibration example.
 */
export function calibrationIssueUrl(input: CalibrationIssueInput): string {
  const labels = "feedback,calibration";
  const title = `[calibration] ${feedbackKindTitle(input.kind)} — ${input.intent}`;
  const body = [
    "## Feedback type",
    "",
    feedbackKindTitle(input.kind),
    "",
    "## Prompt Preflight result",
    "",
    `- Intent: ${input.intent}`,
    `- Vagueness score: ${input.score}/100`,
    `- Severity: ${input.severity}`,
    `- Decision: ${input.decision}`,
    `- Checks: ${input.checks.length ? input.checks.join(", ") : "none"}`,
    "",
    "## Example prompt",
    "",
    "```text",
    input.prompt,
    "```",
    "",
    "## What should have happened?",
    "",
    "- [ ] This should have been allowed",
    "- [ ] This should have been blocked/nudged",
    "- [ ] The questions/template should be different",
    "",
    "## Notes",
    "",
    "Please remove any private details before submitting."
  ].join("\n");

  return `${CALIBRATION_ISSUE_URL}?title=${encodeURIComponent(title)}&labels=${encodeURIComponent(labels)}&body=${encodeURIComponent(body)}`;
}

/**
 * Converts feedback kinds to human-facing text.
 */
function feedbackKindTitle(kind: CalibrationIssueInput["kind"]): string {
  if (kind === "false_positive") {
    return "False positive";
  }
  if (kind === "missed_vagueness") {
    return "Missed vagueness";
  }
  return "Prompt feedback";
}
