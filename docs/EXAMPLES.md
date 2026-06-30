# Vague Prompt Examples and Templates

This page shows common vague prompts that make AI agents guess, plus stronger templates you can copy.

Use these patterns when Prompt Preflight pauses a request. Fill in the brackets, remove anything irrelevant, and send the clarified prompt.

The canonical benchmark prompt library lives at [`src/prompt_preflight/data/vague_prompts.txt`](../src/prompt_preflight/data/vague_prompts.txt). Add new vague-prompt examples there first so Codex, Claude Code, Kiro, and the benchmark stay aligned.

## Quick formula

Most useful prompts answer four questions:

```text
Do [specific action] to [specific target] so that [observable outcome].
Keep [constraints] unchanged.
Use [important context, stack, style, or data].
Verify with [tests, checks, examples, or acceptance criteria].
```

For model-friendly prompts, especially in Claude, Codex, and other agent workflows, use clear sections instead of one blended paragraph:

```text
Task:
[specific thing to do]

Context:
[source material, files, data, constraints, or background]

Output format:
[exact structure, length, schema, bullets, table, patch, slides, etc.]

Example/style reference:
[optional sample when tone or format matters]

Self-check:
[how to verify constraints, citations, tests, or acceptance criteria]
```

For image prompts, use:

```text
Create a [style] image of [specific subject] with [details],
in [setting/background], viewed from [camera angle/composition],
with [lighting/mood], in [aspect ratio/output format].
```

## Bug fixes

Vague prompts people use:

- Fix it
- Fix this bug
- Fix checkout
- Fix the checkout bug
- Fix the login bug
- Fix production issue
- Fix the flaky tests
- Make it work

Template:

```text
Fix [specific bug] in [file/component/flow].

Current behavior:
[what happens now]

Expected behavior:
[what should happen]

Reproduction steps:
[steps, command, URL, or test case]

Constraints:
[what must not change]

Verify with:
[test, command, log, screenshot, or acceptance criteria]
```

Example:

```text
Fix checkout failing when a saved card is expired.
Current behavior: clicking Pay shows a generic 500 error.
Expected behavior: show a card-expired message and keep the cart intact.
Reproduce with test user qa-expired-card@example.com in staging.
Preserve the existing Stripe webhook behavior.
Verify with a regression test for expired cards.
```

## New features

Vague prompts people use:

- Build a dashboard
- Create an admin panel
- Implement auth
- Add notifications
- Build a chat feature
- Build a customer portal
- Create a plugin
- Implement the feature

Template:

```text
Build [specific feature] for [target user/use case].

Minimum features:
- [requirement 1]
- [requirement 2]
- [requirement 3]

Platform/stack:
[framework, language, service, or constraints]

Data/source:
[API, database table, mock data, file, or none]

Out of scope:
[what not to build yet]

Success criteria:
[observable behavior or tests]
```

Example:

```text
Build an admin user-management page for support agents.
Minimum features: search users by email, view account status, and suspend/reactivate accounts.
Use the existing React dashboard and `/api/admin/users` endpoint.
Out of scope: role editing and billing changes.
Success criteria: add tests for search and suspend/reactivate flows.
```

## Refactors

Vague prompts people use:

- Clean up the code
- Refactor everything
- Refactor this
- Rewrite the frontend
- Rewrite the whole repo
- Remove unused stuff
- Rename things properly

Template:

```text
Refactor [specific file/module/component] to [desired structure or outcome].

Scope:
[files/components included]

Do not change:
[public APIs, UI behavior, data format, performance expectations]

Reason:
[readability, duplication, testability, dependency removal]

Verify with:
[existing tests, new tests, build command]
```

Example:

```text
Refactor `src/auth/session.ts` to separate token parsing from session persistence.
Scope only this module and its tests.
Do not change exported function names or cookie format.
Reason: make token parsing easier to test.
Verify with existing auth tests plus one new malformed-token test.
```

## UI and design

Vague prompts people use:

- Make the UI better
- Modernize the UI
- Polish the landing page
- Make forms nicer
- Design a better homepage
- Improve this component
- Make onboarding user-friendly

Template:

```text
Improve [specific screen/component] so [observable user outcome].

Target users:
[who uses this]

Style direction:
[minimal, dense, playful, enterprise, mobile-first, etc.]

Keep unchanged:
[brand colors, layout constraints, accessibility, API behavior]

Must include:
[content, states, interactions, responsive behavior]

Success criteria:
[visual checks, accessibility checks, screenshots, tests]
```

Example:

```text
Improve the onboarding checklist so new users can see setup progress at a glance.
Target users: first-time workspace admins.
Style direction: clean SaaS dashboard, not playful.
Keep existing brand colors and API calls unchanged.
Must include completed, current, and blocked states.
Verify with responsive screenshots for desktop and mobile.
```

