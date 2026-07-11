import * as vscode from "vscode";
import { OPEN_EXAMPLES_COMMAND, openPromptExamples } from "./examplesLink";
import { isPromptPreflightResultText } from "./generatedDocuments";
import {
  closeGeneratedPromptTabs,
  forgetGeneratedPromptDocument,
  isTrackedGeneratedPromptDocument,
  trackGeneratedPromptDocument
} from "./generatedTabs";
import { PromptPreflightCodeActionProvider } from "./promptCodeActions";
import { PreflightAnalysis, runPreflight } from "./preflightClient";
import { PromptDiagnosticsController } from "./promptDiagnostics";
import { createTeamPolicyFile, enableLocalTelemetry, openTeamPolicy } from "./teamPolicy";
import { insertPromptTemplate } from "./templateInserter";
import { WorkspacePromptLinter } from "./workspaceLinter";
import { PromptComposerPanel } from "./promptComposerPanel";
import { releaseReadinessMarkdown } from "./releaseReadiness";
import { buildSetupDoctorReport, setupDoctorMarkdown } from "./setupDoctor";
import { TelemetryDashboardPanel } from "./telemetryDashboardPanel";
import { shouldRecordTelemetry } from "./telemetryStore";

/**
 * Tracks where a prompt came from so a suggested rewrite can be applied back to
 * the user's original Markdown file or selected text.
 */
interface PromptSource {
  uri: vscode.Uri;
  range?: vscode.Range;
  replaceWholeDocument?: boolean;
}

/**
 * Carries the prompt text plus optional editor location metadata through the
 * check pipeline.
 */
interface PromptInput {
  prompt: string;
  source?: PromptSource;
}

/**
 * Stores analyzer results for temporary result documents so CodeLens actions in
 * those documents can find the original source prompt later.
 */
interface AnalysisRecord {
  analysis: PreflightAnalysis;
  source?: PromptSource;
}

/**
 * In-memory lookup keyed by temporary result document URI. VS Code gives untitled
 * result tabs stable URIs for the session, which is enough for CodeLens actions.
 */
const analysisRecords = new Map<string, AnalysisRecord>();

/**
 * Notifies VS Code that Prompt Preflight result CodeLens actions should be
 * recalculated after a new analysis document is opened.
 */
const resultCodeLensRefresh = new vscode.EventEmitter<void>();

/**
 * Provides the clickable in-editor Markdown action. VS Code calls this provider
 * whenever a Markdown document is opened or changed, and the provider returns a
 * CodeLens above the first line that runs Prompt Preflight against the document.
 */
class MarkdownPromptCodeLensProvider implements vscode.CodeLensProvider {
  /**
   * Creates top-of-file actions for non-empty Markdown prompt files.
   */
  provideCodeLenses(document: vscode.TextDocument): vscode.CodeLens[] {
    if (document.getText().trim().length === 0 || isPromptPreflightResult(document)) {
      return [];
    }

    const topOfDocument = new vscode.Range(0, 0, 0, 0);
    const lenses = [
      new vscode.CodeLens(topOfDocument, {
        title: "🟢 ▶ Run Prompt Preflight Check",
        command: "promptPreflight.checkDocument",
        tooltip: "Check this Markdown prompt with Prompt Preflight",
        arguments: [document.uri]
      })
    ];

    if (isTrackedGeneratedPromptDocument(document)) {
      lenses.push(closeGeneratedTabsCodeLens(topOfDocument));
    }

    return lenses;
  }
}

/**
 * Provides actions inside Prompt Preflight result documents. The actions can
 * insert suggestions and close generated Prompt Preflight tabs.
 */
class ResultSuggestedPromptCodeLensProvider implements vscode.CodeLensProvider {
  /**
   * Lets VS Code refresh the insert arrow after this extension records a fresh
   * analysis result.
   */
  readonly onDidChangeCodeLenses = resultCodeLensRefresh.event;

