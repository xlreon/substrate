# Contributing

Substrate is MIT-licensed and runs on community contributions. Issues, PRs, integration guides, and bundle-pack ideas are all welcome.

The full contributor reference lives at [CONTRIBUTING.md](https://github.com/xlreon/substrate/blob/main/CONTRIBUTING.md) in the repo root. This page is the short version.

## Quick start

```bash
git clone https://github.com/xlreon/substrate.git
cd substrate
uv sync --all-extras
uv run pytest -q
uv run ruff check .
uv run mypy .
```

If all four commands pass, you're set up.

## What's most useful

The roadmap is short and explicit:

1. **Windows clipboard support.** Today `substrate use` shells out to `pbcopy`. Linux needs `xclip`/`wl-copy`; Windows needs `clip.exe`. Touches one function in `cli.py`.
2. **More host integrations.** Confirmed configs for Continue, Cody, Windsurf, Claude Desktop — short docs page + test session.
3. **A `remove` subcommand.** Delete a bundle and its history hygienically.
4. **Bundle packs.** Community-curated starter bundles for common workflows (PR review, migrations, releases).
5. **Watch mode for the dashboard.** Auto-regenerate on filesystem changes.

If you want to take one of these, open an issue first so we don't duplicate work.

## Design invariants

These are non-negotiable; PRs that violate them will be asked to revise:

1. **Files on disk are source-of-truth.** No new state that doesn't live on the filesystem.
2. **Git is the history.** No custom version field, no audit log.
3. **No daemons.** Everything must work as a one-shot CLI invocation.
4. **MCP is one of many adapters.** The CLI must work offline, scriptable, without the MCP server running.
5. **YAML frontmatter format stays stable.** Adding fields is fine; renaming or removing fields needs a migration path.

## Style

- Python 3.10+. We use ruff for lint/format and mypy for typing.
- Keep CLI subcommands surgical — each does one thing.
- Tests live next to the code; pytest discovers them automatically.

## Releasing

Maintainer-only — see [CONTRIBUTING.md](https://github.com/xlreon/substrate/blob/main/CONTRIBUTING.md) in the repo for the full release flow.

## Communication

- [GitHub Issues](https://github.com/xlreon/substrate/issues) for bugs and feature requests
- [GitHub Discussions](https://github.com/xlreon/substrate/discussions) for design conversations
- PRs welcome on `main`

If you ship something with substrate that you're proud of, let us know — we'd love to link to it.
