import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import {
  cliPathForRepo,
  hasPromptPreflightCli,
  repoPathCandidates,
  resolveRepoPathFromCandidates
} from "./repoResolver";
import { resolveTelemetryPolicy } from "./telemetryStore";

/**
 * Severity levels shown in the setup doctor report.
 */
export type SetupCheckStatus = "pass" | "warn" | "fail";

/**
 * One setup finding rendered in the Markdown doctor report.
 */
export interface SetupDoctorCheck {
  status: SetupCheckStatus;
  title: string;
  detail: string;
  fix?: string;
}

/**
 * Inputs required to inspect a Prompt Preflight VS Code setup.
 */
export interface SetupDoctorInput {
  extensionPath: string;
  workspacePath?: string;
  configuredRepoPath?: string;
  pythonPath: string;
  homeDir?: string;
}

/**
 * Full setup doctor model.
 */
export interface SetupDoctorReport {
  checks: SetupDoctorCheck[];
  candidateCliPaths: string[];
}

/**
 * Returns true when the extension itself is running from VS Code's installed
 * extension folder instead of a local source checkout.
 */
function isInstalledExtensionPath(extensionPath: string, homeDir: string): boolean {
  const installedRoots = [
    path.join(homeDir, ".vscode", "extensions"),
    path.join(homeDir, ".vscode-insiders", "extensions")
  ].map((candidate) => path.resolve(candidate));
  const resolvedExtensionPath = path.resolve(extensionPath);
  return installedRoots.some((root) => resolvedExtensionPath.startsWith(root));
}

/**
 * Finds installed Prompt Preflight extension folders that can collide with the
 * Extension Development Host.
 */
export function installedPromptPreflightExtensions(homeDir = os.homedir()): string[] {
  const extensionRoots = [
    path.join(homeDir, ".vscode", "extensions"),
    path.join(homeDir, ".vscode-insiders", "extensions")
  ];
  const matches: string[] = [];

  for (const root of extensionRoots) {
    if (!fs.existsSync(root)) {
      continue;
    }
    for (const entry of fs.readdirSync(root)) {
      if (
        entry.startsWith("akg268.prompt-preflight-vscode") ||
        entry.startsWith("arunkumar-ganesan.prompt-preflight-vscode")
      ) {
        matches.push(path.join(root, entry));
      }
    }
  }

  return matches.sort();
}

/**
 * Adds one check to the report under construction.
 */
function addCheck(
  checks: SetupDoctorCheck[],
  status: SetupCheckStatus,
  title: string,
  detail: string,
  fix?: string
): void {
  checks.push({ status, title, detail, fix });
}

/**
 * Builds a setup doctor report without depending on VS Code APIs, which keeps
 * the logic easy to unit test.
 */
export function buildSetupDoctorReport(input: SetupDoctorInput): SetupDoctorReport {
  const homeDir = input.homeDir || os.homedir();
  const checks: SetupDoctorCheck[] = [];
  const candidates = repoPathCandidates(input);
  const candidateCliPaths = candidates.map(cliPathForRepo);
  const resolvedRepoPath = resolveRepoPathFromCandidates(input);
  const resolvedCliPath = cliPathForRepo(resolvedRepoPath);

  if (hasPromptPreflightCli(resolvedRepoPath)) {
    addCheck(
      checks,
      "pass",
      "Python analyzer found",
      `Using ${resolvedCliPath}`
    );
  } else {
    addCheck(
      checks,
      "fail",
      "Python analyzer missing",
      `Could not find scripts/prompt_preflight.py. Checked ${candidateCliPaths.length} candidate path${candidateCliPaths.length === 1 ? "" : "s"}.`,
      "A Marketplace VSIX should include bundled-analyzer/scripts/prompt_preflight.py. If you are developing from source, open the main prompt-preflight repo as the workspace or set promptPreflight.repoPath to the repo checkout."
    );
  }

  if (input.workspacePath) {
    addCheck(checks, "pass", "Workspace folder open", input.workspacePath);
  } else {
    addCheck(
      checks,
      "warn",
      "No workspace folder open",
      "Some features need a workspace folder to locate .prompt-preflight.json and telemetry.",
      "Open the prompt-preflight repo or a project folder before running checks."
    );
  }

  const installed = installedPromptPreflightExtensions(homeDir);
  const runningInstalled = isInstalledExtensionPath(input.extensionPath, homeDir);
  const oldPublisherInstalled = installed.some((entry) =>
    path.basename(entry).startsWith("akg268.prompt-preflight-vscode")
  );
  if (!runningInstalled && installed.length > 0) {
    addCheck(
      checks,
      "fail",
      "Installed extension collides with dev host",
      installed.join("\n"),
      "Uninstall installed Prompt Preflight extensions before pressing F5, or test the installed VSIX without Extension Development Host."
    );
  } else if (oldPublisherInstalled) {
    addCheck(
      checks,
      "fail",
      "Old publisher extension installed",
      installed.join("\n"),
      "Run `code --uninstall-extension akg268.prompt-preflight-vscode` and reload VS Code."
    );
  } else {
    addCheck(
      checks,
      "pass",
      "No duplicate installed extension detected",
      installed.length ? installed.join("\n") : "No installed Prompt Preflight extension folders found."
    );
  }

  if (input.workspacePath) {
    const policyPath = path.join(input.workspacePath, ".prompt-preflight.json");
    if (fs.existsSync(policyPath)) {
      const telemetry = resolveTelemetryPolicy(input.workspacePath);
      addCheck(
        checks,
        telemetry.enabled ? "pass" : "warn",
        "Workspace policy found",
        `${policyPath}\nTelemetry: ${telemetry.enabled ? "enabled" : "disabled"}\nTelemetry file: ${telemetry.telemetryPath}`,
        telemetry.enabled ? undefined : "Run Prompt Preflight: Enable Local Telemetry to update telemetry.enabled to true."
      );
    } else {
      addCheck(
        checks,
        "warn",
        "Workspace policy missing",
        `${policyPath} does not exist.`,
        "Run Prompt Preflight: Enable Local Telemetry to create .prompt-preflight.json with telemetry.enabled set to true."
      );
    }
  }

  addCheck(
    checks,
    input.pythonPath.trim() ? "pass" : "warn",
    "Python path configured",
    input.pythonPath || "No python path configured.",
    input.pythonPath.trim() ? undefined : "Set promptPreflight.pythonPath to python3 or your Python executable."
  );

  return { checks, candidateCliPaths };
}

/**
 * Renders the setup doctor model as a Markdown report.
 */
export function setupDoctorMarkdown(report: SetupDoctorReport): string {
  const lines = [
    "# Prompt Preflight Setup Doctor",
    "",
    "Use this report to diagnose Extension Development Host, VSIX, repo path, and telemetry setup issues.",
    "",
    "## Checks",
    ""
  ];

  for (const check of report.checks) {
    const icon = check.status === "pass" ? "✅" : check.status === "warn" ? "⚠️" : "❌";
    lines.push(`### ${icon} ${check.title}`, "", "```text", check.detail, "```", "");
    if (check.fix) {
      lines.push("Fix:", "", "```text", check.fix, "```", "");
    }
  }

  lines.push("## CLI paths checked", "");
  for (const candidate of report.candidateCliPaths) {
    lines.push(`- ${candidate}`);
  }
  lines.push("");

  return lines.join("\n");
}
