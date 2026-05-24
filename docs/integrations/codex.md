# Codex CLI

Wire substrate into the [Codex CLI](https://github.com/openai/codex) so its agent can search and read your bundles over MCP.

## Install substrate

```bash
uv tool install substrate-kb
substrate init
```

## Add the MCP server

Codex CLI reads MCP server definitions from `~/.codex/config.toml`. Add an `mcp_servers` entry:

```toml
[mcp_servers.substrate]
command = "substrate-mcp"
args = []
```

If `substrate-mcp` isn't on the Codex process PATH, use the absolute path returned by `which substrate-mcp`.

For a project-scoped store:

```toml
[mcp_servers.substrate-project]
command = "substrate-mcp"
args = []
env = { SUBSTRATE_HOME = "./.substrate" }
```

## Confirm it's running

Start a Codex session and ask:

```text
Use substrate to list today's bundles.
```

The agent should call `get_by_date` with today's ISO date and return a list. If it claims the tool doesn't exist, double-check the TOML keys and restart the session.

## Teach the agent

Codex CLI honors `AGENTS.md` at the repo root (and the user-global `~/.codex/AGENTS.md`). Add:

```markdown
## substrate

Use the substrate MCP server when:

- The user references past notes or a date → `get_by_date`
- The user mentions a playbook/runbook/rubric → `search_bundles`, then
  `get_bundle` and follow the body verbatim
- The user gives a bundle id → `get_bundle`

After using a bundle, call `log_use(id=..., note=...)`.
```

## Further reading

- [Claude Code integration](claude-code.md) — same patterns, fuller treatment
- [Pre-authored prompts](../pre-authored-prompts.md)
