---
title: "I built a CLI for my AI agents to share notes. Open-sourcing it."
date: 2026-05-24
author: Sidharth Satapathy
tags: [substrate, mcp, agents, open-source, cli, knowledge-management]
description: "Substrate is a local-first knowledge store for AI agents — markdown bundles, git-versioned, exposed over MCP. Here's why I built it and what it solved."
---

# I built a CLI for my AI agents to share notes. Open-sourcing it.

Yesterday my Claude Code session compacted and I lost the entire reasoning chain about why we picked Fly.io over Render. Three hours of trade-off analysis — cold start latency, Wireguard networking, pricing at the 4-container mark — gone. I had written the decision down in a markdown file weeks ago, but the next session didn't know it existed. It asked me the same questions. I answered them again, worse, because I'd already forgotten half my own reasoning. This keeps happening. Not because the tools are bad, but because nothing connects what I know to what my agents see.

## The shape of the problem

I tried the obvious fixes. None of them stuck.

**Vector memory is a black box.** Tools like mem0 embed your notes and retrieve "relevant" chunks. But you can't audit what got retrieved, you can't tell why a note was ranked third instead of first, and you can't force a specific piece of context into the window. It's lossy by design. When I need my agent to see my exact deployment checklist, "semantically similar" isn't good enough.

**CLAUDE.md is flat and global.** It's one file at the root of your project. Everything goes in — coding conventions, environment setup, architecture decisions, temporary notes. No dates, no tags, no provenance. By the time you have 200 lines in there, it's a junk drawer. Finding the thing you wrote last Tuesday means scrolling, not querying.

**Notion and Obsidian are human-shaped.** They're built for people who browse and click. My agents need files they can fetch programmatically — by date, by tag, by substring. An agent can't navigate a Notion sidebar. It needs an API that returns markdown and gets out of the way.

## What substrate is

Substrate is a local-first knowledge store. You write bundles — small, deliberate notes — and any MCP-compatible agent can pull them into context on demand. No daemon, no database, no embeddings server.

**A bundle is a markdown file with YAML frontmatter.** That's the entire data model. You write what you want your agents to know, tag it, and save it.

```markdown
---
id: 2026-05-24-deploy-staging-landmines
created: 2026-05-24T19:30:00+05:30
tags: [deployment, fly, gotcha]
context_refs: []
---

# What broke

asyncpg refused TLS with `?ssl=disable` — needed `?sslmode=disable`.
Fly.io internal DNS requires `.internal` suffix, not the public hostname.
```

**Bundles live under `~/.substrate/bundles/YYYY-MM-DD/`.** Git tracks every add and edit automatically. Your `git log` is your audit trail. Your `git diff` shows exactly what changed. No custom versioning, no proprietary format.

**An MCP server exposes them to any agent that speaks MCP.** Claude Code, Cursor, Zed, Continue — one config line and your agent can search, fetch, and cite specific bundles.

Install and wire it up:

```bash
uv tool install substrate-kb
substrate init

# Claude Code
claude mcp add substrate -- substrate-mcp

# Cursor / Zed / any MCP host
# Add to your MCP config:
# { "mcpServers": { "substrate": { "command": "substrate-mcp" } } }
```

Five MCP tools: `list_bundles`, `get_bundle`, `search_bundles`, `get_by_date`, `log_use`. That's the whole surface. Agents read, humans write.

## What I built it for

I've been using substrate on my main repo for two weeks. Here are the patterns that stuck.

### Cross-session handoffs

The compaction problem I described at the top? Solved. Before I end a session, I write a handoff bundle: what was decided, what's half-finished, what to watch out for. The next session starts with "look at my notes from yesterday" — the agent calls `get_by_date`, reads the handoff, and picks up where I left off. No re-explaining.

```bash
substrate add "handoff deploy staging" --tag handoff
# write the context in $EDITOR, save, done
```

The next session:

