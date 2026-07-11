import * as vscode from "vscode";
import {
  GeneratedDocumentKind,
  GeneratedDocumentRegistry
} from "./generatedDocuments";

/**
 * Shared in-memory registry for generated Prompt Preflight documents in the
 * current VS Code extension session.
 */
const generatedDocuments = new GeneratedDocumentRegistry();

/**
 * Captures the result of a generated-tab close attempt.
 */
export interface CloseGeneratedTabsResult {
  attemptedCount: number;
  closed: boolean;
}

/**
 * Tracks a VS Code document that Prompt Preflight opened on behalf of the user.
 */
export function trackGeneratedPromptDocument(
  document: vscode.TextDocument,
  kind: GeneratedDocumentKind
): void {
  generatedDocuments.track(document.uri.toString(), kind);
}

/**
 * Removes a document from generated-tab tracking after it closes.
 */
export function forgetGeneratedPromptDocument(uri: vscode.Uri): void {
  generatedDocuments.forget(uri.toString());
}

/**
 * Returns true when a text document is one of the generated tabs tracked during
 * this extension session.
 */
export function isTrackedGeneratedPromptDocument(document: vscode.TextDocument): boolean {
  return generatedDocuments.has(document.uri.toString());
}

/**
 * Closes all tabs that Prompt Preflight generated during the current extension
 * session while leaving normal user files alone.
 */
export async function closeGeneratedPromptTabs(): Promise<CloseGeneratedTabsResult> {
  const tabs = vscode.window.tabGroups.all
    .flatMap((group) => group.tabs)
    .filter((tab) => {
      const uri = tabTextUri(tab);
      return uri ? generatedDocuments.has(uri.toString()) : false;
    });

  if (!tabs.length) {
    return { attemptedCount: 0, closed: true };
  }

  const closed = await vscode.window.tabGroups.close(tabs, true);
  return { attemptedCount: tabs.length, closed };
}

/**
 * Extracts the text-document URI from a VS Code tab when the tab represents a
 * normal editor document.
 */
function tabTextUri(tab: vscode.Tab): vscode.Uri | undefined {
  if (tab.input instanceof vscode.TabInputText) {
    return tab.input.uri;
  }
  return undefined;
}
