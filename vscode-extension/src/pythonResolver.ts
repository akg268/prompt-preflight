import { spawn } from "child_process";

/**
 * Minimum Python runtime supported by the bundled Prompt Preflight analyzer.
 */
export const MINIMUM_PYTHON_VERSION = "3.10";

/**
 * One Python command that Prompt Preflight can probe or use to run the analyzer.
 */
export interface PythonCandidate {
  command: string;
  argsPrefix: string[];
  label: string;
  source: "configured" | "path" | "common-path";
}

/**
 * Result from trying one Python candidate.
 */
export interface PythonProbeAttempt {
  candidate: PythonCandidate;
  ok: boolean;
  status: "ok" | "not-found" | "too-old" | "failed" | "timeout";
  versionText?: string;
  detail?: string;
}

/**
 * Successful Python runtime resolution used by the analyzer runner.
 */
export interface PythonResolution {
  candidate: PythonCandidate;
  versionText?: string;
  attempts: PythonProbeAttempt[];
}

/**
 * Error thrown when no Python 3.10+ runtime can be found.
 */
export class PythonResolutionError extends Error {
  /**
   * Carries all attempted commands so callers can render actionable setup help.
   */
  constructor(
    message: string,
    readonly attempts: PythonProbeAttempt[],
    readonly configuredPythonPath: string
  ) {
    super(message);
    this.name = "PythonResolutionError";
  }
}

/**
 * Caches the last successful Python lookup for the extension session.
 */
let cachedResolution:
  | {
      key: string;
      resolution: PythonResolution;
    }
  | undefined;

/**
 * Returns true when an unknown error is the Python auto-detection error type.
 */
export function isPythonResolutionError(error: unknown): error is PythonResolutionError {
  return error instanceof PythonResolutionError;
}

/**
 * Adds a Python candidate once, preserving the intended priority order.
 */
function addCandidate(
  candidates: PythonCandidate[],
  command: string,
  argsPrefix: string[],
  label: string,
  source: PythonCandidate["source"]
): void {
  const key = `${command}\0${argsPrefix.join("\0")}`;
  if (candidates.some((candidate) => `${candidate.command}\0${candidate.argsPrefix.join("\0")}` === key)) {
    return;
  }
  candidates.push({ command, argsPrefix, label, source });
}

/**
 * Converts a user setting into a Python candidate. The setting is treated as an
 * executable path by default so Windows paths with spaces remain valid.
 */
function configuredCandidate(configuredPythonPath: string): PythonCandidate | undefined {
  const trimmed = configuredPythonPath.trim();
  if (!trimmed) {
    return undefined;
  }

  const pyLauncherMatch = trimmed.match(/^(py(?:\.exe)?)\s+-3$/i);
  if (pyLauncherMatch) {
    return {
      command: pyLauncherMatch[1],
      argsPrefix: ["-3"],
      label: trimmed,
      source: "configured"
    };
  }

  return {
    command: trimmed,
    argsPrefix: [],
    label: trimmed,
    source: "configured"
  };
}

/**
 * Builds the ordered list of Python commands Prompt Preflight should try.
 */
export function pythonCandidates(
  configuredPythonPath: string,
  platform: NodeJS.Platform = process.platform
): PythonCandidate[] {
  const candidates: PythonCandidate[] = [];
  const configured = configuredCandidate(configuredPythonPath);
  if (configured) {
    addCandidate(candidates, configured.command, configured.argsPrefix, configured.label, "configured");
  }

  addCandidate(candidates, "python3", [], "python3", "path");
  addCandidate(candidates, "python", [], "python", "path");

  if (platform === "win32") {
    addCandidate(candidates, "py", ["-3"], "py -3", "path");
    addCandidate(candidates, "py", [], "py", "path");
  }

  if (platform === "darwin") {
    addCandidate(candidates, "/opt/homebrew/bin/python3", [], "/opt/homebrew/bin/python3", "common-path");
    addCandidate(candidates, "/usr/local/bin/python3", [], "/usr/local/bin/python3", "common-path");
    addCandidate(candidates, "/usr/bin/python3", [], "/usr/bin/python3", "common-path");
  }

  if (platform === "linux") {
    addCandidate(candidates, "/usr/bin/python3", [], "/usr/bin/python3", "common-path");
    addCandidate(candidates, "/usr/local/bin/python3", [], "/usr/local/bin/python3", "common-path");
  }

  return candidates;
}

/**
 * Extracts a semantic Python version from `python --version` output.
 */
export function parsePythonVersion(versionText: string): [number, number, number] | undefined {
  const match = versionText.match(/Python\s+(\d+)\.(\d+)(?:\.(\d+))?/i);
  if (!match) {
    return undefined;
  }
  return [
    Number.parseInt(match[1], 10),
    Number.parseInt(match[2], 10),
    Number.parseInt(match[3] || "0", 10)
  ];
}

