import * as fs from "fs";
import * as os from "os";
import * as path from "path";

/**
 * Default local telemetry file name used by the Python CLI and host hooks.
 */
export const DEFAULT_TELEMETRY_FILE_NAME = ".prompt-preflight-telemetry.jsonl";

/**
 * Raw telemetry event shape read from Prompt Preflight's JSONL file.
 */
export type TelemetryEvent = Record<string, unknown>;

/**
 * Describes where the extension should read telemetry and whether new VS Code
 * checks should append events.
 */
export interface TelemetryPolicy {
  enabled: boolean;
  telemetryPath: string;
  source: "workspace-policy" | "default";
}

/**
 * Summarizes one bar in a dashboard chart.
 */
export interface TelemetryBar {
  label: string;
  value: number;
}

/**
 * Token totals shown in the dashboard. Values are estimates, not billing truth.
 */
export interface TokenTelemetrySummary {
  eventsWithEstimates: number;
  visiblePromptTokensEstimateTotal: number;
  estimatedRequestTokensTotal: number;
  responseTokensEstimateTotal: number;
  estimatedAvoidedRetryTokens: number;
  promptRisk: TelemetryBar[];
  responseRisk: TelemetryBar[];
}

/**
 * Aggregated telemetry data used by the webview dashboard.
 */
export interface TelemetryDashboardSummary {
  telemetryPath: string;
  telemetryEnabled: boolean;
  policySource: "workspace-policy" | "default";
  eventsRead: number;
  malformedLines: number;
  promptsChecked: number;
  promptsBlocked: number;
  promptsNudged: number;
  promptsAllowed: number;
  promptsBypassed: number;
  followupsAccepted: number;
  postflightResponsesChecked: number;
  postflightResponsesBlocked: number;
  decisions: TelemetryBar[];
  blockedByCheck: TelemetryBar[];
  postflightBlockedByCheck: TelemetryBar[];
  hosts: TelemetryBar[];
  dailyEvents: TelemetryBar[];
  tokens: TokenTelemetrySummary;
}

/**
 * Parses a JSON-like object section from `.prompt-preflight.json`.
 */
function readJsonObject(filePath: string): Record<string, unknown> | undefined {
  if (!fs.existsSync(filePath)) {
    return undefined;
  }

  try {
    const parsed = JSON.parse(fs.readFileSync(filePath, "utf8"));
    return isRecord(parsed) ? parsed : undefined;
  } catch {
    return undefined;
  }
}

/**
 * Checks whether an unknown value is a plain object-like record.
 */
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/**
 * Resolves a configured telemetry path relative to the workspace root.
 */
function resolveTelemetryFilePath(workspacePath: string, configuredPath: unknown): string {
  const rawPath = typeof configuredPath === "string" && configuredPath.trim()
    ? configuredPath.trim()
    : DEFAULT_TELEMETRY_FILE_NAME;
  const expandedPath = rawPath === "~" || rawPath.startsWith("~/")
    ? path.join(os.homedir(), rawPath.slice(2))
    : rawPath;
  return path.isAbsolute(expandedPath) ? expandedPath : path.join(workspacePath, expandedPath);
}

/**
 * Reads telemetry policy from `.prompt-preflight.json`, falling back to the
 * default local JSONL path when no policy exists.
 */
export function resolveTelemetryPolicy(workspacePath: string): TelemetryPolicy {
  const policyPath = path.join(workspacePath, ".prompt-preflight.json");
  const policy = readJsonObject(policyPath);

  if (!policy) {
    return {
      enabled: false,
      telemetryPath: path.join(workspacePath, DEFAULT_TELEMETRY_FILE_NAME),
      source: "default"
    };
  }

  const telemetry = policy.telemetry;
  if (isRecord(telemetry)) {
    return {
      enabled: Boolean(telemetry.enabled),
      telemetryPath: resolveTelemetryFilePath(workspacePath, telemetry.path),
      source: "workspace-policy"
    };
  }

  return {
    enabled: Boolean(telemetry),
    telemetryPath: resolveTelemetryFilePath(workspacePath, undefined),
    source: "workspace-policy"
  };
}

/**
 * Returns true when VS Code prompt checks should append local telemetry events.
 */
