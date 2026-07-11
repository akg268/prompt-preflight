import assert from "assert/strict";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import {
  bundledAnalyzerPath,
  cliPathForRepo,
  repoPathCandidates,
  resolveRepoPathFromCandidates
} from "../repoResolver";
import { runSuite } from "./testHarness";

/**
 * Creates a temporary directory for resolver tests.
 */
function tempDir(): string {
  return fs.mkdtempSync(path.join(os.tmpdir(), "prompt-preflight-repo-resolver-"));
}

/**
 * Creates the minimal CLI file shape that identifies a prompt-preflight repo.
 */
function markAsPromptPreflightRepo(repoPath: string): void {
  fs.mkdirSync(path.dirname(cliPathForRepo(repoPath)), { recursive: true });
  fs.writeFileSync(cliPathForRepo(repoPath), "#!/usr/bin/env python3\n");
}

/**
 * Unit tests for locating the shared Python analyzer from an installed or
 * development VS Code extension.
 */
export function runRepoResolverTests(): void {
  runSuite("repoResolver", [
    /**
     * Verifies an explicit setting wins over all auto-detected candidates.
     */
    {
      name: "prefers configured repo path",
      run: () => {
        const root = tempDir();
        try {
          const configured = path.join(root, "configured");
          const workspace = path.join(root, "workspace");
          const extension = path.join(root, "extensions", "prompt-preflight-vscode");
          markAsPromptPreflightRepo(configured);
          markAsPromptPreflightRepo(workspace);

          const resolved = resolveRepoPathFromCandidates({
            extensionPath: extension,
            workspacePath: workspace,
            configuredRepoPath: configured
          });

          assert.equal(resolved, configured);
        } finally {
          fs.rmSync(root, { recursive: true, force: true });
        }
      }
    },

    /**
     * Verifies installed VSIX usage works when the main repo is the open workspace.
     */
    {
      name: "uses workspace repo when installed extension parent is not the repo",
      run: () => {
        const root = tempDir();
        try {
          const workspace = path.join(root, "prompt-preflight");
          const extension = path.join(root, ".vscode", "extensions", "prompt-preflight-vscode");
          markAsPromptPreflightRepo(workspace);

          const resolved = resolveRepoPathFromCandidates({
            extensionPath: extension,
            workspacePath: workspace
          });

          assert.equal(resolved, workspace);
        } finally {
          fs.rmSync(root, { recursive: true, force: true });
        }
      }
    },

    /**
     * Verifies users can open the parent folder that contains `prompt-preflight`.
     */
    {
      name: "checks prompt-preflight child under workspace",
      run: () => {
        const root = tempDir();
        try {
          const workspace = path.join(root, "Prompt Optimizer");
          const repo = path.join(workspace, "prompt-preflight");
          const extension = path.join(root, ".vscode", "extensions", "prompt-preflight-vscode");
          markAsPromptPreflightRepo(repo);

          const resolved = resolveRepoPathFromCandidates({
            extensionPath: extension,
            workspacePath: workspace
          });

          assert.equal(resolved, repo);
        } finally {
          fs.rmSync(root, { recursive: true, force: true });
        }
      }
    },

    /**
     * Verifies a Marketplace-style installed extension can use its packaged
     * analyzer without requiring promptPreflight.repoPath.
     */
    {
      name: "uses bundled analyzer when no repo checkout is available",
      run: () => {
        const root = tempDir();
        try {
          const workspace = path.join(root, "workspace");
          const extension = path.join(root, ".vscode", "extensions", "prompt-preflight-vscode");
          const bundled = bundledAnalyzerPath(extension);
          fs.mkdirSync(workspace, { recursive: true });
          markAsPromptPreflightRepo(bundled);

          const resolved = resolveRepoPathFromCandidates({
            extensionPath: extension,
            workspacePath: workspace
          });

          assert.equal(resolved, bundled);
        } finally {
          fs.rmSync(root, { recursive: true, force: true });
        }
      }
    },

    /**
     * Verifies the checked path list includes useful fallback candidates.
     */
    {
      name: "builds ordered candidate paths",
      run: () => {
        const candidates = repoPathCandidates({
          extensionPath: "/tmp/extensions/prompt-preflight-vscode",
          workspacePath: "/tmp/workspace",
          configuredRepoPath: "/tmp/configured"
        });

        assert.deepEqual(candidates.slice(0, 3), [
          "/tmp/configured",
          "/tmp/workspace",
          "/tmp/workspace/prompt-preflight"
        ]);
        assert.ok(candidates.includes("/tmp/extensions/prompt-preflight-vscode/bundled-analyzer"));
      }
    }
  ]);
}
