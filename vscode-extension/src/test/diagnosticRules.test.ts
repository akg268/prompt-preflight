import assert from "assert/strict";
import {
  diagnosticSummariesFromAnalysis,
  shouldAnalyzePromptDocument
} from "../diagnosticRules";
import { runSuite } from "./testHarness";

/**
 * Unit tests for pure diagnostic rules that do not require VS Code's extension
 * host.
 */
export function runDiagnosticRulesTests(): void {
  runSuite("diagnosticRules", [
  /**
   * Verifies diagnostics run only for prompt-like document languages.
   */
    {
      name: "analyzes prompt file languages and skips source code",
      run: () => {
        assert.equal(
          shouldAnalyzePromptDocument("markdown", "Create a car image", {
            fileName: "/workspace/test.md"
          }),
          true
        );
        assert.equal(shouldAnalyzePromptDocument("xml", "<prompt></prompt>"), true);
        assert.equal(shouldAnalyzePromptDocument("toml", "profile = \"general\""), true);
        assert.equal(shouldAnalyzePromptDocument("typescript", "const prompt = 'hello';"), false);
      }
    },

  /**
   * Verifies documentation pages with sample prompts do not create noisy
   * Problems-panel entries.
   */
    {
      name: "skips documentation files like docs/EXAMPLES.md",
      run: () => {
        assert.equal(
          shouldAnalyzePromptDocument("markdown", "# Examples\n\nCreate a car image", {
            fileName: "/workspace/docs/EXAMPLES.md"
          }),
          false
        );
        assert.equal(
          shouldAnalyzePromptDocument("markdown", "# README\n\nCreate a car image", {
            fileName: "/workspace/README.md"
          }),
          false
        );
      }
    },

  /**
   * Verifies generated result documents do not diagnose themselves.
   */
    {
      name: "skips Prompt Preflight result documents",
      run: () => {
        assert.equal(
          shouldAnalyzePromptDocument(
            "markdown",
            "# Prompt Preflight Result\n\n- Vagueness score: `90/100`"
          ),
          false
        );
      }
    },

  /**
   * Verifies large documents are skipped so README-style files do not create
   * noisy automatic diagnostics.
   */
    {
      name: "skips documents beyond the configured max character limit",
      run: () => {
        assert.equal(
          shouldAnalyzePromptDocument("markdown", "x".repeat(11), { maxCharacters: 10 }),
          false
        );
      }
    },

  /**
   * Verifies vague analyzer results become one actionable diagnostic.
   */
    {
      name: "creates one warning diagnostic for prompts that need clarification",
      run: () => {
        const diagnostics = diagnosticSummariesFromAnalysis(
          {
            should_clarify: true,
            score: 91,
            severity: "high",
            reasons: ["missing context"],
            questions: ["What audience should this target?"]
          },
          "\nCreate a story for kids"
        );

        assert.equal(diagnostics.length, 1);
        assert.equal(diagnostics[0].severity, "warning");
        assert.match(diagnostics[0].message, /needs clarification/);
        assert.match(diagnostics[0].message, /Vagueness score 91\/100/);
        assert.match(diagnostics[0].message, /missing context/);
        assert.match(diagnostics[0].message, /Open Prompt Preflight examples/);
        assert.equal(diagnostics[0].range.startLine, 1);
      }
    },

  /**
   * Verifies clear analyzer results remove diagnostics.
   */
    {
      name: "returns no diagnostics for clear prompts",
      run: () => {
        const diagnostics = diagnosticSummariesFromAnalysis(
          {
            should_clarify: false,
            score: 0,
            severity: "low",
            reasons: [],
            questions: []
          },
          "Create a photorealistic image of a red Mustang, 16:9."
        );

        assert.deepEqual(diagnostics, []);
      }
    }
  ]);
}
