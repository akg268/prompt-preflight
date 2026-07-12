# Structured Prompt Templates

Prompt Preflight supports copy-pasteable prompt contracts in Markdown, XML, and TOML. These templates help users give agents enough context up front, so they spend fewer turns guessing, correcting, and retrying.

The same template catalog powers Codex, Claude Code, Kiro, and the CLI:

```text
src/prompt_preflight/data/prompt_templates.json
```

## Print a template locally

From the repository root:

```bash
python3 scripts/prompt_preflight.py --template image --template-format md
python3 scripts/prompt_preflight.py --template software --template-format xml
python3 scripts/prompt_preflight.py --template research --template-format toml
python3 scripts/prompt_preflight.py --template feature-spec --template-format md
python3 scripts/prompt_preflight.py --template agent-prompt --template-format toml
```

## Spec-driven development templates

Prompt Preflight includes a spec-driven development template pack for teams that want coding agents to work from clearer requirements before implementation begins:

- `feature_spec`
- `requirements_spec`
- `technical_design_spec`
- `implementation_plan`
- `agent_execution_prompt`
- `spec_review_checklist`

These templates are available in Markdown, XML, and TOML. In VS Code, run `Prompt Preflight: New Prompt Template`, choose a format, then choose one of the spec-driven profiles.

<!-- BEGIN GENERATED TEMPLATE DOCS - do not edit by hand -->
Supported profiles:

- `general`
- `software`
- `feature_spec`
- `requirements_spec`
- `technical_design_spec`
- `implementation_plan`
- `agent_execution_prompt`
- `spec_review_checklist`
- `image`
- `writing`
- `research`
- `data_analysis`
- `presentation`
- `customer_support`
- `prd`
- `incident_response`
- `sql`
- `design_critique`
- `meeting_notes`
- `marketing_campaign`
- `blog_post`
- `competitive_research`
- `ux_research`
- `sales_email`
- `legal_review`
- `hiring_interview`
- `education_lesson`

Supported formats:

- `md`
- `xml`
- `toml`

## Required fields by profile

| Profile | Required fields | Useful optional fields |
| --- | --- | --- |
| `general` | task, context, output format, success criteria | constraints, examples, non-goals, privacy notes |
| `software` | task, scope/context, constraints, output format, success criteria | platform/stack, non-goals, examples, plan-first, privacy notes |
| `feature_spec` | problem statement, goals, target users, functional requirements, acceptance criteria, constraints | non-goals, risks, open questions, examples, output format |
| `requirements_spec` | scope, user stories, functional requirements, non-functional requirements, edge cases, acceptance criteria, open questions | constraints, dependencies, examples, risks, output format |
| `technical_design_spec` | problem context, architecture, affected components, data or API changes, tradeoffs, compatibility, verification plan | migration plan, rollout plan, rollback plan, risks, alternatives, open questions |
| `implementation_plan` | task or scope, phases, implementation steps, dependencies, verification plan, rollback plan | constraints, risks, open questions, owners, output format |
| `agent_execution_prompt` | task, source spec, scope, constraints, implementation plan, verification plan, output format | plan-first, non-goals, rollback plan, examples, privacy notes |
| `spec_review_checklist` | source spec, review criteria, missing information, risk checks, decision, output format | constraints, examples, success criteria |
| `image` | task, visual details, style/mood, output format | avoid, examples, success criteria |
| `writing` | task, audience, purpose, context/source material, output format | tone, length, examples, exclusions, success criteria |
| `research` | research question, scope, sources, criteria, output format | date range, geography, citation style, uncertainty rule |
| `data_analysis` | task, data source, question, metrics, output format, validation | segments, assumptions, filters, examples |
| `presentation` | task, audience, goal, storyline, output format | source material, visual style, speaker notes, success criteria |
| `customer_support` | task, customer issue, prior interactions, desired tone, policy or constraints, resolution, channel, output format | examples |
| `prd` | task, problem statement, target users, functional requirements, non-functional requirements, scope, success metrics, output format | constraints, examples |
| `incident_response` | task, incident summary, severity, timeline, impact, root cause, remediation, output format | constraints |
| `sql` | query goal, schema, dialect, filters, performance constraints, expected output, success criteria | examples |
| `design_critique` | task, artifact, design goals, target users, evaluation criteria, severity, deliverable format | constraints |
| `meeting_notes` | task, meeting purpose, attendees, source transcript, decisions, action items, output format | constraints |
| `marketing_campaign` | task, campaign goal, target audience, key message, channels, output format | examples, constraints, tone, budget |
| `blog_post` | task, topic, audience, key takeaways, desired tone, output format | word count, examples, seo keywords, call to action |
| `competitive_research` | task, competitors, criteria, sources, output format | examples, constraints |
| `ux_research` | task, research goal, data sources, themes, output format | examples, constraints, target audience |
| `sales_email` | task, recipient, value proposition, call to action, tone, output format | word count, examples, context |
| `legal_review` | task, document, compliance criteria, disclaimer, output format | examples, constraints |
| `hiring_interview` | task, role, competencies, interview stage, output format | examples, company values, constraints |
| `education_lesson` | task, subject, target audience, learning objectives, duration, output format | materials needed, examples, constraints |
<!-- END GENERATED TEMPLATE DOCS -->

If a user submits a structured prompt but leaves a required field empty or placeholder-only, Prompt Preflight pauses the request and asks only for the missing required fields.

## Markdown example

```md
# Task
Create an image of a red 1967 Ford Mustang.

# Visual Details
The car is parked on a rainy Tokyo street with neon reflections and chrome details.

# Style
Photorealistic, cinematic, high contrast night mood.

# Output Format
16:9 landscape PNG.
```

## XML example

```xml
<prompt profile="research">
  <research_question>Which SOC 2 alternative is best for a seed-stage SaaS?</research_question>
  <scope>US vendors in 2026, excluding enterprise-only options.</scope>
  <sources>Official docs, vendor pricing pages, and credible security/compliance sources.</sources>
  <criteria>Cost, implementation effort, audit readiness, integrations, and risks.</criteria>
  <output_format>Markdown table plus a short recommendation with links.</output_format>
</prompt>
```

## TOML example

```toml
profile = "software"
task = "Refactor src/auth/session.ts to separate token parsing from session persistence"
scope = "Only src/auth/session.ts and its tests"
constraints = [
  "Preserve exported function names",
  "Do not change cookie format"
]
output_format = "Patch plus brief summary"
success_criteria = [
  "Existing auth tests pass",
  "Add one malformed-token regression test"
]
```

## Template validation examples

This structured prompt is still missing a required image field:

```md
# Task
Create a car image

# Visual Details
A red vintage Mustang on a rainy neon street.

# Output Format
16:9 PNG.
```

Prompt Preflight will pause it because `style or mood` is missing.

This TOML prompt is also incomplete because bracket placeholders do not count as real answers:

```toml
profile = "software"
task = "[Build/fix/change/refactor specific thing]"
scope = "src/auth.py"
constraints = "Preserve public API"
output_format = "Patch plus summary"
success_criteria = "[Test or acceptance criterion]"
```

Prompt Preflight will ask the user to fill in the required `task` and `success criteria` sections with concrete details.
