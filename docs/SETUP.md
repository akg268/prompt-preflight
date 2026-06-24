# Prompt Preflight setup guide for Codex

This guide is for people installing Prompt Preflight into their own Codex environment. Prompt Preflight runs locally, makes no network or model calls, and uses a `UserPromptSubmit` hook to check a prompt before Codex begins model work.

For Claude Code, use [Prompt Preflight for Claude Code](CLAUDE.md).

## Requirements

- Codex CLI or the Codex app with plugins and hooks support.
- Python 3.10 or later.
- A downloaded or cloned `prompt-preflight` folder containing `.codex-plugin/plugin.json`.

Check the prerequisites:

```bash
codex --version
codex features list
python3 --version
```

`codex features list` should show `plugins` and `hooks` enabled. On Windows, use `python --version` if `python3` is unavailable.

## Quick smoke test

Before installing anything, open a terminal in the downloaded `prompt-preflight` folder and run:

```bash
python3 scripts/prompt_preflight.py "Create a car image"
```

Expected result: Prompt Preflight pauses the request, shows an improved image prompt, and asks about the car, visual style, composition, lighting, and aspect ratio. Exit code `2` means clarification is recommended; it is not a crash.

Test a detailed prompt:

```bash
python3 scripts/prompt_preflight.py "Create a photorealistic image of a red 1967 Ford Mustang on a wet Tokyo street at night, low camera angle, cinematic lighting, 16:9."
```

Expected result: `Clear to send` with exit code `0`.

## Run the benchmark

The repo includes a deterministic benchmark with 100 intentionally vague prompts. It checks how often Prompt Preflight pauses prompts that are likely to cause expensive retry loops.

Run:

```bash
python3 scripts/benchmark_vague_prompts.py
```

Save a full JSON report:

```bash
python3 scripts/benchmark_vague_prompts.py \
  --min-block-rate 0.90 \
  --json-output benchmark-results.json
```

The benchmark uses no model calls, API keys, or network requests. It is also wired into the repository's GitHub Actions workflow so pull requests can catch regressions automatically.

## Install into a personal Codex marketplace

Codex discovers personal plugins through `~/.agents/plugins/marketplace.json`. The plugin source for this setup lives at `~/plugins/prompt-preflight`.

### Recommended install

From the downloaded `prompt-preflight` folder, run:

```bash
python3 scripts/install_prompt_preflight.py --target codex
```

On Windows, use `python` if `python3` is unavailable:

```powershell
python scripts\install_prompt_preflight.py --target codex
```

The installer does the manual setup for you:

1. Validates that the current folder contains the Prompt Preflight plugin.
2. Copies the plugin to `~/plugins/prompt-preflight`.
3. Creates or updates `~/.agents/plugins/marketplace.json`.
4. Preserves unrelated marketplace entries.
5. Attempts to run `codex plugin remove prompt-preflight@<marketplace>` if needed.
6. Attempts to run `codex plugin add prompt-preflight@<marketplace>`.

If the Codex CLI is not on your shell `PATH`, the installer does not treat that as fatal. It completes the file and marketplace setup, prints the manual `codex plugin add ...` command, and prints a Codex app link you can open instead.

Preview the actions without writing files:

```bash
python3 scripts/install_prompt_preflight.py --target codex --dry-run
```

Copy files and update the marketplace, but skip the Codex CLI install step:

```bash
python3 scripts/install_prompt_preflight.py --target codex --skip-codex-add
```

Fail instead of warning when the Codex CLI is unavailable:

```bash
python3 scripts/install_prompt_preflight.py --target codex --require-codex-cli
```

If you want a fresh file copy, use:

```bash
python3 scripts/install_prompt_preflight.py --target codex --clean
```

`--clean` only removes the destination folder when it already looks like a Prompt Preflight install.

The Codex-specific installer remains available for advanced use:

```bash
python3 scripts/install_codex_plugin.py --help
```

Confirm installation:

```bash
codex plugin list
```

Expected result: `prompt-preflight@personal` is listed as installed and enabled. If your existing personal marketplace has a different top-level `name`, the installer uses that name instead of `personal`.

### Manual fallback

Use these steps if you do not want the installer to write to your personal plugin folder or marketplace file.

#### 1. Copy the plugin

On macOS or Linux:

```bash
mkdir -p "$HOME/plugins/prompt-preflight"
cp -R /path/to/prompt-preflight/. "$HOME/plugins/prompt-preflight/"
```

On Windows PowerShell:

```powershell
$Source = "C:\path\to\prompt-preflight"
$Destination = Join-Path $HOME "plugins\prompt-preflight"
New-Item -ItemType Directory -Force -Path $Destination | Out-Null
Copy-Item "$Source\*" $Destination -Recurse -Force
Copy-Item "$Source\.codex-plugin" $Destination -Recurse -Force
```

Confirm this file now exists:

```text
~/plugins/prompt-preflight/.codex-plugin/plugin.json
```

#### 2. Add the marketplace entry

The personal marketplace file is:

```text
~/.agents/plugins/marketplace.json
```

If the file does not exist, create it with:

```json
{
  "name": "personal",
  "interface": {
    "displayName": "Personal"
  },
  "plugins": [
    {
      "name": "prompt-preflight",
      "source": {
        "source": "local",
        "path": "./plugins/prompt-preflight"
      },
      "policy": {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL"
      },
      "category": "Productivity"
    }
  ]
}
```

