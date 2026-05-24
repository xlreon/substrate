# Contributing to substrate

Thanks for considering a contribution. Substrate is small on purpose — fewer than 1,500 lines of Python — so the bar for new code is "does it earn its keep?" Patches that simplify or shrink the surface are especially welcome.

## Dev setup

```bash
git clone https://github.com/xlreon/substrate.git
cd substrate
uv sync --extra dev          # installs runtime + dev deps into .venv
uv run pytest -q             # run the full test suite (~2s)
uv run ruff check .          # lint
uv run mypy cli.py mcp_server.py  # types
```

Editable install for end-to-end testing:

```bash
uv tool install --editable .
substrate --help
```

Use a throwaway store while developing so you don't pollute your real one:

```bash
export SUBSTRATE_HOME=/tmp/substrate-dev
substrate init
substrate add "test bundle"
```

## What good contributions look like

**Welcome:**
- Bug fixes with a regression test
- Smaller code that does the same thing
- New CLI flags or MCP tools that solve a *real* documented use case (open an issue first)
- Docs, examples, integrations with other MCP-capable agents
- Cross-platform fixes (Windows clipboard, Linux `xclip`, etc.)

**Slow down:**
- New optional dependencies — each one needs a clear motivation
- Configurable behavior nobody asked for
- Network access, daemon processes, web UIs that need a server
- Schema changes to the bundle frontmatter — bring those to an issue with rationale

## Conventions

- Python 3.10+ syntax, type hints throughout
- `ruff` for formatting and linting (`uv run ruff format . && uv run ruff check .`)
- `mypy` clean on `cli.py` and `mcp_server.py`
- Tests: `pytest`, no asyncio unless the code under test is async
- One feature per PR, ~150 lines or fewer when possible
- Commit messages: `<area>: <imperative summary>` — areas are `cli`, `mcp`, `ui`, `docs`, `ci`, `deps`

## Architecture invariants (don't break these without a strong reason)

1. **Markdown files on disk are source-of-truth.** Indexes, caches, embeddings, dashboards must be disposable and rebuildable.
2. **No daemon, no database, no network.** The filesystem *is* the API.
3. **The CLI and the MCP server must work without each other.** Each is independently usable.
4. **Git is the history.** Don't invent a separate audit log or "version" frontmatter field.
5. **`SUBSTRATE_HOME` is honored everywhere.** Never hard-code `~/.substrate`.

## Releasing (maintainers)

1. Bump version in `pyproject.toml`
2. Add a `## [vX.Y.Z] - YYYY-MM-DD` block at the top of `CHANGELOG.md`
3. Open a PR titled `release: vX.Y.Z`
4. On merge, tag: `git tag vX.Y.Z && git push --tags`
5. GitHub Actions builds and publishes to PyPI

## Code of Conduct

By participating, you agree to abide by the [Code of Conduct](CODE_OF_CONDUCT.md).
