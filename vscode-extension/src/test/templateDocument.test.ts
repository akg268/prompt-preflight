import assert from "assert/strict";
import { templateDocumentSpec, templateFormatOptions } from "../templateDocument";
import { runSuite } from "./testHarness";

/**
 * Unit tests for template-document creation rules.
 */
export function runTemplateDocumentTests(): void {
  runSuite("templateDocument", [
  /**
   * Verifies Markdown templates open as new Markdown documents.
   */
    {
      name: "builds a Markdown untitled document spec",
      run: () => {
        const spec = templateDocumentSpec("# Task\n[Describe the task]\n", "md");

        assert.equal(spec.language, "markdown");
        assert.equal(spec.content, "# Task\n[Describe the task]\n");
      }
    },

  /**
   * Verifies XML templates open as new XML documents.
   */
    {
      name: "builds an XML untitled document spec",
      run: () => {
        const spec = templateDocumentSpec("<prompt></prompt>\n", "xml");

        assert.equal(spec.language, "xml");
        assert.equal(spec.content, "<prompt></prompt>\n");
      }
    },

  /**
   * Verifies TOML templates open as new TOML documents.
   */
    {
      name: "builds a TOML untitled document spec",
      run: () => {
        const spec = templateDocumentSpec("profile = \"general\"\n", "toml");

        assert.equal(spec.language, "toml");
        assert.equal(spec.content, "profile = \"general\"\n");
      }
    },

  /**
   * Verifies the user-facing format picker offers every supported template
   * style in the preferred order.
   */
    {
      name: "builds user-facing format choices",
      run: () => {
        const options = templateFormatOptions();

        assert.deepEqual(
          options.map((option) => option.format),
          ["md", "toml", "xml"]
        );
        assert.deepEqual(
          options.map((option) => option.label),
          ["Markdown", "TOML", "XML"]
        );
      }
    }
  ]);
}
