# Contributing

## Development setup

Requires Python 3.10 or later. No external dependencies — the project uses only the standard library.

Clone the repository and you're ready to work:

```bash
git clone https://github.com/<owner>/prompt-preflight.git
cd prompt-preflight
```

## Running tests

```bash
python3 -m unittest discover -s tests -q
```

This discovers and runs all test files under `tests/`. It covers the analyzer, hook adapters, installers, and the benchmark minimum-block-rate check.

For verbose output, replace `-q` with `-v`.

## Running the benchmark

```bash
python3 scripts/benchmark_vague_prompts.py
```

The benchmark runs 100 intentionally vague prompts through the analyzer and reports how many are blocked, which are missed, and scores by intent. It exits non-zero if the block rate falls below 90%.

Save structured results:

```bash
python3 scripts/benchmark_vague_prompts.py --json-output benchmark-results.json
```

Benchmark results are **regression evidence**, not guaranteed token savings. They show whether the analyzer still catches the prompts it was calibrated on. Do not frame benchmark numbers as fixed savings claims — actual token impact depends on model, context, and task.

## Adding calibration regressions

Prompt Preflight relies on small, concrete regression examples to keep its rule-based analysis honest. There are two kinds of regressions:

### Missed prompt — vague prompt that slipped through

A missed prompt is a vague request where `analyze_prompt` returns `should_clarify=False`. It should have been caught but wasn't.

1. **Add the prompt to the benchmark set.** Open `scripts/benchmark_vague_prompts.py` and append the prompt string to the `VAGUE_PROMPTS` tuple. Keep it short and realistic — the smallest prompt that reproduces the issue.

2. **Add a calibration case to the test.** Open `tests/test_analyzer.py`, find `test_calibration_set`, and add an entry mapping the prompt to `True`:

   ```python
   "Fix the flaky tests": True,
   ```

   This asserts that the analyzer should clarify this prompt.

3. **Fix the analyzer** (in `src/prompt_preflight/analyzer.py`) so the new case passes.

4. **Run the tests and benchmark** to confirm nothing else regressed:

   ```bash
   python3 -m unittest discover -s tests -q
   python3 scripts/benchmark_vague_prompts.py
   ```

### False positive — clear prompt that was incorrectly blocked

A false positive is a specific, actionable prompt where `analyze_prompt` returns `should_clarify=True`. It should have passed through but was blocked.

1. **Add a calibration case to the test.** Open `tests/test_analyzer.py`, find `test_calibration_set`, and add an entry mapping the prompt to `False`:

   ```python
   "Add an aria-label to `LoginButton` and test it": False,
   ```

   This asserts that the analyzer should let this prompt through.

2. **Fix the analyzer** so the new case passes without breaking existing calibration entries.

3. **Run the tests and benchmark** to confirm:

   ```bash
   python3 -m unittest discover -s tests -q
   python3 scripts/benchmark_vague_prompts.py
   ```

### Checklist for any regression case

- Add the smallest prompt that reproduces the issue.
- Place it alongside similar cases in `test_calibration_set` (or `VAGUE_PROMPTS` for missed prompts).
- Verify the expected behavior locally.
- Run the full test suite.
- Run the benchmark if the change affects scoring or intent routing.

## Pull requests

- Stay scoped to the reported issue — one concern per PR when practical.
- If a behavior change affects what the analyzer catches or lets through, update both the calibration tests and the benchmark set.
- Include the prompt that triggered the issue in the PR description so maintainers can reproduce it.
