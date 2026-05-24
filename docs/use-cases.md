# Use cases

Substrate is a shared, lightweight, CLI-based interface for organising prompts and markdown files — yours, or the ones your agents generate — into a knowledge pool that any MCP-compatible agent can pull from. This page is the bullet-proof case for why it exists.

## The one-line pitch

> **Files on disk are source-of-truth. Git is the history. MCP is the wire protocol. Your agents read from a directory you control.**

If that sentence makes sense to you, you already know whether you want it.

---

## The shape of the problem

Modern coding agents — Claude Code, Cursor, Zed, Codex, Continue — are good at the next 30 minutes of work and bad at the next 30 days. The reasons aren't the model. They're plumbing:

1. **Sessions reset.** Compaction, new conversation, new agent, new machine — yesterday's reasoning is gone.
2. **Knowledge is locked inside conversations.** When an agent writes a great runbook in chat, it dies with that chat unless you copy it somewhere.
3. **CLAUDE.md grows into a junk drawer.** One flat file with no dates, tags, or provenance.
4. **Vector stores hide the why.** "Relevant" chunks come back; ranking decisions don't. You can't force a specific bundle into the window.
5. **Wikis aren't agent-shaped.** Notion and Obsidian are built for browsers and humans.

Substrate fits between your agents and your filesystem. It's the smallest possible layer that solves all five.

---

## What you put in a bundle

A bundle is a markdown file. Anything markdown-shaped is fair game:

| Bundle type | Example slug | Why it lives here |
|---|---|---|
| **Handoff** | `handoff-deploy-staging.md` | Cross-session continuity. Last session's reasoning, next session's starting point. |
| **Pre-authored prompt** | `prompt-bug-triage-template.md` | A prompt you wrote calmly that an agent picks up later under pressure. |
| **Convention** | `convention-api-error-envelope.md` | Project-wide rules that multiple agents need to obey. |
| **Decision record** | `decision-fly-over-render.md` | Why a choice was made. Surfaces when someone questions it later. |
| **Debugging breadcrumb** | `gotcha-asyncpg-ssl-disable.md` | A bug you already solved once. Future-you doesn't have to re-spelunk. |
| **Runbook / playbook** | `runbook-migration-checklist.md` | Step-by-step instructions the agent follows verbatim. |
| **Context dump** | `context-customer-X-onboarding.md` | One-off context for a specific task. Discardable after. |

Substrate doesn't care what type a bundle is. There's no `kind` field, no enum. The format is universally markdown + frontmatter; the meaning lives in the body and the tags.

---

## The four canonical use cases

### 1. Shared knowledge pool for parallel agents

You're running three agents on the same repo — one on backend, one on frontend, one on tests. They need to agree on conventions (error envelope shape, naming rules, retry semantics) but you don't want to paste the same paragraph into every session.

Write the convention once:

```bash
substrate add "convention api error envelope" --tag convention,api
# write the convention, save
```

Each agent's first turn includes a system prompt that says "search substrate for `convention,api` tags before deciding on response shapes." All three agents converge on the same envelope. You wrote one bundle.

This scales. Twenty agents on twenty branches still share one pool. Updating the convention is a `substrate edit` — every agent sees the new version on its next search.

### 2. Pre-authored prompts that agents pick up on cue

The killer use case. You write a prompt **once, calmly, when you're thinking clearly**. An agent picks it up **later, at execution time, when you might be distracted, on mobile, or asking for a quick fix**.

```bash
substrate add "prompt run db migration" --tag prompt,playbook,migration
```

The bundle body is the full migration playbook — checks for lock contention, sets statement timeout, tests rollback, verifies in staging. Then, six days later:

> "Run the migration playbook on the new index addition."

The agent searches substrate for `prompt,playbook,migration`, gets back exactly the bundle you wrote, and follows it step by step. You didn't have to re-explain anything. The bundle was your calm self leaving instructions for the rushed-self moment.

