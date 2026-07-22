import {
  TemplateDocumentSpec,
  TemplateFormat,
  templateDocumentSpec
} from "./templateDocument";

/**
 * Shared catalog shape needed to route a spec shortcut to its template body.
 */
export interface SpecTemplateCatalog {
  profiles: Record<
    string,
    {
      templates: Partial<Record<TemplateFormat, string[]>>;
    }
  >;
}

/**
 * Spec-driven template profiles exposed as direct VS Code commands.
 */
export const SPEC_TEMPLATE_COMMANDS = [
  {
    command: "promptPreflight.newFeatureSpec",
    title: "New Feature Spec",
    profileKey: "feature_spec"
  },
  {
    command: "promptPreflight.newRequirementsSpec",
    title: "New Requirements Spec",
    profileKey: "requirements_spec"
  },
  {
    command: "promptPreflight.newTechnicalDesignSpec",
    title: "New Technical Design Spec",
    profileKey: "technical_design_spec"
  },
  {
    command: "promptPreflight.newImplementationPlan",
    title: "New Implementation Plan",
    profileKey: "implementation_plan"
  },
  {
    command: "promptPreflight.newAgentExecutionPrompt",
    title: "New Agent Execution Prompt",
    profileKey: "agent_execution_prompt"
  },
  {
    command: "promptPreflight.newSpecReviewChecklist",
    title: "New Spec Review Checklist",
    profileKey: "spec_review_checklist"
  }
] as const;

export type SpecTemplateProfileKey = (typeof SPEC_TEMPLATE_COMMANDS)[number]["profileKey"];

/**
 * Runtime boundaries used by a spec shortcut. Keeping these injectable makes
 * command routing testable without loading the VS Code runtime in Node.
 */
export interface OpenSpecTemplateDependencies {
  chooseFormat: () => Promise<TemplateFormat | undefined>;
  loadCatalog: () => Promise<SpecTemplateCatalog>;
  openUntitledDocument: (document: TemplateDocumentSpec) => Promise<void>;
}

/**
 * Runs a direct spec-template shortcut through the shared picker, catalog, and
 * untitled-document flow.
 */
export async function openSpecTemplate(
  profileKey: SpecTemplateProfileKey,
  dependencies: OpenSpecTemplateDependencies
): Promise<TemplateFormat | undefined> {
  const format = await dependencies.chooseFormat();
  if (!format) {
    return undefined;
  }

  const catalog = await dependencies.loadCatalog();
  const lines = catalog.profiles[profileKey]?.templates[format];
  if (!lines) {
    throw new Error(`${profileKey} does not have a template for ${format}.`);
  }

  const content = `${lines.join("\n").trimEnd()}\n`;
  await dependencies.openUntitledDocument(templateDocumentSpec(content, format));
  return format;
}
