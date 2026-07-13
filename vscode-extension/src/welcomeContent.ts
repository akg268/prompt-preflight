/**
 * Global-state key used to remember the extension version that already showed
 * the welcome page.
 */
export const WELCOME_VERSION_STATE_KEY = "promptPreflight.welcomeVersion";

/**
 * Marketplace listing URL shown in the welcome page.
 */
export const MARKETPLACE_URL =
  "https://marketplace.visualstudio.com/items?itemName=arunkumar-ganesan.prompt-preflight-vscode";

/**
 * Returns true when the welcome page should open for this extension version.
 */
export function shouldShowWelcomePage(
  seenVersion: string | undefined,
  currentVersion: string
): boolean {
  return Boolean(currentVersion) && seenVersion !== currentVersion;
}

/**
 * Builds the one-time welcome Markdown shown after install or version update.
 */
export function welcomeMarkdown(extensionVersion: string, feedbackUrl: string): string {
  return [
    "# Welcome to Prompt Preflight",
    "",
    `Version: \`${extensionVersion}\``,
    "",
    "Prompt Preflight helps catch vague AI-agent prompts before coding agents and AI tools spend model turns.",
    "",
    "## Try it in 60 seconds",
    "",
    "1. Create or open a Markdown file.",
    "2. Add this marker at the top if you want workspace lint to include the file:",
    "",
    "   ```md",
    "   <!-- prompt-preflight: check -->",
    "   ```",
    "",
    "3. Type a vague prompt:",
    "",
    "   ```text",
    "   build a dashboard",
    "   ```",
    "",
    "4. Click the green `Run Prompt Preflight Check` CodeLens action.",
    "5. Review the questions, suggested prompt, and Vagueness score.",
    "",
    "## Useful commands",
    "",
    "- `Prompt Preflight: Check Selected Prompt`",
    "- `Prompt Preflight: New Prompt Template`",
    "- `Prompt Preflight: Open Prompt Composer`",
    "- `Prompt Preflight: Enable Local Telemetry`",
    "- `Prompt Preflight: Open Telemetry Dashboard`",
    "- `Prompt Preflight: Run Setup Doctor`",
    "- `Prompt Preflight: Share Beta Feedback`",
    "",
    "## Spec-driven development",
    "",
    "Run `Prompt Preflight: New Prompt Template`, choose Markdown/TOML/XML, then choose one of:",
    "",
    "- `feature_spec`",
    "- `requirements_spec`",
    "- `technical_design_spec`",
    "- `implementation_plan`",
    "- `agent_execution_prompt`",
    "- `spec_review_checklist`",
    "",
    "These templates help turn vague feature ideas into clearer specs before Codex, Claude Code, Kiro, or another coding agent starts editing files.",
    "",
    "## Privacy",
    "",
    "- Prompt checks run locally.",
    "- The analyzer makes no model calls.",
    "- Prompt text is not sent to a network service.",
    "- Optional telemetry is local and prompt-free.",
    "",
    "## Share beta feedback",
    "",
    `Please share what worked, what felt confusing, and any false positives/false negatives: ${feedbackUrl}`,
    "",
    "## Marketplace",
    "",
    MARKETPLACE_URL,
    ""
  ].join("\n");
}