/**
 * Returns true when a parsed Python version satisfies the analyzer requirement.
 */
export function isSupportedPythonVersion(version: [number, number, number] | undefined): boolean {
  if (!version) {
    return true;
  }
  const [major, minor] = version;
  return major > 3 || (major === 3 && minor >= 10);
}

/**
 * Runs one Python candidate with `--version` to verify it exists and is new
 * enough for Prompt Preflight.
 */
function probePythonCandidate(candidate: PythonCandidate, timeoutMs: number): Promise<PythonProbeAttempt> {
  return new Promise((resolve) => {
    const child = spawn(candidate.command, [...candidate.argsPrefix, "--version"], {
      stdio: ["ignore", "pipe", "pipe"]
    });

    let settled = false;
    let stdout = "";
    let stderr = "";

    const timeout = setTimeout(() => {
      if (settled) {
        return;
      }
      settled = true;
      child.kill();
      resolve({
        candidate,
        ok: false,
        status: "timeout",
        detail: "Timed out while checking Python version."
      });
    }, timeoutMs);

    child.stdout.setEncoding("utf8");
    child.stderr.setEncoding("utf8");
    child.stdout.on("data", (chunk: string) => {
      stdout += chunk;
    });
    child.stderr.on("data", (chunk: string) => {
      stderr += chunk;
    });
    child.on("error", (error: NodeJS.ErrnoException) => {
      if (settled) {
        return;
      }
      settled = true;
      clearTimeout(timeout);
      resolve({
        candidate,
        ok: false,
        status: error.code === "ENOENT" ? "not-found" : "failed",
        detail: error.message
      });
    });
    child.on("close", (code) => {
      if (settled) {
        return;
      }
      settled = true;
      clearTimeout(timeout);
      const versionText = `${stdout} ${stderr}`.trim().replace(/\s+/g, " ");
      const version = parsePythonVersion(versionText);
      if (code === 0 && isSupportedPythonVersion(version)) {
        resolve({ candidate, ok: true, status: "ok", versionText });
        return;
      }
      if (code === 0 && !isSupportedPythonVersion(version)) {
        resolve({
          candidate,
          ok: false,
          status: "too-old",
          versionText,
          detail: `Python ${MINIMUM_PYTHON_VERSION}+ is required.`
        });
        return;
      }
      resolve({
        candidate,
        ok: false,
        status: "failed",
        versionText,
        detail: stderr.trim() || stdout.trim() || `Exited with code ${code}.`
      });
    });
  });
}

/**
 * Finds the first usable Python command from the configured setting and common
 * fallback names/paths.
 */
export async function resolvePythonCommand(
  configuredPythonPath: string,
  platform: NodeJS.Platform = process.platform,
  timeoutMs = 3000
): Promise<PythonResolution> {
  const cacheKey = `${platform}\0${configuredPythonPath.trim()}`;
  if (cachedResolution?.key === cacheKey) {
    return cachedResolution.resolution;
  }

  const attempts: PythonProbeAttempt[] = [];
  for (const candidate of pythonCandidates(configuredPythonPath, platform)) {
    const attempt = await probePythonCandidate(candidate, timeoutMs);
    attempts.push(attempt);
    if (attempt.ok) {
      const resolution = {
        candidate,
        versionText: attempt.versionText,
        attempts
      };
      cachedResolution = { key: cacheKey, resolution };
      return resolution;
    }
  }

  throw new PythonResolutionError(
    pythonResolutionMessage(configuredPythonPath, attempts),
    attempts,
    configuredPythonPath
  );
}

/**
 * Renders compact attempted-command text for UI errors and setup reports.
 */
export function formatPythonAttempts(attempts: PythonProbeAttempt[]): string {
  if (!attempts.length) {
    return "No Python commands were checked.";
  }
  return attempts
    .map((attempt) => {
      const command = attempt.candidate.label;
      const status = attempt.status === "ok" ? "ok" : attempt.status;
      const detail = attempt.versionText || attempt.detail;
      return detail ? `${command}: ${status} (${detail})` : `${command}: ${status}`;
    })
    .join("\n");
}

/**
 * Builds the human-readable error shown when Python cannot be detected.
 */
export function pythonResolutionMessage(
  configuredPythonPath: string,
  attempts: PythonProbeAttempt[]
): string {
  const configured = configuredPythonPath.trim()
    ? `Configured promptPreflight.pythonPath: ${configuredPythonPath.trim()}`
    : "No promptPreflight.pythonPath is configured; auto-detection was used.";
  const tried = attempts.map((attempt) => attempt.candidate.label).join(", ") || "no candidates";
  return [
    `Prompt Preflight could not find Python ${MINIMUM_PYTHON_VERSION}+ to run the local analyzer.`,
    configured,
    `Tried: ${tried}.`,
    "Install Python or set promptPreflight.pythonPath to the full Python executable path."
  ].join(" ");
}
