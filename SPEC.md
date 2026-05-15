# Substrate — Technical Specification

**Version:** 0.1 (v0 shipped May 11, 2026)
**Status:** Trial week active. **Gate 0 = Friday May 15, 6 PM IST.**
**Authoritative companion docs:** [`one-pager.md`](./one-pager.md), [`cli.py`](./cli.py)

> Substrate is a local-first prompt+context bundle library with git-backed versioning. v0 ships as a CLI; v1.0 adds an MCP server that exposes the bundle store to any MCP-aware AI client. This document specifies the full system through enterprise (v4), with each phase gated on a falsifiable success criterion.

## TL;DR

- **Shipped (v0):** CLI with `init / add / list / get / use / log / edit / history`. Stores markdown bundles with YAML frontmatter under `~/.substrate/bundles/YYYY-MM-DD/`. Git-versioned. Append-only usage log = falsifiable metric.
- **Next (v1.0, conditional Wed May 13):** MCP server over stdio exposing `list_bundles / get_bundle / search_bundles / get_by_date / log_use`. Installed in Claude Code, Cursor, Zed via one config line.
- **Hard gate:** Substrate's continued existence depends on Gate 0 passing on Friday May 15, 6 PM IST. ≥5 `substrate use` entries with notes mapping to real shipped artifacts (Guvio PR, blog draft, day-job RFC/PR). FAIL → archive Saturday morning.
- **Architecture invariant:** Markdown files on disk are source-of-truth. Every index, every cache, every embedding is disposable and rebuildable.

## Section Index