> "Check my substrate notes from May 23 and continue the deploy work."

The agent calls `search_bundles("deploy", since="2026-05-23")`, reads the bundle, and has full context. I've done this across eight sessions now. It works every time.

### Parallel agent dispatch

I run multiple agents on the same codebase — one on the API layer, one on the frontend, one on tests. They need to agree on conventions. Before substrate, I'd paste the same instructions into each session. Now I write a convention bundle once:

```bash
substrate add "convention error responses" --tag convention,api
```

The bundle specifies the error envelope format, status code mapping, and retry semantics. Each agent finds it via MCP search when it needs to make a decision about error handling. Agent A writes a convention, Agent B reads it mid-task. They stay consistent without me copy-pasting between windows.

### Pre-authored prompts

Some tasks need detailed instructions that are too long for CLAUDE.md and too specific to be permanent rules. Database migrations, for example. I have a bundle that walks through the exact steps: check for lock contention, set statement timeout, test rollback, verify in staging first. When I tell an agent "run the migration playbook," it searches for the bundle tagged `migration,playbook` and follows it.

The key insight: **I author the bundle once, at my own pace, when I'm thinking clearly.** The agent consumes it later, at execution time, when I might be distracted or in a hurry. The bundle is my calm self leaving instructions for my rushed self's agent.

### Debugging breadcrumbs

When I hit a gnarly bug — the kind that takes three hours and involves reading framework source code — I write a bundle documenting the root cause and the fix. Tagged `gotcha` or `debugging`. Six days later, a related bug surfaces. The agent searches for the original investigation and finds it immediately. Without the bundle, I would have repeated the same spelunking.

## The dashboard

`substrate ui --open` generates a single self-contained HTML file. No server, no JavaScript framework, no build step. Open it in your browser and you get:

- **Four-stat overview** — total bundles, this week, today, last activity timestamp.
- **30-day activity chart** — a bar chart showing how many bundles you created each day. Useful for spotting gaps.
- **Most-referenced leaderboard** — which bundles actually get used, computed from mentions in your CLAUDE.md or AGENTS.md, git commit count, and `log_use` invocations.
- **Tag filter chips** — click a tag, see only those bundles.
- **Day-grouped timeline** — every bundle, grouped by creation date, with collapsible bodies so you can scan or drill in.
- **Modal form** — draft a new bundle in the browser and copy a shell command to land it.

All static HTML. Generated on demand. No server. The file survives substrate being uninstalled — it's just HTML with your data baked in.

## Where it's going

Substrate is open-source under the MIT license. The PyPI package is [`substrate-kb`](https://pypi.org/project/substrate-kb/). The source is at [github.com/xlreon/substrate](https://github.com/xlreon/substrate).

I'm maintaining it actively and PRs are welcome. Here's what I'd love help with:

- **Windows support.** The clipboard integration shells out to `pbcopy` today. Linux and Windows need `xclip`/`wl-copy` and `clip.exe` respectively. The plumbing is straightforward.
- **More MCP host integrations.** Claude Code and Cursor are tested. Zed, Continue, Windsurf, Claude Desktop — community confirmations and config snippets would be great.
- **Community-curated bundle packs.** I keep reaching for the same shapes: deployment checklists, code review rubrics, debugging runbooks, architecture decision templates. A shared repository of starter bundles would lower the ramp for new users.
- **Project-scoped stores.** `SUBSTRATE_HOME=./project-substrate` already works, but first-class support for per-project stores alongside the global one is on the roadmap.

The philosophy stays fixed: files on disk are source-of-truth, git is the history, no magic. Everything else is negotiable.

## Try it

```bash
uv tool install substrate-kb
substrate init
substrate add "my first bundle" --tag getting-started
```

Three commands, you're running. Docs at [substrate.sidharthsatapathy.com](https://substrate.sidharthsatapathy.com). If it earns its keep in your workflow, [star the repo](https://github.com/xlreon/substrate).
