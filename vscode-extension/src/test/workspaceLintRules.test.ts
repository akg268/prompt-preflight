import assert from "assert/strict";
import {
  PROMPT_PREFLIGHT_CHECK_MARKER,
  hasPromptPreflightCheckMarker,
  languageIdForFileName,
  shouldLintPromptCandidate,
  workspaceLintSummary
} from "../workspaceLintRules";
import { runSuite } from "./testHarness";

/**
 * Unit tests for pure workspace linting rules.
 */
export function runWorkspaceLintRulesTests(): void {
  runSuite("workspaceLintRules", [
    /**
     * Verifies prompt file extensions map to the language IDs used by diagnostics.
     */
    {
      name: "maps prompt extensions to language IDs",
      run: () => {
        assert.equal(languageIdForFileName("prompt.md"), "markdown");
        assert.equal(languageIdForFileName("prompt.xml"), "xml");
        assert.equal(languageIdForFileName("prompt.toml"), "toml");
        assert.equal(languageIdForFileName("src/extension.ts"), undefined);
      }
    },

    /**
     * Verifies workspace lint requires an explicit opt-in marker.
     */
    {
      name: "skips unmarked prompt files",
      run: () => {
        assert.equal(
          shouldLintPromptCandidate({
            fileName: "/workspace/prompts/test.md",
            text: "Create a car image"
          }),
          false
        );
      }
    },

    /**
     * Verifies the single marker opts Markdown, XML, and TOML files into linting.
     */
    {
      name: "lints marked Markdown XML and TOML prompt files",
      run: () => {
        assert.equal(
          shouldLintPromptCandidate({
            fileName: "/workspace/prompts/test.md",
            text: "<!-- prompt-preflight: check -->\n\nCreate a car image"
          }),
          true
        );
        assert.equal(
          shouldLintPromptCandidate({
            fileName: "/workspace/prompts/test.xml",
            text: "<!-- prompt-preflight: check -->\n<prompt>Create a car image</prompt>"
          }),
          true
        );
        assert.equal(
          shouldLintPromptCandidate({
            fileName: "/workspace/prompts/test.toml",
            text: "# prompt-preflight: check\nprofile = \"image\"\ntask = \"Create a car image\""
          }),
          true
        );
      }
    },

    /**
     * Verifies documentation remains skipped even if it contains prompt examples.
     */
    {
      name: "skips docs even when they mention prompts",
      run: () => {
        assert.equal(
          hasPromptPreflightCheckMarker(`<!-- ${PROMPT_PREFLIGHT_CHECK_MARKER} -->`),
          true
        );
        assert.equal(
          shouldLintPromptCandidate({
            fileName: "/workspace/docs/EXAMPLES.md",
            text: "<!-- prompt-preflight: check -->\n\nCreate a car image"
          }),
          false
        );
      }
    },

    /**
     * Verifies the lint summary shows failing prompt files and their vagueness
     * score.
     */
    {
      name: "summarizes failing prompt files",
      run: () => {
        const summary = workspaceLintSummary(
          [
            {
              fileName: "prompts/test.md",
              shouldClarify: true,
              score: 82,
              severity: "high",
              reasons: ["missing context"],
              questions: ["What audience should this target?"]
            }
          ],
          { skipped: 3 }
        );

        assert.match(summary, /Files checked: 1/);
        assert.match(summary, /Files skipped: 3/);
        assert.match(summary, /Opt-in marker required: prompt-preflight: check/);
        assert.match(summary, /Needs clarification: 1/);
        assert.match(summary, /Vagueness score 82\/100/);
        assert.match(summary, /prompts\/test.md/);
      }
    },

    /**
     * Verifies the lint summary gives a clean message when everything passes.
     */
    {
      name: "summarizes a clean lint run",
      run: () => {
        const summary = workspaceLintSummary([
          {
            fileName: "prompts/clear.md",
            shouldClarify: false,
            score: 0,
            severity: "low",
            reasons: [],
            questions: []
          }
        ]);

        assert.match(summary, /Files checked: 1/);
        assert.match(summary, /All checked prompt files are clear to send/);
      }
    }
  ]);
}
