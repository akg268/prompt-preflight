# Changelog

## 1.0.0

- Promotes Prompt Preflight for VS Code to the stable release build after installed-extension UAT.
- Bundles the Python analyzer so Marketplace and VSIX users do not need `promptPreflight.repoPath`.
- Includes Python runtime auto-detection, Setup Doctor, local telemetry dashboard, prompt-library lint, folder profiles, result feedback actions, and spec-driven prompt templates.
- Documents the harmless VS Code CLI `DEP0169` install warning.

## 0.1.0

- Adds result feedback actions for Helpful, False positive, Missed vagueness, and prefilled calibration issues.
- Adds `.prompt-preflight.json` folder profile routing to VS Code checks, diagnostics, and workspace lint.
- Adds prompt-free local feedback telemetry and dashboard feedback charts.
- Adds a token-savings proof panel to the local telemetry dashboard.
- Adds CI prompt-library lint documentation and cross-tool parity coverage.

## 0.0.5

- Removes the VS Code Marketplace Preview label from extension metadata.
- Renames the visible feedback command to `Prompt Preflight: Share Feedback`.

## 0.0.4

- Adds Python runtime auto-detection for `python3`, `python`, Windows `py -3`, and common macOS/Linux install paths.
- Improves missing-Python failures with actions to run Setup Doctor, open the Python setting, or install Python.
- Updates Setup Doctor to show the detected Python runtime and every command it tried.

## 0.0.3

- Adds a first-run welcome page with quick-start steps, privacy notes, and spec-driven template guidance.
- Adds `Prompt Preflight: Open Welcome` so users can reopen onboarding anytime.
- Adds `Prompt Preflight: Share Beta Feedback`, which opens the public GitHub beta-feedback issue.

## 0.0.2

- Adds Marketplace beta positioning and packaged README/demo polish.
- Adds `Prompt Preflight: New Prompt Template`, which asks users to choose Markdown, TOML, or XML before selecting a template profile.
- Adds spec-driven development templates for feature specs, requirements specs, technical design specs, implementation plans, agent execution prompts, and spec review checklists.
- Keeps the bundled Python analyzer in the VSIX so Marketplace users do not need `promptPreflight.repoPath`.

## 0.0.1

- Initial local-development VS Code extension.
- Adds prompt checks, Markdown CodeLens, suggested prompt insertion, Prompt Composer, template commands, diagnostics, workspace prompt lint, team policy template, and generated-tab cleanup.
- Adds VSIX packaging metadata and package scripts.