See [pre-authored-prompts.md](pre-authored-prompts.md) for the full pattern.

### 3. Cross-session handoffs

Your Claude Code session compacted and you lost two hours of trade-off analysis. Or you closed your laptop, came back the next morning, and the agent has no memory of yesterday.

Before stopping work, write a handoff:

```bash
substrate add "handoff deploy staging" --tag handoff
# write what was decided, what's half-done, what to watch out for
```

Next session, anywhere, any agent:

> "Open my substrate handoff from yesterday and continue where we left off."

The agent runs `get_by_date(date="2026-05-23", tag="handoff")`, reads the bundle, and resumes with the full reasoning chain in context. This is the use case that pays for substrate by itself.

### 4. Debugging breadcrumbs

You spent three hours figuring out why `asyncpg` refused TLS connections with `?ssl=disable`. The fix was `?sslmode=disable`. Six days later, a related bug surfaces.

Without substrate, the agent re-discovers the issue from scratch. With substrate, you wrote a bundle the day you fixed it:

```bash
substrate add "gotcha asyncpg ssl disable" --tag gotcha,asyncpg,deployment
```

The next agent search for `asyncpg` returns the bundle in 80ms. Three-hour debugging session collapses to a 5-second `search_bundles` call.

---

## What substrate is **not**

Being clear about scope keeps the surface small.

| It is **not** | Why it isn't |
|---|---|
| A vector database | No embeddings, no ranking. Boring substring + tag match. You can `grep` it. |
| A wiki or documentation system | Bundles aren't pages. No hierarchy, no internal links required. |
| A task tracker | Use Linear, GitHub Issues, your todo app. |
| A chat history archive | Use the export from your IDE. Substrate stores prompts and context, not transcripts. |
| A secrets manager | Never put credentials in a bundle. `usage.log` is gitignored but bundles aren't. |
| A long-term memory model | It's a filesystem with conventions. The "memory" comes from your agent reading the file. |

---

## How substrate compares

| | Substrate | mem0 / Letta | CLAUDE.md | Notion / Obsidian |
|---|---|---|---|---|
| **Storage** | Markdown on disk | Vector DB | One file | Proprietary DB |
| **History** | git | Opaque | git (project) | Vendor history |
| **Agent surface** | MCP (5 tools) | Custom SDK | Read at start | Manual paste |
| **You can grep it?** | yes | no | yes | no |
| **Offline-first?** | yes | no | yes | no |
| **Forced retrieval?** | yes (by id) | no (ranked) | full file | manual |
| **Falsifiable usage?** | yes (`usage.log`) | telemetry-only | no | no |
| **Lock-in?** | none — markdown | high | none | very high |

Substrate is the most boring option in this table. That's intentional.

---

## When substrate is overkill

- **One agent, one session, one project.** If you never close the session, you don't need cross-session memory.
- **A team with strong wiki habits.** If everyone already writes Notion docs and reads them, adding substrate doesn't help humans — but it can still help agents.
- **Pure RAG over a fixed corpus.** Substrate is for *your* notes. If you need to retrieve over thousands of documents you didn't write, a vector store is the right tool.

---

## When substrate earns its keep

- **You run 3+ agents in parallel.** Convention bundles keep them coherent.
- **You start fresh sessions multiple times a day.** Handoff bundles eliminate re-explaining.
- **You have recurring playbooks** (migrations, deploys, releases, audits) that benefit from being captured once and applied many times.
- **You want your agents to learn from each other.** Agent A writes a bundle, Agent B reads it tomorrow.
- **You distrust opaque vector retrieval.** Substrate gives you exact `id`-based fetch, plus the ability to inspect every retrieval after the fact.

---

## Further reading

- [Quickstart](quickstart.md) — five minutes from install to first bundle
- [Pre-authored prompts](pre-authored-prompts.md) — the killer-feature deep dive
- [Concepts](concepts.md) — bundles, frontmatter, git model
- [Claude Code integration](integrations/claude-code.md) — wire substrate into your daily driver
