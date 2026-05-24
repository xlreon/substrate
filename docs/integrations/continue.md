# Continue

Wire substrate into [Continue](https://continue.dev) (VS Code / JetBrains extension) so the chat panel can pull bundles via MCP.

## Install substrate

```bash
uv tool install substrate-kb
substrate init
```

## Add the MCP server

Continue reads MCP servers from `~/.continue/config.yaml` (or the legacy `config.json`). Add:

```yaml
mcpServers:
  - name: substrate
    command: substrate-mcp
```

If the binary isn't on Continue's PATH, use the absolute path from `which substrate-mcp`.

For a project-scoped store:

```yaml
mcpServers:
  - name: substrate-project
    command: substrate-mcp
    env:
      SUBSTRATE_HOME: ./.substrate
```

Reload the Continue extension (Command Palette → "Continue: Reload"). The substrate server should appear in the MCP indicator.

## Teach the agent

Continue uses system messages defined in your config. Add a rule:

```yaml
systemMessage: |
  You have access to substrate via MCP. When the user references past notes,
  playbooks, or specific bundle ids, search substrate first. Follow matching
  prompt bundles verbatim. After using one, call log_use.
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| Server not loaded | Check `~/.continue/config.yaml` syntax |
| Tool calls error | Run `substrate-mcp` manually; check stderr |
| Tools listed but never called | Add the system-message rule above |

## Further reading

- [Claude Code integration](claude-code.md) — fuller workflow reference
- [Pre-authored prompts](../pre-authored-prompts.md)
