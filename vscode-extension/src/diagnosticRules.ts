/**
 * Minimal analyzer shape needed to create editor diagnostics. Keeping this type
 * local avoids importing VS Code-bound modules into pure unit tests.
 */
export interface DiagnosticAnalysis {
  should_clarify: boolean;
  score: number;
  severity: string;
  reasons: string[];
  questions: string[];
}

/**
 * Plain range shape used by tests and converted to VS Code ranges at runtime.
 */
export interface DiagnosticRangeSummary {
  startLine: number;
  startCharacter: number;
  endLine: number;
  endCharacter: number;
}

/**
 * Plain diagnostic shape used by tests and converted to VS Code diagnostics at
 * runtime.
 */
export interface PromptDiagnosticSummary {
  severity: "warning" | "information";
  message: string;
  source: string;
  code: string;
  range: DiagnosticRangeSummary;
}

/**
 * Optional document metadata used to avoid diagnosing docs and generated files.
 */
export interface PromptDocumentAnalysisOptions {
  fileName?: string;
  isUntitled?: boolean;
  maxCharacters?: number;
}

/**
 * Language IDs that Prompt Preflight treats as possible prompt files.
 */
const PROMPT_LANGUAGE_IDS = new Set(["markdown", "xml", "toml"]);

/**
 * Markdown files that usually document the project instead of containing one
 * active prompt to send to an AI agent.
 */
const DOCUMENTATION_FILE_NAMES = new Set([
  "claude.md",
  "contributing.md",
  "examples.md",
  "kiro.md",
  "launch.md",
  "license.md",
  "postflight.md",
  "readme.md",
  "setup.md",
  "templates.md"
]);

/**
 * Default maximum document size for automatic diagnostics. This avoids running
 * prompt checks on large docs that are unlikely to be single prompts.
 */
export const DEFAULT_DIAGNOSTIC_MAX_CHARACTERS = 8000;

/**
 * Decides whether a document should receive automatic Prompt Preflight
 * diagnostics.
 */
export function shouldAnalyzePromptDocument(
  languageId: string,
  text: string,
  options: PromptDocumentAnalysisOptions = {}
): boolean {
  const trimmed = text.trim();
  const maxCharacters = options.maxCharacters ?? DEFAULT_DIAGNOSTIC_MAX_CHARACTERS;
  return (
    PROMPT_LANGUAGE_IDS.has(languageId) &&
    trimmed.length > 0 &&
    trimmed.length <= maxCharacters &&
    !trimmed.startsWith("# Prompt Preflight Result") &&
    !isDocumentationFile(options.fileName, options.isUntitled)
  );
}

/**
 * Converts analyzer output into plain diagnostic summaries.
 */
export function diagnosticSummariesFromAnalysis(
  analysis: DiagnosticAnalysis,
  text: string
): PromptDiagnosticSummary[] {
  if (!analysis.should_clarify) {
    return [];
  }

  return [
    {
      severity: severityName(analysis.severity),
      message: diagnosticMessage(analysis),
      source: "Prompt Preflight",
      code: "prompt-preflight",
      range: firstMeaningfulLineRange(text)
    }
  ];
}

/**
 * Maps analyzer severity names to editor diagnostic severity names.
 */
function severityName(severity: string): "warning" | "information" {
  return severity.toLowerCase() === "low" ? "information" : "warning";
}

/**
 * Builds a concise Problems-panel message from the analyzer output.
 */
function diagnosticMessage(analysis: DiagnosticAnalysis): string {
  const reason = analysis.reasons[0] ? ` ${analysis.reasons[0]}` : "";
  const question = analysis.questions[0] ? ` Ask: ${analysis.questions[0]}` : "";
  return `Prompt needs clarification. Vagueness score ${analysis.score}/100.${reason}${question} See examples: run "Open Prompt Preflight examples".`;
}

/**
 * Detects project docs that may contain examples of vague prompts but should not
 * be treated as the prompt the user is about to send.
 */
function isDocumentationFile(fileName?: string, isUntitled = false): boolean {
  if (isUntitled || !fileName) {
    return false;
  }

  const normalizedPath = fileName.replace(/\\/g, "/").toLowerCase();
  const baseName = normalizedPath.split("/").pop() || "";
  return normalizedPath.includes("/docs/") || DOCUMENTATION_FILE_NAMES.has(baseName);
}

/**
 * Finds the first non-empty line so the diagnostic underlines the prompt body
 * instead of blank space.
 */
function firstMeaningfulLineRange(text: string): DiagnosticRangeSummary {
  const lines = text.split(/\r?\n/);
  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    if (line.trim().length > 0) {
      return {
        startLine: index,
        startCharacter: 0,
        endLine: index,
        endCharacter: Math.max(line.length, 1)
      };
    }
  }

  return {
    startLine: 0,
    startCharacter: 0,
    endLine: 0,
    endCharacter: 1
  };
}
