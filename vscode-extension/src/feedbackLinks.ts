/**
 * Public GitHub issue where beta users can report VS Code extension feedback.
 */
export const BETA_FEEDBACK_ISSUE_URL =
  "https://github.com/akg268/prompt-preflight/issues/69";

/**
 * Returns the canonical beta-feedback issue URL for commands, docs, and tests.
 */
export function betaFeedbackIssueUrl(): string {
  return BETA_FEEDBACK_ISSUE_URL;
}
