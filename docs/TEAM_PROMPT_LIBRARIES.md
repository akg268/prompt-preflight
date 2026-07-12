# Team Prompt Libraries

Teams often store AI-agent prompts in Markdown, XML, or TOML files within docs folders, ticket/PR templates, or internal prompt libraries. Prompt Preflight for VS Code provides tools to manage these shared libraries, ensuring prompts meet clarity and safety bars before they are sent to coding agents or AI tools.

For a comprehensive guide to all VS Code extension features, refer to the [VS Code Extension README](../vscode-extension/README.md).

## Opting a file into checks

To include a prompt file in workspace-wide checks, you must add the opt-in marker near the top of the file. The canonical inner string is `prompt-preflight: check`. It is placed as a comment matching the file format.

For Markdown or XML files, use:
```html
<!-- prompt-preflight: check -->
```

For TOML files, use:
```toml
# prompt-preflight: check
```

## Creating the team policy (`.prompt-preflight.json`)

To share your Prompt Preflight rules, create a `.prompt-preflight.json` file in your workspace root.

Use the Command Palette:
**`Prompt Preflight: Create .prompt-preflight.json`**

A minimal working example based on the repository's template:

```json
{
  "enabled": true,
  "mode": "block",
  "threshold": 45,
  "max_questions": 3,
  "checks": {
    "clarity": "nudge",
    "context": "nudge",
    "output_contract": "nudge",
    "template_contract": "block",
    "risk": "block",
    "plan_first": "block",
    "privacy": "block"
  },
  "severity_thresholds": {
    "block": "high",
    "nudge": "medium"
  },
  "telemetry": {
    "enabled": false,
    "path": ".prompt-preflight-telemetry.jsonl"
  },
  "token_observability": {
    "enabled": true,
    "default_max_output_tokens": 1000,
    "estimated_retry_output_tokens": 800
  }
}
```

## Linting the workspace

To scan your team's prompt library, run the following from the Command Palette:
**`Prompt Preflight: Lint Workspace Prompt Files`**

This command lints every annotated prompt file in the workspace. Any prompt file that does not include the opt-in marker is explicitly skipped with the message: `Opt-in marker required: prompt-preflight: check`.

## Local telemetry

Prompt Preflight provides local prompt-free telemetry. 

You can enable it using the Command Palette:
**`Prompt Preflight: Enable Local Telemetry`**

This sets telemetry to enabled in `.prompt-preflight.json`. The VS Code extension and the `prompt-preflight` CLI discover the report path from `.prompt-preflight.json` and append prompt-free events locally.

**Prompt Preflight telemetry is strictly local and prompt-free.** It records event metadata, decisions, and token estimates, but your prompt content is never included.

You can view your local metrics by running:
**`Prompt Preflight: Open Telemetry Dashboard`**

## Minimal example repository layout

Here is a typical layout showing where prompts, the annotation, and the policy sit:

```text
my-repo/
|-- .prompt-preflight.json                # Shared team policy config
|-- .prompt-preflight-telemetry.jsonl     # Local metrics (kept out of version control)
`-- docs/
    `-- prompts/
        |-- pr-template.md                # Contains <!-- prompt-preflight: check -->
        `-- refactor-kickoff.toml         # Contains # prompt-preflight: check
```
