import * as vscode from "vscode";
import { OPEN_EXAMPLES_COMMAND } from "./examplesLink";

/**
 * Provides Quick Fix actions for Prompt Preflight diagnostics.
 */
export class PromptPreflightCodeActionProvider implements vscode.CodeActionProvider {
  /**
   * Advertises that this provider returns Quick Fix actions.
   */
  static readonly providedCodeActionKinds = [vscode.CodeActionKind.QuickFix];

  /**
   * Creates an action that opens the example prompt library for Prompt Preflight
   * diagnostics.
   */
  provideCodeActions(
    _document: vscode.TextDocument,
    _range: vscode.Range | vscode.Selection,
    context: vscode.CodeActionContext
  ): vscode.CodeAction[] {
    const hasPromptPreflightDiagnostic = context.diagnostics.some(
      (diagnostic) => diagnostic.source === "Prompt Preflight"
    );
    if (!hasPromptPreflightDiagnostic) {
      return [];
    }

    const action = new vscode.CodeAction(
      "Open Prompt Preflight examples",
      vscode.CodeActionKind.QuickFix
    );
    action.command = {
      title: "Open Prompt Preflight examples",
      command: OPEN_EXAMPLES_COMMAND
    };
    action.isPreferred = true;
    return [action];
  }
}
