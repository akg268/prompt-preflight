import * as vscode from "vscode";
import { betaFeedbackIssueUrl } from "./feedbackLinks";

/**
 * Opens the public feedback issue in the user's browser.
 */
export async function openBetaFeedbackIssue(): Promise<void> {
  await vscode.env.openExternal(vscode.Uri.parse(betaFeedbackIssueUrl()));
}
