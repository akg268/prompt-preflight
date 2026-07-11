import * as path from "path";
import * as vscode from "vscode";
import { trackGeneratedPromptDocument } from "./generatedTabs";
import {
  TEAM_POLICY_FILE_NAME,
  policyTextWithTelemetryEnabled,
  teamPolicyDocumentSpec,
  teamPolicyFilePath,
  teamPolicyTemplateText
} from "./policyDocument";

/**
 * Opens the workspace Prompt Preflight team policy, or creates an untitled
 * policy template when the workspace does not have one yet.
 */
export async function openTeamPolicy(): Promise<void> {
  const folder = vscode.workspace.workspaceFolders?.[0];
  if (!folder) {
    await openUntitledPolicyTemplate();
    return;
  }

  const policyUri = vscode.Uri.file(path.join(folder.uri.fsPath, TEAM_POLICY_FILE_NAME));
  if (await fileExists(policyUri)) {
    const document = await vscode.workspace.openTextDocument(policyUri);
    await vscode.window.showTextDocument(document, vscode.ViewColumn.Beside);
    return;
  }

  await openUntitledPolicyTemplate();
  void vscode.window.showInformationMessage(
    `Prompt Preflight: save this template as ${TEAM_POLICY_FILE_NAME} in your workspace root to share the policy with your team.`
  );
}

/**
 * Creates `.prompt-preflight.json` in the first workspace root and opens it.
 * Existing policy files are opened without being overwritten.
 */
export async function createTeamPolicyFile(): Promise<void> {
  const folder = vscode.workspace.workspaceFolders?.[0];
  if (!folder) {
    void vscode.window.showErrorMessage(
      "Prompt Preflight: open a workspace folder before creating .prompt-preflight.json."
    );
    return;
  }

  const policyUri = vscode.Uri.file(teamPolicyFilePath(folder.uri.fsPath));
  if (await fileExists(policyUri)) {
    const document = await vscode.workspace.openTextDocument(policyUri);
    await vscode.window.showTextDocument(document, vscode.ViewColumn.Beside);
    void vscode.window.showInformationMessage(
      `Prompt Preflight: ${TEAM_POLICY_FILE_NAME} already exists. Opened existing file.`
    );
    return;
  }

  await vscode.workspace.fs.writeFile(policyUri, Buffer.from(teamPolicyTemplateText(), "utf8"));
  const document = await vscode.workspace.openTextDocument(policyUri);
  await vscode.window.showTextDocument(document, vscode.ViewColumn.Beside);
  void vscode.window.showInformationMessage(
    `Prompt Preflight: created ${TEAM_POLICY_FILE_NAME} in the workspace root.`
  );
}

/**
 * Creates or updates `.prompt-preflight.json` so local prompt-free telemetry is
 * explicitly enabled, then opens the policy file for review.
 */
export async function enableLocalTelemetry(): Promise<void> {
  const folder = vscode.workspace.workspaceFolders?.[0];
  if (!folder) {
    void vscode.window.showErrorMessage(
      "Prompt Preflight: open a workspace folder before enabling local telemetry."
    );
    return;
  }

  const policyUri = vscode.Uri.file(teamPolicyFilePath(folder.uri.fsPath));
  const existingText = await readPolicyText(policyUri);
  if (existingText === undefined && await fileExists(policyUri)) {
    await openPolicyFile(policyUri);
    void vscode.window.showErrorMessage(
      `Prompt Preflight: could not read ${TEAM_POLICY_FILE_NAME}. Opened the file for manual review.`
    );
    return;
  }

  try {
    const nextText = policyTextWithTelemetryEnabled(existingText ?? teamPolicyTemplateText());
    await vscode.workspace.fs.writeFile(policyUri, Buffer.from(nextText, "utf8"));
    await openPolicyFile(policyUri);
    void vscode.window.showInformationMessage(
      "Prompt Preflight: local telemetry is enabled. Run a prompt check, then refresh the dashboard."
    );
  } catch (error) {
    if (await fileExists(policyUri)) {
      await openPolicyFile(policyUri);
    }
    const message = error instanceof Error ? error.message : String(error);
    void vscode.window.showErrorMessage(
      `Prompt Preflight: could not enable telemetry automatically. ${message}`
    );
  }
}

/**
 * Opens a new untitled JSON document with the default team policy content.
 */
async function openUntitledPolicyTemplate(): Promise<void> {
  const spec = teamPolicyDocumentSpec();
  const document = await vscode.workspace.openTextDocument({
    language: spec.language,
    content: spec.content
  });
  trackGeneratedPromptDocument(document, "policy");
  await vscode.window.showTextDocument(document, vscode.ViewColumn.Beside);
}

/**
 * Opens a policy file beside the active editor.
 */
async function openPolicyFile(policyUri: vscode.Uri): Promise<void> {
  const document = await vscode.workspace.openTextDocument(policyUri);
  await vscode.window.showTextDocument(document, vscode.ViewColumn.Beside);
}

/**
 * Reads a policy file as UTF-8 text. Missing files return undefined.
 */
async function readPolicyText(uri: vscode.Uri): Promise<string | undefined> {
  try {
    const bytes = await vscode.workspace.fs.readFile(uri);
    return Buffer.from(bytes).toString("utf8");
  } catch {
    return undefined;
  }
}

/**
 * Checks whether a VS Code URI points to an existing file.
 */
async function fileExists(uri: vscode.Uri): Promise<boolean> {
  try {
    const stat = await vscode.workspace.fs.stat(uri);
    return stat.type === vscode.FileType.File;
  } catch {
    return false;
  }
}
