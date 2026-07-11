import assert from "assert/strict";
import {
  releaseChecklistSections,
  releaseReadinessMarkdown
} from "../releaseReadiness";
import { runSuite } from "./testHarness";

/**
 * Unit tests for the public-release readiness checklist.
 */
export function runReleaseReadinessTests(): void {
  runSuite("releaseReadiness", [
    /**
     * Verifies the release gate covers the high-risk areas we care about.
     */
    {
      name: "contains required release gate sections",
      run: () => {
        const sectionTitles = releaseChecklistSections().map((section) => section.title);

        assert.ok(sectionTitles.includes("Local quality gates"));
        assert.ok(sectionTitles.includes("VS Code clean-install gates"));
        assert.ok(sectionTitles.includes("Public packaging gates"));
        assert.ok(sectionTitles.includes("Docs and launch gates"));
        assert.ok(sectionTitles.includes("Privacy and safety gates"));
        assert.ok(sectionTitles.includes("Repo hygiene gates"));
      }
    },

    /**
     * Verifies the rendered Markdown includes the concrete commands and product
     * checks needed before public release.
     */
    {
      name: "renders actionable markdown checklist",
      run: () => {
        const markdown = releaseReadinessMarkdown();

        assert.match(markdown, /Prompt Preflight Release Readiness Checklist/);
        assert.match(markdown, /python3 -m unittest discover -s tests -q/);
        assert.match(markdown, /Prompt Preflight: Run Setup Doctor/);
        assert.match(markdown, /Prompt Preflight: Open Telemetry Dashboard/);
        assert.match(markdown, /Telemetry remains local and prompt-free/);
        assert.match(markdown, /When those are true, it is time to release publicly/);
      }
    }
  ]);
}
