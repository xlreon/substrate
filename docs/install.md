# Install

## Requirements

- **Python 3.10+** (3.12 recommended)
- **Git** (substrate uses it for automatic version history)
- **macOS or Linux** (Windows is experimental — see [FAQ](faq.md))

## Option 1: uv tool (recommended)

```bash
uv tool install substrate-kb
```

This installs the `substrate` and `substrate-mcp` commands into an isolated environment managed by [uv](https://docs.astral.sh/uv/).

## Option 2: pipx

```bash
pipx install substrate-kb
```

Same result, different tool. Use whichever you already have.

## Option 3: From source (editable)

```bash
git clone https://github.com/xlreon/substrate.git
cd substrate
uv tool install --editable .
```

Editable installs let you modify the source and see changes immediately — useful for contributors.

## Option 4: Directly from git

```bash
uv tool install git+https://github.com/xlreon/substrate
```

Pulls the latest `main` without cloning locally. Good for one-off installs on remote machines.

## Verify the install

```bash
substrate --help
```

You should see the top-level help with commands like `init`, `add`, `list`, `search`, `get`, `ui`, etc.

```
Usage: substrate [OPTIONS] COMMAND [ARGS]...

  Local prompt+context bundles with versioning.

Commands:
  init     Initialize ~/.substrate as a versioned bundle store.
  add      Create a new bundle in today's folder and open it in $EDITOR.
  list     List bundles, optionally filtered by tag or date.
  search   Find bundles by substring match across id, tags, and body.
  get      Print a bundle to stdout (pipe-friendly).
  use      Copy a bundle to clipboard (without frontmatter) and log the use.
  log      Show usage log. This is the falsifiable metric.
  edit     Edit an existing bundle.
  history  git log for a specific bundle.
  ui       Generate a static HTML dashboard.
```

## Initialize the store

Run this once to create the bundle store:

```bash
substrate init
```

This creates `~/.substrate/`, git-inits it, and you're ready to go.

## Changing the store location

By default, bundles live in `~/.substrate/bundles/`. Set `SUBSTRATE_HOME` to move the store anywhere:

```bash
# Shared team folder
export SUBSTRATE_HOME=/opt/team-substrate

# Synced via Dropbox
export SUBSTRATE_HOME=~/Dropbox/substrate

# Project-local store
export SUBSTRATE_HOME=./project-substrate
```

Add this to your shell profile (`~/.zshrc`, `~/.bashrc`) so it persists across sessions. Substrate honors `SUBSTRATE_HOME` everywhere — CLI, MCP server, and dashboard.

After setting a new `SUBSTRATE_HOME`, run `substrate init` again to initialize that location.

## Next steps

→ [Quickstart](quickstart.md) — 5-minute walkthrough  
→ [Claude Code setup](integrations/claude-code.md) — wire up the MCP server
