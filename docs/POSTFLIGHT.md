# Postflight quality checks (design note)

## Preflight vs postflight

Preflight runs **before** a model turn. It inspects the *prompt* on
`UserPromptSubmit` and can block or nudge before any tokens are spent.

Postflight runs **after** an agent response. It inspects the *response* (and,
where available, the list of files that changed) and flags failure modes that
are only visible once the model has answered: the output ignored the requested
format, tests were requested but never written, the response claims edits that
never happened, an explicit "don't do X" constraint was violated, `[TODO]`-style
placeholders were left in, or a research answer shipped without citations.

Because postflight needs the *response*, it cannot use `UserPromptSubmit`. It
needs a host hook point that fires at the end of a turn.

## Host surfaces

| Host | Post-response hook | Data available | Can it ask the agent to fix? | Status |
| --- | --- | --- | --- | --- |
| CLI | n/a (invoked directly) | prompt + response passed as args/stdin; `--changed-files` optional | Exit code only (`0`/`2`) | **Supported** — the portable prototype, no host API needed |
| Claude Code | `Stop` / `SubagentStop` | transcript path (JSONL) → last assistant message; no authoritative changed-file list | Yes — a block decision can send the agent back to revise | **Supported (prototype)** — payload/output shape must be confirmed against current Claude Code hooks docs |
| Codex | none verified | — | — | Not supported yet; no documented post-response hook found in this repo |
| Kiro | none verified | — | — | Not supported yet; `userPromptSubmit` is pre-turn only |

The CLI is the guaranteed path: it needs no host cooperation and doubles as a CI
gate. The Claude Code `Stop` hook is the richest integration because it can hand
the response back to the agent for a fix.

Postflight telemetry is currently wired for the CLI and the Claude Code Stop
hook. Codex and Kiro remain preflight-only until those hosts expose or confirm a
post-response hook surface.

### A note on the Claude Code `Stop` contract

This repo only ships `UserPromptSubmit` adapters, so the exact `Stop` payload
fields (`transcript_path`, `stop_hook_active`) and the accepted output shape
(`decision: "block"` + `reason` to continue the agent) were taken from the
documented behavior and should be re-confirmed against current Claude Code hooks
documentation before relying on them. The adapter reads `stop_hook_active` to
avoid looping on its own block, and fails open (exit 0, no output) on any error.

## Check catalog

| Check | Fires when | Default severity |
| --- | --- | --- |
| `output_format` | prompt asked for json/table/bullets/numbered/yaml/csv and the response doesn't contain it | medium |
| `tests_present` | prompt asked for tests and the response has no test indicators | medium |
| `file_change_claim` | response claims edits; blocks if `changed_files == []`, informational if metadata is absent | medium / low |
| `constraint_adherence` | prompt said "avoid/without/don't use X" and X appears in the response (best-effort, literal) | medium |
| `placeholders` | response contains `[TODO]`, `FIXME`, `[YOUR_...]`, etc. | medium |
| `citations` | prompt asked for research/citations and the response has no citation markers | medium |
| `privacy` | a secret/credential shape appears in the response (reuses the preflight detectors; redacts) | high |

## Decision model

Each check emits at most one finding. A per-check **policy** (`block` /
`nudge` / `off`) decides whether a finding counts toward `needs_attention`:

- `block` (default for every check) → the finding sets `needs_attention` and the
  CLI exits `2` / the Stop hook asks for a fix.
- `nudge` → the finding is surfaced in output and JSON but does not block.
- `off` (alias `disable`) → the check is skipped entirely.

`needs_attention` ignores informational findings, so a change claim with no
metadata never blocks. Defaults are strict so the CLI exit code is a meaningful
gate; soften per check in `.prompt-preflight.json` under a `postflight` block.

## Local telemetry and token observability

Postflight can write the same prompt-free JSONL telemetry file used by
preflight. The event stores aggregate counts and local token estimates only; it
does not store the original prompt, response text, reason strings, or file
contents.

Record a one-off postflight telemetry event from the CLI:

```bash
python3 scripts/prompt_postflight.py \
  --record-telemetry \
  --prompt "Return the result as JSON" \
  "the status is ok"
```

If `.prompt-preflight.json` enables telemetry, the Claude Code Stop hook records
postflight events automatically:

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

View the combined preflight/postflight report:

```bash
python3 scripts/prompt_preflight.py --telemetry-report
```

Token observability uses a deterministic local estimate (`~4 characters = 1
token`). It is meant for trend reporting and risk signals, not exact provider
billing reconciliation.

## Limitations

- **Heuristic and high-precision by design.** The checks prefer to miss a subtle
  issue over emitting a false positive, so they will not catch every failure.
- **`constraint_adherence` and `output_format` are best-effort.** Constraint
  checking only handles literal "avoid/without/don't use `<token>`" phrasing and
  can be fooled when the response merely quotes the constraint. Format detection
  recognizes common shapes, not every possible one.
- **`file_change_claim` depends on host metadata.** Without an authoritative
  changed-file list (e.g. from a `Stop` payload) it degrades to informational.
- **No token-savings guarantee.** Like preflight, postflight consumes zero model
  tokens itself but does not measure exact savings. Telemetry can estimate
  response size and retry opportunity, not provider billing truth.
- **`Stop`-hook contract is unverified in-repo** (see above).

## Privacy and security

Postflight performs no network I/O and calls no model. `analyze_postflight`
reads no files at all — it works purely on the strings passed to it, and
`changed_files` is names/paths only, never contents. Only two places touch the
filesystem, both legitimately: `postflight_config.load_postflight_config` reads
`.prompt-preflight.json` (its own config, exactly as preflight's `load_config`
does), and the `Stop`-hook adapter reads the transcript JSONL to obtain the
response text it is meant to check. If a secret shows up in a response, it is
redacted in all user-facing output.