  /**
   * Creates CodeLens actions for Prompt Preflight result documents.
   */
  provideCodeLenses(document: vscode.TextDocument): vscode.CodeLens[] {
    if (!isPromptPreflightResult(document)) {
      return [];
    }

    const lenses = [closeGeneratedTabsCodeLens(new vscode.Range(0, 0, 0, 0))];
    const record = analysisRecords.get(document.uri.toString());
    if (!record?.source || !record.analysis.suggested_prompt) {
      return lenses;
    }

    const suggestedPromptLine = findLine(document, "## Suggested Prompt");
    if (suggestedPromptLine === undefined) {
      return lenses;
    }

    lenses.push(
      new vscode.CodeLens(new vscode.Range(suggestedPromptLine, 0, suggestedPromptLine, 0), {
        title: "➡ Insert suggested prompt into original file",
        command: "promptPreflight.insertSuggestedPrompt",
        tooltip: "Replace the original prompt with this suggested Prompt Preflight template",
        arguments: [document.uri]
      })
    );
    return lenses;
  }
}

/**
 * Builds the shared CodeLens for closing generated Prompt Preflight tabs.
 */
function closeGeneratedTabsCodeLens(range: vscode.Range): vscode.CodeLens {
  return new vscode.CodeLens(range, {
    title: "🧹 Close Prompt Preflight generated tabs",
    command: "promptPreflight.closeGeneratedTabs",
    tooltip: "Close result, template, and composer tabs opened by Prompt Preflight"
  });
}

/**
 * Identifies temporary result documents produced by this extension.
 */
function isPromptPreflightResult(document: vscode.TextDocument): boolean {
  return isPromptPreflightResultText(document.getText());
}

/**
 * Finds the first Markdown line whose trimmed text exactly matches the target.
 */
function findLine(document: vscode.TextDocument, target: string): number | undefined {
  for (let index = 0; index < document.lineCount; index += 1) {
    if (document.lineAt(index).text.trim() === target) {
      return index;
    }
  }
  return undefined;
}

/**
 * Returns the first open workspace folder so the analyzer can resolve project
 * config and file references relative to the user's active project.
 */
function activeWorkspacePath(): string | undefined {
  const folder = vscode.workspace.workspaceFolders?.[0];
  return folder?.uri.fsPath;
}

/**
 * Reads the currently selected editor text and treats it as the prompt to check.
 * Returning undefined lets the command fall back to an input box.
 */
function selectedPrompt(): PromptInput | undefined {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    return undefined;
  }

  const selection = editor.selection;
  if (selection.isEmpty) {
    return undefined;
  }

  const prompt = editor.document.getText(selection).trim();
  if (!prompt) {
    return undefined;
  }

  return {
    prompt,
    source: {
      uri: editor.document.uri,
      range: selection
    }
  };
}

/**
 * Prompts the user for text when they run the command without selecting a
 * prompt in the editor.
 */
async function askForPrompt(): Promise<string | undefined> {
  return vscode.window.showInputBox({
    title: "Prompt Preflight",
    prompt: "Paste a prompt to check",
    placeHolder: "Create a car image"
  });
}

/**
 * Reads the full text of a Markdown document addressed by a CodeLens command.
 * If the command did not pass a URI, the active editor document is used.
 */
async function documentPrompt(uri?: vscode.Uri): Promise<string | undefined> {
  const document = uri
    ? await vscode.workspace.openTextDocument(uri)
    : vscode.window.activeTextEditor?.document;
  return document?.getText().trim();
}

/**
 * Builds a source record for a full-document Markdown check so insertion can
 * replace the original document with the suggested prompt.
 */
function documentSource(uri?: vscode.Uri): PromptSource | undefined {
  const documentUri = uri || vscode.window.activeTextEditor?.document.uri;
  if (!documentUri) {
    return undefined;
  }
  return {
    uri: documentUri,
    replaceWholeDocument: true
  };
}

/**
 * Returns a range that covers every character in a document.
 */
function wholeDocumentRange(document: vscode.TextDocument): vscode.Range {
  const lastLine = document.lineAt(document.lineCount - 1);
  return new vscode.Range(0, 0, document.lineCount - 1, lastLine.range.end.character);
}

