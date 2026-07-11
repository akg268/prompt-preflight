import * as path from "path";
import * as vscode from "vscode";
import { diagnosticSummariesFromAnalysis } from "./diagnosticRules";
import { runPreflight } from "./preflightClient";
import {
  PROMPT_LINT_EXCLUDE_GLOB,
  PROMPT_LINT_INCLUDE_GLOB,
  PromptLintSummaryCounts,
  PromptLintResult,
  shouldLintPromptCandidate,
  workspaceLintSummary
} from "./workspaceLintRules";

/**
 * Converts pure diagnostic severity names to VS Code diagnostic severities.
 */
const VSCODE_SEVERITY: Record<"warning" | "information", vscode.DiagnosticSeverity> = {
  warning: vscode.DiagnosticSeverity.Warning,
  information: vscode.DiagnosticSeverity.Information
};

/**
 * Owns the command that lints all prompt files in a workspace.
 */
export class WorkspacePromptLinter implements vscode.Disposable {
  private readonly diagnostics = vscode.languages.createDiagnosticCollection(
    "prompt-preflight-workspace"
  );
  private readonly output = vscode.window.createOutputChannel("Prompt Preflight");

  /**
   * Stores extension context needed to locate the Python analyzer.
   */
  constructor(private readonly context: vscode.ExtensionContext) {}

  /**
   * Clears output and diagnostics when the extension unloads.
   */
  dispose(): void {
    this.diagnostics.dispose();
    this.output.dispose();
  }

  /**
   * Lints prompt-like files in the first workspace folder and displays a summary.
   */
  async lintWorkspace(): Promise<void> {
    const folder = vscode.workspace.workspaceFolders?.[0];
    if (!folder) {
      void vscode.window.showWarningMessage(
        "Prompt Preflight: open a workspace folder before running workspace lint."
      );
      return;
    }

    this.diagnostics.clear();
    const lintRun = await vscode.window.withProgress(
      {
        location: vscode.ProgressLocation.Notification,
        title: "Prompt Preflight: linting workspace prompt files...",
        cancellable: false
      },
      async () => this.analyzeWorkspaceFolder(folder)
    );

    this.output.clear();
    this.output.appendLine(policyLine(folder.uri.fsPath));
    this.output.append(workspaceLintSummary(lintRun.results, lintRun.counts));
    this.output.show(true);

    const failing = lintRun.results.filter((result) => result.shouldClarify).length;
    if (failing) {
      void vscode.window.showWarningMessage(
        `Prompt Preflight: ${failing} prompt file${failing === 1 ? "" : "s"} need clarification.`
      );
    } else {
      void vscode.window.showInformationMessage("Prompt Preflight: workspace prompt lint passed.");
    }
  }

  /**
   * Finds and analyzes prompt-like files in one workspace folder.
   */
  private async analyzeWorkspaceFolder(
    folder: vscode.WorkspaceFolder
  ): Promise<{ results: PromptLintResult[]; counts: PromptLintSummaryCounts }> {
    const uris = await vscode.workspace.findFiles(
      new vscode.RelativePattern(folder, PROMPT_LINT_INCLUDE_GLOB),
      new vscode.RelativePattern(folder, PROMPT_LINT_EXCLUDE_GLOB)
    );
    const results: PromptLintResult[] = [];
    const counts: PromptLintSummaryCounts = { skipped: 0 };

    for (const uri of uris) {
      const text = await readWorkspaceFile(uri);
      if (!shouldLintPromptCandidate({ fileName: uri.fsPath, text })) {
        counts.skipped += 1;
        continue;
      }

      const analysis = await runPreflight(text, {
        extensionPath: this.context.extensionPath,
        workspacePath: folder.uri.fsPath
      });
      const relativePath = path.relative(folder.uri.fsPath, uri.fsPath);
      results.push({
        fileName: relativePath,
        shouldClarify: analysis.should_clarify,
        score: analysis.score,
        severity: analysis.severity,
        reasons: analysis.reasons,
        questions: analysis.questions
      });
      this.setDiagnostics(uri, text, analysis);
    }

    return { results, counts };
  }

  /**
   * Sets Problems-panel diagnostics for one linted prompt file.
   */
  private setDiagnostics(uri: vscode.Uri, text: string, analysis: Parameters<typeof diagnosticSummariesFromAnalysis>[0]): void {
    const diagnostics = diagnosticSummariesFromAnalysis(analysis, text).map((summary) => {
      const diagnostic = new vscode.Diagnostic(
        new vscode.Range(
          summary.range.startLine,
          summary.range.startCharacter,
          summary.range.endLine,
          summary.range.endCharacter
        ),
        summary.message,
        VSCODE_SEVERITY[summary.severity]
      );
      diagnostic.source = summary.source;
      diagnostic.code = summary.code;
      return diagnostic;
    });
    this.diagnostics.set(uri, diagnostics);
  }
}

/**
 * Reads a workspace file as UTF-8 text.
 */
async function readWorkspaceFile(uri: vscode.Uri): Promise<string> {
  const bytes = await vscode.workspace.fs.readFile(uri);
  return new TextDecoder("utf-8").decode(bytes);
}

/**
 * Reports which team policy file the linter will use.
 */
function policyLine(workspacePath: string): string {
  const policyPath = path.join(workspacePath, ".prompt-preflight.json");
  return `Team policy: ${policyPath}\n`;
}