export function shouldRecordTelemetry(workspacePath?: string): boolean {
  if (!workspacePath) {
    return false;
  }
  return resolveTelemetryPolicy(workspacePath).enabled;
}

/**
 * Parses JSONL telemetry text while counting malformed lines for diagnostics.
 */
export function parseTelemetryJsonl(text: string): { events: TelemetryEvent[]; malformedLines: number } {
  const events: TelemetryEvent[] = [];
  let malformedLines = 0;

  for (const line of text.split(/\r?\n/)) {
    if (!line.trim()) {
      continue;
    }
    try {
      const parsed = JSON.parse(line);
      if (isRecord(parsed)) {
        events.push(parsed);
      } else {
        malformedLines += 1;
      }
    } catch {
      malformedLines += 1;
    }
  }

  return { events, malformedLines };
}

/**
 * Reads events from the local telemetry file, returning an empty set if the file
 * has not been created yet.
 */
export function readTelemetryFile(filePath: string): { events: TelemetryEvent[]; malformedLines: number } {
  if (!fs.existsSync(filePath)) {
    return { events: [], malformedLines: 0 };
  }
  return parseTelemetryJsonl(fs.readFileSync(filePath, "utf8"));
}

/**
 * Converts a map of counts into sorted chart bars.
 */
function barsFromCounts(counts: Map<string, number>): TelemetryBar[] {
  return [...counts.entries()]
    .map(([label, value]) => ({ label, value }))
    .sort((left, right) => right.value - left.value || left.label.localeCompare(right.label));
}

/**
 * Adds one to a count map for the provided label.
 */
function increment(counts: Map<string, number>, label: string): void {
  counts.set(label, (counts.get(label) || 0) + 1);
}

/**
 * Safely reads a number-like field from a telemetry object.
 */
