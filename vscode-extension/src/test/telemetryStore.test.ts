import assert from "assert/strict";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import {
  loadTelemetryDashboardSummary,
  parseTelemetryJsonl,
  resolveTelemetryPolicy,
  shouldRecordTelemetry,
  summarizeTelemetryEvents
} from "../telemetryStore";
import { runSuite } from "./testHarness";

/**
 * Creates a temporary workspace for telemetry store tests.
 */
function tempWorkspace(): string {
  return fs.mkdtempSync(path.join(os.tmpdir(), "prompt-preflight-vscode-telemetry-"));
}

/**
 * Removes a temporary workspace created by this test file.
 */
function cleanupWorkspace(workspacePath: string): void {
  fs.rmSync(workspacePath, { recursive: true, force: true });
}

/**
 * Builds a JSONL line from a telemetry event object.
 */
function line(event: Record<string, unknown>): string {
  return `${JSON.stringify(event)}\n`;
}

/**
 * Unit tests for local telemetry storage and dashboard summarization.
 */
export function runTelemetryStoreTests(): void {
  runSuite("telemetryStore", [
    /**
     * Verifies JSONL parsing skips bad lines without throwing.
     */
    {
      name: "parses telemetry JSONL and counts malformed lines",
      run: () => {
        const parsed = parseTelemetryJsonl(`${line({ decision: "blocked" })}not-json\n`);

        assert.equal(parsed.events.length, 1);
        assert.equal(parsed.malformedLines, 1);
      }
    },

    /**
     * Verifies the dashboard summary keeps preflight and postflight counts separate.
     */
    {
      name: "summarizes preflight postflight and token observability",
      run: () => {
        const summary = summarizeTelemetryEvents(
          [
            {
              phase: "preflight",
              host: "vscode",
              decision: "blocked",
              checks: ["context", "risk"],
              timestamp: "2026-07-07T10:00:00Z",
              token_observability: {
                prompt: {
                  visible_prompt_tokens_estimate: 12,
                  estimated_total_request_tokens: 1012,
                  token_risk: "low"
                },
                estimated_avoided_retry_tokens: 812
              }
            },
            {
              phase: "postflight",
              host: "claude-code-postflight",
              decision: "postflight_blocked",
              checks: ["output_format"],
              timestamp: "2026-07-07T10:05:00Z",
              token_observability: {
                response: {
                  response_tokens_estimate: 50,
                  token_risk: "low"
                }
              }
            }
          ],
          "/tmp/telemetry.jsonl",
          true
        );

        assert.equal(summary.promptsChecked, 1);
        assert.equal(summary.promptsBlocked, 1);
        assert.equal(summary.postflightResponsesChecked, 1);
        assert.equal(summary.postflightResponsesBlocked, 1);
        assert.equal(summary.tokens.estimatedAvoidedRetryTokens, 812);
        assert.equal(summary.tokens.responseTokensEstimateTotal, 50);
        assert.deepEqual(summary.blockedByCheck[0], { label: "context", value: 1 });
      }
    },

    /**
     * Verifies workspace policy controls the telemetry file and recording state.
     */
    {
      name: "resolves workspace telemetry policy",
      run: () => {
        const workspace = tempWorkspace();
        try {
          fs.writeFileSync(
            path.join(workspace, ".prompt-preflight.json"),
            JSON.stringify({
              telemetry: {
                enabled: true,
                path: "local/telemetry.jsonl"
              }
            })
          );

          const policy = resolveTelemetryPolicy(workspace);

          assert.equal(policy.enabled, true);
          assert.equal(policy.source, "workspace-policy");
          assert.equal(policy.telemetryPath, path.join(workspace, "local", "telemetry.jsonl"));
          assert.equal(shouldRecordTelemetry(workspace), true);
        } finally {
          cleanupWorkspace(workspace);
        }
      }
    },

    /**
     * Verifies boolean telemetry config matches the Python config behavior.
     */
    {
      name: "supports boolean telemetry policy",
      run: () => {
        const workspace = tempWorkspace();
        try {
          fs.writeFileSync(
            path.join(workspace, ".prompt-preflight.json"),
            JSON.stringify({
              telemetry: true
            })
          );

          const policy = resolveTelemetryPolicy(workspace);

          assert.equal(policy.enabled, true);
          assert.equal(policy.source, "workspace-policy");
          assert.equal(policy.telemetryPath, path.join(workspace, ".prompt-preflight-telemetry.jsonl"));
        } finally {
          cleanupWorkspace(workspace);
        }
      }
    },

    /**
     * Verifies a policy without telemetry is still reported as a workspace policy.
     */
    {
      name: "reports workspace policy when telemetry section is missing",
      run: () => {
        const workspace = tempWorkspace();
        try {
          fs.writeFileSync(
            path.join(workspace, ".prompt-preflight.json"),
            JSON.stringify({
              enabled: true
            })
          );

          const policy = resolveTelemetryPolicy(workspace);

          assert.equal(policy.enabled, false);
          assert.equal(policy.source, "workspace-policy");
        } finally {
          cleanupWorkspace(workspace);
        }
      }
    },

    /**
     * Verifies home-relative telemetry paths match the Python config behavior.
     */
    {
      name: "expands home-relative telemetry paths",
      run: () => {
        const workspace = tempWorkspace();
        try {
          fs.writeFileSync(
            path.join(workspace, ".prompt-preflight.json"),
            JSON.stringify({
              telemetry: {
                enabled: true,
                path: "~/prompt-preflight-telemetry.jsonl"
              }
            })
          );

          const policy = resolveTelemetryPolicy(workspace);

          assert.equal(policy.telemetryPath, path.join(os.homedir(), "prompt-preflight-telemetry.jsonl"));
        } finally {
          cleanupWorkspace(workspace);
        }
      }
    },

    /**
     * Verifies a missing telemetry file still produces an empty dashboard model.
     */
    {
      name: "loads empty summary when telemetry file does not exist",
      run: () => {
        const workspace = tempWorkspace();
        try {
          const summary = loadTelemetryDashboardSummary(workspace);

          assert.equal(summary.eventsRead, 0);
          assert.equal(summary.promptsChecked, 0);
          assert.equal(summary.telemetryEnabled, false);
        } finally {
          cleanupWorkspace(workspace);
        }
      }
    }
  ]);
}