/**
 * Converts the analyzer JSON result into a readable Markdown report that can be
 * opened beside the user's editor for easy review and copy/paste.
 */
function analysisMarkdown(analysis: PreflightAnalysis, canInsertSuggestion: boolean): string {
  const prompt = analysis.redacted_prompt || analysis.prompt;
  const lines: string[] = [
    "# Prompt Preflight Result",
    "",
    `- Intent: \`${analysis.intent}\``,
    `- Vagueness score: \`${analysis.score}/100\``,
    `- Severity: \`${analysis.severity}\``,
    `- Decision: ${analysis.should_clarify ? "Needs clarification" : "Clear to send"}`,
    ""
  ];

  if (analysis.checks.length) {
    lines.push("## Checks", "", ...analysis.checks.map((check) => `- \`${check}\``), "");
  }

  if (analysis.reasons.length) {
    lines.push("## Reasons", "", ...analysis.reasons.map((reason) => `- ${reason}`), "");
  }

  lines.push("## Original Prompt", "", "```text", prompt, "```", "");

  if (analysis.suggested_prompt) {
    lines.push(
      "## Suggested Prompt",
      "",
      canInsertSuggestion
        ? "> ➡️ Use the action above this heading to insert this suggested prompt into the original file."
        : "> Copy this suggested prompt into your editor, then fill the bracketed fields before sending.",
      "",
      "```text",
      analysis.suggested_prompt,
      "```",
      ""
    );
  }

  if (analysis.questions.length) {
    lines.push(
      "---",
      "",
      "## 🚨 Questions To Answer Before Sending",
      "",
      "> [!IMPORTANT]",
      "> 🚨 **STOP — answer these before sending this prompt.**",
      ">",
      "> These missing details are likely to cause back-and-forth or wasted model calls.",
      ">",
      ...analysis.questions.map((question, index) => `> 🔴 **${index + 1}.** ${question}`),
      "",
      "---",
      ""
    );
  }

  return lines.join("\n");
}

/**
 * Opens the Markdown analysis report in a temporary editor tab.
 */
async function showAnalysisDocument(
  analysis: PreflightAnalysis,
  source?: PromptSource
): Promise<void> {
  const document = await vscode.workspace.openTextDocument({
    content: analysisMarkdown(analysis, Boolean(source)),
    language: "markdown"
  });
  trackGeneratedPromptDocument(document, "result");
  analysisRecords.set(document.uri.toString(), { analysis, source });
  resultCodeLensRefresh.fire();
  await vscode.window.showTextDocument(document, vscode.ViewColumn.Beside);
}

/**
 * Closes tabs that Prompt Preflight opened, such as result reports and generated
 * prompt/template documents.
 */
async function closePromptPreflightGeneratedTabs(): Promise<void> {
  const result = await closeGeneratedPromptTabs();
  if (result.attemptedCount === 0) {
    void vscode.window.showInformationMessage("Prompt Preflight: no generated tabs are open.");
    return;
  }

  if (result.closed) {
    void vscode.window.showInformationMessage(
      `Prompt Preflight: closed ${result.attemptedCount} generated tab${result.attemptedCount === 1 ? "" : "s"}.`
    );
    return;
  }

  void vscode.window.showWarningMessage(
    "Prompt Preflight: close canceled. Some generated tabs may have unsaved changes."
  );
}

/**
 * Applies the suggested prompt from a result document back into the source file
 * or source selection that produced the analysis.
 */
