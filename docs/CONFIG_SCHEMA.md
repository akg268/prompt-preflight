# Config JSON Schema

Prompt Preflight ships a JSON Schema for project policy files:

- Schema: [`schemas/prompt-preflight.schema.json`](../schemas/prompt-preflight.schema.json)
- Example: [`.prompt-preflight.example.json`](../.prompt-preflight.example.json)

## Autocomplete and validation

The VS Code extension contributes `jsonValidation` for:

- `.prompt-preflight.json`
- `.prompt-preflight.example.json`

In a checkout of this monorepo (or when the schema is on the `json.schemas` path), editors that support Draft 2020-12 will offer property completion and flag invalid enum values (for example a bad `checks.*` policy).

## Profiles (forward-compatible)

The schema accepts an optional top-level `profiles` array for path/intent overlays from the Shared Contract. Entries may include `match`, `intent`, `mode`, `checks`, and `max_questions`. Prefer including `match`. Absence of `profiles` remains valid so the current example file validates unchanged.

Runtime loading of `profiles` in `config.py` is not required for schema validation.
