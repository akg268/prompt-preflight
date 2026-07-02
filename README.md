# Prompt Preflight

> Catch underspecified requests before they become expensive model turns.

Prompt Preflight is a local Codex plugin, Claude Code plugin, Kiro hook, and standalone CLI that checks whether a prompt is safe and specific enough to act on. It now looks at prompt clarity, missing context, output expectations, high-risk operations, plan-first needs, and likely secrets before an AI agent spends a model turn. When ambiguity or risk is high, it pauses the request and gives the user:

1. Their original prompt.
2. A domain-aware example of a stronger prompt.
3. Up to three questions that fill the most important gaps.

The check uses deterministic Python rules. It makes no network requests and calls no model.

## Prompt examples and templates

When Prompt Preflight catches a vague prompt, it links to vague prompt examples and templates. The [examples page](docs/EXAMPLES.md) includes common vague prompts for bug fixes, new features, refactors, UI work, performance, deployment, tests, documentation, security, analytics, image generation, writing, research, data analysis, and presentations.

The canonical vague-prompt library lives in [`src/prompt_preflight/data/vague_prompts.txt`](src/prompt_preflight/data/vague_prompts.txt). Codex, Claude Code, Kiro, the CLI, and the benchmark all use the same Python package, so new vague-prompt examples should be added there instead of creating tool-specific lists.

## Help the project grow

If Prompt Preflight saves you even one failed agent turn, please consider starring the repo. Stars make it easier for other Codex, Claude Code, and Kiro users to discover the project, and they help signal which integrations are worth building next.

## Demo

Prompt Preflight catches a vague Codex prompt before model work begins:

![Prompt Preflight demo](docs/assets/prompt-preflight-demo.gif)

The demo shows the core loop:

```text
User submits a vague request
  → Prompt Preflight runs locally
  → Codex gets blocked before spending a model turn
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

Example output after the prompt is clarified:

![Photorealistic red Mustang on a rainy neon-lit street](docs/assets/clarified-car-image.png)

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
- Detects likely secrets and redacts them in user-facing feedback.
- Adds risk and plan-first checks for production deploys, migrations, destructive actions, and broad repo changes.
- Checks for missing attachments or referenced source files, using host attachment metadata when available to avoid re-asking for provided files (file contents are NEVER read).
- Asks at most three high-value questions.
- Lets clear prompts and conversational follow-ups pass through.
- Supports a one-time `[preflight:skip]` bypass for normal clarity/risk checks; likely-secret privacy blocks are not bypassed.
- Supports configurable block and nudge modes.
- Fails open if hook input is malformed.
- Provides structured JSON for evaluation and debugging.

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

| Host | Install command | Hook trigger | Block mode | Nudge mode | Setup guide |
| --- | --- | --- | --- | --- | --- |
| Codex | `python3 scripts/install_prompt_preflight.py --target codex` | `UserPromptSubmit` | Yes — blocks vague prompts before model work | Yes — set `mode: "nudge"` in `.prompt-preflight.json` | [Codex setup](docs/SETUP.md) |
| Claude Code | `python3 scripts/install_prompt_preflight.py --target claude` | `UserPromptSubmit` | Yes — returns a blocking hook decision | Yes — set `mode: "nudge"` in `.prompt-preflight.json` | [Claude Code setup](docs/CLAUDE.md) |
| Kiro IDE | `python3 scripts/install_prompt_preflight.py --target kiro --kiro-workspace /path/to/project` | `userPromptSubmit` | Yes — exits `2` with clarification feedback | Yes — set `mode: "nudge"` in `.prompt-preflight.json` | [Kiro setup](docs/KIRO.md) |
| Kiro CLI | Run `python3 scripts/prompt_preflight.py "<prompt>"` before invoking Kiro CLI, or wire the same command into a custom-agent hook | `userPromptSubmit` custom-agent hook | No documented blocking path; CLI hooks add stdout to context | Yes — use direct preflight output or nudge-mode context | [Kiro CLI note](docs/KIRO.md#kiro-cli-note) |

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
  "telemetry": {
    "enabled": false,
    "path": ".prompt-preflight-telemetry.jsonl"
  }
}
```

- `block`: stop the vague submission before model work.
- `nudge`: allow the turn while instructing the host assistant to clarify first.
- `threshold`: raise it to interrupt less often.
- `max_questions`: limit clarification questions from 1 to 5.
- `enabled`: disable Prompt Preflight for a project.
- `telemetry`: optional local-only counts; disabled by default.

Bypass one request without changing configuration:

```text
Create a car image [preflight:skip]
```

## Local telemetry

Prompt Preflight can record local, opt-in telemetry to help estimate avoided retry loops. It is disabled by default.

Enable it in `.prompt-preflight.json`:

```json
{
  "telemetry": {
    "enabled": true,
    "path": ".prompt-preflight-telemetry.jsonl"
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

The telemetry file stores only aggregate fields:

- host, such as `codex`, `claude-code`, `kiro`, or `cli`
- decision, such as `blocked`, `nudged`, `allowed`, `bypassed`, or `followup_accepted`
- detected intent
- clarification score, ambiguity score, and impact score
- reason count and question count
- timestamp

It does not store prompt text, suggested rewrites, clarification questions, reason strings, file contents, or conversation history.

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

Privacy: this file stores counts, decisions, hosts, intents, and scores only.
It does not store prompt text, suggested rewrites, questions, or reason strings.
```

Record telemetry for a one-off CLI check:

```bash
python3 scripts/prompt_preflight.py \
  --record-telemetry \
  "Create a car image"
```

`Estimated avoided retry turns` is intentionally conservative: it counts prompts blocked before model work as one likely avoided failed attempt. It is an estimate, not a token-savings guarantee.

## Privacy and security

Prompt text is analyzed locally. Prompt Preflight does not:

- Send prompt text to a server
- Store prompt history
- Require an API key
- Invoke a cheaper model to decide whether an expensive model should run
- Modify files during prompt analysis

Prompt Preflight can detect common credential shapes such as API keys, tokens, password assignments, private key blocks, and cloud access keys. When that happens, it blocks before the model sees the prompt, redacts the credential in feedback, and asks the user to replace it with a placeholder. It can also check whether referenced source files exist, but it only checks file names/paths and does not read file contents.

As with any local plugin, review `.codex-plugin/plugin.json`, `hooks/hooks.json`, and `scripts/prompt_preflight_hook.py` before trusting the hook.

For Claude Code, review `.claude-plugin/plugin.json`, `hooks/claude-hooks.json`, and `scripts/prompt_preflight_claude_hook.py`.

For Kiro, review the generated `.kiro/hooks/prompt-preflight.json` file and `scripts/prompt_preflight_kiro_hook.py`.

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
