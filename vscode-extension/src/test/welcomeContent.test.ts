import assert from "assert/strict";
import {
  shouldShowWelcomePage,
  welcomeMarkdown,
  WELCOME_VERSION_STATE_KEY
} from "../welcomeContent";
import { runSuite } from "./testHarness";

/**
 * Unit tests for first-run welcome-page content and state decisions.
 */
export function runWelcomeContentTests(): void {
  runSuite("welcomeContent", [
    /**
     * Verifies the welcome page opens once for a new extension version.
     */
    {
      name: "shows when version has not been seen",
      run: () => {
        assert.equal(shouldShowWelcomePage(undefined, "0.0.3"), true);
        assert.equal(shouldShowWelcomePage("0.0.2", "0.0.3"), true);
        assert.equal(shouldShowWelcomePage("0.0.3", "0.0.3"), false);
      }
    },

    /**
     * Verifies the global state key stays stable across releases.
     */
    {
      name: "uses a stable global-state key",
      run: () => {
        assert.equal(WELCOME_VERSION_STATE_KEY, "promptPreflight.welcomeVersion");
      }
    },

    /**
     * Verifies welcome content points users to the core beta actions.
     */
    {
      name: "renders onboarding commands and feedback link",
      run: () => {
        const markdown = welcomeMarkdown(
          "0.0.3",
          "https://github.com/akg268/prompt-preflight/issues/69"
        );

        assert.match(markdown, /Welcome to Prompt Preflight/);
        assert.match(markdown, /Prompt Preflight: New Prompt Template/);
        assert.match(markdown, /Prompt Preflight: Share Beta Feedback/);
        assert.match(markdown, /feature_spec/);
        assert.match(markdown, /prompt text is not sent to a network service/i);
        assert.match(markdown, /https:\/\/github.com\/akg268\/prompt-preflight\/issues\/69/);
      }
    }
  ]);
}
