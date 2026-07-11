# Launch assets

Copy-paste material for sharing Prompt Preflight on Hacker News, Reddit,
LinkedIn, and X. Keep claims factual: Prompt Preflight is a local, deterministic
check that runs before a model turn. It makes no model or network calls. It
does not promise a fixed token-savings number.

Before posting, run the demo locally to make sure it still works on a clean
checkout:

```bash
python3 scripts/demo.py
```

The script shows a vague prompt being blocked, a detailed prompt passing
through, and a one-line benchmark summary. It exits non-zero if anything
regresses, so it doubles as a pre-launch smoke test.

## One-line description

> Prompt Preflight is a local preflight layer for coding agents and VS Code that
> catches underspecified prompts before they become expensive model turns. No
> model calls, no network, no API keys.

## Links

- Repo: <https://github.com/akg268/prompt-preflight>
- VS Code Marketplace beta: <https://marketplace.visualstudio.com/items?itemName=arunkumar-ganesan.prompt-preflight-vscode>

## Short description (for X, LinkedIn lead, Reddit title)

> Prompt Preflight pauses vague prompts before your coding agent or AI workflow
> spends a model turn on them. It runs locally with deterministic Python rules,
> shows a stronger rewrite, and asks at most three high-value questions. Add it
> to Codex, Claude Code, or Kiro as a preflight hook, or install the VS Code
> Marketplace beta to check prompt files before sending them to any AI tool.

## Hacker News

Title (under 80 chars):

> Show HN: Prompt Preflight – catch vague prompts before they hit the model

Body:

> Prompt Preflight is a local preflight layer for coding agents and VS Code. It
> can run before a Codex, Claude Code, or Kiro turn, and it can also check prompt
> files directly inside VS Code. When a prompt is actionable but underspecified,
> it blocks or nudges the request and returns a tailored rewrite plus up to
> three targeted questions.
>
> It uses deterministic Python rules. No model calls, no network, no API key.
> The bundled vague-prompt benchmark is meant as a regression guard, not a
> savings guarantee.
>
> Repo and install instructions: https://github.com/akg268/prompt-preflight
>
> VS Code Marketplace beta:
> https://marketplace.visualstudio.com/items?itemName=arunkumar-ganesan.prompt-preflight-vscode
>
> Try it without installing:
>
>     python3 scripts/demo.py
>
> Feedback on missed prompts and false positives is especially useful — those
> become calibration cases in `tests/test_analyzer.py`.

## Reddit (r/LocalLLaMA, r/ChatGPTCoding, r/programming)

Title:

> Prompt Preflight: a local pre-check that blocks vague prompts before your
> coding agent spends a model turn

Body:

> I kept losing model turns to prompts like "make the dashboard better" or
> "fix it" — the agent guesses, I correct, it retries with a longer context.
> Prompt Preflight is a tiny local tool that intercepts those prompts before
> the model runs and shows a stronger rewrite plus up to three questions.
>
> - Deterministic Python rules, no model or network calls
> - VS Code Marketplace beta, plus Codex, Claude Code, Kiro, and CLI support
> - Ships with a 168-prompt benchmark for regression testing
> - MIT licensed
>
> Repo: https://github.com/akg268/prompt-preflight
>
> VS Code beta: https://marketplace.visualstudio.com/items?itemName=arunkumar-ganesan.prompt-preflight-vscode
>
> Local demo:
>
>     python3 scripts/demo.py
>
> Happy to take vague prompts that *should* be blocked but aren't — those
> become calibration cases.

## LinkedIn

> Vague prompts are expensive. A request like "optimize the database" or
> "make the app faster" often triggers a guess, a correction, and a retry —
> each carrying more context than the last.
>
> Prompt Preflight is a small open-source tool I've been working on that runs
> a local, deterministic check before your coding agent spends a model turn.
> When a prompt is actionable but underspecified, it pauses the request and
> returns a tailored rewrite plus up to three high-value questions.
>
> - VS Code Marketplace beta, plus Codex, Claude Code, Kiro, and CLI support
> - No model calls, no network, no API key
> - Ships with a 168-prompt regression benchmark
> - MIT licensed
>
> Repo: https://github.com/akg268/prompt-preflight
>
> VS Code beta: https://marketplace.visualstudio.com/items?itemName=arunkumar-ganesan.prompt-preflight-vscode

## X / Twitter

Single post:

> Prompt Preflight: a local pre-check that blocks vague prompts before your
> coding agent spends a model turn. Deterministic Python rules, no network,
> no API key. VS Code beta + Codex / Claude Code / Kiro / CLI. MIT.
>
> https://github.com/akg268/prompt-preflight

Thread (optional follow-ups):

> 1/ Vague prompts create expensive loops: model guesses → you correct →
>    model retries with a longer context. Prompt Preflight moves clarification
>    *before* that loop.
>
> 2/ It returns a tailored rewrite and up to three targeted questions, scoped
>    by detected intent (software build, bug fix, deployment, migration,
>    optimization, image generation).
>
> 3/ 168-prompt benchmark is included as a regression guard. The repo has a
>    one-command demo: `python3 scripts/demo.py`.

## GIF or short-video recording checklist

Use this list every time you re-record the demo so the asset stays clean and
shareable.

- [ ] Clean shell prompt. No machine name, no internal hostname, no
      employer-tagged username. Use a generic prompt such as `$`.
- [ ] Neutral working directory name (`prompt-preflight` is fine).
- [ ] No secrets visible: scrub `.env`, API keys, tokens, customer names,
      internal URLs, private repo names, ticket IDs, or Slack handles.
- [ ] No personal notifications on screen: silence Slack, email, calendar,
      and OS banners before recording.
- [ ] Terminal in a high-contrast theme that survives GIF compression.
- [ ] Font size large enough to read at the post's display width.
- [ ] Window cropped to the terminal only — hide unrelated tabs, dock items,
      and browser bookmarks.
- [ ] Record the three demo steps in order: vague prompt blocked, detailed
      prompt allowed, benchmark summary line.
- [ ] Keep the clip under ~30 seconds for GIFs and under ~60 seconds for
      video. Trim long pauses.
- [ ] Re-watch the final clip end-to-end before publishing and confirm none
      of the items above slipped in.
- [ ] Save the source recording alongside the published asset so it can be
      re-cropped or re-encoded later without re-recording.
