# Zed

Wire substrate into [Zed](https://zed.dev) so the Assistant panel can call into your bundle store via MCP.

## Install substrate

```bash
uv tool install substrate-kb
substrate init
```

## Add the MCP server

Zed reads MCP servers from your `settings.json` (open it with `cmd-,` → "Open Settings"). Add the `context_servers` block:

```json
{
  "context_servers": {
    "substrate": {
      "command": {
        "path": "substrate-mcp",
        "args": [],
        "env": {}
      }
    }
  }
}
```

If `substrate-mcp` isn't on Zed's PATH, use the absolute path from `which substrate-mcp`.

Save the settings file. Zed should pick up the server within a few seconds; otherwise restart.

## Confirm it's running

Open the Assistant panel (`cmd-?`) and look at the context-servers indicator. You should see `substrate` listed as active, with five tools.

Ask the assistant:

```text
Use substrate to list the bundles I created this week.
```

It should call `list_bundles` and return results.

## Teach the agent

Zed's Assistant honors instructions from the system message. Either set a global rule in your settings:

```json
{
  "assistant": {
    "default_model": { /* ... */ },
    "system_message": "You have access to substrate via MCP. When the user references playbooks, runbooks, or past notes, search substrate first. Follow matching prompt bundles verbatim. After using a bundle, call log_use."
  }
}
```

Or write the instruction directly in the conversation each time. Setting it globally is the lower-friction option.

## Project-scoped store

Set `SUBSTRATE_HOME` in the server's `env` block to point at a project-local store:

```json
{
  "context_servers": {
    "substrate-project": {
      "command": {
        "path": "substrate-mcp",
        "args": [],
        "env": { "SUBSTRATE_HOME": "./.substrate" }
      }
    }
  }
}
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| Server not listed | Check JSON syntax in `settings.json` |
| Server listed but inactive | Check Zed's log: `tail -f ~/Library/Logs/Zed/Zed.log` (macOS) |
| Tools call but return errors | Run `substrate-mcp` manually; check stderr |

## Further reading

- [Pre-authored prompts](../pre-authored-prompts.md)
- [Use cases](../use-cases.md)
