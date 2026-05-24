# Quickstart

Five minutes from install to your first bundle in the dashboard.

## 1. Initialize the store

```bash
substrate init
```

```
initialized: /Users/you/.substrate
```

This creates `~/.substrate/`, git-inits it, and sets up the bundle directory structure.

## 2. Add your first bundle

```bash
substrate add "my first bundle" --tag example --tag getting-started
```

Your `$EDITOR` opens with a pre-filled template:

```markdown
---
id: 2026-05-24-my-first-bundle
created: 2026-05-24T19:30:00+05:30
tags: [example, getting-started]
context_refs: []
---

# Prompt

<write your prompt here>

# Context

<paste files, graph queries, or notes here>
```

Write something, save, and quit your editor. Substrate commits the file to git automatically.

```
saved: 2026-05-24-my-first-bundle
```

## 3. List your bundles

```bash
substrate list
```

```
┌──────────────────────────────┬──────────────────────────┬──────────────────────────────────┐
│ id                           │ tags                     │ path                             │
├──────────────────────────────┼──────────────────────────┼──────────────────────────────────┤
│ 2026-05-24-my-first-bundle   │ example, getting-started │ 2026-05-24/my-first-bundle.md    │
└──────────────────────────────┴──────────────────────────┴──────────────────────────────────┘
```

Filter by tag:

```bash
substrate list --tag example
```

## 4. Search for bundles

```bash
substrate search "example"
```

```
1 match(es)
┌──────────────────────────────┬──────────────────────────┬───────────────────┐
│ id                           │ tags                     │ match             │
├──────────────────────────────┼──────────────────────────┼───────────────────┤
│ 2026-05-24-my-first-bundle   │ example, getting-started │ example           │
└──────────────────────────────┴──────────────────────────┴───────────────────┘
```

Search is case-insensitive and matches across id, tags, and body text.

## 5. Read a bundle

```bash
substrate get 2026-05-24-my-first-bundle
```

This prints the full bundle (including frontmatter) to stdout. Pipe it anywhere:

```bash
# Copy to clipboard (macOS)
substrate get 2026-05-24-my-first-bundle | pbcopy

# Pipe to another tool
substrate get 2026-05-24-my-first-bundle | bat -l md
```

Or use `substrate use` to copy the body (without frontmatter) and log the retrieval:

```bash
substrate use 2026-05-24-my-first-bundle
```

```
copied: 2026-05-24-my-first-bundle
```

## 6. Open the dashboard

```bash
substrate ui --open
```

This generates a single self-contained HTML file and opens it in your browser. You'll see:

- A 4-stat overview (total bundles, this week, today, last activity)
- A 30-day activity bar chart
- Your bundles in a day-grouped timeline
- A **+ New bundle** button to draft bundles from the browser

## What's next?

| Topic | Link |
|---|---|
| Wire up Claude Code / Cursor / Zed | [integrations/](integrations/claude-code.md) |
| Understand the bundle format | [concepts.md](concepts.md) |
| Pre-authored prompt templates | [pre-authored-prompts.md](pre-authored-prompts.md) |
| Why substrate exists | [use-cases.md](use-cases.md) |
