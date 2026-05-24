# What is substrate?

**Substrate is a local-first knowledge store for AI agents.** You write a "bundle" — a markdown file with YAML frontmatter — and any MCP-compatible tool (Claude Code, Cursor, Zed, …) can pull it into context on demand. No daemon, no database, no embeddings server. Files on disk are the source of truth. Git is the history. An MCP server is the agent-facing API.

```
~/.substrate/
└── bundles/
    └── 2026-05-24/
        ├── handoff-deploy-staging.md
        └── convention-error-handling.md
```

That's the whole thing. Open them in your editor. Diff them with `git`. Grep them with `ripgrep`. Substrate adds an opinionated CLI and an MCP server on top — nothing else.

---

## Get started

| What | Where |
|---|---|
| **Install** | [install.md](install.md) — uv, pipx, or from source |
| **5-minute tour** | [quickstart.md](quickstart.md) — copy-paste walkthrough |
| **Why substrate?** | [use-cases.md](use-cases.md) — the positioning piece |
| **Concepts** | [concepts.md](concepts.md) — bundles, frontmatter, git model |
| **Dashboard** | [dashboard.md](dashboard.md) — `substrate ui` walkthrough |
| **Pre-authored prompts** | [pre-authored-prompts.md](pre-authored-prompts.md) — the killer feature |

## Integrations

| Host | Guide |
|---|---|
| Claude Code | [integrations/claude-code.md](integrations/claude-code.md) |
| Cursor | [integrations/cursor.md](integrations/cursor.md) |
| Zed | [integrations/zed.md](integrations/zed.md) |

## More

- [FAQ](faq.md)
- [Contributing](contributing.md)
- [GitHub](https://github.com/xlreon/substrate)
- [Changelog](https://github.com/xlreon/substrate/blob/main/CHANGELOG.md)

---

## Design principles

1. **Files on disk are source-of-truth.** Every index, cache, dashboard is disposable and rebuildable from the markdown.
2. **Git is the history.** No custom audit log, no "version" frontmatter field.
3. **Boring formats.** Markdown + YAML frontmatter. No proprietary schema.
4. **Falsifiable retrieval.** `log_use` exists so you can prove (or disprove) that the store earns its keep.
5. **MCP-native, not MCP-only.** The CLI works offline, in a script, in a CI job. The MCP layer is an optional adapter.

---

MIT License · [Sidharth Satapathy](https://github.com/xlreon)