async function insertSuggestedPrompt(resultUri?: vscode.Uri): Promise<void> {
  const resultDocument = resultUri
    ? await vscode.workspace.openTextDocument(resultUri)
    : vscode.window.activeTextEditor?.document;
  if (!resultDocument) {
    void vscode.window.showWarningMessage("Prompt Preflight: open a result document first.");
    return;
  }

  const record = analysisRecords.get(resultDocument.uri.toString());
  if (!record?.source) {
    void vscode.window.showWarningMessage(
      "Prompt Preflight: this result is not linked to an original editor file."
    );
    return;
  }

  const suggestedPrompt = record.analysis.suggested_prompt;
  if (!suggestedPrompt) {
    void vscode.window.showInformationMessage("Prompt Preflight: no suggested prompt to insert.");
    return;
  }

  const sourceDocument = await vscode.workspace.openTextDocument(record.source.uri);
  const sourceEditor = await vscode.window.showTextDocument(sourceDocument, vscode.ViewColumn.One);
  const targetRange = record.source.range || wholeDocumentRange(sourceDocument);
  const applied = await sourceEditor.edit((editBuilder) => {
    editBuilder.replace(targetRange, suggestedPrompt);
  });

  if (applied) {
    void vscode.window.showInformationMessage(
      "Prompt Preflight: suggested prompt inserted into the original file."
    );
  } else {
    void vscode.window.showErrorMessage("Prompt Preflight: could not insert the suggested prompt.");
  }
}

/**
 * Shared execution path for all prompt-checking entrypoints. It calls the local
 * analyzer, shows a status notification, optionally copies the suggested prompt,
 * and always opens the detailed Markdown result.
 */
async function checkPromptText(
  context: vscode.ExtensionContext,
  prompt: string,
  source?: PromptSource
): Promise<void> {
  if (!prompt || !prompt.trim()) {
    return;
  }

  await vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: "Checking prompt with Prompt Preflight...",
      cancellable: false
    },
    async () => {
      const analysis = await runPreflight(prompt, {
        extensionPath: context.extensionPath,
        workspacePath: activeWorkspacePath(),
        recordTelemetry: shouldRecordTelemetry(activeWorkspacePath())
      });

      if (!analysis.should_clarify) {
        void vscode.window.showInformationMessage(
          `Prompt Preflight: clear to send (Vagueness score ${analysis.score}/100).`
        );
        await showAnalysisDocument(analysis, source);
        return;
      }

      const action = await vscode.window.showWarningMessage(
        `Prompt Preflight: prompt needs clarification (Vagueness score ${analysis.score}/100).`,
        "Show Details",
        "Copy Suggested Prompt"
      );

      if (action === "Copy Suggested Prompt" && analysis.suggested_prompt) {
        await vscode.env.clipboard.writeText(analysis.suggested_prompt);
        void vscode.window.showInformationMessage("Suggested prompt copied.");
      }

      await showAnalysisDocument(analysis, source);
    }
  );
}

/**
 * Command handler for the Command Palette/right-click action. It checks selected
 * editor text first and falls back to asking the user to paste a prompt.
 */
async function checkPrompt(context: vscode.ExtensionContext): Promise<void> {
  const selection = selectedPrompt();
  if (selection) {
    await checkPromptText(context, selection.prompt, selection.source);
    return;
  }

  const prompt = await askForPrompt();
  if (!prompt) {
    return;
  }
  await checkPromptText(context, prompt);
}

/**
 * Command handler for the Markdown CodeLens action. It checks the full Markdown
 * document so users can keep prompts as files and run checks with one click.
 */
async function checkMarkdownDocument(
  context: vscode.ExtensionContext,
  uri?: vscode.Uri
): Promise<void> {
  const prompt = await documentPrompt(uri);
  if (!prompt) {
    void vscode.window.showInformationMessage("Prompt Preflight: Markdown file is empty.");
    return;
  }
  await checkPromptText(context, prompt, documentSource(uri));
}

/**
 * Opens a generated Markdown setup report that diagnoses common VS Code
 * extension setup problems.
 */
async function openSetupDoctor(context: vscode.ExtensionContext): Promise<void> {
  const config = vscode.workspace.getConfiguration("promptPreflight");
  const report = buildSetupDoctorReport({
    extensionPath: context.extensionPath,
    workspacePath: activeWorkspacePath(),
    configuredRepoPath: config.get<string>("repoPath") || "",
    pythonPath: config.get<string>("pythonPath") || "python3"
  });
  const document = await vscode.workspace.openTextDocument({
    content: setupDoctorMarkdown(report),
    language: "markdown"
  });
  trackGeneratedPromptDocument(document, "result");
  await vscode.window.showTextDocument(document, vscode.ViewColumn.Beside);
}

/**
 * Opens the public-release checklist as a generated Markdown document.
 */
