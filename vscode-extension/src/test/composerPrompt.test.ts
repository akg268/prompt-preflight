import assert from "assert/strict";
import {
  ComposerForm,
  PROMPT_CHECK_MARKER,
  buildComposedPrompt,
  composerFormHasRequiredFields,
  composerProfileRequiresConstraints
} from "../composerPrompt";
import { runSuite } from "./testHarness";

/**
 * Unit tests for pure Prompt Composer prompt-building logic.
 */
export function runComposerPromptTests(): void {
  runSuite("composerPrompt", [
    /**
     * Verifies generated prompts opt into workspace lint by default.
     */
    {
      name: "adds the prompt-preflight check marker",
      run: () => {
        const prompt = buildComposedPrompt(completeForm());

        assert.ok(prompt.startsWith(PROMPT_CHECK_MARKER));
        assert.match(prompt, /# Task/);
        assert.match(prompt, /Create a car image/);
      }
    },

    /**
     * Verifies success criteria are normalized into Markdown bullets.
     */
    {
      name: "formats success criteria as bullet lines",
      run: () => {
        const prompt = buildComposedPrompt({
          ...completeForm(),
          successCriteria: "Use 16:9\nNo people in the image"
        });

        assert.match(prompt, /- Use 16:9/);
        assert.match(prompt, /- No people in the image/);
      }
    },

    /**
     * Verifies incomplete forms are not considered ready.
     */
    {
      name: "detects missing required fields",
      run: () => {
        assert.equal(composerFormHasRequiredFields(completeForm()), true);
        assert.equal(
          composerFormHasRequiredFields({
            ...completeForm(),
            context: ""
          }),
          false
        );
      }
    },

    /**
     * Verifies empty optional fields are omitted instead of emitted as
     * placeholder text that the analyzer could treat as missing content.
     */
    {
      name: "omits empty optional constraints and examples",
      run: () => {
        const prompt = buildComposedPrompt({
          ...completeForm(),
          profile: "general",
          constraints: "",
          examples: ""
        });

        assert.doesNotMatch(prompt, /# Optional/);
        assert.doesNotMatch(prompt, /Boundaries or things to preserve/);
        assert.doesNotMatch(prompt, /Sample output/);
      }
    },

    /**
     * Verifies software prompts require explicit constraints because that
     * profile asks agents to preserve behavior and avoid out-of-scope changes.
     */
    {
      name: "requires constraints for software profile",
      run: () => {
        assert.equal(composerProfileRequiresConstraints("software"), true);
        assert.equal(composerProfileRequiresConstraints("general"), false);
        assert.equal(
          composerFormHasRequiredFields({
            ...completeForm(),
            profile: "software",
            constraints: ""
          }),
          false
        );

        const prompt = buildComposedPrompt({
          ...completeForm(),
          profile: "software",
          constraints: ""
        });

        assert.match(prompt, /# Constraints/);
        assert.match(prompt, /Required boundaries/);
      }
    },

    /**
     * Verifies profile metadata cannot break the generated HTML comment.
     */
    {
      name: "sanitizes profile metadata comments",
      run: () => {
        const prompt = buildComposedPrompt({
          ...completeForm(),
          profile: "image --> bad"
        });

        assert.doesNotMatch(prompt, /image --> bad/);
        assert.match(prompt, /<!-- profile: image  bad -->/);
      }
    }
  ]);
}

/**
 * Returns a complete composer form for tests.
 */
function completeForm(): ComposerForm {
  return {
    profile: "image",
    task: "Create a car image",
    context: "Magazine cover for a classic car issue.",
    outputFormat: "Markdown prompt with 16:9 image details.",
    successCriteria: "Specific subject, style, lighting, and aspect ratio are included.",
    constraints: "No people.",
    examples: "Cinematic automotive photography."
  };
}
