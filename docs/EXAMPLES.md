# Task
[Specific action to perform]

# Context
[Relevant background, files, source material, data, links, or constraints]

# Output Format
[Exact structure: bullets, table, JSON, patch, report, image specs, etc.]

# Success Criteria
- [How the agent should verify the result]
- [What must be true when the work is done]

# Optional
- Constraints: [boundaries or things to preserve]
- Examples: [sample output or style reference]
- Non-goals: [what not to do]
# Prompt Preflight examples

This page shows underspecified prompts alongside prompts that Prompt Preflight would let through. The examples are grouped by domain to demonstrate how different tasks require different kinds of context to succeed.

## Software builds & changes

For stricter copy-paste contracts, see [Structured Prompt Templates](TEMPLATES.md). Prompt Preflight can validate Markdown, XML, and TOML prompt contracts and pause when required fields are missing or still placeholder-only.

The canonical benchmark prompt library lives at [`src/prompt_preflight/data/vague_prompts.txt`](../src/prompt_preflight/data/vague_prompts.txt). Add new vague-prompt examples there first so Codex, Claude Code, Kiro, and the benchmark stay aligned.

The structured prompt template catalog lives at [`src/prompt_preflight/data/prompt_templates.json`](../src/prompt_preflight/data/prompt_templates.json). Add shared template changes there so all integrations stay aligned.

Prompt Preflight also checks for likely secrets, missing context, missing output contracts, and high-risk work that should start with a plan.
### Example 1
**Before (vague):**
> Build a chat feature

**After (ready):**
> Add a real-time chat component to the `CustomerPortal` view so users can message support directly. Keep the design consistent with the existing `MessageBubble` components. Verify that messages send successfully and persist after a page refresh.

### Example 2
**Before (vague):**
> Rewrite the frontend

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

You can print stricter Markdown, XML, or TOML versions from the CLI:

```bash
python3 scripts/prompt_preflight.py --template software --template-format md
python3 scripts/prompt_preflight.py --template image --template-format xml
python3 scripts/prompt_preflight.py --template research --template-format toml
```

For high-risk prompts, add a plan-first boundary:

```text
Plan-first:
Inspect the relevant context, propose the rollout or change plan, and wait for confirmation before making production, migration, destructive, or broad repository changes.
```

Never paste real secrets into prompts. Use placeholders instead:

```text
Use [REDACTED_SECRET] as the example API key.
```

For image prompts, use:

```text
Create a [style] image of [specific subject] with [details],
in [setting/background], viewed from [camera angle/composition],
with [lighting/mood], in [aspect ratio/output format].
```
**After (ready):**
> Rewrite the `Dashboard` and `Profile` views in React, replacing the legacy Handlebars templates. The outcome must match the current layout identically, without adding new CSS classes. Verify that all existing unit tests in `tests/ui/` pass after the migration.

## Bug fixes

### Example 1
**Before (vague):**
> Fix the checkout bug

**After (ready):**
> Fix the `StripePayment` component where it throws a "token missing" error when users submit the checkout form twice in rapid succession. The fix must disable the submit button after the first click. Verify by running the checkout flow with a mocked network delay and ensuring no duplicate charge is created.

### Example 2
**Before (vague):**
> Fix production issue

**After (ready):**
> Investigate the 500 errors occurring on the `/api/v1/reports` endpoint in production. Identify why the database connection pool is exhausting under load and implement a backoff retry logic. Ensure the fix does not break the existing rate limits. Verify with load testing in staging.

## Deployment & migration

### Example 1
**Before (vague):**
> Deploy this to production

**After (ready):**
> Deploy the latest release branch to the production Kubernetes cluster. Before applying, ensure the `DB_PASSWORD` secret is properly mounted. Wait for the rolling update to complete and verify the new pod health checks pass on the `/healthz` endpoint.

### Example 2
**Before (vague):**
> Migrate users

**After (ready):**
> Write a script to migrate all user records from the `legacy_users` table to the new `accounts` table in PostgreSQL. Map the `username` field to `email` and ensure the script logs any records that fail validation. Verify by running the migration in a dry-run mode against the staging database.

## Optimization

### Example 1
**Before (vague):**
> Optimize the database

**After (ready):**
> Add a composite index on `(user_id, created_at)` to the `transactions` table to speed up the recent transactions query. Ensure the migration script runs without locking the table for writes. Verify the query execution time drops below 50ms using `EXPLAIN ANALYZE`.

### Example 2
**Before (vague):**
> Make the app faster

**After (ready):**
> Implement Redis caching for the `/api/v1/products` endpoint to reduce page load time. The cache should TTL after 5 minutes and automatically invalidate when a product is updated. Verify by measuring the API response time under high concurrency and confirming it stays under 100ms.

## Image generation

### Example 1
**Before (vague):**
> Create a poster

**After (ready):**
> Create a minimalist vector illustration of a jazz band playing in a cozy club. The visual style should be retro 1950s with a warm color palette (deep reds, oranges, and golds). The composition should feature the saxophonist in the center foreground, illuminated by a single spotlight, leaving the background dimly lit. Aspect ratio 3:4.

### Example 2
**Before (vague):**
> Generate a logo

**After (ready):**
> Create a flat vector logo for a coffee shop named "Bean & Leaf" with a warm, artisanal feel. The mark pairs a stylized coffee bean with a single tea leaf in one geometric icon, using a two-color palette of deep espresso brown and sage green, placed above the wordmark with even padding. Use rounded sans-serif typography on a transparent background, flat lighting, no gradients or drop shadows. Aspect ratio 1:1, exported as an SVG file.
