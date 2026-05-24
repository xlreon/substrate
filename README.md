<div align="center">

# substrate

**Lightweight, injectable knowledge bundles for AI agents.**

Git-versioned · MCP-native · Lives in your filesystem as plain markdown.

[![CI](https://github.com/xlreon/substrate/actions/workflows/ci.yml/badge.svg)](https://github.com/xlreon/substrate/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

</div>

[📖 Full docs](https://substrate.sidharthsatapathy.com) · [Blog post](https://substrate.sidharthsatapathy.com/blog/2026-05-substrate-and-context-rich-agents)

---

Substrate is a local-first knowledge store designed for the agent era. You write a "bundle" — a markdown file with YAML frontmatter — and any MCP-compatible AI tool (Claude Code, Cursor, Zed, Continue, …) can pull it into context on demand. No daemon, no database, no embeddings server. Files on disk are the source of truth; git is the history; an MCP server is the agent-facing API.

```
~/.substrate/
└── bundles/
    └── 2026-05-24/
        ├── handoff-deploy-staging.md
        └── convention-error-handling.md
```

That's the whole thing. Open them in your editor. Diff them with git. Grep them with ripgrep. Substrate just adds an opinionated CLI and an MCP server on top.

## Why substrate

You're using AI agents every day. They forget everything between sessions. The fixes on offer:

- **Mem.ai / mem0 / vector DBs** — embeddings-heavy, opaque, lossy, lock-in.
- **CLAUDE.md / cursor rules** — global, mixed with code, no provenance.
- **Notion / Obsidian** — not designed for programmatic agent access.

Substrate sits in the gap: **portable markdown bundles** you author deliberately, **git-versioned** so changes are auditable, and **MCP-exposed** so any agent can fetch them by id, tag, date, or substring. Nothing magic — and that's the point.

## Install

Requires Python 3.10+.

```bash
# Standalone CLI tool (recommended)
uv tool install substrate-kb

# Or with pipx
pipx install substrate-kb

# Or editable from source
git clone https://github.com/xlreon/substrate.git
cd substrate && uv tool install --editable .
```

Initialize the store (one-time):

```bash
substrate init       # creates ~/.substrate, git-inits it
```

## 60-second tour

```bash
substrate add "deploy staging landmines"   # opens $EDITOR on a new bundle
substrate list --tag handoff               # filter by tag
substrate search "asyncpg ssl"             # substring across id/tags/body
substrate get 2026-05-24-deploy-staging-landmines | pbcopy
substrate ui --open                        # static HTML dashboard
```

Bundles are markdown files under `~/.substrate/bundles/YYYY-MM-DD/`. Every `add` and `edit` commits to git automatically.

## Where your bundles live

Substrate code lives at [github.com/xlreon/substrate](https://github.com/xlreon/substrate). You install the binary — you don't fork or clone unless you want to contribute.

**Your bundles live in `~/.substrate/bundles/YYYY-MM-DD/<slug>.md`. Your data, not ours.**

`substrate init` git-inits `~/.substrate/` locally so you get versioning for free. Want to back it up?

```bash
cd ~/.substrate && git remote add origin <your-private-repo> && git push -u origin main
```

Want to move the store? Set `SUBSTRATE_HOME`:

```bash
export SUBSTRATE_HOME=/opt/team-substrate    # shared NFS mount
export SUBSTRATE_HOME=~/Dropbox/substrate    # synced folder
export SUBSTRATE_HOME=./project-substrate    # project-local
```

Substrate honors `SUBSTRATE_HOME` everywhere — CLI, MCP server, dashboard.

## For AI agents (MCP)

Substrate ships an MCP server (`substrate-mcp`) exposing the bundle store to any MCP-compatible client.

**Claude Code:**
```bash
claude mcp add substrate -- substrate-mcp
```

**Cursor / Zed / Continue / other MCP hosts** — add to your MCP config:
```jsonc
{
  "mcpServers": {
    "substrate": { "command": "substrate-mcp" }
  }
}
```

**Tools exposed:**
| Tool | Purpose |
|---|---|
| `list_bundles` | Enumerate, optionally filter by tag/date |
| `get_bundle` | Fetch a bundle by id |
| `search_bundles` | Substring search across id, tags, body |
| `get_by_date` | Temporal lookup (`2026-05-24` or a range) |
| `log_use` | Record that an agent used a bundle (optional retrieval metric) |

Now your agent can pull context on demand:

> "What did we decide about retry semantics last week?"
> → agent calls `search_bundles("retry", since="2026-05-17")` → reads top hits → answers with citations to specific bundle ids.

## Bundle format

```markdown
---
id: 2026-05-24-deploy-staging-landmines
created: 2026-05-24T19:30:00+05:30
tags: [deployment, fly, gotcha]
context_refs: []
---

# What broke

asyncpg refused TLS with `?ssl=disable` — needed `?sslmode=disable` instead.
…
```

The format is **deliberately boring**: any text editor works, the files survive substrate being uninstalled, and your `git log` is the history. No proprietary blobs, no opaque indexes.

## The dashboard

`substrate ui --open` generates a single self-contained HTML file with:

- 4-stat overview (total / this week / today / last activity)
- 30-day activity bar chart
- "Most referenced" leaderboard (computed from your AGENTS.md / CLAUDE.md mentions + git commit count)
- Tag filter chips
- Day-grouped timeline with collapsible bodies
- Modal form to draft a new bundle and copy a one-liner shell command to land it

Set `SUBSTRATE_ACTIVE_FILE` to point at the markdown file where you declare your current "active" bundle (e.g. `~/AGENTS.md`, `~/CLAUDE.md`, anywhere) and the dashboard will highlight that one at the top:

```bash
export SUBSTRATE_ACTIVE_FILE=~/AGENTS.md
```

In that file, add a line containing `ACTIVE BUNDLE` and the bundle path:

```markdown
## Now
- **ACTIVE BUNDLE:** `~/.substrate/bundles/2026-05-24/handoff-deploy-staging.md`
```

(Marker text is configurable via `SUBSTRATE_ACTIVE_MARKER`.)

## CLI surface

| Command | What it does |
|---|---|
| `substrate init` | Initialize `~/.substrate` as a git-backed store |
| `substrate add <name>` | New bundle in today's folder, opens `$EDITOR` |
| `substrate list` | List bundles, optionally `--tag` / `--date` filtered |
| `substrate search <query>` | Substring search across id, tags, body |
| `substrate get <id>` | Print a bundle to stdout (pipe-friendly) |
| `substrate use <id>` | Copy body to clipboard + log usage |
| `substrate log` | Show usage log (the falsifiable retrieval metric) |
| `substrate edit <id>` | Open an existing bundle in `$EDITOR` |
| `substrate history <id>` | `git log` for a specific bundle |
| `substrate ui` | Generate a static HTML dashboard |

Full reference: `substrate --help`. Design notes: [SPEC.md](SPEC.md).

## Design principles

1. **Files on disk are source-of-truth.** Every index, cache, embedding, dashboard is disposable and rebuildable from the markdown.
2. **Git is the history.** No custom audit log, no "version" frontmatter field.
3. **Boring formats.** Markdown + YAML frontmatter. No JSON-LD, no proprietary schema.
4. **Falsifiable retrieval.** `log_use` exists so you can prove (or disprove) that the store earns its keep.
5. **MCP-native, not MCP-only.** The CLI works offline, in a script, in a CI job; the MCP layer is an optional adapter.

## Contributing

PRs welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for dev setup and conventions. Bug reports and feature requests: [open an issue](https://github.com/xlreon/substrate/issues).

## Support substrate

- ⭐ Star on GitHub if substrate earns its keep in your workflow
- 💬 Share use cases in [Discussions](https://github.com/xlreon/substrate/discussions)
- 🐛 File issues, especially for cross-platform breakage
- 📝 Write up your integration — we'll link it from the docs

## License

[MIT](LICENSE) © Sidharth Satapathy
