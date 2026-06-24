# Prompt Preflight for Claude Code

This guide shows how to test and install Prompt Preflight as a Claude Code plugin.

Prompt Preflight runs locally before Claude sees a submitted prompt. It uses a `UserPromptSubmit` hook to pause vague, consequential requests and ask for the missing details first. It makes no network calls and does not call a model.

## Requirements

- Claude Code installed and authenticated.
- Python 3.10 or later.
- A downloaded or cloned `prompt-preflight` folder containing `.claude-plugin/plugin.json`.

Check the basics:

```bash
claude --version
python3 --version
```

If you do not see plugin commands in Claude Code, update Claude Code first.

## Test without installing

From the `prompt-preflight` repository root:

```bash
claude --plugin-dir .
```

Inside Claude Code:

```text
/hooks
```

Review the Prompt Preflight `UserPromptSubmit` hook. It should point to:

```text
scripts/prompt_preflight_claude_hook.py
```

Then submit:

```text
Create a car image
```

Expected result: Claude Code blocks the prompt before model work begins and shows a better image prompt template plus targeted questions about subject details, style, composition, lighting, and aspect ratio.

Try a detailed prompt:

```text
Create a photorealistic image of a red 1967 Ford Mustang on a wet Tokyo street at night, low camera angle, cinematic lighting, 16:9.
```

Expected result: Prompt Preflight allows it to proceed.

## Install as a personal Claude Code plugin

From the `prompt-preflight` repository root:

```bash
python3 scripts/install_prompt_preflight.py --target claude
```

The installer copies the plugin to:

```text
~/.claude/skills/prompt-preflight
```

Claude Code automatically loads that folder as:

```text
prompt-preflight@skills-dir
```

Restart Claude Code or run:

```text
/reload-plugins
```

Confirm it loaded:

```text
/plugin list
```

Review the hook:

```text
/hooks
```

## Installer options

Preview the install without writing files:

```bash
python3 scripts/install_prompt_preflight.py --target claude --dry-run
```

Install to a custom skills directory:

```bash
python3 scripts/install_prompt_preflight.py \
  --target claude \
  --claude-skills-dir /path/to/.claude/skills
```

Replace the existing installed copy:

```bash
python3 scripts/install_prompt_preflight.py --target claude --clean
```

`--clean` only removes the destination folder if it already contains a Prompt Preflight Claude plugin manifest.

The Claude-specific installer remains available for advanced use:

```bash
python3 scripts/install_claude_plugin.py --help
```

## Manual install

If you prefer not to use the installer:

```bash
mkdir -p "$HOME/.claude/skills/prompt-preflight"
cp -R . "$HOME/.claude/skills/prompt-preflight/"
```

Then restart Claude Code or run `/reload-plugins`.

## Hook smoke test

You can test the Claude hook contract without opening Claude Code:

```bash
python3 scripts/prompt_preflight_claude_hook.py <<'EOF'
{"hook_event_name":"UserPromptSubmit","cwd":".","prompt":"Create a car image"}
EOF
```

Expected output is JSON like:

```json
{
  "decision": "block",
  "reason": "Prompt Preflight paused this request ...",
  "suppressOriginalPrompt": true
}
```

For a clear prompt, the hook prints nothing and exits `0`.

## Configuration

Create `.prompt-preflight.json` in the project where Claude Code is running:

```json
{
  "enabled": true,
  "mode": "block",
  "threshold": 45,
  "max_questions": 3
}
```

- `block`: stop the vague prompt before Claude sees it.
- `nudge`: let the turn continue while adding context that tells Claude to clarify first.
- `threshold`: raise it to interrupt less often.
- `max_questions`: limit clarification questions from 1 to 5.
- `enabled`: disable Prompt Preflight for one project.

Bypass one request:

```text
Create a car image [preflight:skip]
```

## Important files

- `.claude-plugin/plugin.json`: Claude plugin manifest.
- `hooks/claude-hooks.json`: Claude `UserPromptSubmit` hook registration.
- `scripts/prompt_preflight_claude_hook.py`: executable hook adapter.
- `src/prompt_preflight/claude_hook.py`: Claude hook output logic.
- `src/prompt_preflight/analyzer.py`: shared prompt clarity analyzer.

## Troubleshooting

If the plugin does not show up:

1. Start Claude Code from the `prompt-preflight` root when using `claude --plugin-dir .`.
2. Run `/reload-plugins`.
3. Check `/plugin list`.
4. Check `/hooks`.
5. Confirm Python is available as `python3`.

If `python3` is not available on your machine, edit `hooks/claude-hooks.json` and change the hook command to use your Python executable.

## Uninstall

For the personal skills-directory install:

```bash
rm -rf "$HOME/.claude/skills/prompt-preflight"
```

Then restart Claude Code or run `/reload-plugins`.
