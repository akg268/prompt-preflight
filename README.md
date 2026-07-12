# Prompt Preflight

> Catch vague prompts before coding agents and AI tools spend model turns.

Prompt Preflight is a local prompt-quality layer for AI workflows. It can be used in two main ways:

1. **As a preflight plugin/hook for coding agents** — add it to tools such as Codex, Claude Code, or Kiro so prompts are checked before the agent starts reading files, calling tools, or spending a model turn.
2. **As a VS Code extension** — install it from the Visual Studio Marketplace to check, lint, compose, and improve prompts directly inside Markdown/XML/TOML prompt files before pasting or sending them to any AI tool.

Both paths use the same deterministic Python analyzer. Prompt Preflight makes no model calls, uses no API key, and sends no prompt text to a network service.

Prompt Preflight checks whether a prompt is safe and specific enough to act on. It looks at prompt clarity, missing context, output expectations, high-risk operations, plan-first needs, and likely secrets before an AI agent spends a model turn. When ambiguity or risk is high, it pauses the request and gives the user:

1. Their original prompt.
2. A domain-aware example of a stronger prompt.
3. Up to three questions that fill the most important gaps.

## Where Prompt Preflight fits

Use Prompt Preflight when prompts are about to enter an expensive or state-changing AI workflow:

| Surface | How it helps |
| --- | --- |
| Coding-agent plugins/hooks | Blocks or nudges vague prompts before Codex, Claude Code, or Kiro start acting on a repo. |
| VS Code extension | Lets users check prompt files, insert better prompt templates, lint team prompt libraries, and view local telemetry. |
| CLI and scripts | Provides the same analyzer for local testing, automation, benchmarks, and custom integrations. |

The same prompt rules, vague-prompt library, structured templates, and telemetry format are shared across all integrations.

## VS Code Marketplace beta

Prompt Preflight for VS Code is available as a Marketplace beta:

