# Concepts

## What is a bundle?

A bundle is a markdown file with YAML frontmatter. That's it — no binary format, no database row, no opaque blob. You can open it in any text editor, `grep` it, `diff` it, or pipe it through `jq` after stripping the frontmatter.

Bundles are the atomic unit of knowledge in substrate. Each one captures a single piece of context: a handoff note, a convention, a prompt template, a debugging runbook, a decision record.

## Frontmatter schema

Every bundle starts with a YAML frontmatter block:

```yaml
---
id: 2026-05-24-deploy-staging-landmines
created: 2026-05-24T19:30:00+05:30
tags: [deployment, fly, gotcha]
context_refs: []
---
```

| Field | Type | Description |
|---|---|---|
| `id` | `string` | Unique identifier. Format: `YYYY-MM-DD-slug`. |
| `created` | `ISO 8601 datetime` | When the bundle was created (with timezone). |
| `tags` | `list[string]` | Freeform tags for filtering and discovery. |
| `context_refs` | `list[string]` | Optional references to other bundles or external resources. |

The frontmatter is parsed by both the CLI and the MCP server. Agents use `id` and `tags` for lookup; `context_refs` is available for linking related bundles but is not indexed today.

## Store layout

```
~/.substrate/              ← SUBSTRATE_HOME (configurable)
├── .git/                  ← automatic git repo
├── .gitignore             ← excludes usage.log from git
├── bundles/
│   ├── 2026-05-23/
│   │   └── convention-error-handling.md
│   └── 2026-05-24/
│       ├── handoff-deploy-staging.md
│       └── prompt-bug-triage-template.md
└── usage.log              ← append-only TSV (not git-tracked)
```

Bundles are organized by creation date under `bundles/YYYY-MM-DD/`. The date folder is determined by when `substrate add` runs. The file name is the slug portion of the bundle id.

## ID rules

Bundle IDs follow the format `YYYY-MM-DD-slug`:

- **Date prefix:** The date the bundle was created (`2026-05-24`)
- **Slug:** The name you pass to `substrate add`, lowercased, with non-alphanumeric characters replaced by hyphens

Examples:

| Name argument | Resulting ID |
|---|---|
| `"deploy staging landmines"` | `2026-05-24-deploy-staging-landmines` |
| `"Fix: asyncpg SSL"` | `2026-05-24-fix-asyncpg-ssl` |
| `"prompt-bug-triage-template"` | `2026-05-24-prompt-bug-triage-template` |

IDs are globally unique because of the date prefix. They're also human-readable and `grep`-friendly.

## Git versioning model

Substrate uses git as its history layer. No custom audit log, no "version" field in frontmatter.

- `substrate init` runs `git init -b main` inside `SUBSTRATE_HOME`
- `substrate add` commits after you save and exit your editor
- `substrate edit` commits after you save and exit your editor
- Every commit message follows `add <bundle-id>` or `edit <bundle-id>`

Check the history of any bundle:

```bash
substrate history 2026-05-24-deploy-staging-landmines
```

This runs `git log` scoped to that bundle's file. You get standard git diffs, blame, and all the tools you already know.

To back up your store, add a remote and push:

```bash
cd ~/.substrate
git remote add origin <your-private-repo-url>
git push -u origin main
```

## Usage log

`~/.substrate/usage.log` is an append-only TSV file that records every time a bundle is used. It is **not** tracked by git (listed in `.gitignore`).

Format:

```
<ISO-8601-timestamp>\t<bundle-id>\t<note>
```

Example:

```
2026-05-24T19:45:00+05:30	2026-05-24-deploy-staging-landmines	PR #42
2026-05-24T20:10:00+05:30	2026-05-23-convention-error-handling	[claude-code] retry logic
```

Usage is logged by:
- `substrate use <id>` (CLI — also copies body to clipboard)
- `log_use` (MCP tool — called by agents)

The log is the falsifiable retrieval metric: it lets you prove which bundles are actually being used and which are shelf-ware.

View it with:

```bash
substrate log
substrate log --since 2026-05-20
```

## Further reading

- [Quickstart](quickstart.md) — hands-on walkthrough
- [Use cases](use-cases.md) — why this architecture
- [SPEC.md](https://github.com/xlreon/substrate/blob/main/SPEC.md) — full design specification
