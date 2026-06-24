# Prompt Preflight

> Catch underspecified requests before they become expensive model turns.

Prompt Preflight is a local Codex plugin, Claude Code plugin, and standalone CLI that checks whether a prompt is specific enough to act on. When ambiguity and the cost of being wrong are both high, it pauses the request and gives the user:

1. Their original prompt.
2. A domain-aware example of a stronger prompt.
3. Up to three questions that fill the most important gaps.

The check uses deterministic Python rules. It makes no network requests and calls no model.

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

Actual savings depend on prompt quality, model behavior, context size, and task complexity. Prompt Preflight does not currently claim a fixed savings percentage; measured token telemetry is future work.

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
  "Create a [photorealistic/illustrated/3D] image of a car with
   [key colors, materials, and distinctive details], in [setting/background],
   viewed from [camera angle/composition], with [lighting/mood],
   in [aspect ratio]."

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

- Runs before a Codex or Claude Code model turn through `UserPromptSubmit`.
- Uses no model, API key, network access, or external service.
- Routes prompts by domain before selecting feedback.
- Includes software and image-generation feedback profiles.
- Shows a tailored rewrite instead of only saying “be more specific.”
- Asks at most three high-value questions.
- Lets clear prompts and conversational follow-ups pass through.
- Supports a one-time `[preflight:skip]` bypass.
- Supports configurable block and nudge modes.
- Fails open if hook input is malformed.
- Provides structured JSON for evaluation and debugging.

## How the decision works

Prompt Preflight estimates three things:

1. **Intent:** What kind of work is being requested?
2. **Ambiguity:** Which domain-specific details are missing?
3. **Impact:** How expensive would a wrong interpretation be?

It interrupts only when the prompt is actionable and both ambiguity and impact cross the configured threshold. This prevents the plugin from interrogating users about simple questions, confirmations, or already-specific work.

Current domain profiles include:

- Software builds and changes
- Bug fixes
- Optimization
- Deployment and migration
- Image generation

Unsupported domains use a conservative fallback rather than receiving software-specific questions.

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

Structured output includes the detected `intent`, ambiguity score, impact score, reasons, questions, and suggested prompt.

## Benchmark vague-prompt detection

Prompt Preflight includes a fixed benchmark of 100 intentionally vague prompts across software work, bug fixes, deployment, migration, optimization, and image generation.

Run it locally:

```bash
python3 scripts/benchmark_vague_prompts.py
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

With the current default threshold, the benchmark catches:

```text
98 / 100 vague prompts
10 / 10 image-generation prompts
```

The two current misses are:

```text
Fix the flaky tests
Generate more tests
```

These misses are useful calibration cases. They show why the benchmark is not just a vanity metric: it gives maintainers concrete prompts to discuss, tune, and convert into regression tests when the desired behavior is clear.

This is a regression guard, not a token-savings guarantee. The benchmark consumes zero model tokens and helps catch changes that would let vague, costly prompts slip through.

The repository also includes a GitHub Actions workflow at `.github/workflows/benchmark.yml`. It runs the unit tests and the 100-prompt benchmark on pushes, pull requests, and manual workflow dispatch.

## Install

Use the unified installer when you want the simplest path:

```bash
python3 scripts/install_prompt_preflight.py
```

By default it sets up both supported hosts:

- Codex: copies the plugin to `~/plugins/prompt-preflight`, updates `~/.agents/plugins/marketplace.json`, and attempts `codex plugin add prompt-preflight@personal`.
- Claude Code: copies the plugin to `~/.claude/skills/prompt-preflight`, which Claude loads as `prompt-preflight@skills-dir`.

Preview the setup without writing files:

```bash
python3 scripts/install_prompt_preflight.py --dry-run
```

Install only one host:

```bash
python3 scripts/install_prompt_preflight.py --target codex
python3 scripts/install_prompt_preflight.py --target claude
```

Refresh existing installed copies:

```bash
python3 scripts/install_prompt_preflight.py --clean
```

The host-specific installers are still available when you need advanced options.

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

## Configuration

Create `.prompt-preflight.json` in the project where Codex or Claude Code runs:

```json
{
  "enabled": true,
  "mode": "block",
  "threshold": 45,
  "max_questions": 3
}
```

- `block`: stop the vague submission before model work.
- `nudge`: allow the turn while instructing the host assistant to clarify first.
- `threshold`: raise it to interrupt less often.
- `max_questions`: limit clarification questions from 1 to 5.
- `enabled`: disable Prompt Preflight for a project.

Bypass one request without changing configuration:

```text
Create a car image [preflight:skip]
```

## Privacy and security

Prompt text is analyzed locally. Prompt Preflight does not:

- Send prompt text to a server
- Store prompt history
- Require an API key
- Invoke a cheaper model to decide whether an expensive model should run
- Modify files during prompt analysis

As with any local plugin, review `.codex-plugin/plugin.json`, `hooks/hooks.json`, and `scripts/prompt_preflight_hook.py` before trusting the hook.

For Claude Code, review `.claude-plugin/plugin.json`, `hooks/claude-hooks.json`, and `scripts/prompt_preflight_claude_hook.py`.

## Limitations

- Rule-based intent routing cannot understand every phrasing.
- Domain coverage is intentionally narrow and high-precision today.
- Clarification can add friction when the user prefers the model to make assumptions.
- Token savings are task-dependent and are not yet measured automatically.
- Prompts may use `[preflight:skip]` when interruption is not worthwhile.

Incorrect classifications should become regression tests. Run a questionable prompt with `--json` and capture its detected intent, reasons, and questions.

## Development

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

The project currently has regression coverage for vague and detailed prompts, domain routing, bypass behavior, nudge mode, and malformed hook input.

## Roadmap

- Token and retry savings telemetry
- More domain profiles, including writing, research, data analysis, and presentations
- User-defined terminology and intent rules
- Per-domain thresholds
- More host adapters beyond Codex and Claude Code
- False-positive feedback capture and calibration reports


## License

MIT
