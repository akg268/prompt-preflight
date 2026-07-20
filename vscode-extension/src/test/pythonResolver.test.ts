import assert from "assert/strict";
import {
  isSupportedPythonVersion,
  parsePythonVersion,
  pythonCandidates,
  pythonResolutionMessage
} from "../pythonResolver";
import { runSuite } from "./testHarness";

/**
 * Unit tests for Python runtime candidate ordering and setup messages.
 */
export function runPythonResolverTests(): void {
  runSuite("pythonResolver", [
    /**
     * Verifies auto-detection still works when the user leaves the setting empty.
     */
    {
      name: "tries default PATH commands without configured python path",
      run: () => {
        const candidates = pythonCandidates("", "darwin").map((candidate) => candidate.label);

        assert.deepEqual(candidates.slice(0, 2), ["python3", "python"]);
        assert.ok(candidates.includes("/opt/homebrew/bin/python3"));
      }
    },

    /**
     * Verifies a user setting remains the highest-priority candidate.
     */
    {
      name: "tries configured python path first",
      run: () => {
        const candidates = pythonCandidates("/custom/python3", "linux");

        assert.equal(candidates[0].label, "/custom/python3");
        assert.equal(candidates[0].source, "configured");
      }
    },

    /**
     * Verifies Windows Python launcher syntax can be configured without
     * breaking executable paths that contain spaces.
     */
    {
      name: "supports windows py launcher candidate",
      run: () => {
        const configured = pythonCandidates("py -3", "win32")[0];

        assert.equal(configured.command, "py");
        assert.deepEqual(configured.argsPrefix, ["-3"]);
      }
    },

    /**
     * Verifies Python version parsing accepts the current supported range.
     */
    {
      name: "parses and validates python versions",
      run: () => {
        assert.deepEqual(parsePythonVersion("Python 3.12.4"), [3, 12, 4]);
        assert.equal(isSupportedPythonVersion(parsePythonVersion("Python 3.9.18")), false);
        assert.equal(isSupportedPythonVersion(parsePythonVersion("Python 3.10.0")), true);
        assert.equal(isSupportedPythonVersion(undefined), true);
      }
    },

    /**
     * Verifies missing Python errors tell users what to do next.
     */
    {
      name: "renders actionable missing python message",
      run: () => {
        const message = pythonResolutionMessage("", []);

        assert.match(message, /Python 3\.10\+/);
        assert.match(message, /promptPreflight\.pythonPath/);
        assert.match(message, /Install Python/);
      }
    }
  ]);
}
