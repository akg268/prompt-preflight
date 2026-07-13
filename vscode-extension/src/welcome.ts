import * as vscode from "vscode";
import { betaFeedbackIssueUrl } from "./feedbackLinks";
import { trackGeneratedPromptDocument } from "./generatedTabs";
import {
  shouldShowWelcomePage,
  welcomeMarkdown,
  WELCOME_VERSION_STATE_KEY
} from "./welcomeContent";

/**
 * Reads the extension version from VS Code extension metadata.
 */
function extensionVersion(context: vscode.ExtensionContext): string {
  const version = context.extension.packageJSON?.version;
  return typeof version === "string" && version ? version : "unknown";
}

/**
 * Opens the welcome page as a generated Markdown tab.
 */
export async function openWelcomePage(context: vscode.ExtensionContext): Promise<void> {
  const document = await vscode.workspace.openTextDocument({
    content: welcomeMarkdown(extensionVersion(context), betaFeedbackIssueUrl()),
    language: "markdown"
  });
  trackGeneratedPromptDocument(document, "welcome");
  await vscode.window.showTextDocument(document, vscode.ViewColumn.Beside);
}

/**
 * Shows the welcome page once per extension version.
 */
export async function maybeOpenWelcomePage(context: vscode.ExtensionContext): Promise<void> {
  const currentVersion = extensionVersion(context);
  const seenVersion = context.globalState.get<string>(WELCOME_VERSION_STATE_KEY);
  if (!shouldShowWelcomePage(seenVersion, currentVersion)) {
    return;
  }

  await openWelcomePage(context);
  await context.globalState.update(WELCOME_VERSION_STATE_KEY, currentVersion);
}