async function openReleaseReadinessChecklist(): Promise<void> {
  const document = await vscode.workspace.openTextDocument({
    content: releaseReadinessMarkdown(),
    language: "markdown"
  });
  trackGeneratedPromptDocument(document, "result");
  await vscode.window.showTextDocument(document, vscode.ViewColumn.Beside);
}

/**
 * VS Code extension entrypoint. Registers commands when the extension activates.
 */
export function activate(context: vscode.ExtensionContext): void {
  const diagnosticsController = new PromptDiagnosticsController(context, activeWorkspacePath);
  diagnosticsController.start();
  const workspaceLinter = new WorkspacePromptLinter(context);

  context.subscriptions.push(
    diagnosticsController,
    workspaceLinter,
    resultCodeLensRefresh,
    vscode.commands.registerCommand("promptPreflight.checkSelection", () =>
      checkPrompt(context)
    ),
    vscode.commands.registerCommand("promptPreflight.checkDocument", (uri?: vscode.Uri) =>
      checkMarkdownDocument(context, uri)
    ),
    vscode.commands.registerCommand("promptPreflight.insertSuggestedPrompt", (uri?: vscode.Uri) =>
      insertSuggestedPrompt(uri)
    ),
    vscode.commands.registerCommand("promptPreflight.closeGeneratedTabs", () =>
      closePromptPreflightGeneratedTabs()
    ),
    vscode.commands.registerCommand("promptPreflight.insertMarkdownTemplate", () =>
      insertPromptTemplate(context, "md")
    ),
    vscode.commands.registerCommand("promptPreflight.insertXmlTemplate", () =>
      insertPromptTemplate(context, "xml")
    ),
    vscode.commands.registerCommand("promptPreflight.insertTomlTemplate", () =>
      insertPromptTemplate(context, "toml")
    ),
    vscode.commands.registerCommand(OPEN_EXAMPLES_COMMAND, () => openPromptExamples(context)),
    vscode.commands.registerCommand("promptPreflight.lintWorkspacePrompts", () =>
      workspaceLinter.lintWorkspace()
    ),
    vscode.commands.registerCommand("promptPreflight.openTeamPolicy", () => openTeamPolicy()),
    vscode.commands.registerCommand("promptPreflight.createTeamPolicy", () =>
      createTeamPolicyFile()
    ),
    vscode.commands.registerCommand("promptPreflight.enableTelemetry", () =>
      enableLocalTelemetry()
    ),
    vscode.commands.registerCommand("promptPreflight.openComposer", () =>
      PromptComposerPanel.open(context, (prompt: string) => checkPromptText(context, prompt))
    ),
    vscode.commands.registerCommand("promptPreflight.openTelemetryDashboard", () =>
      TelemetryDashboardPanel.open(context, activeWorkspacePath())
    ),
    vscode.commands.registerCommand("promptPreflight.runSetupDoctor", () =>
      openSetupDoctor(context)
    ),
    vscode.commands.registerCommand("promptPreflight.openReleaseReadinessChecklist", () =>
      openReleaseReadinessChecklist()
    ),
    vscode.workspace.onDidCloseTextDocument((document) => {
      analysisRecords.delete(document.uri.toString());
      forgetGeneratedPromptDocument(document.uri);
    }),
    vscode.languages.registerCodeLensProvider(
      { language: "markdown" },
      new MarkdownPromptCodeLensProvider()
    ),
    vscode.languages.registerCodeLensProvider(
      { language: "markdown" },
      new ResultSuggestedPromptCodeLensProvider()
    ),
    vscode.languages.registerCodeActionsProvider(
      [
        { language: "markdown" },
        { language: "xml" },
        { language: "toml" }
      ],
      new PromptPreflightCodeActionProvider(),
      {
        providedCodeActionKinds: PromptPreflightCodeActionProvider.providedCodeActionKinds
      }
    )
  );
}

/**
 * VS Code extension shutdown hook. VS Code disposes command subscriptions and
 * editor listeners registered through the extension context.
 */
export function deactivate(): void {
  // No manual shutdown work is required.
}
