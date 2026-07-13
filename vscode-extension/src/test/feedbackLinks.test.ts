import assert from "assert/strict";
import { betaFeedbackIssueUrl } from "../feedbackLinks";
import { runSuite } from "./testHarness";

/**
 * Unit tests for public feedback URLs.
 */
export function runFeedbackLinksTests(): void {
  runSuite("feedbackLinks", [
    /**
     * Verifies feedback goes to the public beta issue.
     */
    {
      name: "returns the beta feedback issue URL",
      run: () => {
        assert.equal(
          betaFeedbackIssueUrl(),
          "https://github.com/akg268/prompt-preflight/issues/69"
        );
      }
    }
  ]);
}
