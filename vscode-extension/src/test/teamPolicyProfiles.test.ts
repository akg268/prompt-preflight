import assert from "assert/strict";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import {
  globPatternToRegExp,
  profileForWorkspaceFile,
  profileFromPolicy
} from "../teamPolicyProfiles";
import { runSuite } from "./testHarness";

/**
 * Creates a temporary workspace for team policy profile tests.
 */
function tempWorkspace(): string {
  return fs.mkdtempSync(path.join(os.tmpdir(), "prompt-preflight-policy-profiles-"));
}

/**
 * Unit tests for folder-based profile routing in VS Code.
 */
export function runTeamPolicyProfilesTests(): void {
  runSuite("teamPolicyProfiles", [
    /**
     * Verifies simple glob support for folder policies.
     */
    {
      name: "matches double-star profile globs",
      run: () => {
        const matcher = globPatternToRegExp("docs/prompts/research/**");

        assert.equal(matcher.test("docs/prompts/research/vendors.md"), true);
        assert.equal(matcher.test("docs/prompts/specs/vendors.md"), false);
      }
    },

    /**
     * Verifies profile mappings preserve object order and return first match.
     */
    {
      name: "returns first matching profile from policy",
      run: () => {
        const profile = profileFromPolicy(
          {
            profiles: {
              "docs/prompts/research/**": "research",
              "**/*.md": "general"
            }
          },
          "docs/prompts/research/vendors.md"
        );

        assert.equal(profile, "research");
      }
    },

    /**
     * Verifies workspace files resolve through .prompt-preflight.json.
     */
    {
      name: "resolves workspace file profile",
      run: () => {
        const workspace = tempWorkspace();
        try {
          fs.mkdirSync(path.join(workspace, "docs", "prompts", "specs"), { recursive: true });
          fs.writeFileSync(
            path.join(workspace, ".prompt-preflight.json"),
            JSON.stringify({
              profiles: {
                "docs/prompts/specs/**": "feature_spec"
              }
            })
          );

          assert.equal(
            profileForWorkspaceFile(
              workspace,
              path.join(workspace, "docs", "prompts", "specs", "checkout.md")
            ),
            "feature_spec"
          );
        } finally {
          fs.rmSync(workspace, { recursive: true, force: true });
        }
      }
    }
  ]);
}
