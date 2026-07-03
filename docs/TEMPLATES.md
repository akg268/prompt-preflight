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
```

Supported profiles:

- `general`
- `software`
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

Supported formats:

- `md`
- `xml`
- `toml`

## Required fields by profile

| Profile | Required fields | Useful optional fields |
| --- | --- | --- |
| `general` | task, context, output format, success criteria | constraints, examples, non-goals, privacy notes |
| `software` | task, scope/context, constraints, output format, success criteria | platform/stack, non-goals, examples, plan-first |
| `image` | task, visual details, style/mood, output format | avoid, examples, success criteria |
| `writing` | task, audience, purpose, context/source material, output format | tone, length, examples, exclusions |
| `research` | research question, scope, sources, criteria, output format | date range, geography, citation style, uncertainty rule |
| `data_analysis` | task, data source, question, metrics, output format, validation | segments, filters, assumptions |
| `presentation` | task, audience, goal, storyline, output format | source material, visual style, speaker notes |
| `customer_support` | task, customer issue, prior interactions, desired tone, policy or constraints, resolution, channel, output format | examples |
| `prd` | task, problem statement, target users, functional requirements, non-functional requirements, scope, success metrics, output format | constraints, examples |
| `incident_response` | task, incident summary, severity, timeline, impact, root cause, remediation, output format | constraints |
| `sql` | query goal, schema, dialect, filters, performance constraints, expected output, success criteria | examples |
| `design_critique` | task, artifact, design goals, target users, evaluation criteria, severity, deliverable format | constraints |
| `meeting_notes` | task, meeting purpose, attendees, source transcript, decisions, action items, output format | constraints |

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