function numberField(record: Record<string, unknown>, key: string): number {
  const value = record[key];
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

/**
 * Safely reads a string-like field from a telemetry object.
 */
function stringField(record: Record<string, unknown>, key: string, fallback: string): string {
  const value = record[key];
  return typeof value === "string" && value.trim() ? value : fallback;
}

/**
 * Normalizes missing legacy event phases to `preflight`.
 */
function eventPhase(event: TelemetryEvent): "preflight" | "postflight" | "other" {
  const phase = stringField(event, "phase", "preflight");
  if (phase === "preflight" || phase === "postflight") {
    return phase;
  }
  return "other";
}

/**
 * Extracts check names from either preflight or postflight event shapes.
 */
function eventChecks(event: TelemetryEvent): string[] {
  const checks = event.checks;
  if (!Array.isArray(checks)) {
    return [];
  }
  return checks.filter((check): check is string => typeof check === "string" && check.trim().length > 0);
}

/**
 * Converts an ISO timestamp into a compact YYYY-MM-DD dashboard bucket.
 */
function dayBucket(event: TelemetryEvent): string {
  const timestamp = event.timestamp;
  if (typeof timestamp !== "string" || timestamp.length < 10) {
    return "unknown";
  }
  return timestamp.slice(0, 10);
}

/**
 * Adds prompt/response token observability fields into running totals.
 */
function addTokenObservability(
  event: TelemetryEvent,
  totals: TokenTelemetrySummary
): void {
  const tokenPayload = isRecord(event.token_observability) ? event.token_observability : undefined;
  if (!tokenPayload) {
    return;
  }

  totals.eventsWithEstimates += 1;
  totals.estimatedAvoidedRetryTokens += numberField(tokenPayload, "estimated_avoided_retry_tokens");

  const prompt = isRecord(tokenPayload.prompt) ? tokenPayload.prompt : undefined;
  if (prompt) {
    totals.visiblePromptTokensEstimateTotal += numberField(prompt, "visible_prompt_tokens_estimate");
    totals.estimatedRequestTokensTotal += numberField(prompt, "estimated_total_request_tokens");
    incrementRisk(totals.promptRisk, stringField(prompt, "token_risk", "unknown"));
  }

  const response = isRecord(tokenPayload.response) ? tokenPayload.response : undefined;
  if (response) {
    totals.responseTokensEstimateTotal += numberField(response, "response_tokens_estimate");
    incrementRisk(totals.responseRisk, stringField(response, "token_risk", "unknown"));
  }
}

/**
 * Adds a token-risk count to an existing bar list.
 */
function incrementRisk(risks: TelemetryBar[], risk: string): void {
  const existing = risks.find((bar) => bar.label === risk);
  if (existing) {
    existing.value += 1;
  } else {
    risks.push({ label: risk, value: 1 });
  }
}

/**
 * Summarizes parsed telemetry events for charts and KPI cards.
 */
export function summarizeTelemetryEvents(
  events: TelemetryEvent[],
  telemetryPath: string,
  telemetryEnabled: boolean,
  malformedLines = 0,
  policySource: "workspace-policy" | "default" = "default"
): TelemetryDashboardSummary {
  const decisions = new Map<string, number>();
  const blockedByCheck = new Map<string, number>();
  const postflightBlockedByCheck = new Map<string, number>();
  const hosts = new Map<string, number>();
  const dailyEvents = new Map<string, number>();
  const tokens: TokenTelemetrySummary = {
    eventsWithEstimates: 0,
    visiblePromptTokensEstimateTotal: 0,
    estimatedRequestTokensTotal: 0,
    responseTokensEstimateTotal: 0,
    estimatedAvoidedRetryTokens: 0,
    promptRisk: [],
    responseRisk: []
  };

  let promptsChecked = 0;
  let promptsBlocked = 0;
  let promptsNudged = 0;
  let promptsAllowed = 0;
  let promptsBypassed = 0;
  let followupsAccepted = 0;
  let postflightResponsesChecked = 0;
  let postflightResponsesBlocked = 0;

  for (const event of events) {
    const phase = eventPhase(event);
    const decision = stringField(event, "decision", "unknown");
    increment(hosts, stringField(event, "host", "unknown"));
    increment(dailyEvents, dayBucket(event));
    addTokenObservability(event, tokens);

    if (phase === "preflight") {
      promptsChecked += 1;
      increment(decisions, decision);
      if (decision === "blocked") {
        promptsBlocked += 1;
        for (const check of eventChecks(event)) {
          increment(blockedByCheck, check);
        }
      } else if (decision === "nudged") {
        promptsNudged += 1;
      } else if (decision === "allowed") {
        promptsAllowed += 1;
      } else if (decision === "bypassed") {
        promptsBypassed += 1;
      } else if (decision === "followup_accepted") {
        followupsAccepted += 1;
      }
    }

    if (phase === "postflight") {
      postflightResponsesChecked += 1;
      if (decision === "postflight_blocked") {
        postflightResponsesBlocked += 1;
        for (const check of eventChecks(event)) {
          increment(postflightBlockedByCheck, check);
        }
      }
    }
  }

  tokens.promptRisk = tokens.promptRisk.sort((left, right) => right.value - left.value);
  tokens.responseRisk = tokens.responseRisk.sort((left, right) => right.value - left.value);
  const dailyBars = [...dailyEvents.entries()]
    .map(([label, value]) => ({ label, value }))
    .sort((left, right) => left.label.localeCompare(right.label));

  return {
    telemetryPath,
    telemetryEnabled,
    policySource,
    eventsRead: events.length,
    malformedLines,
    promptsChecked,
    promptsBlocked,
    promptsNudged,
    promptsAllowed,
    promptsBypassed,
    followupsAccepted,
    postflightResponsesChecked,
    postflightResponsesBlocked,
    decisions: barsFromCounts(decisions),
    blockedByCheck: barsFromCounts(blockedByCheck),
    postflightBlockedByCheck: barsFromCounts(postflightBlockedByCheck),
    hosts: barsFromCounts(hosts),
    dailyEvents: dailyBars,
    tokens
  };
}

/**
 * Loads and summarizes telemetry for one workspace root.
 */
export function loadTelemetryDashboardSummary(workspacePath: string): TelemetryDashboardSummary {
  const policy = resolveTelemetryPolicy(workspacePath);
  const parsed = readTelemetryFile(policy.telemetryPath);
  return summarizeTelemetryEvents(
    parsed.events,
    policy.telemetryPath,
    policy.enabled,
    parsed.malformedLines,
    policy.source
  );
}
