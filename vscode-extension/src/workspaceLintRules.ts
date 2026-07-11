import { shouldAnalyzePromptDocument } from "./diagnosticRules";

/**
 * Plain candidate shape used by the workspace linter and its unit tests.
 */
export interface PromptLintCandidate {
  fileName: string;
  text: string;
}

/**
 * Plain lint result shape used to render output summaries.
 */
export interface PromptLintResult {
  fileName: string;
  shouldClarify: boolean;
  score: number;
  severity: string;
  reasons: string[];
  questions: string[];
}

/**
 * Summary counts for files that were discovered but skipped by the opt-in lint
 * marker rule.
 */
export interface PromptLintSummaryCounts {
  skipped: number;
}

/**
 * Include glob for files that can contain structured prompts.
 */
export const PROMPT_LINT_INCLUDE_GLOB = "**/*.{md,xml,toml}";

/**
 * Exclude glob for directories that should not be linted as user prompts.
 */
export const PROMPT_LINT_EXCLUDE_GLOB =
  "**/{.git,node_modules,out,dist,build,.vscode-test,coverage,htmlcov}/**";

/**
 * Single marker that opts a file into workspace prompt linting.
 */
export const PROMPT_PREFLIGHT_CHECK_MARKER = "prompt-preflight: check";

/**
 * Number of characters at the beginning of the file where the opt-in marker is
 * accepted.
 */
const MARKER_SCAN_LIMIT = 800;

/**
 * Maps file extensions to VS Code language IDs.
 */
export function languageIdForFileName(fileName: string): string | undefined {
  const lower = fileName.toLowerCase();
  if (lower.endsWith(".md")) {
    return "markdown";
  }
  if (lower.endsWith(".xml")) {
    return "xml";
  }
  if (lower.endsWith(".toml")) {
    return "toml";
  }
  return undefined;
}

/**
 * Decides whether one workspace file should be linted as an active prompt.
 */
export function shouldLintPromptCandidate(candidate: PromptLintCandidate): boolean {
  const languageId = languageIdForFileName(candidate.fileName);
  if (!languageId) {
    return false;
  }

  if (!hasPromptPreflightCheckMarker(candidate.text)) {
    return false;
  }

  return shouldAnalyzePromptDocument(languageId, candidate.text, {
    fileName: candidate.fileName
  });
}

/**
 * Detects the single opt-in marker near the top of a prompt file.
 */
export function hasPromptPreflightCheckMarker(text: string): boolean {
  return text.slice(0, MARKER_SCAN_LIMIT).toLowerCase().includes(PROMPT_PREFLIGHT_CHECK_MARKER);
}

/**
 * Builds a concise text summary for the workspace lint output channel.
 */
export function workspaceLintSummary(
  results: PromptLintResult[],
  counts: PromptLintSummaryCounts = { skipped: 0 }
): string {
  const failing = results.filter((result) => result.shouldClarify);
  const lines = [
    "Prompt Preflight workspace lint",
    "",
    `Files checked: ${results.length}`,
    `Files skipped: ${counts.skipped}`,
    `Needs clarification: ${failing.length}`,
    `Opt-in marker required: ${PROMPT_PREFLIGHT_CHECK_MARKER}`,
    ""
  ];

  if (!results.length) {
    lines.push("No prompt files opted into workspace lint.");
  } else if (!failing.length) {
    lines.push("All checked prompt files are clear to send.");
  } else {
    for (const result of failing) {
      const reason = result.reasons[0] ? ` — ${result.reasons[0]}` : "";
      const question = result.questions[0] ? ` Ask: ${result.questions[0]}` : "";
      lines.push(
        `- ${result.fileName}: Vagueness score ${result.score}/100 (${result.severity})${reason}${question}`
      );
    }
  }

  return `${lines.join("\n")}\n`;
}
