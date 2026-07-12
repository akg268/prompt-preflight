import * as fs from "fs/promises";
import * as path from "path";
import * as vscode from "vscode";
import { trackGeneratedPromptDocument } from "./generatedTabs";
import { bundledAnalyzerPath } from "./repoResolver";
import {
  FORMAT_LABEL,
  TemplateFormat,
  templateDocumentSpec,
  templateFormatOptions
} from "./templateDocument";

/**
 * Represents one required-field group from the shared prompt template catalog.
 */
interface TemplateRequirement {
  label: string;
  fields: string[];
}

/**
 * Represents one prompt profile from the shared prompt template catalog.
 */
interface TemplateProfile {
  display_name: string;
  required: TemplateRequirement[];
  templates: Partial<Record<TemplateFormat, string[]>>;
}

/**
 * Represents the shared data file that powers prompt templates across tools.
 */
interface TemplateCatalog {
  profiles: Record<string, TemplateProfile>;
}

/**
 * Adds the catalog profile metadata needed after the user picks a template.
 */
interface TemplateQuickPickItem extends vscode.QuickPickItem {
  profileKey: string;
  profile: TemplateProfile;
}

/**
 * Adds the chosen template format to a VS Code QuickPick item.
 */
interface TemplateFormatQuickPickItem extends vscode.QuickPickItem {
  format: TemplateFormat;
}

/**
 * Asks the user which template format they want before opening the usual
 * profile picker. This is the best default command for users who know they want
 * a prompt template but have not chosen Markdown, TOML, or XML yet.
 */
export async function insertPromptTemplateWithFormatChoice(
  context: vscode.ExtensionContext
): Promise<void> {
  const selectedFormat = await chooseTemplateFormat();
  if (!selectedFormat) {
    return;
  }

  await insertPromptTemplate(context, selectedFormat.format);
}

/**
 * Inserts a structured prompt template in the requested format. Users choose the
 * profile first, then the extension opens a new untitled prompt document. This
 * intentionally avoids changing whatever source file happens to be active.
 */
export async function insertPromptTemplate(
  context: vscode.ExtensionContext,
  format: TemplateFormat
): Promise<void> {
  try {
    const catalog = await loadTemplateCatalog(context);
    const selectedProfile = await chooseTemplateProfile(catalog, format);
    if (!selectedProfile) {
      return;
    }

    const template = templateText(selectedProfile.profile, format);
    if (!template) {
      void vscode.window.showWarningMessage(
        `Prompt Preflight: ${selectedProfile.label} does not have a ${FORMAT_LABEL[format]} template.`
      );
      return;
    }

    await openTemplateDocument(template, format);
    void vscode.window.showInformationMessage(
      `Prompt Preflight: opened a new ${FORMAT_LABEL[format]} ${selectedProfile.profileKey} template.`
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    void vscode.window.showErrorMessage(`Prompt Preflight: ${message}`);
  }
}

/**
 * Lets the user choose Markdown, TOML, or XML before choosing a template
 * profile.
 */
async function chooseTemplateFormat(): Promise<TemplateFormatQuickPickItem | undefined> {
  const picks = templateFormatOptions().map((option) => ({
    label: option.label,
    description: option.description,
    format: option.format
  }));

  return vscode.window.showQuickPick(picks, {
    title: "New Prompt Template",
    placeHolder: "Choose Markdown, TOML, or XML"
  });
}

/**
 * Returns the user-configured repository path, if one was provided.
 */
function configuredRepoPath(): string | undefined {
  const repoPath = vscode.workspace
    .getConfiguration("promptPreflight")
    .get<string>("repoPath", "")
    .trim();
  return repoPath || undefined;
}

/**
 * Produces the possible locations for the shared prompt template catalog.
 */
function candidateCatalogPaths(context: vscode.ExtensionContext): string[] {
  const configuredPath = configuredRepoPath();
  const candidates = [
    configuredPath,
    path.resolve(context.extensionPath, ".."),
    bundledAnalyzerPath(context.extensionPath),
    context.extensionPath
  ].filter((candidate): candidate is string => Boolean(candidate));

  return Array.from(new Set(candidates)).map((repoPath) =>
    path.join(repoPath, "src", "prompt_preflight", "data", "prompt_templates.json")
  );
}

/**
 * Loads the shared prompt template catalog from the repo checkout.
 */
async function loadTemplateCatalog(context: vscode.ExtensionContext): Promise<TemplateCatalog> {
  const candidates = candidateCatalogPaths(context);
  for (const candidate of candidates) {
    try {
      const rawCatalog = await fs.readFile(candidate, "utf-8");
      return JSON.parse(rawCatalog) as TemplateCatalog;
    } catch {
      // Try the next candidate path before surfacing a friendly error.
    }
  }

  throw new Error(
    [
      "could not find src/prompt_preflight/data/prompt_templates.json.",
      "The VSIX should include a bundled template catalog. If you are developing from source, set promptPreflight.repoPath to your prompt-preflight checkout.",
      `Checked: ${candidates.join(", ")}`
    ].join(" ")
  );
}

/**
 * Lets the user choose which domain/profile template they want to insert.
 */
async function chooseTemplateProfile(
  catalog: TemplateCatalog,
  format: TemplateFormat
): Promise<TemplateQuickPickItem | undefined> {
  const picks = Object.entries(catalog.profiles)
    .map(([profileKey, profile]) => ({
      label: profile.display_name,
      description: profileKey,
      detail: requiredFieldSummary(profile),
      profileKey,
      profile
    }))
    .sort((left, right) => {
      if (left.profileKey === "general") {
        return -1;
      }
      if (right.profileKey === "general") {
        return 1;
      }
      return left.label.localeCompare(right.label);
    });

  return vscode.window.showQuickPick(picks, {
    title: `New ${FORMAT_LABEL[format]} Prompt Template`,
    placeHolder: "Choose a prompt template profile"
  });
}

/**
 * Builds the one-line required-field summary displayed in the profile picker.
 */
function requiredFieldSummary(profile: TemplateProfile): string {
  const labels = profile.required.map((requirement) => requirement.label);
  return labels.length ? `Required: ${labels.join(", ")}` : "No required fields listed";
}

/**
 * Converts a catalog template from an array of lines to insertable editor text.
 */
function templateText(profile: TemplateProfile, format: TemplateFormat): string | undefined {
  const lines = profile.templates[format];
  if (!lines) {
    return undefined;
  }
  return `${lines.join("\n").trimEnd()}\n`;
}

/**
 * Opens a new untitled editor populated with the selected template.
 */
async function openTemplateDocument(
  template: string,
  format: TemplateFormat
): Promise<vscode.TextEditor> {
  const documentSpec = templateDocumentSpec(template, format);
  const document = await vscode.workspace.openTextDocument({
    language: documentSpec.language,
    content: documentSpec.content
  });
  trackGeneratedPromptDocument(document, "template");
  return vscode.window.showTextDocument(document);
}
