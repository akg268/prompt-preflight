import * as fs from "fs";
import { spawn } from "child_process";
import * as vscode from "vscode";
import {
  cliPathForRepo,
  repoPathCandidates,
  resolveRepoPathFromCandidates
} from "./repoResolver";

/**
 * Mirrors the JSON contract emitted by the existing Prompt Preflight Python CLI.
 * The extension uses this shape to render user-facing prompt feedback without
 * reimplementing the analyzer rules in TypeScript.
 */
export interface PreflightAnalysis {
  prompt: string;
  should_clarify: boolean;
  score: number;
  ambiguity: number;
  impact: number;
  reasons: string[];
  questions: string[];
  intent: string;
  suggested_prompt?: string;
  bypassed: boolean;
  checks: string[];
  severity: string;
  redacted_prompt?: string;
}

/**
 * Carries runtime paths needed to locate the repo checkout and run analysis in
 * the user's current workspace context.
 */
export interface PreflightOptions {
  extensionPath: string;
  workspacePath?: string;
  recordTelemetry?: boolean;
}

/**
 * Reads a Prompt Preflight VS Code setting from the extension configuration.
 */
function getConfig<T>(key: string): T {
  return vscode.workspace.getConfiguration("promptPreflight").get<T>(key) as T;
}

/**
 * Finds the analyzer root that contains the Python CLI. During local
 * development this can be the repo checkout; in Marketplace/VSIX installs this
 * should resolve to the bundled analyzer shipped with the extension. repoPath
 * remains as an override for contributors testing analyzer changes from source.
 */
export function resolveRepoPath(extensionPath: string, workspacePath?: string): string {
  const configuredRepoPath = getConfig<string>("repoPath");
  return resolveRepoPathFromCandidates({
    extensionPath,
    workspacePath,
    configuredRepoPath
  });
}

/**
 * Builds the absolute path to the existing Python CLI entrypoint.
 */
export function resolveCliPath(repoPath: string): string {
  return cliPathForRepo(repoPath);
}

/**
 * Runs the local Python analyzer and returns the structured analysis result.
 * This keeps the VS Code extension aligned with Codex, Claude Code, Kiro, and
 * CLI behavior because they all use the same Prompt Preflight analyzer.
 */
export async function runPreflight(
  prompt: string,
  options: PreflightOptions
): Promise<PreflightAnalysis> {
  const configuredRepoPath = getConfig<string>("repoPath");
  const repoPath = resolveRepoPath(options.extensionPath, options.workspacePath);
  const cliPath = resolveCliPath(repoPath);

  if (!fs.existsSync(cliPath)) {
    const checkedPaths = repoPathCandidates({
      extensionPath: options.extensionPath,
      workspacePath: options.workspacePath,
      configuredRepoPath
    })
      .map((candidate) => `- ${resolveCliPath(candidate)}`)
      .join("\n");
    throw new Error(
      [
        `Could not find Prompt Preflight CLI at ${cliPath}.`,
        "The VSIX should include a bundled analyzer. If you are developing from source, open the main prompt-preflight repo as your workspace or set promptPreflight.repoPath to your checkout.",
        "",
        "Checked:",
        checkedPaths || "- no candidate paths"
      ].join("\n")
    );
  }

  const pythonPath = getConfig<string>("pythonPath") || "python3";
  const threshold = Math.max(0, Math.min(100, getConfig<number>("threshold") ?? 45));
  const maxQuestions = Math.max(1, Math.min(5, getConfig<number>("maxQuestions") ?? 3));
  const cwd = options.workspacePath || repoPath;

  const args = [
    cliPath,
    "--json",
    "--threshold",
    String(threshold),
    "--max-questions",
    String(maxQuestions)
  ];
  if (options.recordTelemetry) {
    args.push("--record-telemetry");
  }

  return new Promise((resolve, reject) => {
    const child = spawn(pythonPath, args, {
      cwd,
      stdio: ["pipe", "pipe", "pipe"]
    });

    let stdout = "";
    let stderr = "";

    child.stdout.setEncoding("utf8");
    child.stderr.setEncoding("utf8");
    child.stdout.on("data", (chunk: string) => {
      stdout += chunk;
    });
    child.stderr.on("data", (chunk: string) => {
      stderr += chunk;
    });
    child.on("error", reject);
    child.on("close", (code) => {
      // The CLI returns 2 when a prompt needs clarification. For the extension,
      // that is a successful analysis result, not a process failure.
      if (code !== 0 && code !== 2) {
        reject(new Error(stderr || `Prompt Preflight exited with code ${code}`));
        return;
      }

      try {
        resolve(JSON.parse(stdout.trim()) as PreflightAnalysis);
      } catch (error) {
        reject(
          new Error(
            `Prompt Preflight returned invalid JSON. stdout=${stdout.trim()} stderr=${stderr.trim()}`
          )
        );
      }
    });

    child.stdin.end(prompt);
  });
}
