# Dashboard

`substrate ui` generates a single self-contained HTML file that you open in any browser. No server, no build step, no JavaScript framework. The file is regenerated from your filesystem on demand.

```bash
substrate ui --open
```

The `--open` flag launches your default browser. Without it, the file is written to `~/.substrate/index.html` and you can open it manually.

---

## What's in the dashboard

The dashboard has six panels, laid out as a left sidebar + main timeline.

### 1. Stats overview

Four numbers at the top:

| Stat | Meaning |
|---|---|
| **Total bundles** | Every markdown file under `bundles/`. |
| **This week** | Bundles created in the last 7 days. |
| **Today** | Bundles created today. |
| **Last activity** | Relative timestamp of the most recent bundle. |

Useful for spotting flat weeks — if "this week" is 0, the store is shelfware.

### 2. 30-day activity chart

An inline SVG bar chart showing bundle creation per day for the last 30 days. Empty days are zero bars. Hover a bar to see the date and count.

The chart is recomputed every time you run `substrate ui`. There's no caching; bars reflect whatever is on disk right now.

### 3. Most-referenced leaderboard

A "hot list" of bundles ranked by a weighted score:

```
score = mentions_in_active_files * 4
      + git_commits_touching_bundle * 1
      + log_use_invocations * 2
      + 8 if currently_active else 0
```

- **mentions:** `grep` count across `MEMORY.md` (or whatever file `SUBSTRATE_ACTIVE_FILE` points to).
- **git commits:** Number of commits in the substrate repo that touched the bundle file.
- **log_use invocations:** Reads from `usage.log`.
- **currently active:** The single bundle marked as ACTIVE (see below).

The leaderboard is your falsifiable metric: bundles at the top earn their keep; bundles at the bottom might be shelf-ware.

### 4. Tag filter chips

A row of clickable tags. Click one and the timeline below filters to bundles with that tag. Click again to clear. The chips are alphabetically sorted; the count of bundles per tag is shown in parentheses.

### 5. Day-grouped timeline

The main panel. Bundles are grouped by creation date (the date folder under `bundles/`), with sticky day headers as you scroll. Each card shows:

- Bundle id (linked — click to open the markdown file)
- Created timestamp (e.g. "today", "2 days ago")
- Tags
- A preview of the body (first ~200 chars)
- A small "active" badge if this bundle is the current ACTIVE bundle

The cards collapse the body by default; click to expand and read inline.

### 6. + New bundle modal

A floating button (bottom-right) opens a `<dialog>` modal where you can:

1. Type a slug.
2. Add comma-separated tags.
3. Paste a body.

The modal generates a copy-paste-able bash heredoc that creates the file, commits it, and regenerates the dashboard:

```bash
mkdir -p ~/.substrate/bundles/2026-05-24 && cat > ~/.substrate/bundles/2026-05-24/my-new-bundle.md <<'EOF'
---
id: 2026-05-24-my-new-bundle
created: 2026-05-24T20:30:00+05:30
tags: [example]
context_refs: []
---

(your body)
EOF
cd ~/.substrate && git add bundles/2026-05-24/my-new-bundle.md && git commit -m "add 2026-05-24-my-new-bundle"
substrate ui
```

This pattern means the dashboard can be opened from any machine (synced via Dropbox, git, or sneakernet) and the "add" workflow still works without server infrastructure.

---

## Active bundle marker

The dashboard highlights one bundle as "currently active" — the bundle your agents should treat as primary context this session.

To mark a bundle active, point `SUBSTRATE_ACTIVE_FILE` at a markdown file that contains a line like:

```text
ACTIVE BUNDLE: bundles/2026-05-24/handoff-deploy-staging.md
```

Substrate parses that file on `substrate ui`, finds the marker, and shows the matching bundle with an "active" badge plus the +8 hotness bonus.

The marker text is configurable via `SUBSTRATE_ACTIVE_MARKER` (defaults to `ACTIVE BUNDLE`).

Typical setup:

```bash
# in ~/.zshrc
export SUBSTRATE_ACTIVE_FILE=~/notes/MEMORY.md
```

Edit `~/notes/MEMORY.md` to change which bundle is active. The dashboard updates on the next `substrate ui` run.

---

## How it's built

The dashboard is **deliberately boring**:

- A single Python function in `cli.py` walks `bundles/`, parses frontmatter with `pyyaml`, renders bodies with `markdown-it-py`.
- Output is a single HTML file with inline CSS and inline JS.
- Charts are inline `<svg>` — no Chart.js, no D3.
- The modal is a native `<dialog>` element. No React, no Vue, no framework.
- `prefers-reduced-motion` is respected.

If you don't like the styling, fork it. The whole renderer is ~600 lines of Python.

---

## Regenerating

The dashboard is a snapshot. Regenerate whenever you want to refresh:

```bash
substrate ui          # write to ~/.substrate/index.html
substrate ui --open   # write and open in browser
```

There's no watch mode. If you want auto-refresh, wrap it:

```bash
# refresh every 5 minutes
while true; do substrate ui; sleep 300; done
```

Or trigger from a git hook in your substrate store:

```bash
# ~/.substrate/.git/hooks/post-commit
substrate ui
```

---

## Sharing the dashboard

The generated `index.html` is fully self-contained — drop it on any web host and it works:

- Cloudflare Pages, Vercel, Netlify (static)
- A `python -m http.server` over Tailscale to a teammate
- An S3 bucket with a Cloudfront distribution
- An attachment in an email

Bundles are referenced by relative path inside the HTML; if you want links to open the actual markdown files, host the `bundles/` directory alongside `index.html`.

---

## Privacy

The dashboard reads only your local filesystem. There is no telemetry, no network call, no analytics — just `Read` operations against `~/.substrate/`. If you trust the substrate CLI binary, you can trust the dashboard.

If you commit the substrate store to a remote git repo, your bundles travel with it. The dashboard does not change that surface — it only renders what's already on disk.

---

## Further reading

- [Quickstart](quickstart.md) — generate your first dashboard
- [Concepts](concepts.md) — how active-bundle resolution works
- [Use cases](use-cases.md) — why the hotness score is the falsifiable metric
