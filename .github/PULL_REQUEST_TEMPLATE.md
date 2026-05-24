## What

<!-- One-line summary. -->

## Why

<!-- The motivation. Link to an issue if applicable. -->

## How

<!-- Brief overview of the approach. Highlight any design decisions. -->

## Verification

- [ ] `uv run pytest -q` passes
- [ ] `uv run ruff check .` is clean
- [ ] `uv run ruff format --check .` is clean
- [ ] `uv run mypy cli.py mcp_server.py` is clean
- [ ] Manual test of the affected command (`substrate <cmd>`)

## Architecture invariants

- [ ] Files on disk remain source-of-truth
- [ ] No new daemon, database, or network dependency
- [ ] CLI and MCP server still work without each other
- [ ] `SUBSTRATE_HOME` is honored throughout