## Performance and cost

Vague prompts people use:

- Make the app faster
- Optimize performance
- Optimize the database
- Optimize this query
- Optimize the onboarding flow
- Optimize costs
- Improve scalability

Template:

```text
Optimize [specific endpoint/query/page/job] to achieve [measurable target].

Current baseline:
[latency, cost, memory, query count, throughput]

Target:
[desired metric]

Constraints:
[behavior, compatibility, cost ceiling, infrastructure limits]

Measure with:
[benchmark, tracing, SQL explain, load test, dashboard]
```

Example:

```text
Optimize `/api/search` for logged-in users.
Current p95 latency is ~1.8s on staging for 10k records.
Target p95 under 500ms without changing response shape.
Do not add new paid infrastructure.
Measure with the existing search benchmark and include before/after numbers.
```

## Deployment and migration

Vague prompts people use:

- Deploy this to production
- Deploy everything
- Deploy the worker
- Make deployment safer
- Migrate the database
- Migrate the legacy data
- Migrate users
- Upgrade infrastructure
- Upgrade the whole project

Template:

```text
[Deploy/Migrate/Upgrade] [specific service/data/system] in [environment].

Scope:
[what changes]

Pre-checks:
[backups, health checks, schema checks, permissions]

Rollback plan:
[how to recover]

Constraints:
[downtime, compatibility, data preservation, rollout order]

Success criteria:
[health checks, logs, metrics, smoke tests]
```

Example:

```text
Migrate billing subscriptions from `plan_id` to `price_id` in production.
Scope: database schema, migration script, and billing read path.
Pre-check: create a backup and verify every active subscription has a Stripe price.
Rollback: keep `plan_id` until the new read path is verified.
Constraint: no billing downtime.
Success criteria: migration dry run passes and billing smoke tests pass.
```

## Tests

Vague prompts people use:

- Generate more tests
- Rewrite all tests
- Fix the flaky tests
- Add better coverage
- Test this properly

Template:

```text
Add tests for [specific behavior] in [file/module/flow].

Cases to cover:
- [case 1]
- [case 2]
- [case 3]

Use:
[unit/integration/e2e framework]

Avoid:
[brittle snapshots, network calls, excessive mocking]

Verify with:
[test command]
```

Example:

```text
Add unit tests for password reset token expiry in `src/auth/reset.ts`.
Cover valid token, expired token, malformed token, and reused token.
Use the existing Jest setup.
Avoid real email or network calls.
Verify with `npm test -- reset`.
```

## Documentation

Vague prompts people use:

- Generate better documentation
- Polish docs
- Write a README
- Explain the API
- Make docs clearer

Template:

```text
Write/update documentation for [specific feature/API/workflow].

Audience:
[new users, maintainers, operators, API consumers]

Include:
- [setup steps]
- [examples]
- [troubleshooting]
- [limitations]

Source of truth:
[code, OpenAPI schema, existing docs, issue]

Format:
[README, Markdown page, API reference, tutorial]
```

Example:

```text
Update docs for the webhook retry behavior.
Audience: API consumers.
Include retry schedule, signature verification, idempotency expectations, and one curl example.
Source of truth: `src/webhooks/retry.ts` and `docs/API.md`.
Format: add a section to `docs/webhooks.md`.
```

## Security, auth, billing, and permissions

Vague prompts people use:

- Add security everywhere
- Implement permissions
- Make auth robust
- Replace auth
- Add better payments
- Fix billing
- Remove security risk

Template:

```text
Change [specific security/auth/billing/permission behavior].

Risk being addressed:
[threat, bug, compliance need, abuse case]

Scope:
[files, routes, roles, flows]

Required behavior:
[rules, matrix, validation, audit logging]

Must preserve:
[existing sessions, payment flows, public API, data]

Verify with:
[tests, manual checks, security review checklist]
```

Example:

```text
Add role-based access checks to project deletion.
Risk: members can currently delete projects they do not own.
Scope: DELETE `/api/projects/:id`, UI delete button, and audit log.
Required behavior: only owners and admins can delete.
Preserve existing project archive behavior.
Verify with API tests for owner, admin, member, and anonymous users.
```

## Data analysis, reports, and analytics

Vague prompts people use:

- Analyze the data
- Analyze retention trends
- Make a chart
- Summarize the spreadsheet
- Find insights
- Calculate the metrics
- Visualize sales data
- Generate a nice report
- Create a reporting system
- Integrate analytics
- Make the dashboard better
- Add metrics

Template:

```text
Analyze/create [report/dashboard/chart/analytics event] for [audience/use case].

Questions it should answer:
- [question 1]
- [question 2]

Data source:
[tables, events, API, CSV, spreadsheet, or file]

Metrics:
[revenue, churn, conversion, retention, count, average, trend, etc.]

Filters/grouping:
[date range, user, account, status, etc.]

Output format:
[table, chart, CSV, JSON, dashboard card]

Success criteria:
[sample output, validation query, screenshot]
```