[Install Prompt Preflight for VS Code](https://marketplace.visualstudio.com/items?itemName=arunkumar-ganesan.prompt-preflight-vscode)

Or install from the command line:

```bash
code --install-extension arunkumar-ganesan.prompt-preflight-vscode
```

The VS Code extension bundles the Python analyzer, so Marketplace users do not need to clone this repo or set `promptPreflight.repoPath`.

## Prompt examples and templates

When Prompt Preflight catches a vague prompt, it links to vague prompt examples and templates. The [examples page](docs/EXAMPLES.md) includes common vague prompts for bug fixes, new features, refactors, UI work, performance, deployment, tests, documentation, security, analytics, image generation, writing, research, data analysis, and presentations.

Prompt Preflight also includes [structured prompt templates](docs/TEMPLATES.md) in Markdown, XML, and TOML. These prompt contracts define mandatory fields such as task, context, output format, constraints, and success criteria, plus domain-specific fields for image generation, writing, research, data analysis, presentations, and spec-driven development.

The spec-driven development pack includes feature specs, requirements specs, technical design specs, implementation plans, agent execution prompts, and spec review checklists. It is designed for teams that want Codex, Claude Code, Kiro, or another coding agent to work from a complete spec instead of a vague one-line request.

The canonical vague-prompt library lives in [`src/prompt_preflight/data/vague_prompts.txt`](src/prompt_preflight/data/vague_prompts.txt). Codex, Claude Code, Kiro, the CLI, and the benchmark all use the same Python package, so new vague-prompt examples should be added there instead of creating tool-specific lists.

The structured template catalog lives in [`src/prompt_preflight/data/prompt_templates.json`](src/prompt_preflight/data/prompt_templates.json), so all supported tools validate the same required fields.

*(For teams managing shared prompt templates in VS Code, see the [Team Prompt Libraries](docs/TEAM_PROMPT_LIBRARIES.md) guide).*
*(For teams using a spec-first approach to bound agents, see the [Team Spec-First Workflow](docs/TEAM_SPEC_FIRST_WORKFLOW.md) guide).*

## Help the project grow

If Prompt Preflight saves you even one failed agent turn, please consider starring the repo. Stars make it easier for other Codex, Claude Code, and Kiro users to discover the project, and they help signal which integrations are worth building next.

## Demo

Prompt Preflight catches a vague prompt inside the VS Code extension before model work begins:

![Prompt Preflight VS Code extension demo](vscode-extension/media/demo.gif)

The demo shows the core loop:

```text
User submits a vague request
  → Prompt Preflight runs locally
  → the coding agent or AI workflow is blocked/nudged before spending a model turn
  → the user receives a stronger prompt template and targeted questions
```

Run the same loop yourself with no network or model calls:

```bash
python3 scripts/demo.py
```

See [docs/LAUNCH.md](docs/LAUNCH.md) for copy-paste launch text and the
GIF/video recording checklist.

## Why this exists

A vague prompt often creates an expensive loop:

```text
Vague request
  → model reads project context
  → model produces the wrong interpretation
  → user corrects it
  → model reads the expanded conversation
  → model does the work again
```

The wasted cost is not limited to the first answer. The retry also carries the earlier prompt, output, corrections, and additional context.

Prompt Preflight moves clarification before that loop:

```text
Vague request
  → local preflight check
  → targeted clarification
  → one stronger request
  → useful model work
```

It does not reduce the price per token. It reduces avoidable model input, unwanted output, repeated tool work, and correction turns.

## Where token savings come from

Without preflight, the approximate cost of a failed attempt and retry is:

```text
failed input + failed output + correction context + replacement input + replacement output
```

With preflight, the local check consumes zero model tokens. The intended path becomes:

```text
clarified input + useful output
```

The potential tokens avoided are therefore approximately:

```text
failed input + failed output + correction context + duplicated work
```

Actual savings depend on prompt quality, model behavior, context size, and task complexity. Prompt Preflight does not claim a fixed savings percentage. Optional local telemetry can estimate avoided retry turns, but it does not measure exact token savings.

The largest benefit is expected on tasks where a wrong interpretation is costly, such as repository-wide changes, migrations, deployments, architecture work, or iterative image generation.

## Example: image generation

User prompt:

```text
Create a car image
```

Prompt Preflight responds before image generation begins:

```text
Your prompt:
  "Create a car image"

Try asking:
  "Task: Create a [photorealistic/illustrated/3D] image of a car with
   [key colors, materials, and distinctive details]. Context: [setting/background],
   [camera angle/composition], and [lighting/mood]. Output format: [aspect ratio,
   resolution, file type, or transparent background]."

Fill in the brackets by answering:
1. What should the car look like?
2. What visual style and mood do you want?
3. What setting, composition, lighting, and aspect ratio should it use?
```

This prevents an arbitrary first image followed by several rounds of visual corrections.

Prompt Preflight does not create the image itself; it makes the request specific before the AI tool runs. The current project visual is the VS Code extension logo:

![Prompt Preflight VS Code extension logo](vscode-extension/media/icon.png)

## Example: software work

User prompt:

```text
Make the dashboard better
```

Prompt Preflight suggests:

```text
Improve the dashboard in [specific page/component] so [observable outcome].
Keep [important behavior or design constraints] unchanged.
Verify with [tests or acceptance criteria].
```

The model receives a target, outcome, boundaries, and definition of done before it reads files or edits code.

## Key features

- Runs before a Codex, Claude Code, or Kiro model turn through `UserPromptSubmit`.
- Uses no model, API key, network access, or external service.
- Routes prompts by domain before selecting feedback.
- Includes software, image-generation, and content feedback profiles.
- Shows a tailored rewrite instead of only saying “be more specific.”
- Structures rewrites around task, context, output format, examples, and self-checks.
- Provides Markdown, XML, and TOML prompt-contract templates.
- Adds spec-driven development templates for feature specs, requirements specs, technical designs, implementation plans, agent execution prompts, and spec review checklists.
- In VS Code, `Prompt Preflight: New Prompt Template` asks users whether they want Markdown, TOML, or XML before opening a template.
- Validates structured prompts and pauses when required fields are empty or placeholder-only.
- Detects likely secrets and redacts them in user-facing feedback.
- Adds risk and plan-first checks for production deploys, migrations, destructive actions, and broad repo changes.
- Checks for missing attachments or referenced source files, using host attachment metadata when available to avoid re-asking for provided files (file contents are NEVER read).
- Asks at most three high-value questions.
- Lets clear prompts and conversational follow-ups pass through.
- Supports a one-time `[preflight:skip]` bypass for normal clarity/risk checks; likely-secret privacy blocks are not bypassed.
- Supports configurable block and nudge modes.
- Fails open if hook input is malformed.
- Provides structured JSON for evaluation and debugging.
- Includes a VS Code extension for checking prompt files, composing structured prompts, running workspace prompt lint, showing inline diagnostics, and viewing local telemetry graphs. The VSIX bundles the Python analyzer, so normal users do not need a repo checkout or `promptPreflight.repoPath`. See [Prompt Preflight for VS Code](vscode-extension/README.md).

## How the decision works

Prompt Preflight estimates three things:

1. **Intent:** What kind of work is being requested?
2. **Ambiguity:** Which domain-specific details are missing?
3. **Impact:** How expensive would a wrong interpretation be?

It interrupts only when the prompt is actionable and both ambiguity and impact cross the configured threshold. This prevents the plugin from interrogating users about simple questions, confirmations, or already-specific work.

The analyzer also emits check categories in JSON output:

- `clarity`: subjective or underspecified wording
- `context`: missing files, components, attachments, data, audience, source material, or scope
- `output_contract`: missing format, verification, examples, or success criteria
- `template_contract`: structured Markdown/XML/TOML prompt is missing required fields
- `risk`: production, migration, destructive, security-sensitive, or broad-scope work
- `plan_first`: work that should start with a plan and confirmation
- `privacy`: likely secrets or credentials in the prompt

Current domain profiles include:

- Software builds and changes
- Bug fixes
- Optimization
- Deployment and migration
- Image generation
- Writing
- Research
- Data analysis
- Presentations

Unsupported domains use a conservative fallback rather than receiving software-specific questions. Content domains such as writing, research, data analysis, and presentations receive audience, source, output, and quality-bar questions instead of file/component or platform-stack questions.

## Quick local test

Requires Python 3.10 or later.

```bash
python3 scripts/prompt_preflight.py "Create a car image"
```

A prompt requiring clarification exits with status `2`. A prompt ready to send exits with status `0`:

```bash
python3 scripts/prompt_preflight.py \
  "Create a photorealistic image of a red 1967 Ford Mustang on a wet Tokyo street at night, low camera angle, cinematic lighting, 16:9."
```

Inspect the full analysis:

```bash
python3 scripts/prompt_preflight.py --json "Rewrite the whole project"
```

Structured output includes the detected `intent`, ambiguity score, impact score, severity, check categories, reasons, questions, and suggested prompt. If a likely secret is detected, JSON output uses the redacted prompt text.

Print a structured prompt template:

```bash
python3 scripts/prompt_preflight.py --template image --template-format md
python3 scripts/prompt_preflight.py --template software --template-format xml
python3 scripts/prompt_preflight.py --template research --template-format toml
```

If a structured prompt is missing required fields, Prompt Preflight catches that too:

```bash
python3 scripts/prompt_preflight.py "$(cat <<'EOF'
# Task
Create a car image
# Visual Details
A red vintage Mustang on a rainy neon street.
# Output Format
16:9 PNG.
EOF
)"
```

Expected result: Prompt Preflight asks for the missing `style or mood` section before the model spends a turn.

## Benchmark vague-prompt detection

Prompt Preflight includes a fixed benchmark of 168 intentionally vague prompts across software work, bug fixes, deployment, migration, optimization, image generation, writing, research, data analysis, and presentations.

The benchmark reads from the shared vague-prompt library:

```text
src/prompt_preflight/data/vague_prompts.txt
```

Run it locally:

```bash
python3 scripts/benchmark_vague_prompts.py
```

Run it against another newline-based prompt library:

```bash
python3 scripts/benchmark_vague_prompts.py \
  --library-path path/to/vague_prompts.txt
```

Save complete results as JSON:

```bash
python3 scripts/benchmark_vague_prompts.py \
  --min-block-rate 0.90 \
  --json-output benchmark-results.json
```

The benchmark reports:

- Number of vague prompts blocked before model work
- Missed prompts that should be reviewed
- Average ambiguity, impact, and clarification scores
- Results grouped by detected intent

### What the first benchmark taught us

The first 100-prompt run exposed exactly the kind of regression risk this project is meant to catch. Early scoring was too lenient on short action prompts such as:

```text
Update the API
Fix checkout
Integrate analytics
Implement caching
```

Those prompts look actionable, but they omit the target behavior, constraints, and acceptance criteria. Acting on them can easily trigger a costly loop: the model guesses, the user corrects it, and the model repeats the work with more conversation history in context.

The benchmark also exposed a domain-routing issue. A prompt like:

```text
Render a house
```

should receive image-generation feedback, not software-project feedback. The analyzer now treats common visual render prompts as image-generation requests so the user gets questions about style, composition, lighting, and output format instead of files, components, or platform stack.

The expanded benchmark now covers content work too. Prompts like:

```text
Write a better intro
Research this topic
Analyze the data
Create a presentation
```

should receive content-specific feedback about audience, source material, research scope, metrics, output format, deck storyline, and slide constraints.

With the current default threshold, the benchmark catches:

```text
168 / 168 vague prompts
12 / 12 image-generation prompts
12 / 12 writing prompts
11 / 11 research prompts
12 / 12 data-analysis prompts
13 / 13 presentation prompts
```

Every benchmark prompt is currently caught. The two prompts that were the last to be tuned:

```text
Fix the flaky tests
Generate more tests
```

are now caught after recent analyzer tuning (output-format and context checks), while specific prompts that already name a concrete file or source still pass through.

These calibration cases show why the benchmark is not just a vanity metric: it gives maintainers concrete prompts to discuss, tune, and convert into regression tests when the desired behavior is clear.

This is a regression guard, not a token-savings guarantee. The benchmark consumes zero model tokens and helps catch changes that would let vague, costly prompts slip through.

The repository also includes a GitHub Actions workflow at `.github/workflows/benchmark.yml`. It runs the unit tests and the expanded vague-prompt benchmark on pushes, pull requests, and manual workflow dispatch.

## Install

Use the unified installer when you want the simplest path:

```bash
python3 scripts/install_prompt_preflight.py
```

By default it sets up Codex and Claude Code:

- Codex: copies the plugin to `~/plugins/prompt-preflight`, updates `~/.agents/plugins/marketplace.json`, and attempts `codex plugin add prompt-preflight@personal`.
- Claude Code: copies the plugin to `~/.claude/skills/prompt-preflight`, which Claude loads as `prompt-preflight@skills-dir`.

Kiro is installed explicitly because the hook can be workspace-level or user-level:

```bash
python3 scripts/install_prompt_preflight.py \
  --target kiro \
  --kiro-workspace /path/to/your/project
```

Preview the setup without writing files:

```bash
python3 scripts/install_prompt_preflight.py --dry-run
```

Install only one host:

```bash
python3 scripts/install_prompt_preflight.py --target codex
python3 scripts/install_prompt_preflight.py --target claude
python3 scripts/install_prompt_preflight.py --target kiro --kiro-scope user
```

Refresh existing installed copies:

```bash
python3 scripts/install_prompt_preflight.py --clean
```

The host-specific installers are still available when you need advanced options.

### Host compatibility matrix

For research on potential new integrations (Cursor, Windsurf, VS Code), see the [Host Integrations Report](docs/INTEGRATIONS.md).

| Host | Install command | Hook trigger | Block mode | Nudge mode | Setup guide |
| --- | --- | --- | --- | --- | --- |
| Codex | `python3 scripts/install_prompt_preflight.py --target codex` | `UserPromptSubmit` | Yes — blocks vague prompts before model work | Yes — set `mode: "nudge"` in `.prompt-preflight.json` | [Codex setup](docs/SETUP.md) |
| Claude Code | `python3 scripts/install_prompt_preflight.py --target claude` | `UserPromptSubmit` | Yes — returns a blocking hook decision | Yes — set `mode: "nudge"` in `.prompt-preflight.json` | [Claude Code setup](docs/CLAUDE.md) |
| Claude Code (Postflight) | `scripts/prompt_preflight_postflight_claude_hook.py` | `Stop` / `SubagentStop` | Yes — returns a `decision: block` asking the agent to fix | N/A — blocks or stays silent (no nudge path) | [Postflight note](docs/POSTFLIGHT.md) |
| Kiro IDE | `python3 scripts/install_prompt_preflight.py --target kiro --kiro-workspace /path/to/project` | `userPromptSubmit` | Yes — exits `2` with clarification feedback | Yes — set `mode: "nudge"` in `.prompt-preflight.json` | [Kiro setup](docs/KIRO.md) |
| Kiro CLI | Run `python3 scripts/prompt_preflight.py "<prompt>"` before invoking Kiro CLI, or wire the Kiro hook adapter into a custom-agent hook | `userPromptSubmit` custom-agent hook | No documented blocking path; CLI hooks add stdout to context | Yes — use nudge-mode hook output as context | [Kiro CLI custom-agent usage](docs/KIRO.md#kiro-cli-custom-agent-usage) |

## Install in Codex

Codex-only install:

```bash
python3 scripts/install_prompt_preflight.py --target codex
```

The installer copies the plugin to `~/plugins/prompt-preflight`, creates or updates the personal marketplace at `~/.agents/plugins/marketplace.json`, and attempts to run `codex plugin add prompt-preflight@personal`.

If the Codex CLI is not on your shell `PATH`, the installer still completes the file and marketplace setup, then prints the command and Codex app link needed to finish installation.

Advanced Codex-only installer:

```bash
python3 scripts/install_codex_plugin.py --help
```

See the [external setup guide](docs/SETUP.md) for:

- macOS, Linux, and Windows installation
- Personal marketplace configuration
- Installer options and manual fallback steps
- Hook review and trust
- End-to-end Codex tests
- Updating and uninstalling
- Troubleshooting

After installation, restart Codex, open a new thread, and review the hook with `/hooks`.

## Install in Claude Code

Prompt Preflight also ships as a Claude Code plugin using `.claude-plugin/plugin.json` and a Claude-specific hook config at `hooks/claude-hooks.json`.

Test it without installing:

```bash
claude --plugin-dir .
```

Then run `/hooks`, review the `UserPromptSubmit` hook, and submit:

```text
Create a car image
```

Install it as a personal Claude Code skills-directory plugin:

```bash
python3 scripts/install_prompt_preflight.py --target claude
```

The installer copies the plugin to:

```text
~/.claude/skills/prompt-preflight
```

Claude Code loads that folder as `prompt-preflight@skills-dir` on the next session. You can also run `/reload-plugins` inside an open Claude Code session.

Advanced Claude-only installer:

```bash
python3 scripts/install_claude_plugin.py --help
```

See the [Claude Code setup guide](docs/CLAUDE.md) for local testing, hook smoke tests, install options, configuration, and troubleshooting.

## Install in Kiro

Prompt Preflight supports Kiro IDE through a `UserPromptSubmit` command hook. Kiro blocks prompt submission when the hook exits with status `2`, so the Kiro adapter writes the clarification message to stderr and exits `2` for vague prompts.

Install into one workspace:

```bash
python3 scripts/install_prompt_preflight.py \
  --target kiro \
  --kiro-workspace /path/to/your/project
```

Install for all Kiro workspaces:

```bash
python3 scripts/install_prompt_preflight.py \
  --target kiro \
  --kiro-scope user
```

See the [Kiro setup guide](docs/KIRO.md) for IDE hook testing, user-level install, direct hook smoke tests, and the Kiro CLI note.

## Configuration

Create `.prompt-preflight.json` in the project where Codex, Claude Code, or Kiro runs:

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
    "path": ".prompt-preflight-telemetry.jsonl",
    "max_events": 1000,
    "max_bytes": 1048576,
    "retention_days": 30
    "timestamp_mode": "exact"
    "path": ".prompt-preflight-telemetry.jsonl"
  },
  "token_observability": {
    "enabled": true,
    "default_max_output_tokens": 1000,
    "estimated_retry_output_tokens": 800
  }
}
```

- `mode`: legacy global behavior (block or nudge). Backward compatible if `checks` is missing.
- `threshold`: legacy global numeric threshold.
- `checks`: per-check policy ("block", "nudge", "disable", "off"). Evaluated before `mode`.
- `severity_thresholds`: defines the severity ("low", "medium", "high") needed to trigger a "block" or "nudge" per check.
- `max_questions`: limit clarification questions from 1 to 5.
- `enabled`: disable Prompt Preflight for a project.
- `telemetry`: optional local-only counts; disabled by default. Under `telemetry`, you can configure `max_events` (integer limit), `max_bytes` (integer size limit), and `retention_days` (integer age limit) to automatically prune the file (oldest events first) so it stays bounded without manual cleanup. Note that `retention_days` requires timestamps; if you disable timestamps via a `timestamp_mode` of "none", age-based pruning will be skipped gracefully.
- `telemetry`: optional local-only counts; disabled by default. Under `telemetry`, `timestamp_mode` ("exact", "date", or "none") sets the precision of per-event timestamps. "exact" gives precise analysis but can reveal usage timing, "date" reduces granularity to the day, and "none" removes per-event timing. The default is "exact".
- `telemetry`: optional local-only counts; disabled by default.
- `token_observability`: optional local token estimates for reports; enabled by default when telemetry is recorded.

### Per-Check Safe Defaults

If a specific check is not explicitly set in `checks`, Prompt Preflight uses these safe defaults:

- `privacy`, `risk`, and `plan_first`: **block**
- `clarity`, `context`, `output_contract`, and `template_contract`: **nudge** (or the global `mode` if configured)

Bypass one request without changing configuration:

```text
Create a car image [preflight:skip]
```

## Postflight quality checks (experimental)

Preflight checks a prompt before a model turn. **Postflight** checks an agent
response *after* the turn and flags common failure modes deterministically:
wrong output format, missing tests, hollow file-change claims, violated negative
constraints, leftover `[TODO]` placeholders, and missing citations. It makes no
network or model calls and never reads file contents. See
[docs/POSTFLIGHT.md](docs/POSTFLIGHT.md) for the design note and limitations.

Run it on a response (exit `0` = clean, `2` = needs attention):

```
python3 scripts/prompt_postflight.py --prompt "Return the result as JSON" "the status is ok"
python3 scripts/prompt_postflight.py --json --prompt "Research X with citations" "$(cat answer.txt)"
python3 scripts/prompt_postflight.py --record-telemetry --prompt "Return JSON" "the answer is 42"
```

Configure it in `.prompt-preflight.json` under an optional `postflight` block.
Defaults are strict (every check blocks) so the exit code is a useful CI gate;
soften any check to `nudge` (surfaced but non-blocking) or `off`:

```json
{
  "postflight": {
    "enabled": true,
    "checks": {
      "output_format": "block",
      "tests_present": "block",
      "file_change_claim": "block",
      "constraint_adherence": "nudge",
      "placeholders": "block",
      "citations": "nudge",
      "privacy": "block"
    }
  }
}
```

| Host | Command | Trigger | Status |
| --- | --- | --- | --- |
| CLI | `python3 scripts/prompt_postflight.py "<response>"` | direct invocation | Supported |
| Claude Code | `scripts/prompt_preflight_postflight_claude_hook.py` | `Stop` | Prototype (verify hook contract) |
| Codex / Kiro | — | — | Not supported yet |

Postflight telemetry is available through the CLI and the Claude Code Stop-hook adapter. Codex and Kiro are still preflight-only until those hosts expose or confirm a post-response hook surface.

## Local telemetry

Prompt Preflight can record local, opt-in telemetry to help estimate avoided retry loops. It is disabled by default. If bounded via `max_events`, `max_bytes`, or `retention_days` in configuration, the file will automatically rotate by pruning older events at write time.

Enable it in `.prompt-preflight.json`:

```json
{
  "telemetry": {
    "enabled": true,
    "path": ".prompt-preflight-telemetry.jsonl"
  },
  "token_observability": {
    "enabled": true,
    "default_max_output_tokens": 1000,
    "estimated_retry_output_tokens": 800
  }
}
```

Users see telemetry only when they run a report command. The normal workflow is:

```text
1. Enable telemetry in .prompt-preflight.json.
2. Use Codex, Claude Code, Kiro, or the CLI normally.
3. Prompt Preflight appends prompt-free events to .prompt-preflight-telemetry.jsonl.
4. Run --telemetry-report to see the summary.
```

VS Code users can also open a local graph dashboard:

```text
Prompt Preflight: Open Telemetry Dashboard
```

The dashboard reads the same local JSONL telemetry file and renders cards plus bar charts for decisions, block reasons, hosts, daily activity, postflight checks, and token-risk buckets.

The telemetry file stores only aggregate fields:

- host, such as `codex`, `claude-code`, `kiro`, or `cli`
- decision, such as `blocked`, `nudged`, `allowed`, `bypassed`, or `followup_accepted`
- detected intent
- clarification score, ambiguity score, and impact score
- reason count and question count
- timestamp (precision is configurable via `timestamp_mode`)
- prompt and response character counts
- prompt and response token estimates
- estimated total request tokens
- token risk buckets (`low`, `medium`, `high`)
- estimated avoided retry token opportunity for blocked preflight prompts
- timestamp

It does not store prompt text, suggested rewrites, clarification questions, reason strings, file contents, or conversation history.

Token observability uses a local deterministic estimate (`~4 characters = 1 token`). It is useful for trend and risk reporting, but it is not provider billing truth and does not replace provider usage dashboards.

Generate a report from the project directory (or any parent directory that contains `.prompt-preflight.json`):

```bash
python3 scripts/prompt_preflight.py --telemetry-report
```

When no path is passed, the command loads `.prompt-preflight.json` and uses the configured `telemetry.path`. To point at a different project directory:

```bash
python3 scripts/prompt_preflight.py --cwd /path/to/project --telemetry-report
```

Generate JSON:

```bash
python3 scripts/prompt_preflight.py --telemetry-report --json
```

You can still pass an explicit telemetry file path:

```bash
python3 scripts/prompt_preflight.py \
  --telemetry-report path/to/telemetry.jsonl
