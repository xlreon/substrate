# Claude Code

Wire substrate into [Claude Code](https://docs.claude.com/en/docs/claude-code) so the CLI can search your bundles, fetch them by id, and follow pre-authored prompts.

## Install substrate

```bash
uv tool install substrate-kb
substrate init
```

This puts the `substrate` and `substrate-mcp` binaries on your PATH and initializes the bundle store at `~/.substrate/`.

## Add the MCP server to Claude Code

Claude Code reads MCP server definitions from your config. The fastest way:

```bash
claude mcp add substrate -- substrate-mcp
```

Verify:

```bash
claude mcp list
```

You should see `substrate` in the output. The server speaks stdio; Claude Code launches it as a subprocess per session.

If you prefer the JSON config form, edit `~/.claude.json` (or your platform-specific Claude Code config) and add:

```json
{
  "mcpServers": {
    "substrate": {
      "command": "substrate-mcp"
    }
  }
}
```

If `substrate-mcp` isn't on the PATH the agent process sees, point at the absolute path returned by `which substrate-mcp`.

## Confirm the agent can see it

Start a new Claude Code session and type:

```text
List the substrate bundles created today.
```

The agent should call `get_by_date` and return a list. If it instead says "I don't have a substrate tool," the server isn't registered — re-run `claude mcp list` and check the binary path.

## Teach the agent your workflow

The MCP server exposes the tools, but the agent doesn't know **when** to use them unless you say so. Add the following to your project `CLAUDE.md` (or your global one if you want substrate available everywhere):

```markdown
## substrate (knowledge bundle store)

You have MCP access to a substrate store. Use it whenever:

- The user references "my notes," "yesterday's handoff," or a date — call
  `get_by_date(date=<ISO date>)`.
- The user mentions a "playbook," "runbook," "rubric," or "template" — call
  `search_bundles` with the keywords. If a bundle with tag `prompt` or
  `playbook` matches, read it with `get_bundle` and follow it verbatim.
- The user references a specific bundle id (e.g. `2026-05-24-foo`) — call
  `get_bundle(id="2026-05-24-foo")` directly.
- You're about to make a decision that benefits from prior context — search
  for relevant tags before deciding.

After using a bundle, call `log_use(id=<id>, note=<short summary>)` so we can
measure which bundles earn their keep.
```

Drop this block in once. From that point on, the agent reaches for substrate without prompting.

## A first useful flow

### Capture a handoff at session end

When you're winding down a session and want continuity tomorrow:

```text
You: "Write a substrate handoff: we picked Fly.io over Render because of
Wireguard support, the new flag is FLY_MULTI_REGION, and the migration
runs Monday."
```

The agent should respond by drafting a bundle and giving you the `substrate add` command. Run it; the bundle is saved.

Or have the agent write directly via the filesystem:

```text
You: "Save that as a substrate bundle named 'handoff fly decision' tagged
handoff,deploy."
```

Either pattern works. The CLI option is more idiomatic; the direct-write option is more autonomous.

### Resume the next morning

```text
You: "Open my substrate handoff from yesterday and continue the deploy work."
```

The agent calls `get_by_date(date="2026-05-23", tag="handoff")`, reads the bundle, and resumes with the full reasoning chain in context.

### Trigger a pre-authored prompt

You have a bundle tagged `playbook,migration`:

```text
You: "Run the migration playbook on the new index addition."
```

The agent should search substrate, find the playbook, and follow it step by step. If it tries to improvise instead, your `CLAUDE.md` instructions are too soft — tighten the rule to "follow verbatim, do not improvise around the steps."

## Slash command shortcut

If you have a slash-command plugin in your Claude Code setup, you can wire a single command that always pulls from substrate:

```yaml
# in your slash-command file
name: handoff
description: Open today's handoff bundle and resume work
prompt: |
  Call substrate.get_by_date with today's date and tag "handoff". Read the
  most recent matching bundle and summarize what to do next.
```

Now `/handoff` boots a session into the right context in one keystroke.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `substrate-mcp` not found | Not on PATH for the Claude Code process | Use the absolute path in MCP config |
| Agent returns "no tool named search_bundles" | Server registered but never started | Check stderr of `substrate-mcp` manually; look for Python import errors |
| Agent never uses substrate | No rule in `CLAUDE.md` | Add the workflow block above |
| Search returns nothing | Tags don't match | Try `substrate list --tag <tag>` on the CLI to confirm tagging |
| `log_use` fails silently | `usage.log` write permissions | Check `ls -la ~/.substrate/usage.log` — should be writable by your user |

## Advanced: project-scoped stores

By default, the MCP server reads `~/.substrate/`. To run a project-local store, point `SUBSTRATE_HOME` at a project directory and add a project-specific MCP config:

```json
{
  "mcpServers": {
    "substrate-project": {
      "command": "substrate-mcp",
      "env": {
        "SUBSTRATE_HOME": "./project-substrate"
      }
    }
  }
}
```

Now Claude Code reads from `./project-substrate/` for this project and `~/.substrate/` for everything else. You can register both servers side-by-side under different names.

## Further reading

- [Pre-authored prompts](../pre-authored-prompts.md) — the killer use case
- [Use cases](../use-cases.md) — why this matters
- [Dashboard](../dashboard.md) — visualize what's in your store
