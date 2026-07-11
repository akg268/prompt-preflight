/**
 * Names the kinds of temporary tabs Prompt Preflight opens for users.
 */
export type GeneratedDocumentKind = "result" | "composer" | "template" | "policy";

/**
 * Prefix used by generated Markdown result documents.
 */
export const PROMPT_PREFLIGHT_RESULT_PREFIX = "# Prompt Preflight Result";

/**
 * Tracks generated document URIs without depending on VS Code APIs, which keeps
 * the bookkeeping easy to unit test.
 */
export class GeneratedDocumentRegistry {
  private readonly documents = new Map<string, GeneratedDocumentKind>();

  /**
   * Records that Prompt Preflight opened a temporary or generated document.
   */
  track(uri: string, kind: GeneratedDocumentKind): void {
    this.documents.set(uri, kind);
  }

  /**
   * Removes a document from tracking after VS Code closes it.
   */
  forget(uri: string): void {
    this.documents.delete(uri);
  }

  /**
   * Returns true when the URI belongs to a generated Prompt Preflight document.
   */
  has(uri: string): boolean {
    return this.documents.has(uri);
  }

  /**
   * Returns all tracked URIs, primarily for diagnostics and tests.
   */
  uris(): string[] {
    return [...this.documents.keys()];
  }
}

/**
 * Detects generated Prompt Preflight result documents by their stable heading.
 */
export function isPromptPreflightResultText(text: string): boolean {
  return text.startsWith(PROMPT_PREFLIGHT_RESULT_PREFIX);
}
