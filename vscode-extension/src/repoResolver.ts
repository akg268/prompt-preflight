import * as fs from "fs";
import * as path from "path";

/**
 * Relative path to the shared Python CLI inside the main prompt-preflight repo.
 */
export const PROMPT_PREFLIGHT_CLI_RELATIVE_PATH = path.join("scripts", "prompt_preflight.py");

/**
 * Relative path to the packaged Python analyzer inside the installed VSIX.
 */
export const BUNDLED_ANALYZER_RELATIVE_PATH = "bundled-analyzer";

/**
 * Inputs used to discover either the main prompt-preflight checkout or the
 * packaged analyzer bundled inside the VSIX.
 */
export interface RepoPathResolutionInput {
  extensionPath: string;
  workspacePath?: string;
  configuredRepoPath?: string;
}

/**
 * Joins a repo candidate with the Python CLI path.
 */
export function cliPathForRepo(repoPath: string): string {
  return path.join(repoPath, PROMPT_PREFLIGHT_CLI_RELATIVE_PATH);
}

/**
 * Joins an extension install path with the bundled Python analyzer root.
 */
export function bundledAnalyzerPath(extensionPath: string): string {
  return path.join(extensionPath, BUNDLED_ANALYZER_RELATIVE_PATH);
}

/**
 * Returns true when a directory looks like the main prompt-preflight checkout.
 */
export function hasPromptPreflightCli(repoPath: string): boolean {
  return fs.existsSync(cliPathForRepo(repoPath));
}

/**
 * Adds a candidate path once, preserving resolution priority.
 */
function addCandidate(candidates: string[], candidate?: string): void {
  if (!candidate || !candidate.trim()) {
    return;
  }
  const resolved = path.resolve(candidate.trim());
  if (!candidates.includes(resolved)) {
    candidates.push(resolved);
  }
}

/**
 * Builds the ordered list of places where the extension should look for the
 * main repo or bundled analyzer. This supports local development, installed
 * VSIX usage, and users who open the parent folder that contains
 * `prompt-preflight`.
 */
export function repoPathCandidates(input: RepoPathResolutionInput): string[] {
  const candidates: string[] = [];

  addCandidate(candidates, input.configuredRepoPath);
  addCandidate(candidates, input.workspacePath);
  if (input.workspacePath) {
    addCandidate(candidates, path.join(input.workspacePath, "prompt-preflight"));
  }

  // Development layout:
  // prompt-preflight/
  //   vscode-extension/
  addCandidate(candidates, path.resolve(input.extensionPath, ".."));

  // Marketplace / installed VSIX layout:
  // prompt-preflight-vscode-<version>/
  //   bundled-analyzer/
  //     scripts/prompt_preflight.py
  //     src/prompt_preflight/...
  addCandidate(candidates, bundledAnalyzerPath(input.extensionPath));

  // Extra fallback for custom packaging layouts that put scripts/ at the
  // extension root.
  addCandidate(candidates, input.extensionPath);

  return candidates;
}

/**
 * Finds the first candidate that contains the shared Python analyzer. If none
 * match, return the first candidate so the caller can build a precise error.
 */
export function resolveRepoPathFromCandidates(input: RepoPathResolutionInput): string {
  const candidates = repoPathCandidates(input);
  return candidates.find(hasPromptPreflightCli) || candidates[0] || path.resolve(input.extensionPath, "..");
}
