# Prompt Preflight in CI

Prompt Preflight can lint checked-in prompt libraries in CI before vague prompt
templates reach a team workflow.

The CI command is local and deterministic:

```bash
python3 scripts/lint_prompt_library.py --cwd .
```

By default it scans Markdown, XML, and TOML files under `docs/prompts/**` and
`prompts/**` that explicitly opt in with:

```md
<!-- prompt-preflight: check -->
```

TOML:

```toml
# prompt-preflight: check
```

XML:

```xml
<!-- prompt-preflight: check -->
```

The command exits:

- `0` when every checked prompt is clear
- `2` when one or more prompt files need clarification

It does not print prompt text in the report.

## GitHub Actions example

```yaml
name: Prompt Preflight

on:
  pull_request:
  push:

permissions:
  contents: read

jobs:
  prompt-library:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Lint prompt library
        run: python3 scripts/lint_prompt_library.py --cwd .
```

## Folder-specific profiles

Teams can route different prompt-library folders to different profiles in
`.prompt-preflight.json`:

```json
{
  "profiles": {
    "docs/prompts/specs/**": "feature_spec",
    "docs/prompts/research/**": "research",
    "docs/prompts/data/**": "data_analysis",
    "docs/prompts/presentations/**": "presentation"
  }
}
```

The same profile mapping is used by:

- CLI `--prompt-file`
- CI prompt-library lint
- Codex hook payloads that provide `prompt_path`, `file_path`, `path`, or `file`
- Claude Code hook payloads that provide a prompt path
- Kiro hook payloads that provide a prompt path
- VS Code diagnostics, CodeLens checks, and workspace lint

Use `--all` only for strict repos where every Markdown/XML/TOML file is intended
to be a prompt:

```bash
python3 scripts/lint_prompt_library.py --cwd . --all
```

Use `--include` to scan a different prompt-library folder:

```bash
python3 scripts/lint_prompt_library.py --cwd . --include "team-prompts/**/*.md"
```

Use `--json` for machine-readable CI summaries:

```bash
python3 scripts/lint_prompt_library.py --cwd . --json
```
