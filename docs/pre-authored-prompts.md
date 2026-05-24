# Pre-authored prompts

This is the use case substrate was built around. The rest of the features are scaffolding for this one pattern.

## The pattern in one paragraph

You write a prompt — a detailed instruction, a checklist, a step-by-step playbook — once, deliberately, when you have the context and the patience. Days or weeks later, an agent picks it up via MCP search and follows it. The prompt is **authored in calm time**; it's **executed in busy time**. The bundle is your past self leaving instructions for your future self's agent.

---

## Why this matters

The hardest part of working with an AI agent isn't the model — it's writing a good prompt at the moment you need it. That moment is usually the worst moment:

- You're context-switching from something else.
- You're on mobile, in a meeting, at 11pm.
- You half-remember the gotchas from last time and don't want to repeat them.
- You're rushing, so the prompt comes out vague, the agent guesses, and you spend longer fixing the output than you would have spent writing a real prompt.

**Pre-authored prompts move the prompt-writing work to a calmer moment.** When you have ten minutes and you're thinking clearly, write the bundle. When the busy moment arrives, just trigger it.

```bash
# Calm time, last week
substrate add "prompt run db migration" --tag prompt,playbook,migration
# 200 lines of careful instructions, edge cases, verification steps
```

```text
# Busy time, today
You: "Run the migration playbook on the new index addition."
Agent: [searches substrate, finds the bundle, follows it verbatim]
```

---

## Authoring a pre-authored prompt

A good pre-authored prompt has four sections.

### 1. Trigger phrase (in the body or tags)

How will an agent find this bundle? The simplest answer: tag it with words a human would use. The agent's instructions tell it to search substrate when the user mentions those words.

```yaml
tags: [prompt, playbook, migration, database]
```

When the user says "run the migration playbook," the agent searches `playbook,migration` and finds the bundle.

### 2. The prompt itself

Write it as if you were addressing the agent directly. Imperative voice. Numbered steps. Be specific:

```markdown
# Migration playbook

You are about to run an Alembic migration against production.

## Pre-checks

1. Confirm the migration file is in `alembic/versions/` and the head matches.
2. Read the migration. If it touches a table > 1M rows, escalate.
3. Run `alembic upgrade head --sql` and review the generated SQL.

## Execution

4. Set `statement_timeout = '60s'` for the session.
5. Run `alembic upgrade head` against staging first.
6. Verify in staging: row counts, sample reads, foreign key integrity.
7. Only then run against production.

## Verification

8. Open Grafana → "Database — Lock waits" panel. Confirm < 5s spike.
9. Run the smoke test query in `scripts/post-migration-smoke.sql`.

## Rollback

10. If anything fails verification: `alembic downgrade -1` and page the on-call.
```

### 3. Embedded edge cases

The bundle should anticipate what an agent might do wrong:

```markdown
## Gotchas

- Do not run `alembic upgrade head` with a stale clone — check `git pull` first.
- The `users_email_idx` migration takes ~20 minutes on prod. Run it during the maintenance window only.
- If you see `lock_timeout`, do not retry blindly. Investigate which process holds the lock.
```

These keep the agent from invoking three-hour debugging sessions you've already done.

### 4. A clear "done" signal

End with verification the agent can self-check:

```markdown
## Done when

- `alembic current` shows the new head.
- The smoke test query returns expected rows.
- No errors in the application log within 60 seconds.

If any of the above is false, treat the migration as failed and rollback.
```

---

## How agents discover pre-authored prompts

There are three discovery patterns. Pick the one that matches your workflow.

### Pattern A: Explicit trigger

The user says the trigger phrase; the agent's system prompt tells it to search substrate.

In your `CLAUDE.md` or equivalent agent instructions:

```markdown
## When the user mentions a "playbook" or "runbook"

Search substrate for matching bundles before doing anything:

1. Call `search_bundles` with the keywords from the user's message.
2. If a bundle with tags `playbook` or `prompt` matches, read it via `get_bundle`.
3. Follow it verbatim. Do not improvise around the steps.
4. Log the use with `log_use`.
```

### Pattern B: Tag-scoped systematic search

The agent searches substrate at the start of every task, scoped by tags relevant to the task type.

```markdown
## Before starting work

If the user's request involves migrations, deploys, releases, or audits, search
substrate with `tag:playbook` filtered by the relevant subdomain. Treat any
matching bundle as authoritative instructions.
```

