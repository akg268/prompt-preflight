#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

/**
 * Extension folder that owns package.json and the generated VSIX.
 */
const extensionRoot = path.resolve(__dirname, "..");

/**
 * Main repository root that contains the canonical Python analyzer source.
 */
const repoRoot = path.resolve(extensionRoot, "..");

/**
 * Generated analyzer folder included in the VSIX package.
 */
const bundledRoot = path.join(extensionRoot, "bundled-analyzer");

/**
 * Runtime files needed by the Python analyzer inside the VSIX.
 */
const runtimeCopies = [
  {
    from: path.join(repoRoot, "scripts", "prompt_preflight.py"),
    to: path.join(bundledRoot, "scripts", "prompt_preflight.py")
  },
  {
    from: path.join(repoRoot, "src", "prompt_preflight"),
    to: path.join(bundledRoot, "src", "prompt_preflight")
  },
  {
    from: path.join(repoRoot, "docs", "EXAMPLES.md"),
    to: path.join(bundledRoot, "docs", "EXAMPLES.md")
  }
];

/**
 * Returns true for Python cache/build artifacts that should not be packaged.
 */
function shouldSkip(sourcePath) {
  const basename = path.basename(sourcePath);
  return (
    basename === "__pycache__" ||
    basename === ".pytest_cache" ||
    basename.endsWith(".pyc") ||
    basename.endsWith(".pyo")
  );
}

/**
 * Copies a file or directory recursively while filtering generated Python cache files.
 */
function copyRuntimePath(sourcePath, targetPath) {
  const stat = fs.statSync(sourcePath);
  if (shouldSkip(sourcePath)) {
    return;
  }

  if (stat.isDirectory()) {
    fs.mkdirSync(targetPath, { recursive: true });
    for (const entry of fs.readdirSync(sourcePath)) {
      copyRuntimePath(path.join(sourcePath, entry), path.join(targetPath, entry));
    }
    return;
  }

  fs.mkdirSync(path.dirname(targetPath), { recursive: true });
  fs.copyFileSync(sourcePath, targetPath);
}

/**
 * Counts staged files so packaging logs show an easy sanity check.
 */
function countFiles(directory) {
  let count = 0;
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const entryPath = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      count += countFiles(entryPath);
    } else {
      count += 1;
    }
  }
  return count;
}

/**
 * Validates the minimal runtime shape before VSIX packaging continues.
 */
function assertRequiredFiles() {
  const required = [
    path.join(bundledRoot, "scripts", "prompt_preflight.py"),
    path.join(bundledRoot, "src", "prompt_preflight", "cli.py"),
    path.join(bundledRoot, "src", "prompt_preflight", "analyzer.py"),
    path.join(bundledRoot, "src", "prompt_preflight", "data", "prompt_templates.json"),
    path.join(bundledRoot, "src", "prompt_preflight", "data", "vague_prompts.txt"),
    path.join(bundledRoot, "docs", "EXAMPLES.md")
  ];

  const missing = required.filter((filePath) => !fs.existsSync(filePath));
  if (missing.length) {
    throw new Error(`Bundled analyzer staging missed required files:\n${missing.join("\n")}`);
  }
}

/**
 * Rebuilds the generated VSIX analyzer bundle from canonical repo source.
 */
function main() {
  fs.rmSync(bundledRoot, { recursive: true, force: true });
  fs.mkdirSync(bundledRoot, { recursive: true });

  for (const copy of runtimeCopies) {
    copyRuntimePath(copy.from, copy.to);
  }

  assertRequiredFiles();
  console.log(`Staged bundled Python analyzer at ${bundledRoot} (${countFiles(bundledRoot)} files).`);
}

main();
