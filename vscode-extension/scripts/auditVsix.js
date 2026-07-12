#!/usr/bin/env node

const { execFileSync } = require("child_process");
const fs = require("fs");
const path = require("path");

/**
 * File patterns that must never ship in the public VSIX package.
 */
const FORBIDDEN_PATTERNS = [
  /^extension\/src\//,
  /^extension\/node_modules\//,
  /^extension\/out\/test\//,
  /^extension\/\.vscode\//,
  /^extension\/scripts\//,
  /^extension\/bundled-analyzer\/.*__pycache__\//,
  /^extension\/bundled-analyzer\/.*\.pyc$/,
  /^extension\/bundled-analyzer\/.*\.pyo$/,
  /^extension\/.*\.map$/,
  /^extension\/.*\.vsix$/,
  /^extension\/package-lock\.json$/,
  /^extension\/testprompt\.md$/
];

/**
 * Files that must exist in every usable VSIX package.
 */
const REQUIRED_FILES = [
  "extension/package.json",
  "extension/readme.md",
  "extension/LICENSE.txt",
  "extension/media/icon.png",
  "extension/out/extension.js",
  "extension/out/preflightClient.js",
  "extension/out/setupDoctor.js",
  "extension/out/telemetryDashboardPanel.js",
  "extension/out/releaseReadiness.js",
  "extension/bundled-analyzer/scripts/prompt_preflight.py",
  "extension/bundled-analyzer/src/prompt_preflight/cli.py",
  "extension/bundled-analyzer/src/prompt_preflight/analyzer.py",
  "extension/bundled-analyzer/src/prompt_preflight/data/prompt_templates.json",
  "extension/bundled-analyzer/src/prompt_preflight/data/vague_prompts.txt",
  "extension/bundled-analyzer/docs/EXAMPLES.md"
];

/**
 * Text that must appear in the packaged README after vsce rewrites relative images.
 */
const REQUIRED_README_SNIPPETS = [
  "https://raw.githubusercontent.com/akg268/prompt-preflight/main/vscode-extension/media/demo.gif"
];

/**
 * Reads the VSIX file path from argv and resolves it against cwd.
 */
function resolveVsixPath() {
  const packageJson = JSON.parse(
    fs.readFileSync(path.resolve(process.cwd(), "package.json"), "utf8")
  );
  const defaultName = `${packageJson.name}-${packageJson.version}.vsix`;
  const argPath = process.argv[2] || defaultName;
  return path.resolve(process.cwd(), argPath);
}

/**
 * Lists every path inside a VSIX package using the system unzip command.
 */
function listVsixEntries(vsixPath) {
  const output = execFileSync("unzip", ["-Z", "-1", vsixPath], {
    encoding: "utf8"
  });
  return output.split(/\r?\n/).filter(Boolean).sort();
}

/**
 * Reads one file from inside the VSIX package.
 */
function readVsixEntry(vsixPath, entryPath) {
  return execFileSync("unzip", ["-p", vsixPath, entryPath], {
    encoding: "utf8"
  });
}

/**
 * Returns package entries that match any forbidden pattern.
 */
function forbiddenEntries(entries) {
  return entries.filter((entry) => FORBIDDEN_PATTERNS.some((pattern) => pattern.test(entry)));
}

/**
 * Returns required package files that are missing from the VSIX.
 */
function missingRequiredFiles(entries) {
  const entrySet = new Set(entries);
  return REQUIRED_FILES.filter((required) => !entrySet.has(required));
}

/**
 * Returns required README snippets that are missing from the packaged README.
 */
function missingReadmeSnippets(vsixPath) {
  const readme = readVsixEntry(vsixPath, "extension/readme.md");
  return REQUIRED_README_SNIPPETS.filter((snippet) => !readme.includes(snippet));
}

/**
 * Prints a readable package audit summary.
 */
function printSummary(vsixPath, entries) {
  console.log(`Prompt Preflight VSIX package audit`);
  console.log(`VSIX: ${vsixPath}`);
  console.log(`Files: ${entries.length}`);
}

/**
 * Runs the audit and exits non-zero if the package is not release-safe.
 */
function main() {
  const vsixPath = resolveVsixPath();
  if (!fs.existsSync(vsixPath)) {
    console.error(`VSIX file not found: ${vsixPath}`);
    process.exit(1);
  }

  const entries = listVsixEntries(vsixPath);
  const forbidden = forbiddenEntries(entries);
  const missing = missingRequiredFiles(entries);
  const missingReadme = missingReadmeSnippets(vsixPath);

  printSummary(vsixPath, entries);

  if (forbidden.length) {
    console.error("\nForbidden files included:");
    for (const entry of forbidden) {
      console.error(`- ${entry}`);
    }
  }

  if (missing.length) {
    console.error("\nRequired files missing:");
    for (const entry of missing) {
      console.error(`- ${entry}`);
    }
  }

  if (missingReadme.length) {
    console.error("\nRequired README snippets missing:");
    for (const snippet of missingReadme) {
      console.error(`- ${snippet}`);
    }
  }

  if (forbidden.length || missing.length || missingReadme.length) {
    process.exit(1);
  }

  console.log("Package audit passed.");
}

main();
