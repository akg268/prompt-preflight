import * as vscode from "vscode";
import { diagnosticSummariesFromAnalysis, shouldAnalyzePromptDocument } from "./diagnosticRules";
import { runPreflight } from "./preflightClient";

/**
 * Provides the active workspace path to analyzer calls.
 */
type WorkspacePathProvider = () => string | undefined;

/**
 * Converts pure diagnostic severity names to VS Code diagnostic severities.
 */
const VSCODE_SEVERITY: Record<"warning" | "information", vscode.DiagnosticSeverity> = {
  warning: vscode.DiagnosticSeverity.Warning,
  information: vscode.DiagnosticSeverity.Information
};

/**
 * Owns automatic Prompt Preflight diagnostics for prompt-like editor documents.
 */
export class PromptDiagnosticsController implements vscode.Disposable {
  private readonly collection = vscode.languages.createDiagnosticCollection("prompt-preflight");
  private readonly disposables: vscode.Disposable[] = [];
  private readonly pendingTimers = new Map<string, ReturnType<typeof setTimeout>>();

  /**
   * Stores runtime dependencies needed to analyze open documents.
   */
  constructor(
    private readonly context: vscode.ExtensionContext,
    private readonly workspacePathProvider: WorkspacePathProvider
  ) {}

  /**
   * Starts watching open, changed, saved, and closed prompt-like documents.
   */
  start(): void {
    this.disposables.push(
      vscode.workspace.onDidOpenTextDocument((document) => this.scheduleAnalysis(document)),
      vscode.workspace.onDidChangeTextDocument((event) => this.scheduleAnalysis(event.document)),
      vscode.workspace.onDidSaveTextDocument((document) => this.scheduleAnalysis(document, 0)),
      vscode.workspace.onDidCloseTextDocument((document) => this.clearDocument(document))
    );

    for (const document of vscode.workspace.textDocuments) {
      this.scheduleAnalysis(document, 0);
    }
  }

  /**
   * Disposes diagnostics, listeners, and pending debounce timers.
   */
  dispose(): void {
    for (const timer of this.pendingTimers.values()) {
      clearTimeout(timer);
    }
    this.pendingTimers.clear();
    this.collection.dispose();
    for (const disposable of this.disposables) {
      disposable.dispose();
    }
  }

  /**
   * Debounces document analysis so typing does not spawn analyzer processes on
   * every keystroke.
   */
  private scheduleAnalysis(document: vscode.TextDocument, delay = diagnosticsDebounceMs()): void {
    const key = document.uri.toString();
    const existingTimer = this.pendingTimers.get(key);
    if (existingTimer) {
      clearTimeout(existingTimer);
    }

    const timer = setTimeout(() => {
      this.pendingTimers.delete(key);
      void this.analyzeDocument(document);
    }, delay);
    this.pendingTimers.set(key, timer);
  }

  /**
   * Runs Prompt Preflight for one document and updates the Problems panel.
   */
  private async analyzeDocument(document: vscode.TextDocument): Promise<void> {
    const text = document.getText();
    if (
      !diagnosticsEnabled() ||
      !shouldAnalyzePromptDocument(document.languageId, text, {
        fileName: document.uri.fsPath,
        isUntitled: document.isUntitled
      })
    ) {
      this.clearDocument(document);
      return;
    }

    try {
      const analysis = await runPreflight(text, {
        extensionPath: this.context.extensionPath,
        workspacePath: this.workspacePathProvider()
      });
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
      this.collection.set(document.uri, diagnostics);
    } catch (error) {
      console.error("Prompt Preflight diagnostics failed", error);
      this.clearDocument(document);
    }
  }

  /**
   * Clears diagnostics for a document.
   */
  private clearDocument(document: vscode.TextDocument): void {
    this.collection.delete(document.uri);
  }
}

/**
 * Reads whether automatic prompt diagnostics are enabled.
 */
function diagnosticsEnabled(): boolean {
  return vscode.workspace.getConfiguration("promptPreflight").get<boolean>("diagnostics.enabled", true);
}

/**
 * Reads the debounce delay for automatic prompt diagnostics.
 */
function diagnosticsDebounceMs(): number {
  const configured = vscode.workspace
    .getConfiguration("promptPreflight")
    .get<number>("diagnostics.debounceMs", 900);
  return Math.max(100, Math.min(5000, configured));
}
