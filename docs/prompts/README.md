# Sample prompt library

Copyable starter pack for team prompt libraries. Use it to try folder profiles, opt-in workspace lint, and CI checks before you invent your own layout.

## Layout

```text
docs/prompts/
|-- specs/           # product / build specs (software intent)
|-- research/        # research briefs
|-- data-analysis/   # dataset and metric questions
|-- presentations/   # slide decks and investor narratives
`-- coding/          # concrete coding tasks
```

Each domain folder has an intentionally vague sample and a passing sample so you can see what Prompt Preflight blocks versus allows.

## How to adapt this folder

1. Copy `docs/prompts/` into your repo (or start empty and keep the same domain folders).
2. Copy `.prompt-preflight.example.json` to `.prompt-preflight.json` and keep or trim the `profiles` entries that match these paths.
3. Replace the sample prompts with your real templates. Keep the opt-in marker on every file you want CI or workspace lint to check (copy the comment line from any sample file in this folder).
4. Delete the vague samples once the demo is no longer useful — they exist only to show FAIL output.

## Folder profiles

The repository example config (`.prompt-preflight.example.json`) includes a `profiles` array that routes these folders to domain-appropriate policy. Copy that block into your project `.prompt-preflight.json` and adjust globs or modes as needed.

Example entries:

- `docs/prompts/research/**` → research, block
- `docs/prompts/specs/**` → software, block, with `plan_first` / `template_contract`
- `docs/prompts/data-analysis/**` → data_analysis, block
- `docs/prompts/presentations/**` → presentation, nudge
- `docs/prompts/coding/**` → software, block

## Lint from the CLI

From the repository root:

```bash
python3 scripts/lint_prompt_library.py --cwd . --include "docs/prompts/**/*.md"
```

Behavior:

- Matches Markdown files under `--cwd` using each `--include` glob (repeatable).
- Skips files missing the opt-in marker (the skip line names the required marker string).
- Strips the marker comment, then runs `analyze_prompt` on the remaining text.
- Prints `PASS` / `FAIL` per checked file with a short reasons summary.
- Exits non-zero when any opted-in file needs clarification (`should_clarify`), so CI can gate on it.

In VS Code, the same marker powers **Prompt Preflight: Lint Workspace Prompt Files**.

## What “good” looks like

Vague samples are short requests without audience, files, metrics, or output shape (for example, “Research this topic” or “Make the dashboard better”). Passing samples name concrete inputs, constraints, and deliverables — the same bar as the analyzer’s calibrated allow cases.

## Opt-in marker

Only files that include this HTML comment near the top are linted as prompts. Files without it (including this README) are skipped.

```html
<!-- prompt-preflight: check -->
```

The canonical inner string is `prompt-preflight: check`. Place it as a comment that matches the file format (HTML comment for Markdown/XML; `# prompt-preflight: check` for TOML).
