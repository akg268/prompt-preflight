import * as fs from "fs";
import * as path from "path";

/**
 * Shape of the team policy pieces used for profile routing.
 */
interface PromptPreflightPolicy {
  profiles?: Record<string, unknown>;
}

/**
 * Checks whether an unknown value is a JSON object.
 */
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/**
 * Reads the workspace policy JSON object when it exists and is valid.
 */
function readPolicy(workspacePath: string): PromptPreflightPolicy | undefined {
  const policyPath = path.join(workspacePath, ".prompt-preflight.json");
  if (!fs.existsSync(policyPath)) {
    return undefined;
  }
  try {
    const parsed = JSON.parse(fs.readFileSync(policyPath, "utf8"));
    return isRecord(parsed) ? parsed : undefined;
  } catch {
    return undefined;
  }
}

/**
 * Converts platform-specific paths to policy-friendly forward-slash paths.
 */
function normalizePathForPolicy(value: string): string {
  return value.replace(/\\/g, "/").replace(/^\.\//, "");
}

/**
 * Converts a minimal glob pattern to a regular expression. This intentionally
 * supports the simple profile-policy patterns teams are likely to use:
 * `*`, `**`, and `?`.
 */
export function globPatternToRegExp(pattern: string): RegExp {
  const normalized = normalizePathForPolicy(pattern);
  let source = "^";
  for (let index = 0; index < normalized.length; index += 1) {
    const char = normalized[index];
    const next = normalized[index + 1];
    if (char === "*" && next === "*") {
      source += ".*";
      index += 1;
    } else if (char === "*") {
      source += "[^/]*";
    } else if (char === "?") {
      source += "[^/]";
    } else {
      source += char.replace(/[|\\{}()[\]^$+?.]/g, "\\$&");
    }
  }
  source += "$";
  return new RegExp(source);
}

/**
 * Finds the first configured profile matching a workspace-relative file path.
 */
export function profileFromPolicy(
  policy: PromptPreflightPolicy | undefined,
  relativeFilePath: string
): string | undefined {
  if (!policy || !isRecord(policy.profiles)) {
    return undefined;
  }

  const normalizedPath = normalizePathForPolicy(relativeFilePath);
  const basename = path.posix.basename(normalizedPath);
  for (const [pattern, profile] of Object.entries(policy.profiles)) {
    if (typeof profile !== "string" || !profile.trim()) {
      continue;
    }
    const matcher = globPatternToRegExp(pattern);
    if (matcher.test(normalizedPath) || matcher.test(basename)) {
      return profile.trim();
    }
  }
  return undefined;
}

/**
 * Resolves the Prompt Preflight profile for a file in a VS Code workspace.
 */
export function profileForWorkspaceFile(
  workspacePath: string | undefined,
  filePath: string | undefined
): string | undefined {
  if (!workspacePath || !filePath) {
    return undefined;
  }
  const relativePath = normalizePathForPolicy(path.relative(workspacePath, filePath));
  return profileFromPolicy(readPolicy(workspacePath), relativePath);
}
