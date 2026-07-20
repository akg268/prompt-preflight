import assert from "assert/strict";
import { betaFeedbackIssueUrl, calibrationIssueUrl } from "../feedbackLinks";
import { runSuite } from "./testHarness";

/**
 * Unit tests for public feedback URLs.
 */
export function runFeedbackLinksTests(): void {
  runSuite("feedbackLinks", [
    /**
     * Verifies feedback goes to the public feedback issue.
     */
    {
      name: "returns the public feedback issue URL",
      run: () => {
        assert.equal(
          betaFeedbackIssueUrl(),
          "https://github.com/akg268/prompt-preflight/issues/69"
        );
      }
    },

    /**
     * Verifies calibration issue URLs carry actionable metadata.
     */
    {
      name: "builds calibration issue URL",
      run: () => {
        const url = calibrationIssueUrl({
          kind: "false_positive",
          prompt: "Create a car image",
          intent: "image_generation",
          score: 75,
          severity: "high",
          decision: "block",
          checks: ["context"]
        });

        assert.match(url, /issues\/new/);
        assert.match(decodeURIComponent(url), /False positive/);
        assert.match(decodeURIComponent(url), /Create a car image/);
        assert.match(decodeURIComponent(url), /image_generation/);
      }
    }
  ]);
}
