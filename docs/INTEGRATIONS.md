# Host Integrations & Compatibility

Prompt Preflight is built on a shared, deterministic Python core (`analyze_prompt`) that can be adapted to any AI agent or editor host. 

However, to provide a true **pre-prompt block**—pausing a vague prompt *before* it burns an expensive model turn, and giving the user a chance to fix it—the host must expose a hook that fires immediately after the user hits send, but before the model is invoked. 

This document explores integration options for various hosts. For current installation instructions, see the Host compatibility matrix in the [README](../README.md#host-compatibility-matrix).

*(For teams managing shared prompt templates in VS Code, see the [Team Prompt Libraries](TEAM_PROMPT_LIBRARIES.md) guide).*

## Classification Legend

- `block` — Host exposes a pre-prompt hook that can PREVENT submission and show feedback to the user.
- `nudge` — Host can surface feedback/context before/around the prompt but CANNOT hard-block it.
- `wrapper` — No in-host prompt hook; Prompt Preflight must run as an external CLI step before invoking the tool (e.g., Kiro CLI).
- `unsupported` — No viable integration path today.

## Compatibility Matrix

| Host | Pre-prompt hook / mechanism | Can block before model turn? | Config location | Classification | Official docs |
| --- | --- | --- | --- | --- | --- |
| **Cursor** | `beforeSubmitPrompt` (beta) | Yes (JSON output) | `.cursor/hooks.json` | `block` | [Cursor Hooks](https://cursor.com/docs/hooks) |
| **Windsurf** | `pre_user_prompt` | Yes (exit code 2) | `.windsurf/hooks.json` | `block` | [Windsurf Cascade Hooks](https://docs.windsurf.com/windsurf/cascade/hooks) |
| **VS Code (Copilot)** | `UserPromptSubmit` (Preview) | Yes (exit code 2 / JSON) | `.github/hooks/*.json` | `block` | [VS Code Agent Hooks](https://code.visualstudio.com/docs/agent-customization/hooks) |
| **Continue (CLI)** | `UserPromptSubmit` | Yes (exit code 2) | `~/.continue/settings.json` | `block` | [Continue.dev](https://docs.continue.dev) (pending verification) |
| **Continue (IDE)** | Slash commands / context providers | No (config-driven only) | `config.yaml` | `wrapper` | [Continue.dev](https://docs.continue.dev) (pending verification) |
| **Cline** | `UserPromptSubmit` / `PreToolUse` | Yes (JSON `cancel`) | `.clinerules/hooks/` | `block` | [Cline Hooks](https://cline.bot) |

## Primary Host Analysis

### Cursor (beta)
Cursor supports a `beforeSubmitPrompt` hook (introduced ~v1.7) that fires after the user submits a prompt but before the request reaches the model. It blocks by returning a JSON object `{ "continue": false, "user_message": "<feedback>" }`. When blocked, the user sees the `user_message` in the UI, making it an excellent fit for Prompt Preflight's clarification workflow. The input JSON includes `prompt` and `attachments` (files and rules). Note that while it can block and message the user, it cannot currently inject modified context into the prompt stream. Configured in `.cursor/hooks.json` (version 1).
[Official Docs](https://cursor.com/docs/hooks)

### Windsurf
Windsurf's Cascade agent supports a `pre_user_prompt` hook that fires before the prompt is processed. It uses a standard POSIX exit-code model: exiting with code `2` blocks the prompt, and any `stdout` from the hook script is displayed to the user in the Windsurf UI. This behaves identically to the existing Kiro adapter. Configured via `.windsurf/hooks.json` (with system and user-level fallbacks).
[Official Docs](https://docs.windsurf.com/windsurf/cascade/hooks)

### VS Code (GitHub Copilot Chat) (Preview)
VS Code Copilot Chat introduces Agent hooks (in Preview) featuring a `UserPromptSubmit` event. Hooks can block submission via exit code `2` or by returning JSON with `continue: false` and a `systemMessage`/`stopReason`. VS Code leverages the same hook schema as Claude Code (and even reads `.claude/settings.json`), meaning the existing Claude adapter may be largely reusable. 

**Caveats:** This feature is in Preview. The current implementation creates a session-level block rather than a clean "resubmit a better prompt" loop. Additionally, tool property casing and matchers may differ from the standard Claude Code implementation. Configured in `.github/hooks/*.json`.
[Official Docs](https://code.visualstudio.com/docs/agent-customization/hooks)

## Recommended Next Adapter: Cursor

I recommend building the **Cursor** adapter next. 

**Justification:**
1. **Clean UX:** The `{ "continue": false, "user_message": "..." }` hook contract is explicitly designed for the "pause, give feedback, let the user fix it" loop. This avoids the session-level block limitations currently present in VS Code.
2. **Metadata Parity:** Cursor's payload includes `attachments`, meaning we have the metadata required to run Prompt Preflight's missing-file checks (bringing it up to feature parity with the Claude Code adapter).
3. **Ecosystem & Momentum:** Cursor's user base is vast and rapidly growing, meaning an integration here has high impact.
4. **Feasibility:** Because Prompt Preflight's `analyze_prompt` logic is entirely decoupled, building the adapter simply involves a script that reads the JSON payload from `stdin`, executes the analyzer, and prints the `{continue: false, user_message}` JSON format when `decision == "block" or "nudge"`.