1. [Architecture & Data Model](#1-architecture--data-model)
2. [CLI Surface](#2-cli-surface)
3. [MCP Server](#3-mcp-server)
4. [Search, Retrieval, and Indexing](#4-search-retrieval-and-indexing)
5. [Testing & Verification](#5-testing--verification)
6. [Roadmap, Gates, and Risks](#6-roadmap-gates-and-risks)

---

## 1. Architecture & Data Model

Substrate is a **local-first file tree under git**. Bundles are markdown with YAML frontmatter, stored on disk under `~/.substrate/`, versioned by a single repo, and consumed by a CLI today and an MCP server tomorrow. No daemon, no database, no network — the filesystem *is* the API.

### 1.1 System diagram

```
                      ┌──────────────────────────────────────┐
                      │  ~/.substrate/  (single git repo)    │
                      │  bundles/YYYY-MM-DD/<slug>.md        │
                      │  usage.log  (append-only, untracked) │
                      └──────────────────────────────────────┘
                                   ▲          ▲
                  reads/writes     │          │   reads only
                                   │          │
                ┌──────────────────┴─┐    ┌───┴────────────────────┐
                │  CLI (shipped v0)  │    │  MCP server (v1.0)     │
                │  init/add/list/get │    │  search_by_date        │
                │  use/log/edit/hist │    │  search_by_tag         │
                └────────────────────┘    │  get_bundle            │
                                          └────────────────────────┘
                  - - - - - - - - - - - - - - - - - - - - - - -
                  ┊  Authoring app (v2, deferred)            ┊
                  ┊  Indexer + skill analytics (v2, deferred)┊
                  - - - - - - - - - - - - - - - - - - - - - - -
```

Solid = ships at or before the Friday May 15 gate clears. Dashed = post-gate.

### 1.2 Components

| Component        | Responsibility                                                    | Status                           |
| ---------------- | ----------------------------------------------------------------- | -------------------------------- |
| CLI (`cli.py`)   | Author, list, retrieve, copy-to-clipboard, log, edit, history    | **Shipped** (v0)                |
| Bundle store     | Filesystem tree under `~/.substrate/bundles/`                    | **Shipped** (v0)                |
| Git repo         | Version history, rollback, diff                                  | **Shipped** (v0)                |
| Usage log        | Append-only TSV of `use` invocations (the falsifiable metric)    | **Shipped** (v0)                |
| MCP server       | Read-only MCP endpoint exposing `search_*` + `get_bundle`        | **Planned, v1.0 — unlocks after May 15 gate** |
| Authoring app    | Tauri/Electron UI for write + live context suggestions           | **Deferred, v2**                |
| Indexer / search | Tag/date already O(n); full-text + embedding index               | **Deferred, v2**                |
| Skill analytics  | Derived stats from `usage.log` + git history                     | **Deferred, v2**                |

### 1.3 Bundle schema

```yaml
---
# REQUIRED
id: 2026-05-11-guvio-pdf-import     # "<created-date>-<slug>", globally unique
created: 2026-05-11T10:14:22+05:30  # ISO 8601 with offset
tags: [guvio, backend, import]      # list[str], lowercase, kebab-case

# OPTIONAL
context_refs: []                    # list[ContextRef] — see taxonomy
expected_output_signature: |        # informal description of what "good" output looks like
  PR diff touching guvio-backend/
  with passing tests
author: sid                         # string, single value (multi-author = v3)
updated: 2026-05-11T11:02:00+05:30  # set on edit
parent: 2026-05-04-pdf-import-v0    # forked/iterated from
status: draft | active | archived   # default: active
---
```

**`context_refs` taxonomy** — closed set of five `kind`s in v1:

```yaml
context_refs:
  - { kind: file,   path: guvio-backend/app/services/documents.py, rev: HEAD }
  - { kind: graph,  engine: gitnexus, query: "context EncryptionService" }
  - { kind: memory, key: "project-guvio-launch-posture" }
  - { kind: url,    href: "https://www.dpdpa.gov.in/..." , captured: 2026-05-11 }
  - { kind: inline, label: "raw paste", body: "<embedded>" }
```

Unknown kinds are preserved untouched but ignored by tooling.

### 1.4 Storage layout

```
~/.substrate/
├── .git/                            # version history
├── .gitignore                       # ignores usage.log (private metric, noisy diffs)
├── bundles/
│   └── 2026-05-11/                  # one folder per local-date (timezone-aware)
│       ├── guvio-pdf-import.md
│       └── council-rate-limit.md
└── usage.log                        # append-only TSV: "<iso-ts>\t<bundle_id>\t<note>\n"
```

**Naming rules.** Folder = `YYYY-MM-DD` of bundle creation in author's local timezone. File = `<slug>.md`. Slug = lowercased name, non-alphanum runs collapsed to `-`, trimmed. Fallback `untitled`. Bundle `id` = `<folder>-<slug>`. Same-day slug collisions error out.

### 1.5 Versioning model

Git is implementation detail, not UX. User never types `git` commands.

- `init` → `git init -b main` + initial empty commit.
- `add` → write file, open `$EDITOR`, on exit `git add -A && git commit -m "add <id>"`.
- `edit` → same pattern, message `edit <id>`.
- **Rollback** = `git checkout <sha> -- bundles/<date>/<slug>.md` (documented; `substrate revert` verb is v1.1, post-gate).
- **History** = `substrate history <id>` runs `git log --oneline` scoped to the file.
- `.gitignore` lists only `usage.log` — usage data is local-personal and shouldn't pollute diffs.

`--allow-empty` commits are tolerated (cheap, preserves intent). No squashing, no rebasing — history is the audit trail.

### 1.6 Concurrency

Single-user, single-machine in v1, but two CLI processes can still race.

- **Two `add` calls, same name, same day.** Second `path.exists()` check fails non-zero exit. Git commits serialize; interleaved commits commit both files in one commit — acceptable, no data loss.
- **Two `use` calls.** `usage.log` opened in append-mode (`"a"`); POSIX guarantees `O_APPEND` writes under filesystem block size are atomic on local FS (APFS, ext4). Each line is ≪ 4KB. **The log is safe under concurrent appenders without locking.** This is why the log is flat TSV, not SQLite.
- **Editor races.** Last-writer-wins on disk; git surfaces divergence as dirty-state on next `add`. No locking — cost of a missed edit is bounded by `git reflog`.

File-lock around git operations is v1.2, post-gate, only if a real race is observed.

### 1.7 Privacy commitments

- **Local-first, period.** Bundles live on user's disk. No upload, no sync, no phone-home in v1.
- **No telemetry.** CLI makes zero outbound network calls. MCP server (v1.0) is loopback-only.
- **No analytics scraping.** Skill analytics (v2) run locally against `usage.log` and git history. No data leaves the machine.
- **Opt-in only for any future cloud/team feature** (v3+). Cloud sync, shared workspaces must be explicit subcommands (`substrate remote add`, `substrate push`), never auto-enable.
- **Sensitive content is the user's responsibility.** Substrate does not scan for secrets, but `.gitignore` excludes `usage.log` to avoid leaking work patterns if the repo is shared.

---

## 2. CLI Surface

Invoked as `substrate <command>` after `uv tool install substrate`. Every command except `init` calls `_ensure_init()` and exits non-zero if the store is missing.

### 2.1 v0 commands (shipping now)

| Command | Signature | Side effects |
|---|---|---|
| `init` | `substrate init` | Creates `~/.substrate/{bundles,usage.log,.gitignore}`, runs `git init -b main`, empty `init` commit. Errors if `.git` exists. |
| `add` | `substrate add NAME [-t TAG]...` | Creates `~/.substrate/bundles/YYYY-MM-DD/<slug>.md` from template, opens `$EDITOR`, commits `add <id>`. |
| `list` | `substrate list [-t TAG] [-d YYYY-MM-DD]` | Rich table of `id / tags / path`. No writes. `(no bundles)` if filter empty. |
| `get` | `substrate get ID` | Writes raw bundle (including frontmatter) to stdout. Pipe-friendly. |
| `use` | `substrate use ID [-n NOTE]` | Strips frontmatter, pipes body to `pbcopy`, appends `<ts>\t<id>\t<note>\n` to `usage.log`. **This is the falsifiable metric for Gate 0.** |
| `log` | `substrate log [-s YYYY-MM-DD]` | Rich table of `usage.log` titled with count. Read-only. |
| `edit` | `substrate edit ID` | Opens bundle in `$EDITOR`, commits `edit <id>` (empty allowed). |
| `history` | `substrate history ID` | `git log --oneline -- <path>`. Output unwrapped. |

ID resolution (`_find_bundle`): exact frontmatter `id` first; else substring match against filename stems; ambiguous matches return `None` and exit 1.

### 2.2 Conventions

```
exit 0  ok
exit 1  user error (not initialized, not found, duplicate, etc.)
exit 2  reserved for internal (Typer's default for bad usage)
```

- **stdout = data** (`get` output, `list`/`log` tables). Pipe-safe.
- **stderr = messages** (errors). Success confirmations (`saved:`, `copied:`) go to stdout — single-line, grep-friendly.
- Rich auto-disables ANSI when stdout is not a TTY. No `--no-color` flag needed.

### 2.3 `$EDITOR` integration

Fallback chain (in `add` and `edit`):

```
$EDITOR  →  nvim  (hardcoded default)
```

`subprocess.call` used, so non-zero editor exit does **not** abort. File committed regardless. Empty save on `add` produces template-only bundle. Empty save on `edit` produces empty git diff but logged as `--allow-empty`.

Deferred (v1.x): `vi` fallback when `nvim` absent; `SUBSTRATE_EDITOR` override; `--no-edit` flag for piping content.

### 2.4 Clipboard

`use` shells to `pbcopy` unconditionally. On Linux/Windows silently fails (`check=False`) but usage log still records. Linux (`xclip`/`wl-copy`) and Windows (`clip.exe`) support deferred to v1.x.

### 2.5 Slug & ID rules

```python
slug   = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "untitled"
id     = f"{YYYY-MM-DD}-{slug}"
path   = ~/.substrate/bundles/YYYY-MM-DD/<slug>.md
```

Same-day slug collisions exit 1. Cross-day collisions allowed (different IDs).

### 2.6 Planned v1.x commands (post-Gate 0)

Each blocked behind Friday May 15 gate. Order = priority.

| Command | Why | Friday-gate evidence to justify |
|---|---|---|
| `search QUERY [--tag] [--since]` | Find by remembered word, not ID | Any `use` preceded by `list` + grep, or "couldn't find it" note. |
| `pin TEMPLATE` + `add --from TEMPLATE` | Promote a bundle to template | Two `use` entries on same bundle → template candidate. |
| `import PATH` | Bring existing markdown into store | Any usage note mentioning "copied from <repo>". |
| `stats` | Top tags, top bundles, untagged orphans | Log has ≥10 entries with non-trivial skew. |
| `export ID [--format md\|json\|claude]` | Pipe into Claude/MCP without manual frontmatter stripping | A note saying "had to strip frontmatter by hand". |
| `link FROM TO` (v2) | Cross-reference bundles | Only ships if `stats` shows real clustering. |

**Nothing on this list ships before Gate 0 clears.**

### 2.7 Shell completion

```bash
substrate --install-completion        # detects $SHELL
substrate --show-completion           # prints script for manual install
```

Tested targets: zsh, bash. Fish works via Typer's Click backend but undocumented.

### 2.8 Anti-features

The CLI will deliberately **not** include:

- **No auth / accounts** — local-first; the store is yours on disk.
- **No cloud sync** — push `~/.substrate` to a private git remote yourself.
- **No plugin system** — every command goes through the council.
- **No auto-suggest / LLM-in-the-CLI** — `use` is the human-in-the-loop signal; automating it corrupts the falsifiable metric.
- **No web UI** — terminal is enough. A UI is a distraction until Gate 0 clears twice.

---

## 3. MCP Server

> **Status:** Conditional v1.0 — gated by mid-week pulse check. Ship target **Wed May 13** per Executor plan, *only if* the Friday gate looks reachable on Tuesday. If cadence is soft, slips one week. The CLI is the falsifiable wedge, the MCP server is the distribution multiplier.

### 3.1 Why MCP

The MCP server is the distribution moat. Every prompt-management competitor is gated on login + SDK + workspace. An MCP server is gated on nothing: any MCP-aware client — Claude Code, Cursor, Zed, Claude Desktop, Continue, internal agents — becomes a Substrate consumer the moment the user adds one line to a config file. No accounts, no auth, no telemetry. The bundle store on disk *is* the product surface; MCP is the wire format that makes it ambient across the user's entire agent fleet.

### 3.2 Transport

**stdio only in v1.** Claude Code, Cursor, Zed all launch MCP servers as subprocesses over stdio — lowest-friction transport, zero networking, inherits user's file permissions automatically. SSE and Streamable HTTP transports are deferred: port allocation, auth, lifecycle problems that buy nothing for a local-first single-user tool. Revisit HTTP in v3 when team workspaces require a shared server.

### 3.3 Implementation

- Language: Python 3.12 (shared `cli.py` helpers: `_parse_frontmatter`, `_find_bundle`, `_strip_frontmatter`).
- SDK: official [`mcp`](https://pypi.org/project/mcp/) Python SDK, `mcp.server.Server` with stdio transport (`mcp.server.stdio.stdio_server`).
- Entrypoint: console script `substrate-mcp`:

```toml
[project.scripts]
substrate = "cli:app"
substrate-mcp = "mcp_server:main"
```

Server reads the same `~/.substrate/bundles/` tree the CLI writes — no separate index, no sync. Schema drift impossible by construction.

### 3.4 Tools exposed

All five follow `name / title / description / inputSchema / outputSchema` (2025-06-18 spec, structured output supported).

**`list_bundles`** — enumerate bundles, optional tag/date filter. Latency: **<50ms** for ≤1k bundles.

```json
{
  "name": "list_bundles",
  "inputSchema": {"type":"object","properties":{"tag":{"type":"string"},"date":{"type":"string","pattern":"^\\d{4}-\\d{2}-\\d{2}$"},"limit":{"type":"integer","default":50}}},
  "outputSchema": {"type":"object","properties":{"bundles":{"type":"array","items":{"type":"object","properties":{"id":{"type":"string"},"tags":{"type":"array","items":{"type":"string"}},"path":{"type":"string"},"created":{"type":"string"}},"required":["id","path"]}}},"required":["bundles"]}
}
```

**`get_bundle`** — fetch by id (exact) or fuzzy stem match. Latency: **<20ms**. Errors: `not_found`, `ambiguous`.

```json
{"inputSchema":{"type":"object","required":["id"],"properties":{"id":{"type":"string"},"strip_frontmatter":{"type":"boolean","default":false}}},
 "outputSchema":{"type":"object","required":["id","body","metadata"],"properties":{"id":{"type":"string"},"body":{"type":"string"},"metadata":{"type":"object"}}}}
```

**`search_bundles`** — substring + tag match across body and frontmatter. v1 = `str.lower() in` over corpus (no FTS until ≥1k bundles). Latency: **<150ms** for ≤1k bundles.

```json
{"inputSchema":{"type":"object","required":["query"],"properties":{"query":{"type":"string"},"tag":{"type":"string"},"limit":{"type":"integer","default":10}}},
 "outputSchema":{"type":"object","properties":{"results":{"type":"array","items":{"type":"object","properties":{"id":{"type":"string"},"snippet":{"type":"string"},"score":{"type":"number"}}}}}}}
```

**`get_by_date`** — temporal addressing, the killer UX (*"look at my notes from May 10 and execute"*). Latency: **<30ms**.

```json
{"inputSchema":{"type":"object","required":["date"],"properties":{"date":{"type":"string","description":"YYYY-MM-DD or YYYY-MM-DD..YYYY-MM-DD"}}},
 "outputSchema":{"type":"object","properties":{"bundles":{"type":"array","items":{"type":"object"}}}}}
```

**`log_use`** — append-only usage log. Mirrors `substrate use --note`. Latency: **<10ms**.

```json
{"inputSchema":{"type":"object","required":["id"],"properties":{"id":{"type":"string"},"note":{"type":"string"},"client":{"type":"string","description":"e.g. claude-code, cursor"}}},
 "outputSchema":{"type":"object","required":["logged"],"properties":{"logged":{"type":"boolean"},"ts":{"type":"string"}}}}
```

**Error cases** (uniform): `not_initialized`, `not_found`, `ambiguous`, `invalid_date`. Returned as `isError: true` with structured `content[0].text` JSON. JSON-RPC errors only for unknown-tool / bad-args.

### 3.5 Resources

Each bundle exposed as MCP resource under URI `substrate://bundle/{id}` with `mimeType: text/markdown`. Clients preferring the resource model (Zed, Claude Desktop pinboard) subscribe and embed bundles into context without a tool call. `resources/list` paginates 200 most-recent; full set via `list_bundles` + `resources/read`.

### 3.6 Prompts

Bundles tagged `pinned` exposed as MCP prompts so clients render them as slash commands. Prompt name = bundle id; body = stripped markdown. Path to "my prompts show up as `/my-pinned-prompt` inside Claude Code with zero config." Argument support deferred to v1.1.

### 3.7 Installation

**Claude Code:**
```bash
claude mcp add substrate -- substrate-mcp
```

**Cursor** — `.cursor/mcp.json`:
```json
{"mcpServers":{"substrate":{"command":"substrate-mcp","args":[]}}}
```

**Zed** — `.zed/settings.json`:
```json
{"context_servers":{"substrate":{"command":{"path":"substrate-mcp","args":[],"env":{}}}}}
```

**Claude Desktop** — same `mcpServers` block as Cursor in `~/Library/Application Support/Claude/claude_desktop_config.json`.

### 3.8 Security

- Runs as invoking user, inherits FS permissions — no daemon, no setuid.
- Reads `~/.substrate/` only. No reads outside bundle root.
- No network calls. Zero outbound sockets; `urllib`/`httpx` not imported.
- Only writes permitted: append to `~/.substrate/usage.log` (via `log_use`). Bundle CRUD is CLI-only in v1 — agents read, humans write. Eliminates prompt-injection "edit your own prompt library" attack surface.
- Inputs validated against `inputSchema` before dispatch; ids constrained to `[a-z0-9-]` to prevent path traversal.

### 3.9 Testing

- **Contract tests** using `mcp.client.stdio.stdio_client`: assert `tools/list` returns the five tools with exact JSON schemas; assert `resources/list` returns ≥1 bundle on seeded store; assert each tool returns valid `structuredContent` conforming to `outputSchema`.
- **Smoke test** (`make smoke-mcp`): boot server, list tools, call `list_bundles`, `get_bundle` (round-trip seeded fixture), `log_use`, verify line appended to `usage.log`. <2s end-to-end.
- **Schema-drift guard:** pytest fixture diffs live `tools/list` output against `tests/golden/tools.json`. Schema changes require deliberate golden update.
- **Cross-client manual smoke** before tagging v1.0: register in Claude Code, Cursor, Zed; confirm `get_bundle` round-trips in all three.

---

## 4. Search, Retrieval, and Indexing

The non-negotiable: **markdown files on disk remain the source of truth.** Every index is a derived cache, rebuildable from `~/.substrate/bundles/**/*.md`.

### Phase 0 — Linear scan (current, v0, pre-Friday)

Today's `list` does `BUNDLES.rglob("*.md")`, parses YAML, filters by `tag` and `date` in Python. No index. Every invocation reparses every file.

**Limits, documented honestly:**
- Acceptable up to ~500 bundles (frontmatter parse dominates, ~2–5ms/file on SSD).
- No full-text search. `--tag` exact-match only.
- This is the v0 contract. Do not extend it.

### Phase 1 — SQLite FTS5 index (post-Friday, v1.0)

Persistent index at `~/.substrate/index.db`. Rebuilt incrementally by hooks on `add`/`edit`. FTS5 ships in stdlib `sqlite3` — zero new deps.

```sql
CREATE TABLE bundles (
  id        TEXT PRIMARY KEY,
  path      TEXT NOT NULL UNIQUE,
  created   TEXT NOT NULL,
  updated   TEXT NOT NULL,
  title     TEXT,
  body_hash TEXT NOT NULL
);

CREATE TABLE tags (
  bundle_id TEXT NOT NULL REFERENCES bundles(id) ON DELETE CASCADE,
  tag       TEXT NOT NULL,
  PRIMARY KEY (bundle_id, tag)
);
CREATE INDEX idx_tags_tag ON tags(tag);

CREATE TABLE uses (
  bundle_id TEXT NOT NULL REFERENCES bundles(id) ON DELETE CASCADE,
  used_at   TEXT NOT NULL,
  note      TEXT
);
CREATE INDEX idx_uses_bundle ON uses(bundle_id);
CREATE INDEX idx_uses_when   ON uses(used_at);

CREATE VIRTUAL TABLE bundles_fts USING fts5(
  title, body, tags,
  content='', tokenize='porter unicode61'
);

CREATE TABLE schema_version (v INTEGER NOT NULL);
INSERT INTO schema_version VALUES (1);
```

**Target:** sub-100ms queries up to 10k bundles. Incremental updates compare `body_hash`.

**Opinion: do NOT ship embeddings in v1.0.** FTS5 + tag filters + recency covers the actual retrieval need. Embeddings add 200MB weights, 2–4s cold start, tuning surface — unjustified at 1k bundles.

### Phase 2 — Optional local embeddings (v1.5, gated on demand)

Triggered when bundle count > **2,000** *or* user runs `substrate index --semantic`. Model: `bge-small-en-v1.5` (33MB ONNX) by default, or `nomic-embed-text` via Ollama. Vectors stored in [`sqlite-vec`](https://github.com/asg017/sqlite-vec) loadable extension in same `index.db`.

**Hybrid retrieval:** FTS5 (top 50) + vector cosine (top 50) → reciprocal rank fusion → final top N. Pure semantic-only is a footgun.

### Phase 3 — External graph integration (v2)

Substrate becomes **journal layer**, not graph replacement. User's existing substrate — graphify, GitNexus, claude-mem — stays primary. Substrate reads from them.

At authoring time, Substrate calls:
- `gitnexus query` for code symbols mentioned in the prompt,
- `graphify query` for semantic neighbors,
- `claude-mem mem-search` for prior sessions,

…and surfaces **suggested pins** the user accepts into `context_refs`. The bundle stores the *resolved reference* (graph node ID + repo/commit + query), not content — so context refreshes on `use`. Read-only.

### Query interface

- **CLI:** `substrate search "query" [--tag t] [--since DATE] [--until DATE] [--limit N]`
- **MCP tool:** `search_bundles(query, tags?, since?, until?, limit?)` — same ranking.

**Ranking heuristic (v1.0):**

```
score = bm25(fts) * 1.0
      + recency_boost                  # 0.5 * exp(-age_days / 30)
      + tag_match_boost                # +0.3 per requested tag matched
      + use_boost                      # 0.1 * log(1 + uses_last_30d)
```

Tunable in `~/.substrate/config.toml`. Phase 2 adds `semantic_weight`.

### Temporal queries

First-class:
- absolute: `--date 2026-05-10`, `--since 2026-05-01 --until 2026-05-10`
- relative: `--since "last week"`, `--since "yesterday"`, `--since "7d"`

Parsing via `dateparser`. MCP tool exposes both ISO and a `relative` string so LLM clients pass natural language directly.

### Performance budget

| Operation | Target @ 1k | Target @ 10k |
|---|---|---|
| Full index rebuild | < 500ms | < 5s |
| Incremental update (1 file) | < 20ms | < 20ms |
| FTS5 query | < 50ms | < 100ms |
| Hybrid query (Phase 2) | < 150ms | < 300ms |

Measured via `substrate bench` (admin command, Phase 1). Same harness in CI.

### Index corruption recovery

`substrate reindex [--semantic]`. Idempotent: deletes `index.db`, walks `BUNDLES/**/*.md`, rebuilds. Replays `usage.log` into `uses`. Hook layer auto-invokes on schema version mismatch.

---

## 5. Testing & Verification

### 5.1 Philosophy

Tests pay rent or get cut. Pure functions with branching logic earn tight TDD. CLI commands get integration tests against a real `~/.substrate/` in a tmp dir. Wrappers around `git` and `subprocess` get no tests of their own.

v0 bar: green smoke test + unit coverage on the four pure helpers. Everything else accretes during trial week as bugs surface.

### 5.2 Framework

- **pytest** + **pytest-cov**. That's it.
- No `unittest.mock` unless needed. `pbcopy` is the only thing worth stubbing (Linux CI).
- `tmp_path` for filesystem isolation.

**Required cli.py change (small, add now):** swap `ROOT = Path.home() / ".substrate"` for env-var-aware lookup:

```python
ROOT = Path(os.environ.get("SUBSTRATE_HOME", Path.home() / ".substrate"))
BUNDLES = ROOT / "bundles"
USAGE_LOG = ROOT / "usage.log"
```

Without this, tests pollute real home dir or monkey-patch module globals. Env var also useful for project-scoped stores later.

### 5.3 Test isolation pattern

```python
@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("SUBSTRATE_HOME", str(tmp_path / "substrate"))
    monkeypatch.setenv("EDITOR", "true")  # no-op so `add` doesn't block
    from typer.testing import CliRunner
    from cli import app
    runner = CliRunner()
    runner.invoke(app, ["init"])
    return runner
```

### 5.4 Categories and what ships when

**Unit (add now — by Friday May 15):**
- `_slug`: punctuation collapse, edge dash strip, empty-string fallback, unicode passthrough.
- `_parse_frontmatter`: missing, malformed, empty, well-formed.
- `_strip_frontmatter`: round-trips with `_parse_frontmatter`.
- `_find_bundle`: exact wins over stem; ambiguous returns `None`; missing returns `None`.

**Integration (add now):**
- `init`: creates `.git`, bundles dir, gitignore; refuses second init.
- `add` with `EDITOR=true`: file lands, frontmatter has expected id, commit in `git log`.
- `list`: filters by `--tag` and `--date`; empty state.
- `get`: prints whole file; missing id exits 1.
- `use`: with stubbed `pbcopy`, usage log gets TSV row.
- `log` and `history`: exit 0 with no bundles; `--since` filters.

**Contract — MCP (add post-Wednesday):**
- `tools/list` matches documented set.
- Input schemas validate good/bad fixtures.
- Error cases return MCP errors, not tracebacks.

**Property (add post-Friday):**
- `_slug` idempotency.
- Frontmatter round-trip via `hypothesis`.

### 5.5 Smoke test (add now)

`scripts/smoke.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
export SUBSTRATE_HOME=$(mktemp -d)
export EDITOR=true
substrate init | grep -q "initialized"
substrate add "demo bundle" --tag test
substrate list | grep -q "demo-bundle"
substrate get "$(date +%Y-%m-%d)-demo-bundle" | grep -q "# Prompt"
PBCOPY_SHIM=$(mktemp); echo '#!/bin/sh' > "$PBCOPY_SHIM"; chmod +x "$PBCOPY_SHIM"
PATH="$(dirname "$PBCOPY_SHIM"):$PATH" substrate use "$(date +%Y-%m-%d)-demo-bundle" --note smoke
substrate log | grep -q "smoke"
echo "smoke: ok"
```

Six commands, six assertions. Run before every commit, run in CI.

### 5.6 CI (add post-Friday)

GitHub Actions, matrix `{macos-latest, ubuntu-latest} × {3.10, 3.11, 3.12}`. Linux exports `pbcopy` shim onto `$PATH`. One workflow: `ruff check`, `ruff format --check`, `mypy --strict cli.py`, `pytest --cov=cli --cov-fail-under=70`, `scripts/smoke.sh`.

### 5.7 Lint, format, types (add now)

- **ruff** (lint + format). Config in `pyproject.toml`, line length 100, select `E,F,I,N,UP,B,SIM`.
- **mypy --strict** on `cli.py` only.
- **pre-commit**: ruff + mypy + smoke.

### 5.8 Definition of done

For any new command:
1. Works on fresh `SUBSTRATE_HOME`.
2. Integration test covers happy path + one failure.
3. `scripts/smoke.sh` still passes.
4. `--help` reflects new flags.
5. README command table updated.

No PR merges with any missing.

### 5.9 What NOT to test

- Typer's argument parsing.
- Rich's table rendering — assert on data, not formatting.
- Git's commit/log behavior — assert that we called it.
- The filesystem — `tmp_path` is enough.
- Editor behavior — `EDITOR=true` is the contract.

---

## 6. Roadmap, Gates, and Risks

Each gate has a date, single success criterion, explicit kill action on FAIL, defined unlock on PASS. **No item ships before its prior gate clears.** The spine of this project is the willingness to fold it at any gate.

The Friday May 15 gate may well fail. This spec is written assuming it might. That is the point.

### Gate 0 — Friday May 15, 2026, 6:00 PM IST

- **Criterion:** `substrate log --since 2026-05-11` shows **≥5 entries**, each with a `--note` naming a real shipped artifact: Guvio PR number, blog post draft filename, day-job RFC/PR/design-doc title. Anonymous notes ("testing") do not count.
- **FAIL → Kill action:** Saturday May 16 morning, archive repo to `~/code/archive/substrate-2026-05/`, delete `~/.substrate/`, write 200-word post-mortem to `~/code/billion/substrate-postmortem.md`. No v1, no MCP. The one-pager's "Single decision criterion" authorizes this.
- **PASS → Unlocks:** Gate 1. Permission to spend week 2 on MCP server.

### Gate 1 — Wednesday May 20, 2026

- **Criterion:** MCP server (`substrate-mcp`) runs as stdio server registered with Claude Code, exposes `search_by_date`, `search_by_tag`, `get_bundle`. The phrase **"look at my notes from May X and execute"** in a fresh Claude Code session resolves to a real bundle and runs it end-to-end at least once, captured in `usage.log` with note `mcp-e2e`.
- **FAIL → Kill action:** Drop the MCP server. Remove "MCP-native" from one-pager. Substrate stays CLI-only personal tool. Revisit positioning — the moat thesis depends on multi-client portability.
- **PASS → Unlocks:** Gate 2. Spend weeks 3-4 on sustained dogfooding instead of features.

### Gate 2 — Monday June 1, 2026

- **Criterion:** Sustained personal use: **25+ bundles authored, 50+ `use` invocations** in 3-week window since Gate 0. Plus measurable Guvio velocity delta — comparable tasks (CRUD endpoint, Tiptap extension, Alembic migration) ship ≥30% faster than prior 6-week baseline, computed from PR cycle time.
- **FAIL → Kill action:** Fold into Guvio as private prompt folder. No productization. No OSS. One-pager's fallback ("lawyer-AI-coach module inside Guvio") is the path.
- **PASS → Unlocks:** Gate 3. Begin OSS prep.

### Gate 3 — Tuesday July 15, 2026

- **Criterion:** OSS release on GitHub by July 1, soft launch on HN/X. By July 15: **200 GitHub stars OR 20 active external users** (≥3 invocations each, evidenced by Discord/issues/DMs).
- **FAIL → Kill action:** Keep as personal tool. Archive repo as "released, not maintained." No v2/v3/v4. Refocus on Guvio.
- **PASS → Unlocks:** Gate 4. Begin Tauri authoring app prototype.

### Gate 4 — November 30, 2026 (Q4)

- **Criterion:** Authoring app (Tauri) shipped + skill analytics dashboard. **First paying customer** (≥$20 MRR, real card, real seat — not a friend comp).
- **FAIL → Kill action:** OSS-only forever. Authoring app open-sourced, analytics shelved. No enterprise pursuit.
- **PASS → Unlocks:** Gate 5. Permission to write enterprise pilot proposals.

### Gate 5 — June 30, 2027 (H1)

- **Criterion:** Enterprise CI/CD integration (Jira/Linear → bundle → agent → audit) with **1 signed pilot at Indian regulated-industry firm** sourced from Guvio network, contract ≥₹5L.
- **FAIL → Kill action:** SMB SaaS only. Drop compliance-edition thesis.
- **PASS → Unlocks:** Second pilot, then GTM build-out.

### Engineering risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Git corruption in `~/.substrate/` | Low | High | Markdown is source-of-truth; `reindex` rebuilds SQLite + verifies tree. Survives destroyed `.git/`. |
| SQLite index drift from out-of-band edits | Medium | Medium | Filesystem `mtime` watcher + `reindex`; CI-style integrity check. |
| MCP SDK breaking changes across clients | High | Medium | Pin SDK version; contract tests against recorded fixture; matrix-test last 2 minor versions. |
| `usage.log` corruption from concurrent writes | Medium | Low | Append-only with atomic single-`write()` lines (under PIPE_BUF=4096). |
| Bundle ID collisions | Low | Low | Slug + date prefix; `add` errors on existing path before `$EDITOR`. |
| `$EDITOR` never exits | Medium | Low | Documented; user kills editor. Not Substrate's problem. |
| Data loss from `rm -rf ~/.substrate/` | Low | Catastrophic | Optional `substrate backup` → `tar.gz`; documented as user responsibility. No cloud sync in v1. |

---

## Appendix A — Required v0.0.1 patch

To enable the test isolation pattern in §5.3, `cli.py` needs one line changed at module top:

```python
# before
ROOT = Path.home() / ".substrate"

# after
ROOT = Path(os.environ.get("SUBSTRATE_HOME", Path.home() / ".substrate"))
```

This is the only spec-mandated change to v0. Add it before writing the first test.

## Appendix B — Decision log

| Date | Decision | Rationale |
|---|---|---|
| 2026-05-11 | Markdown + YAML frontmatter as storage format | Source-of-truth on disk, human-editable, git-diffable. Rejected: SQLite-only (hard to grep), JSON (worse for prose). |
| 2026-05-11 | Git as versioning backend | Free, well-understood, gives blame/diff/rollback. Rejected: custom version table (reinventing git). |
| 2026-05-11 | TSV append-only usage log | POSIX-atomic appends; no locking needed. Rejected: SQLite table (concurrency tax for no benefit). |
| 2026-05-11 | MCP over stdio only in v1 | Zero networking; inherits user perms; matches Claude Code/Cursor/Zed defaults. |
| 2026-05-11 | No embeddings in v1.0 | FTS5 covers the actual retrieval need; embeddings add weight + cold-start for no measured win at <1k bundles. |
| 2026-05-11 | Agents read, humans write (MCP) | Eliminates prompt-injection self-edit attack surface. Bundle CRUD stays CLI-only in v1. |
| 2026-05-11 | Gate 0 metric is `use` count, not `add` count | `add` is cheap, `use` is the signal. Creating bundles you never reach for is the failure mode. |
