import * as path from "path";

/**
 * Standard repo-level Prompt Preflight policy file name.
 */
export const TEAM_POLICY_FILE_NAME = ".prompt-preflight.json";

/**
 * Default prompt-free telemetry file path used by the generated team policy.
 */
export const DEFAULT_POLICY_TELEMETRY_PATH = ".prompt-preflight-telemetry.jsonl";

/**
 * Plain document spec for opening a new team policy template.
 */
export interface TeamPolicyDocumentSpec {
  language: string;
  content: string;
}

/**
 * Checks whether an unknown value is an editable JSON object.
 */
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/**
 * Builds the expected absolute policy path for a workspace root.
 */
export function teamPolicyFilePath(workspacePath: string): string {
  return path.join(workspacePath, TEAM_POLICY_FILE_NAME);
}

/**
 * Builds a copy-pasteable default team policy JSON template.
 */
export function teamPolicyTemplateText(): string {
  return `${JSON.stringify(
    {
      enabled: true,
      mode: "block",
      threshold: 45,
      max_questions: 3,
      checks: {
        clarity: "nudge",
        context: "nudge",
        output_contract: "nudge",
        template_contract: "block",
        risk: "block",
        plan_first: "block",
        privacy: "block"
      },
      severity_thresholds: {
        block: "high",
        nudge: "medium"
      },
      telemetry: {
        enabled: false,
        path: DEFAULT_POLICY_TELEMETRY_PATH
      },
      token_observability: {
        enabled: true,
        default_max_output_tokens: 1000,
        estimated_retry_output_tokens: 800
      }
    },
    null,
    2
  )}\n`;
}

/**
 * Returns policy JSON with prompt-free local telemetry explicitly enabled.
 */
export function policyTextWithTelemetryEnabled(policyText: string): string {
  const parsed: unknown = JSON.parse(policyText);
  if (!isRecord(parsed)) {
    throw new Error("Policy file must contain a JSON object.");
  }

  const telemetry = isRecord(parsed.telemetry) ? { ...parsed.telemetry } : {};
  telemetry.enabled = true;
  if (typeof telemetry.path !== "string" || !telemetry.path.trim()) {
    telemetry.path = DEFAULT_POLICY_TELEMETRY_PATH;
  }
  parsed.telemetry = telemetry;

  return `${JSON.stringify(parsed, null, 2)}\n`;
}

/**
 * Builds the untitled document spec shown when a workspace has no team policy
 * file yet.
 */
export function teamPolicyDocumentSpec(): TeamPolicyDocumentSpec {
  return {
    language: "json",
    content: teamPolicyTemplateText()
  };
}
