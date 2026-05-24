# FAQ

## Installation

### Does substrate work on Windows?

Partially. The CLI runs on Python 3.10+, which is available on Windows. Two integrations are stubbed:

- **Clipboard** (`substrate use` copies bundle body to clipboard). Today it shells out to `pbcopy` (macOS). On Windows it would need `clip.exe`; on Linux, `xclip` or `wl-copy`. PRs welcome — see [GitHub Issues](https://github.com/xlreon/substrate/issues).
- **Editor invocation** (`substrate add` and `substrate edit` open `$EDITOR`). Works on Windows if `$EDITOR` is set, but the default fallback is `vi` which assumes a POSIX shell.

Day-to-day reading (`list`, `search`, `get`, `ui`) works fine on Windows.

### Why is the PyPI package `substrate-kb` instead of `substrate`?

The bare name `substrate` was taken by an unrelated package (a Polkadot blockchain SDK helper). To avoid confusion, the PyPI package is `substrate-kb` ("knowledge base"). The CLI command stays `substrate` — only the install command changes.

### Can I run substrate without `uv`?

Yes. Use `pipx` (`pipx install substrate-kb`) or a plain `pip install substrate-kb` inside a venv. `uv` is recommended because it handles the isolated environment for you, but it's not required.

---

## Architecture & data model

### Why YAML frontmatter, not JSON or TOML?

Three reasons:

1. **It's already the convention** for Jekyll, Hugo, Obsidian, and most static-site generators. Tooling exists.
2. **Humans read and edit it without flinching.** Compare `tags: [deploy, fly]` to `"tags": ["deploy", "fly"]`.
3. **Markdown viewers ignore it gracefully.** GitHub renders the file as markdown with the frontmatter as a small table. JSON or TOML wouldn't render.

### Why isn't `usage.log` git-tracked?

Usage is high-churn (every fetch appends a line) and machine-local (different machines fetch different bundles). Committing it would create constant noise, merge conflicts, and leak retrieval patterns through git history.

The bundles are the canonical state; usage is a side-channel signal for the falsifiable-retrieval metric.

### Can multiple machines share one substrate store?

Yes, three ways:

1. **Sync the directory.** Point `SUBSTRATE_HOME` at a Dropbox / iCloud / Syncthing folder.
2. **Git push/pull.** Add a remote inside `~/.substrate/` and treat it like a normal repo.
3. **Shared filesystem.** Set `SUBSTRATE_HOME=/mnt/team-substrate` on every machine.

Option 2 is the most predictable — git's conflict semantics give you explicit merge resolution instead of file-sync surprises.

### What happens if two agents write to the same bundle id at once?

Both write succeed; the later one wins on disk. The git commit history preserves both versions. If you're worried about it, use unique slugs — `handoff-deploy-frontend.md` and `handoff-deploy-backend.md` instead of two writers racing for `handoff-deploy.md`.

---

## Comparison with other tools

### How is this different from mem0 / Letta / Zep?

| | Substrate | mem0 / Letta / Zep |
|---|---|---|
| Storage | Markdown on disk | Vector DB |
| Retrieval | Exact-id, substring, tag | Embedding similarity |
| Audit | `git log` | Vendor-specific dashboard |
| Lock-in | None | Service or vendor-specific format |
| Offline | Yes | Usually no |

Substrate is for *deliberate* knowledge that you author. Vector-memory tools are for *automatic* knowledge they extract from conversations. Different jobs.

### How is this different from CLAUDE.md?

CLAUDE.md is loaded into every session, always. Substrate is loaded on demand by tag, id, or date. Use CLAUDE.md for rules that should apply universally; use substrate for context that's relevant *sometimes*.

You can use both. The README's example setup does.

### How is this different from Obsidian or Notion?

Obsidian and Notion are human-shaped: built for browsing, clicking, manual organization. Substrate is agent-shaped: bundles are addressable by id, searchable by tag, fetched programmatically. You *can* read substrate bundles in Obsidian (point Obsidian at `~/.substrate/bundles/`), but the workflows don't overlap much.

### Why not just use a folder of markdown files?

That's exactly what substrate is — plus a CLI, an MCP server, a usage log, a dashboard, and a few conventions. If you only need the folder, skip substrate. If you want agents to retrieve from it, you'd end up reinventing the rest.

---

## Privacy & security

### Does substrate phone home?

No. There is no telemetry, no analytics, no network call from the CLI or the MCP server. The dashboard is a static HTML file. Substrate has no remote infrastructure.

### Where do my bundles live?

By default, `~/.substrate/`. If you set `SUBSTRATE_HOME`, they live wherever you point it.

### Should I commit `~/.substrate/` to a public repo?

Only if you're comfortable making the contents public. Bundles may include project context, decision history, or names — review before pushing. A private repo is a safer default.

### Can I encrypt my bundles?

Substrate doesn't encrypt at rest. If you need encryption:

- Use full-disk encryption (FileVault, LUKS, BitLocker).
- Put `SUBSTRATE_HOME` inside an encrypted volume (a Veracrypt container, a `git-crypt`-protected repo).
- Or set `SUBSTRATE_HOME` to a directory inside an encrypted filesystem you mount on demand.

### What about secrets in bundles?

Don't put secrets in bundles. The `usage.log` is gitignored but the bundles themselves aren't — they travel anywhere your store travels.

---

## Workflows

### Should every bundle have a date prefix?

Yes — substrate enforces it. Bundles live under `bundles/YYYY-MM-DD/` and their id is `YYYY-MM-DD-slug`. This gives you free temporal ordering and `get_by_date` for cheap.

### Can I move a bundle to a different date?

Yes. Move the file from `bundles/2026-05-23/foo.md` to `bundles/2026-05-24/foo.md` and update the `id:` field in the frontmatter. Commit the move; `git mv` preserves history.

This is unusual — bundles are usually pinned to the date they were authored — but useful if you discover a bundle was misdated.

### How many tags should a bundle have?

Two to five is the sweet spot. One tag is too generic to be useful for filtering; six is usually a sign you're mixing concepts and should split the bundle.

### What's a good slug?

A slug should be:

- **Short** — under 40 characters.
- **Descriptive** — `handoff-deploy-staging` beats `notes-from-tuesday`.
- **Action- or topic-shaped** — `prompt-pr-review`, `gotcha-asyncpg-ssl`, `decision-fly-over-render`.

Substrate lowercases the slug and replaces non-alphanumerics with hyphens.

---

## Operations

### How big can the store get?

Tested with ~1000 bundles, no issues. The dashboard generation walks the filesystem each time, so very large stores (10K+) may start to feel slow on `substrate ui` — the underlying CLI commands stay fast because they're substring/tag based.

### Can I export my bundles?

They're already exported — they're plain markdown files on disk. Zip the `bundles/` directory if you need a single artifact. No proprietary format, no vendor lock-in.

### How do I delete a bundle?

```bash
rm ~/.substrate/bundles/2026-05-24/foo.md
cd ~/.substrate && git add -A && git commit -m "remove 2026-05-24-foo"
```

Or use `substrate` if/when a `remove` subcommand is added (PRs welcome).

The git history still has the bundle. To truly remove it, you'd need `git filter-repo` or `git rebase`, which is rarely worth it.

---

## Contributing

### How do I contribute?

See [Contributing](contributing.md) and the repo's [CONTRIBUTING.md](https://github.com/xlreon/substrate/blob/main/CONTRIBUTING.md). PRs that add a new MCP host integration, fix Windows compatibility, or improve the dashboard are especially welcome.

### Where do I report bugs?

[GitHub Issues](https://github.com/xlreon/substrate/issues). Please include OS, Python version, and a minimal reproduction.

### Where do I propose new features?

Open an issue with the `enhancement` label, or start a [GitHub Discussion](https://github.com/xlreon/substrate/discussions) for early-stage ideas.
