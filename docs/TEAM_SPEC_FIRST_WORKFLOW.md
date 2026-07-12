# Team Spec-First Workflow for Coding Agents

This guide shows how a team can use Prompt Preflight to adopt a spec-driven workflow for AI coding agents. 

A spec-first approach ensures that agents have concrete goals, acceptance criteria, and architectural boundaries before they write code. This workflow is ideal for repo-wide changes, large migrations, or complex features where a wrong interpretation by an agent is expensive. It applies identically to both open-source and private teams, as Prompt Preflight processes all prompts locally without sending data to any servers.

## 1. Draft the feature spec in VS Code

Start by opening your project in VS Code and creating a new spec. The VS Code extension includes built-in templates to guarantee you cover the essential details.

1. Open the Command Palette and run: `Prompt Preflight: New Prompt Template`.
2. Select **`feature_spec`** (or **`requirements_spec`** if you are purely outlining product requirements).
3. Save the newly generated file (e.g., `docs/prompts/my_feature_spec.md`).

## 2. Run Prompt Preflight checks while editing

As you fill out your specification, you can run Prompt Preflight locally to verify that your spec is structurally complete and lacks ambiguous filler. 

- While editing the file, run **`Prompt Preflight: Lint Workspace Prompt Files`** from the Command Palette.
- If required fields are missing or vague language is detected, Prompt Preflight will raise inline diagnostics pausing the request until it is actionable.

## 3. Convert the spec into an implementation plan

Once the feature spec is reviewed, it is often useful to map out the technical approach before coding. 

You can print out a fresh implementation plan template directly via the CLI:

```bash
python3 scripts/prompt_preflight.py --template implementation_plan --template-format md
```

Alternatively, you can generate this using the VS Code Command Palette by selecting `Prompt Preflight: New Prompt Template` and picking `implementation_plan`.

## 4. Create an agent execution prompt

When you are ready to send the work to your coding agent, use the `agent_execution_prompt` template to provide the agent with a bounded task referencing your approved specs and plans.

Install the Prompt Preflight hook for your specific agent host to ensure vague prompts are caught before the agent spends a model turn:

- **Codex**:
  ```bash
  python3 scripts/install_prompt_preflight.py --target codex
  ```
- **Claude Code**:
  ```bash
  python3 scripts/install_prompt_preflight.py --target claude
  ```
- **Kiro**:
  ```bash
  python3 scripts/install_prompt_preflight.py --target kiro --kiro-scope user
  ```

With the hook active, if a team member types a vague request like "build auth", the hook will block it and recommend filling out a spec first.

## 5. Use the spec review checklist

Before executing a high-risk prompt or merging the final feature branch, a human reviewer can optionally use the `spec_review_checklist` template to confirm all edge cases, rollback plans, and constraints were addressed.

You can print this checklist via the CLI:
```bash
python3 scripts/prompt_preflight.py --template spec_review_checklist --template-format md
```

## 6. Keep local telemetry prompt-free and optional

Teams can measure the success of their spec-driven workflow through local, opt-in telemetry. Telemetry tracks how often prompts are blocked for ambiguity and estimates the tokens saved from avoided retry turns.

Enable telemetry by creating or updating `.prompt-preflight.json` in your repository root (or by running `Prompt Preflight: Create .prompt-preflight.json` in VS Code):

```json
{
  "telemetry": {
    "enabled": true,
    "path": ".prompt-preflight-telemetry.jsonl"
  }
}
```

To view a summary of the metrics, you can either:
- Open the Command Palette and run: `Prompt Preflight: Open Telemetry Dashboard`
- Or run the CLI report:
  ```bash
  python3 scripts/prompt_preflight.py --telemetry-report
  ```

Prompt Preflight never stores prompt text or feedback strings in telemetry. 

## 7. Open-Source vs Private Teams

This workflow works identically for open-source and private repositories because Prompt Preflight runs completely locally. No prompt text ever leaves your machine for analysis. 

If your team maintains shared prompt templates, check out the [Team Prompt Libraries](TEAM_PROMPT_LIBRARIES.md) guide to learn how to enforce consistent checks across all team members.