If the file already exists, do not replace it. Preserve its existing `name`, `interface`, and plugin entries, then append the `prompt-preflight` object above to its `plugins` array. Use the marketplace's existing `name` in the installation command below.

Validate the JSON after editing:

```bash
python3 -m json.tool "$HOME/.agents/plugins/marketplace.json"
```

#### 3. Install the plugin

For a marketplace named `personal`:

```bash
codex plugin add prompt-preflight@personal
```

If your marketplace has a different `name`, replace `personal` with that value. The default personal marketplace is discovered automatically; do not run `codex plugin marketplace add` for `~/.agents/plugins/marketplace.json`.

Confirm installation:

```bash
codex plugin list
```

Expected result: `prompt-preflight@personal` is listed as installed and enabled.

## Trust the hook

1. Restart Codex after installation.
2. Open a new thread.
3. In the Codex CLI, run `/hooks`.
4. Review the Prompt Preflight `UserPromptSubmit` hook.
5. Trust the hook if its command points to `scripts/prompt_preflight_hook.py` inside the installed plugin.

Codex records trust against the hook definition. If a future update changes the hook, Codex may ask you to review it again.

## End-to-end tests in Codex

Submit each prompt in a new Codex thread or after the hook is trusted.

### Vague image request

```text
Create a car image
```

Expected: the prompt is paused before image generation. Feedback asks about visual details rather than files or a software stack.

### Detailed image request

```text
Create a photorealistic image of a red 1967 Ford Mustang on a wet Tokyo street at night, low camera angle, cinematic lighting, 16:9.
```

Expected: Prompt Preflight allows the request to proceed.

### Vague software request

```text
Make the dashboard better
```

Expected: feedback asks for the target component, observable outcome, constraints, and verification.

### One-time bypass

```text
Create a car image [preflight:skip]
```

Expected: the request proceeds without clarification.

## Configuration

Create `.prompt-preflight.json` in the project where Codex is running:

```json
{
  "enabled": true,
  "mode": "block",
  "threshold": 45,
  "max_questions": 3
}
```

- `mode: "block"` stops vague prompts before model work.
- `mode: "nudge"` allows the turn but instructs Codex to clarify first.
- A higher `threshold` interrupts less often.
- Set `enabled` to `false` to disable checks for that project.

To bypass one prompt without changing configuration, add `[preflight:skip]`.

## Updating

From the new release folder, run:

```bash
python3 scripts/install_prompt_preflight.py --target codex --clean
```

The installer refreshes `~/plugins/prompt-preflight`, preserves unrelated marketplace entries, removes the existing Prompt Preflight plugin registration if present, and adds it again.

Then restart Codex and open a new thread. Review the hook again in `/hooks` if Codex reports that its definition changed.

Manual update fallback:

```bash
cp -R /path/to/new/prompt-preflight/. "$HOME/plugins/prompt-preflight/"
codex plugin remove prompt-preflight@personal
codex plugin add prompt-preflight@personal
```

Use your marketplace's actual name if it is not `personal`.

## Uninstalling

```bash
codex plugin remove prompt-preflight@personal
```

After confirming removal, you may delete `~/plugins/prompt-preflight` and remove its entry from `~/.agents/plugins/marketplace.json`. Preserve every unrelated marketplace entry.

## Troubleshooting

### The prompt is not checked

1. Run `codex plugin list` and confirm Prompt Preflight is installed and enabled.
2. Run `codex features list` and confirm `plugins` and `hooks` are enabled.
3. Open `/hooks` and confirm the hook is trusted.
4. Restart Codex and test in a new thread.
5. Run the direct smoke test to confirm Python can execute the plugin.

### The installer says the Codex CLI is not on PATH

This usually means you are using the Codex desktop app but the `codex` command is not available in your terminal shell. The installer has still copied the plugin and updated the personal marketplace.

Use one of these finish paths:

1. Open the Codex app link printed by the installer.
2. Add the Codex CLI to your shell `PATH`, then run the printed `codex plugin add prompt-preflight@<marketplace>` command.
3. Re-run the installer with `--skip-codex-add`, restart Codex, and install Prompt Preflight from the app plugin UI if it appears there.

### The hook reports a Python error

Confirm Python 3.10 or later is available as `python3` on macOS/Linux or `python` on Windows. The hook configuration contains a Windows-specific command override.

### Feedback is from the wrong domain

Run the prompt through structured output:

```bash
python3 scripts/prompt_preflight.py --json "your prompt here"
```

Check the returned `intent`, `reasons`, and `questions`. Include that output when reporting a false positive or incorrect domain classification.

### Too many prompts are interrupted

Increase `threshold` gradually, for example from `45` to `55`. Prefer tuning the threshold over disabling the plugin globally.

## Security and privacy

Prompt Preflight analyzes prompt text locally with deterministic Python rules. It does not make network calls or invoke another model. Review `.codex-plugin/plugin.json`, `hooks/hooks.json`, and `scripts/prompt_preflight_hook.py` before trusting the hook, as you should for any local plugin.

For Codex's plugin and hook behavior, see the official [plugin documentation](https://developers.openai.com/codex/plugins/) and [hooks documentation](https://developers.openai.com/codex/hooks/).
