# Calibration corpus

Prompt Preflight uses a **data-driven calibration corpus** so maintainers can add
reviewed examples without writing new test code.

## Where it lives

| Path | Role |
|------|------|
| `tests/data/calibration_corpus.jsonl` | Append-only reviewed examples (one JSON object per line) |
| `tests/test_calibration_corpus.py` | Loads every line and asserts analyzer behavior |

Existing hardcoded calibration suites (`tests/test_writing_research_calibration.py`
and calibration methods in `tests/test_analyzer.py`) remain. The JSONL corpus is
the place to grow new cases without touching those modules.

## Schema

Each non-comment line is a single JSON object:

```json
{
  "id": "fp-0001",
  "prompt": "...",
  "should_clarify": false,
  "expected_intent": "software_build",
  "expected_checks": ["context"],
  "note": "why this expectation is correct"
}
```

| Field | Required | Notes |
|-------|----------|-------|
| `id` | yes | Stable unique id (e.g. `fp-0001` false-positive, `mv-0001` missed vagueness) |
| `prompt` | yes | The prompt text under test |
| `should_clarify` | yes | `true` if the analyzer should block/clarify; `false` if it should pass |
| `expected_intent` | no | When set, must equal `result.intent` |
| `expected_checks` | no | When set, each string must appear in `result.checks` |
| `note` | no | Maintainer rationale |

Blank lines and lines starting with `#` are ignored.

## Adding a reviewed example

1. **Strip private details.** Do not commit secrets, customer names, internal
   URLs, employee identifiers, proprietary copy, or any prompt that could expose
   private project context. Prefer synthetic, generic wording.
2. Run the candidate through the analyzer and confirm the outcome you expect:
   ```bash
   python3 -c "import sys; from pathlib import Path; sys.path.insert(0, str(Path('src'))); from prompt_preflight.analyzer import analyze_prompt; r=analyze_prompt('YOUR PROMPT'); print(r.should_clarify, r.decision, r.intent, list(r.checks))"
   ```
3. Append **one new JSON line** to `tests/data/calibration_corpus.jsonl`.
4. Re-run:
   ```bash
   python3 -m unittest tests.test_calibration_corpus -v
   ```

Do not edit existing corpus rows casually — they are regression anchors. Prefer
appending a new id if behavior or wording needs a new case.

## Privacy reminder (read this)

> **Always strip private details before appending.** The corpus is committed to
> git and may be public. If a real prompt was useful for calibration, rewrite it
> into a generic equivalent that preserves ambiguity structure without leaking
> names, credentials, internal systems, or confidential product plans.
