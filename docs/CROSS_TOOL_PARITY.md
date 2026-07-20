# Cross-tool parity

Prompt Preflight is one analyzer with multiple integration surfaces.

The same prompt rules, profile mappings, templates, and telemetry event shape are
shared across:

- CLI
- Codex hook/plugin
- Claude Code hook/plugin
- Kiro hook
- VS Code extension

## What parity means

For the same prompt and policy:

- vague prompts should be blocked or nudged consistently
- clear prompts should pass consistently
- `.prompt-preflight.json` check policies should mean the same thing everywhere
- folder profile mappings should route prompts to the same template/profile
- telemetry should remain prompt-free across every host

## Profile routing

Teams can add folder profiles in `.prompt-preflight.json`:

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

The Python analyzer is the source of truth. VS Code mirrors the same routing for
editor diagnostics and workspace lint so users get the same feedback before a
prompt is sent to a coding agent.

## Regression test

Run:

```bash
python3 -m unittest discover -s tests -q
```

The `test_cross_tool_parity.py` suite verifies that Codex, Claude Code, Kiro,
and CLI behavior stays aligned for blocked prompts, clear prompts, and
folder-profile routing.
