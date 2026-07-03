# Prompt Preflight for Kiro

This guide shows how to install Prompt Preflight as a Kiro IDE `UserPromptSubmit` hook.

Prompt Preflight runs locally before Kiro spends a model turn. When the prompt is vague and consequential, the hook blocks the submission and returns a clearer prompt template plus targeted questions.

## Requirements

- Kiro IDE with agent hooks support.
- Python 3.10 or later.
- A downloaded or cloned `prompt-preflight` folder.

Check the basics:

```bash
python3 --version
```

## Install in one workspace

From the `prompt-preflight` repository root:

```bash
python3 scripts/install_prompt_preflight.py \
  --target kiro \
  --kiro-workspace /path/to/your/project
```

This writes:

```text
/path/to/your/project/.kiro/hooks/prompt-preflight.json
```

The generated hook points back to this Prompt Preflight checkout:

```text
scripts/prompt_preflight_kiro_hook.py
```

## Install for all Kiro workspaces

Use user scope:

```bash
python3 scripts/install_prompt_preflight.py \
  --target kiro \
  --kiro-scope user
```

This writes:

```text
~/.kiro/hooks/prompt-preflight.json
```

## Windows support

The generated hook command is automatically formatted for your current operating system and correctly quotes paths with spaces on Windows, macOS, and Linux.

By default, the installer uses `python3` for the hook command on macOS/Linux and `python` on Windows (since Windows typically exposes `python` or the `py` launcher). If your environment differs, you can override this by passing `--kiro-python-bin`:

```cmd
python scripts/install_prompt_preflight.py \
  --target kiro \
  --kiro-python-bin py \
  --kiro-workspace C:\path\to\your\project
```

## Preview without writing files

```bash
python3 scripts/install_prompt_preflight.py \
  --target kiro \
  --kiro-workspace /path/to/your/project \
  --dry-run
```

## Kiro IDE test

1. Restart Kiro IDE, or reload hooks from the Agent Hooks panel.
2. Confirm the `prompt-preflight` hook is enabled.
3. Submit:

```text
Create a car image
```

Expected result: Kiro blocks the prompt and shows Prompt Preflight feedback with:

- The original prompt.
- A better fill-in-the-blanks prompt.
- Up to three targeted questions.

Try a detailed prompt:

```text
Create a photorealistic image of a red 1967 Ford Mustang on a wet Tokyo street at night, low camera angle, cinematic lighting, 16:9.
```

Expected result: Prompt Preflight allows it to proceed.

## Direct hook smoke test

Run the hook without opening Kiro:

```bash
python3 scripts/prompt_preflight_kiro_hook.py <<'EOF'
{"hook_event_name":"userPromptSubmit","cwd":".","prompt":"Create a car image"}
EOF
```

A vague prompt exits with status `2` and writes feedback to stderr. A clear prompt exits `0` and prints nothing.

To inspect the feedback in a shell:

```bash
python3 scripts/prompt_preflight_kiro_hook.py 2>&1 <<'EOF'
{"hook_event_name":"userPromptSubmit","cwd":".","prompt":"Create a car image"}
EOF
```

## Configuration

Create `.prompt-preflight.json` in the project where Kiro is running:

```json
{
  "enabled": true,
  "mode": "block",
  "threshold": 45,
  "max_questions": 3,
  "telemetry": {
    "enabled": false,
    "path": ".prompt-preflight-telemetry.jsonl"
  }
}
```

- `block`: stop vague prompts before model work.
- `nudge`: allow the prompt and add clarification guidance to Kiro context.
- `threshold`: raise it to interrupt less often.
- `max_questions`: limit clarification questions from 1 to 5.
- `telemetry`: optional local-only count reporting; disabled by default.
- `enabled`: disable Prompt Preflight for one project.

Bypass one request:

```text
Create a car image [preflight:skip]
```

## View local telemetry

If telemetry is enabled, use Kiro normally. Prompt Preflight writes prompt-free count events to the configured local file, usually:

```text
.prompt-preflight-telemetry.jsonl
```

View the report from the project directory (or any parent directory that contains `.prompt-preflight.json`):

```bash
python3 scripts/prompt_preflight.py --telemetry-report
```

When no path is passed, the command loads `.prompt-preflight.json` and uses the configured `telemetry.path`. To point at a different project directory:

```bash
python3 scripts/prompt_preflight.py --cwd /path/to/project --telemetry-report
```

View JSON:

```bash
python3 scripts/prompt_preflight.py --telemetry-report --json
```

You can still pass an explicit telemetry file path:

```bash
python3 scripts/prompt_preflight.py \
  --telemetry-report path/to/telemetry.jsonl
```

The report shows prompts checked, blocked prompts, nudges, bypasses, follow-up prompts accepted, estimated avoided retry turns, and average clarification score. It does not show original prompts.

## Important files

- `scripts/install_kiro_hook.py`: Kiro-specific installer.
- `scripts/prompt_preflight_kiro_hook.py`: executable Kiro hook adapter.
- `src/prompt_preflight/kiro_hook.py`: Kiro hook output logic.
- `src/prompt_preflight/analyzer.py`: shared prompt clarity analyzer.

## Kiro CLI note

Kiro IDE hooks support blocking `UserPromptSubmit` command hooks. Kiro CLI custom-agent hooks also support `userPromptSubmit`, but the CLI docs currently describe this trigger as adding stdout to context rather than blocking prompt submission. For that reason, the installer above targets Kiro IDE hook files.

If you want a CLI-style workflow, use Prompt Preflight directly before calling Kiro:

```bash
python3 scripts/prompt_preflight.py "Create a car image"
```

## Uninstall

Workspace hook:

```bash
rm /path/to/your/project/.kiro/hooks/prompt-preflight.json
```

User hook:

```bash
rm "$HOME/.kiro/hooks/prompt-preflight.json"
```

Then reload hooks or restart Kiro IDE.

## References

- Kiro IDE hooks: https://kiro.dev/docs/hooks/
- Kiro CLI hooks: https://kiro.dev/docs/cli/hooks/
- Kiro custom agent configuration: https://kiro.dev/docs/cli/custom-agents/configuration-reference/