Example:

```text
Analyze `sales.csv` for the revenue team.
Questions: which regions grew fastest month over month, and which product lines declined?
Metrics: revenue, order count, average order value, and conversion rate.
Group by month, region, and product line.
Output: one markdown table, one chart recommendation, and a short trend summary.
Verify totals against the raw CSV row count and revenue sum.
```

## Image generation

Vague prompts people use:

- Create a car image
- Generate a logo
- Draw a cat
- Illustrate a hero image
- Make a product photo
- Create a product hero image
- Paint a portrait
- Render a house
- Create a poster
- Generate an icon
- Draw a landscape

Template:

```text
Create a [photorealistic/illustrated/3D/vector/etc.] image of [specific subject]
with [colors, materials, condition, details],
in [setting/background],
viewed from [camera angle/composition],
with [lighting/mood],
in [aspect ratio/resolution/output format].
```

Example:

```text
Create a photorealistic image of a red 1967 Ford Mustang with chrome details,
parked on a wet Tokyo street at night,
low camera angle, cinematic neon reflections,
shallow depth of field,
16:9 landscape.
```

## Writing

Vague prompts people use:

- Summarize it
- Write a better intro
- Make this sound professional
- Rewrite this email
- Draft the announcement
- Create website copy
- Improve the proposal
- Write a case study
- Write a newsletter
- Edit this for clarity

Template:

```text
[Write/Rewrite/Summarize/Edit] [specific content].

Audience:
[who will read it]

Purpose:
[what the writing should accomplish]

Source material:
[text, notes, links, transcript, outline, or context to use]

Include/exclude:
[key points, boundaries, claims, examples, or things to avoid]

Tone, length, and format:
[professional/casual/technical/etc., word count, bullets/memo/email/blog/etc.]
```

Example:

```text
Rewrite this launch email for existing beta users.
Audience: engineering managers who already tried the product.
Purpose: get them to enable Prompt Preflight for their team.
Source material: use the three bullet points below and do not invent customer names.
Tone, length, and format: concise, practical, friendly; under 180 words; email format with subject line.
```

## Research

Vague prompts people use:

- Research this topic
- Research compliance tools
- Compare the options
- Find the best tool
- Investigate competitors
- Look into pricing
- Evaluate vendors
- Research the market
- Find sources
- Compare databases
- Investigate this trend

Template:

```text
[Research/Compare/Investigate/Evaluate] [specific topic/options] for [decision/use case].

Research question:
[the decision or question the research should answer]

Scope:
[sources, date range, geography, market segment, and exclusions]

Criteria:
[cost, features, risks, implementation effort, maturity, etc.]

Citation needs:
[official sources, recent sources, peer-reviewed sources, links, or none]

Format:
[summary, table, recommendation, scorecard, annotated links]
```

Example:

```text
Research SOC 2 automation alternatives for a seed-stage SaaS team.
Question: which option is practical before our first enterprise deal?
Scope: current products available in the US; exclude custom consulting-only vendors.
Criteria: cost, implementation effort, audit readiness, integrations, and founder time required.
Format: markdown comparison table plus a recommendation.
Use official pricing/docs links where available.
```

## Presentations

Vague prompts people use:

- Create a presentation
- Make a slide deck
- Prepare slides
- Create training slides
- Design a pitch deck
- Make this presentation better
- Create investor slides
- Build a quarterly review deck
- Polish the slides
- Summarize this into slides
- Create a webinar deck

Template:

```text
Create a [slide count]-slide [deck/presentation] for [audience].

Goal:
[decision, update, pitch, teaching outcome, or call to action]

Storyline:
[sections, key message, and takeaways]

Source material:
[notes, metrics, transcript, document, or links to use]

Style and constraints:
[brand, visual style, amount of text, chart needs, speaker notes, timing]
```

Example:

```text
Create a 10-slide investor deck for seed-stage AI developer-tool buyers.
Goal: convince investors to take a first meeting.
Storyline: problem, existing retry-loop cost, product, demo, traction, market, GTM, competition, team, ask.
Source material: use the metrics in `traction-notes.md`; do not invent revenue.
Style and constraints: clean technical SaaS style, one message per slide, include speaker notes for slides 1 and 10.
```

## Tiny prompts that are often okay

Not every short prompt is bad. Prompt Preflight tries to let low-risk conversational prompts pass, such as:

- go ahead
- approved
- run the tests
- explain OAuth PKCE
- what does this error mean?

Use `[preflight:skip]` when you intentionally want the agent to make reasonable assumptions:

```text
Create a car image [preflight:skip]
```
