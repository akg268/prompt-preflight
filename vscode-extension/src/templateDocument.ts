/**
 * Supported template output formats exposed as VS Code creation commands.
 */
export type TemplateFormat = "md" | "xml" | "toml";

/**
 * Plain description of a new template document. VS Code-specific code converts
 * this shape into an untitled editor tab.
 */
export interface TemplateDocumentSpec {
  language: string;
  content: string;
}

/**
 * Maps template format names to VS Code language IDs for untitled documents.
 */
export const FORMAT_LANGUAGE: Record<TemplateFormat, string> = {
  md: "markdown",
  xml: "xml",
  toml: "toml"
};

/**
 * Maps template format names to human-friendly labels shown in VS Code.
 */
export const FORMAT_LABEL: Record<TemplateFormat, string> = {
  md: "Markdown",
  xml: "XML",
  toml: "TOML"
};

/**
 * Builds the new-document spec for a selected prompt template.
 */
export function templateDocumentSpec(
  template: string,
  format: TemplateFormat
): TemplateDocumentSpec {
  return {
    language: FORMAT_LANGUAGE[format],
    content: template
  };
}
