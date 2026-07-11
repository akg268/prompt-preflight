import assert from "assert/strict";
import {
  GeneratedDocumentRegistry,
  isPromptPreflightResultText
} from "../generatedDocuments";
import { runSuite } from "./testHarness";

/**
 * Unit tests for generated-document bookkeeping used by the close-tabs command.
 */
export function runGeneratedDocumentsTests(): void {
  runSuite("generatedDocuments", [
    /**
     * Verifies generated document URIs can be tracked and forgotten safely.
     */
    {
      name: "tracks and forgets generated document URIs",
      run: () => {
        const registry = new GeneratedDocumentRegistry();

        registry.track("untitled:Prompt-1", "result");
        registry.track("untitled:Prompt-2", "composer");

        assert.equal(registry.has("untitled:Prompt-1"), true);
        assert.equal(registry.has("untitled:Prompt-2"), true);
        assert.deepEqual(registry.uris(), ["untitled:Prompt-1", "untitled:Prompt-2"]);

        registry.forget("untitled:Prompt-1");

        assert.equal(registry.has("untitled:Prompt-1"), false);
        assert.equal(registry.has("untitled:Prompt-2"), true);
      }
    },

    /**
     * Verifies generated analysis documents are recognized by their heading.
     */
    {
      name: "detects Prompt Preflight result documents",
      run: () => {
        assert.equal(
          isPromptPreflightResultText("# Prompt Preflight Result\n\n- Vagueness score: `55/100`"),
          true
        );
        assert.equal(isPromptPreflightResultText("# Task\nCreate a car image"), false);
      }
    }
  ]);
}
