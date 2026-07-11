import assert from "assert/strict";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import { buildSetupDoctorReport, setupDoctorMarkdown } from "../setupDoctor";
import { bundledAnalyzerPath, cliPathForRepo } from "../repoResolver";
import { runSuite } from "./testHarness";

/**
 * Creates an isolated filesystem root for setup doctor tests.
 */
function tempRoot(): string {
  return fs.mkdtempSync(path.join(os.tmpdir(), "prompt-preflight-setup-doctor-"));
}

/**
 * Creates the expected Python CLI file inside a fake prompt-preflight repo.
 */
function createCli(repoPath: string): void {
  fs.mkdirSync(path.dirname(cliPathForRepo(repoPath)), { recursive: true });
  fs.writeFileSync(cliPathForRepo(repoPath), "#!/usr/bin/env python3\n");
}

/**
 * Unit tests for the VS Code setup doctor report model.
 */
export function runSetupDoctorTests(): void {
  runSuite("setupDoctor", [
    /**
     * Verifies a healthy local checkout produces passing repo and telemetry checks.
     */
    {
      name: "reports healthy workspace checkout",
      run: () => {
        const root = tempRoot();
        try {
          const repo = path.join(root, "prompt-preflight");
          const extensionPath = path.join(repo, "vscode-extension");
          createCli(repo);
          fs.writeFileSync(
            path.join(repo, ".prompt-preflight.json"),
            JSON.stringify({
              telemetry: {
                enabled: true,
                path: ".prompt-preflight-telemetry.jsonl"
              }
            })
          );

          const report = buildSetupDoctorReport({
            extensionPath,
            workspacePath: repo,
            pythonPath: "python3",
            homeDir: path.join(root, "home")
          });

          assert.equal(report.checks.find((check) => check.title === "Python analyzer found")?.status, "pass");
          assert.equal(report.checks.find((check) => check.title === "Workspace policy found")?.status, "pass");
        } finally {
          fs.rmSync(root, { recursive: true, force: true });
        }
      }
    },

    /**
     * Verifies installed VSIX users pass setup without setting repoPath when
     * the package includes the bundled analyzer.
     */
    {
      name: "reports healthy bundled analyzer install",
      run: () => {
        const root = tempRoot();
        try {
          const extensionPath = path.join(root, "home", ".vscode", "extensions", "prompt-preflight-vscode");
          createCli(bundledAnalyzerPath(extensionPath));

          const report = buildSetupDoctorReport({
            extensionPath,
            workspacePath: path.join(root, "workspace"),
            pythonPath: "python3",
            homeDir: path.join(root, "home")
          });

          const analyzer = report.checks.find((check) => check.title === "Python analyzer found");

          assert.equal(analyzer?.status, "pass");
          assert.match(analyzer?.detail || "", /bundled-analyzer/);
        } finally {
          fs.rmSync(root, { recursive: true, force: true });
        }
      }
    },

    /**
     * Verifies missing CLI paths produce a failing diagnostic with a setup fix.
     */
    {
      name: "reports missing python analyzer",
      run: () => {
        const root = tempRoot();
        try {
          const workspace = path.join(root, "workspace");
          fs.mkdirSync(workspace, { recursive: true });

          const report = buildSetupDoctorReport({
            extensionPath: path.join(root, "extension"),
            workspacePath: workspace,
            pythonPath: "python3",
            homeDir: path.join(root, "home")
          });

          const missing = report.checks.find((check) => check.title === "Python analyzer missing");

          assert.equal(missing?.status, "fail");
          assert.match(missing?.fix || "", /repoPath/);
        } finally {
          fs.rmSync(root, { recursive: true, force: true });
        }
      }
    },

    /**
     * Verifies installed Prompt Preflight copies are flagged during dev-host work.
     */
    {
      name: "reports installed extension collision for development host",
      run: () => {
        const root = tempRoot();
        try {
          const home = path.join(root, "home");
          const installed = path.join(
            home,
            ".vscode",
            "extensions",
            "akg268.prompt-preflight-vscode-0.0.1"
          );
          fs.mkdirSync(installed, { recursive: true });

          const report = buildSetupDoctorReport({
            extensionPath: path.join(root, "repo", "vscode-extension"),
            workspacePath: path.join(root, "repo"),
            pythonPath: "python3",
            homeDir: home
          });

          const collision = report.checks.find((check) =>
            check.title === "Installed extension collides with dev host"
          );

          assert.equal(collision?.status, "fail");
          assert.match(collision?.detail || "", /akg268/);
        } finally {
          fs.rmSync(root, { recursive: true, force: true });
        }
      }
    },

    /**
     * Verifies the Markdown report is readable and includes fixes.
     */
    {
      name: "renders markdown report",
      run: () => {
        const report = {
          checks: [
            {
              status: "warn" as const,
              title: "Workspace policy missing",
              detail: "No policy",
              fix: "Enable Local Telemetry"
            }
          ],
          candidateCliPaths: ["/tmp/prompt-preflight/scripts/prompt_preflight.py"]
        };

        const markdown = setupDoctorMarkdown(report);

        assert.match(markdown, /Prompt Preflight Setup Doctor/);
        assert.match(markdown, /Enable Local Telemetry/);
        assert.match(markdown, /CLI paths checked/);
      }
    }
  ]);
}
