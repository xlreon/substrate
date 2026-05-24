# Cursor

Wire substrate into [Cursor](https://cursor.com) so the AI side panel and agent mode can read your bundles via MCP.

## Install substrate

```bash
uv tool install substrate-kb
substrate init
```

## Add the MCP server

Cursor reads MCP server definitions from `~/.cursor/mcp.json` (or workspace `.cursor/mcp.json` for project-scoped servers). Open it and add:

```json
{
  "mcpServers": {
    "substrate": {
      "command": "substrate-mcp"
    }
  }
}
```

If `substrate-mcp` isn't on Cursor's PATH (often the case with `uv tool` installs), use the absolute path:

```bash
which substrate-mcp
# /Users/you/.local/bin/substrate-mcp
```

```json
{
  "mcpServers": {
    "substrate": {
      "command": "/Users/you/.local/bin/substrate-mcp"
    }
  }
}
```

Restart Cursor. Open the MCP panel (Settings → MCP) and confirm `substrate` shows as running with five tools listed: `list_bundles`, `get_bundle`, `search_bundles`, `get_by_date`, `log_use`.

## Teach the agent

Cursor honors `.cursorrules` (legacy) and `AGENTS.md` (newer). Add the substrate workflow rule to whichever you use:

```markdown
## substrate

You have access to a substrate knowledge store via MCP. When the user mentions:

- "my notes" or a date → call `get_by_date`
- a "playbook," "rubric," "template" → call `search_bundles` and follow the
  matching bundle verbatim
- a bundle id (e.g. `2026-05-24-foo`) → call `get_bundle` directly

After using a bundle, call `log_use(id=..., note=...)`.
```

## Project-scoped store

To use a different bundle store per project, set `SUBSTRATE_HOME` in your workspace MCP config:

```json
// .cursor/mcp.json (committed to your repo if shared with the team)
{
  "mcpServers": {
    "substrate-project": {
      "command": "substrate-mcp",
      "env": {
        "SUBSTRATE_HOME": "./.substrate"
      }
    }
  }
}
```

Now this workspace reads from `./substrate/` instead of `~/.substrate/`. Useful for team-shared bundles checked into the repo.

## Troubleshooting

| Symptom | Fix |
|---|---|
| MCP panel shows "failed" | Run `substrate-mcp` manually in a terminal; look for import errors |
| Tools don't appear | Server name in config doesn't match what Cursor expects — restart Cursor |
| Search returns nothing | Try `substrate list` on the CLI to confirm bundles exist |
| Agent ignores substrate | Add the workflow block to `.cursorrules` or `AGENTS.md` |

## Further reading

- [Pre-authored prompts](../pre-authored-prompts.md)
- [Use cases](../use-cases.md)
