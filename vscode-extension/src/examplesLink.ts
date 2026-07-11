import * as fs from "fs";
import * as path from "path";
import * as vscode from "vscode";
import { bundledAnalyzerPath } from "./repoResolver";

/**
 * Command identifier used by diagnostics and command registration to open the
 * Prompt Preflight examples document.
 */
export const OPEN_EXAMPLES_COMMAND = "promptPreflight.openExamples";

/**
 * Builds possible roots that can contain the examples doc. Installed VSIX users
 * should resolve to the bundled analyzer; repoPath remains a development
 * override for local source work.
 */
function exampleRoots(extensionPath: string): string[] {
  const configuredRepoPath = vscode.workspace
    .getConfiguration("promptPreflight")
    .get<string>("repoPath", "")
    .trim();
  const roots = [
    configuredRepoPath,
    path.resolve(extensionPath, ".."),
    bundledAnalyzerPath(extensionPath),
    extensionPath
  ].filter((root): root is string => Boolean(root));
  return Array.from(new Set(roots));
}

/**
 * Finds the absolute path to the bundled or checkout examples document.
 */
function examplesPath(extensionPath: string): string | undefined {
  return exampleRoots(extensionPath)
    .map((root) => path.join(root, "docs", "EXAMPLES.md"))
    .find((candidate) => fs.existsSync(candidate));
}

/**
 * Opens the bundled prompt examples document beside the user's current editor.
 */
export async function openPromptExamples(context: vscode.ExtensionContext): Promise<void> {
  const filePath = examplesPath(context.extensionPath);
  if (!filePath) {
    void vscode.window.showErrorMessage(
      "Prompt Preflight: could not find bundled prompt examples. Reinstall the extension, or set promptPreflight.repoPath to a local prompt-preflight checkout while developing from source."
    );
    return;
  }

  const document = await vscode.workspace.openTextDocument(vscode.Uri.file(filePath));
  await vscode.window.showTextDocument(document, vscode.ViewColumn.Beside);
}