This pattern works well for agents that handle a fixed set of operation types.

### Pattern C: Embedded reference

The user references a bundle by id directly:

```text
You: "Apply 2026-05-12-prompt-pr-review-rubric to PR #1234."
```

The agent calls `get_bundle("2026-05-12-prompt-pr-review-rubric")` and follows it. This is the most surgical pattern — no search ambiguity, exact retrieval.

---

## Examples that work well

### PR review rubric

```bash
substrate add "prompt pr review rubric" --tag prompt,review
```

Body: checklist of what to look for (security, naming, test coverage, error handling, surface area), how to phrase critique, what severity buckets exist, when to block vs. nit.

Trigger: "Review PR #1234 using my rubric."

### Bug triage template

```bash
substrate add "prompt bug triage" --tag prompt,triage,bug
```

Body: questions to ask the reporter, steps to reproduce, severity matrix, owner-routing rules.

Trigger: "Triage issue #567."

### Code review by area

```bash
substrate add "prompt code review backend" --tag prompt,review,backend
```

Body: project-specific patterns (async/await rules, transaction boundaries, error envelope shape), what the team considers a blocker.

Trigger: "Review the backend changes against our standards."

### Architecture decision record (ADR) draft

```bash
substrate add "prompt write adr" --tag prompt,adr,docs
```

Body: ADR template, list of sections, examples of each, what makes a decision "worth recording."

Trigger: "Write an ADR for the Fly.io decision."

### New-feature scaffold

```bash
substrate add "prompt new feature scaffold" --tag prompt,scaffold,feature
```

Body: file structure, naming conventions, where to add tests, what existing patterns to follow, how to wire feature flags.

Trigger: "Scaffold a new feature called `audit-trail-export`."

---

## What makes a prompt bundle pay off

A pre-authored prompt is worth the effort when:

- **You'd write it more than three times.** Once isn't enough; three triggers the pattern.
- **The steps are stable** for at least a few weeks. If the playbook changes every day, the bundle decays faster than it earns.
- **Forgetting a step costs you real time.** The bundle exists to prevent recurring three-hour incidents.
- **The agent could plausibly improvise around it badly.** If the model would obviously do the right thing without instructions, you don't need a bundle.

A good test: "Have I explained this to a teammate or another agent more than twice?" If yes, write the bundle.

---

## What makes a prompt bundle decay

- It references a file path that moves.
- It hardcodes a tool version that gets upgraded.
- It refers to a person who left the team.
- The underlying convention changes and nobody edits the bundle.

Mitigations:

- Add a `last-verified: YYYY-MM-DD` line to long-lived bundles.
- Re-review playbook bundles quarterly. Anything you haven't run in 90 days is suspect.
- Prefer relative references ("the migration directory") over absolute paths when reasonable.

---

## Anti-patterns

- **Bundles that are just dumps.** "Here's the codebase, figure it out" is not a prompt.
- **Bundles that contradict themselves.** Write one canonical version; edit it, don't fork it.
- **Bundles that aren't tagged.** Untagged bundles are invisible to search-based agents.
- **Bundles that smuggle in credentials.** Don't.
- **Reflex-tagging everything as `prompt`.** Only bundles meant to be executed as instructions deserve that tag. Notes, decisions, and runbooks need different tags so search stays clean.

---

## Wiring it up

The simplest setup, copy-paste into your `CLAUDE.md` or equivalent:

```markdown
## substrate

You have access to a substrate knowledge store via MCP. When the user mentions:

- A "playbook," "runbook," "rubric," or "template" → call `search_bundles` with
  the keywords. If a bundle with tag `prompt` or `playbook` matches, read it
  with `get_bundle` and follow it.
- "My notes from <date>" → call `get_by_date(date=<date>)`.
- A specific bundle id → call `get_bundle(id=<id>)`.

After using a bundle, call `log_use(id=<id>, note=<short summary>)` so we can
measure which bundles earn their keep.
```

That's the whole integration. Two paragraphs of instruction, and your agents now find your pre-authored prompts on cue.

---

## Further reading

- [Use cases](use-cases.md) — the broader landscape
- [Integrations: Claude Code](integrations/claude-code.md) — full setup example
- [Concepts](concepts.md) — how bundles and tags work under the hood
