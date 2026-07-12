/**
 * Supported template output formats exposed as VS Code creation commands.
 */
export type TemplateFormat = "md" | "xml" | "toml";

/**
 * Plain option shape used to present template formats without depending on the
 * VS Code QuickPick API in unit tests.
 */
export interface TemplateFormatOption {
  format: TemplateFormat;
  label: string;
  description: string;
}

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
 * Ordered list of template formats shown to users when they create a template.
 */
export const TEMPLATE_FORMAT_ORDER: TemplateFormat[] = ["md", "toml", "xml"];

/**
 * Builds the format choices shown before inserting a prompt template.
 */
export function templateFormatOptions(): TemplateFormatOption[] {
  return TEMPLATE_FORMAT_ORDER.map((format) => ({
    format,
    label: FORMAT_LABEL[format],
    description:
      format === "md"
        ? "Readable Markdown sections"
        : format === "toml"
          ? "Structured key/value prompt contract"
          : "XML-style tagged prompt contract"
  }));
}

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
