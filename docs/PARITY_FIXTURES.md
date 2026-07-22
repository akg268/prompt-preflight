# Cross-host parity fixtures

These fixtures prove that Codex, Claude Code, Kiro, the CLI, and the VS Code
analyzer client all agree on the same normalized decision core for a shared set
of prompts — even though each host formats its raw output differently.

## What is compared

Each host run is reduced to:

```json
{
  "decision": "block",
  "should_clarify": true,
  "intent": "image_generation",
  "checks": ["context", "output_contract", "risk", "template_contract"],
  "question_count": 3
}
```

- `decision` / `should_clarify` / `intent` / `checks` / `question_count` come from
  the shared analyzer.
- Hook hosts (Codex, Claude, Kiro) contribute their native allow/block/nudge
  signal; that signal must match the analyzer `decision`.
- VS Code is exercised the same way the extension does: `python3
  scripts/prompt_preflight.py --json`.

## Files

| Path | Role |
|------|------|
| `tests/fixtures/parity/prompts.jsonl` | Shared prompts (`id`, `label`, `prompt` or `prompt_parts`) |
| `tests/fixtures/parity/expected/<id>.json` | Expected normalized core per prompt |
| `tests/test_parity_fixtures.py` | Runs every prompt through every host |

Cases covered: **vague**, **clear**, **privacy-risk**, **structured-template**.

## Run the parity suite

```bash
python3 -m unittest discover -s tests -p 'test_parity_fixtures.py' -v
```

## Regenerate snapshots

When analyzer wording or scoring intentionally changes and the normalized core
should change with it, regenerate the expected files and review the diff:

```bash
python3 scripts/update_parity_fixtures.py
```

Or:

```bash
UPDATE_PARITY_FIXTURES=1 python3 -m unittest discover -s tests -p 'test_parity_fixtures.py' -v
```

Do **not** hand-edit expected JSON to force a green build. Re-run the update
script so the snapshot reflects live host/analyzer output, then commit the
reviewable diff alongside the analyzer change.