```

Sample report:

```text
Prompt Preflight telemetry report
Path: .prompt-preflight-telemetry.jsonl

Prompts checked: 42
Blocked before model work: 18
Nudged: 3
Allowed: 16
Bypassed: 2
Follow-up prompts accepted: 3

Clarification opportunities: 21
Estimated avoided retry turns: 18
Average clarification score: 58.7/100

Postflight
Responses checked: 4
Responses needing attention: 1
  - output_format: 1

Token observability
Events with token estimates: 46
Visible prompt tokens estimated: 12840
Estimated request tokens reserved: 58840
Estimated response tokens observed: 2310
Estimated avoided retry token opportunity: 15840
Prompt token risk:
  - low: 44
  - medium: 2

Privacy: this file stores counts, decisions, hosts, intents, check categories, scores, and token estimates only.
It does not store prompt text, suggested rewrites, questions, or reason strings.
```

Record telemetry for a one-off CLI check:

```bash
python3 scripts/prompt_preflight.py \
  --record-telemetry \
  "Create a car image"
```

`Estimated avoided retry turns` is intentionally conservative: it counts prompts blocked before model work as one likely avoided failed attempt. It is an estimate, not a token-savings guarantee.

`Estimated avoided retry token opportunity` is also conservative. For each blocked preflight prompt, it adds the visible prompt token estimate plus the configured `estimated_retry_output_tokens`. It does not claim exact provider savings.

## Privacy and security

Prompt text is analyzed locally. Prompt Preflight does not:

- Send prompt text to a server
- Store prompt history
- Require an API key
- Invoke a cheaper model to decide whether an expensive model should run
- Modify files during prompt analysis

Prompt Preflight can detect common credential shapes such as API keys, tokens, password assignments, private key blocks, and cloud access keys. When that happens, it blocks before the model sees the prompt, redacts the credential in feedback, and asks the user to replace it with a placeholder. It can also check whether referenced source files exist, but it only checks file names/paths and does not read file contents.

**Important:** If Prompt Preflight catches a REAL credential, that credential was still entered into your local terminal or chat history. You must **rotate** the compromised credential immediately; do not just remove it from the prompt.

As with any local plugin, review `.codex-plugin/plugin.json`, `hooks/hooks.json`, and `scripts/prompt_preflight_hook.py` before trusting the hook.

For Claude Code, review `.claude-plugin/plugin.json`, `hooks/claude-hooks.json`, and `scripts/prompt_preflight_claude_hook.py`.

For Kiro, review the generated `.kiro/hooks/prompt-preflight.json` file and `scripts/prompt_preflight_kiro_hook.py`.

## Release readiness

Prompt Preflight is not ready for a broad public Marketplace release until the
release gates in [docs/RELEASE_READINESS.md](docs/RELEASE_READINESS.md) are
complete or explicitly deferred. The key gates are clean VSIX install, green
Setup Doctor, working telemetry dashboard, current docs/screenshots, privacy
verification, package audit, and repo hygiene.

Run the automated release gates from the repo root:

```bash
python3 scripts/release_check.py
```

That runs Python tests, template-doc validation, the vague-prompt benchmark, VS Code tests, VSIX packaging, VSIX package audit, bundled-analyzer smoke test, and a clean temporary VSIX install. It also prints the remaining manual gates that still need human UAT.

## Limitations

- Rule-based intent routing cannot understand every phrasing.
- Domain coverage is intentionally narrow and high-precision today.
- Clarification can add friction when the user prefers the model to make assumptions.
- Token savings are task-dependent; telemetry estimates avoided retry turns, not exact token savings.
- Prompts may use `[preflight:skip]` when interruption is not worthwhile, except for likely-secret privacy blocks.

Incorrect classifications should become regression tests. Run a questionable prompt with `--json` and capture its detected intent, reasons, and questions.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for test commands, benchmark usage, and how to add calibration regressions.

Run the test suite:

```bash
python3 -m unittest discover -s tests -v
```

Smoke-test the Codex hook contract:

```bash
python3 scripts/prompt_preflight_hook.py <<'EOF'
{"hook_event_name":"UserPromptSubmit","prompt":"Create a car image"}
EOF
```

Smoke-test the Claude Code hook contract:

```bash
python3 scripts/prompt_preflight_claude_hook.py <<'EOF'
{"hook_event_name":"UserPromptSubmit","cwd":".","prompt":"Create a car image"}
EOF
```

Smoke-test the Kiro hook contract:

```bash
python3 scripts/prompt_preflight_kiro_hook.py 2>&1 <<'EOF'
{"hook_event_name":"userPromptSubmit","cwd":".","prompt":"Create a car image"}
EOF
```

The project currently has regression coverage for vague and detailed prompts, domain routing, bypass behavior, nudge mode, and malformed hook input.

## Roadmap

- Richer telemetry reports and trend views
- More domain profiles beyond software, image generation, writing, research, data analysis, and presentations
- User-defined terminology and intent rules
- Per-domain thresholds
- More host adapters beyond Codex, Claude Code, and Kiro
- False-positive feedback capture and calibration reports

## License

MIT
