# Substrate — Implementation Handoff

> For the next Claude (or future Sid) picking this up. Read top-to-bottom once, then refer back.

**Owner:** Sid — solo, also staff engineer + blogger + Guvio founder
**Last session ended:** May 16, 2026 (Saturday) — Gate 0 PASSED (count=5), Gate 1 PASSED (`mcp-e2e` logged 4 days early)
**Hard gate:** **Gate 2 — Monday June 1, 2026**
**Authoritative docs:** [`SPEC.md`](./SPEC.md) (full spec), [`one-pager.md`](./one-pager.md) (product framing + council verdict)

---

## Read these first (in order, ~10 min)

1. **This file** — orientation
2. **`SPEC.md` §6 Gate 2** — sustained-use criterion + kill action
3. **`SPEC.md` §6 Gate 3** — what PASS unlocks (OSS prep, the first public surface)
4. **`one-pager.md`** "Dissent Worth Noting" section — the constraint Sid chose to operate under
5. **`cli.py` + `mcp_server.py`** — current implementation, 9 CLI commands + 5 MCP tools

## Where are we right now?

Run these to orient yourself before doing anything:

```bash
date                                                                        # what day is it
substrate log --since 2026-05-11                                            # full use history
substrate log --since 2026-05-11 | wc -l                                    # Gate 2 numerator (target ≥50)
substrate list | tail -50                                                   # bundle count (target ≥25)
git -C ~/.substrate log --oneline | head -10                                # recent authoring
claude mcp list | grep substrate                                            # MCP server health (must be ✓ Connected)
```

Decision tree:

| Today is | Action |
|---|---|
| Sat May 16 → Sun May 31 | **Dogfooding window.** Author bundles, run them via MCP, log every execution. No new features. |
| Mon Jun 1, before 6 PM IST | Push remaining real-use bundles. Last chance for the metric. |
| Mon Jun 1, after 6 PM IST | **Verify Gate 2.** See "Gate 2 verdict" below. |
| Tue Jun 2 → if Gate 2 FAIL | Execute Gate-2 kill action: fold into Guvio as a private "Practice Knowledge" feature. No standalone product. |
| Tue Jun 2 → if Gate 2 PASS | Open `SPEC.md` §6 Gate 3. Begin OSS prep — license, contribution guide, GitHub Action smoke. Soft launch target: Jul 1. |

## Allowed work this period (Gate 1 → Gate 2)

The work is **using** Substrate, not building it. The council's discipline rule applies hardest here: if you're tempted to add a feature, author a bundle instead.

Permitted code changes between now and Mon Jun 1:

1. **Bug fixes** — anything that prevents the existing surface from working as documented (CLI command, MCP tool, contract test).
2. **Bundle authoring** in `~/.substrate/` — unlimited; this is the work.
3. **Cross-client smoke** — register Substrate in Cursor and Zed at least once; verify `get_bundle` round-trips. Documented in SPEC §3.9.
4. **`feedback-no-coauthor.md` cleanup** — the two existing `Co-Authored-By` trailers on `a325e86` and `b575d68` are a known violation. Sid chose "fix lazily" (option 2). Don't re-add the trailer going forward.

**Time budget:** Bundle-authoring time, not code time. If a coding session exceeds 30 min between now and Jun 1, stop and ask whether it's authorized.

## Still forbidden this period

These remain explicit kill-list items, council-confirmed:

- ❌ **SQLite FTS5 index** (deferred to v1.5 / Phase 1 — gated on bundle count, not date)
- ❌ **Embeddings** (deferred to v2 / Phase 2)
- ❌ **Authoring app** (Tauri / Electron / Swift — Gate 4 decision, not before)
- ❌ **GitHub Actions / CI** beyond a one-line smoke (Gate 3 territory)
- ❌ **Landing page, marketing copy, screencasts** (Gate 3, not before — no public talk pre-Gate-3)
- ❌ **Renaming Substrate** (name decision is post-Gate-3)
- ❌ **Adding `context_refs` integrations to graphify / GitNexus / claude-mem** (SPEC §4 Phase 3 — v2)
- ❌ **Writing a blog post about Substrate** (no public talk pre-Gate-3)
- ❌ **Any work in `~/code/lattice/`, `~/code/billion/`, or other side projects** (kill-list still applies — Substrate displaced one project slot already)

Newly **permitted** post-Gate-1 (was forbidden before):

- ✅ Bug fixes that touch `cli.py` / `mcp_server.py` (no feature additions)
- ✅ `substrate search` and other CLI retrievers (`search` shipped in v0.1.0 — search has now seeded ranking heuristics for the eventual FTS5 swap)
- ✅ Cross-client registration (Cursor / Zed) — needed for Gate 2 evidence diversity

## The Gate 2 metric, precisely

The only numbers that matter Mon Jun 1, 6 PM IST:

```bash
USES=$(substrate log --since 2026-05-11 | tail -n +2 | wc -l)          # exclude header row
BUNDLES=$(substrate list | tail -n +3 | grep -c "^│")                  # rough bundle count
echo "uses=$USES bundles=$BUNDLES"
```

Plus the **Guvio velocity delta** (qualitative — Sid's call, not a grep):

- Comparable Guvio tasks (CRUD endpoint, Tiptap extension, Alembic migration) shipping **≥30% faster** than the prior 6-week baseline, measured by PR cycle time.

**Target:** 25+ bundles, 50+ `use` invocations, +30% Guvio velocity. All three must hold.

### Gate 2 verdict (run at 6 PM IST Mon Jun 1)

```bash
USES=$(substrate log --since 2026-05-11 | tail -n +2 | wc -l)
BUNDLES=$(ls ~/.substrate/bundles/**/*.md 2>/dev/null | wc -l)
echo "Gate 2: bundles=$BUNDLES uses=$USES"
[ "$BUNDLES" -ge 25 ] && [ "$USES" -ge 50 ] && echo "metric-half PASS" || echo "metric-half FAIL"
```

Then Sid's call on the velocity delta — answer "yes" or "no", no negotiation.

### If Gate 2 FAIL — kill action

Do not negotiate. Do not extend. Do not move the goalposts.

Fold Substrate into Guvio as a private prompt-and-context layer:

```bash
# 1. Move the source into Guvio
mkdir -p ~/code/guvio/guvio-backend/app/services/substrate/
mv ~/code/substrate/cli.py ~/code/substrate/mcp_server.py ~/code/substrate/tests/ \
   ~/code/guvio/guvio-backend/app/services/substrate/

# 2. Archive the standalone repo
mv ~/code/substrate ~/code/archive/substrate-2026-06

# 3. Uninstall the CLI (Substrate stops being a tool, becomes a Guvio internal)
uv tool uninstall substrate

# 4. Keep the bundle store — it's where the leverage lives
#    (~/.substrate/ stays; Guvio reads from it directly)

# 5. Postmortem (200 words max)
$EDITOR ~/code/billion/substrate-postmortem-gate-2.md
```

The Gate-2 postmortem answers two questions only:
- Did Substrate fail because the tool was wrong, or because the dogfooding effort wasn't real?
- What's the rule I'll follow next time before promoting an internal tool to a "product"?

### If Gate 2 PASS — Gate 3 unlocked

`SPEC.md §6 Gate 3` becomes the live spec. Deadline: **Tue Jul 15**. The natural-language test:

> Push the repo public on GitHub by Jul 1. Soft-launch on HN/X. By Jul 15: 200 stars OR 20 active external users (≥3 invocations each, evidenced by issues/Discord/DMs).

Implementation order for Gate 3 prep (only after Gate 2 PASS):
1. Add LICENSE (MIT or Apache-2.0 — Sid's call)
2. Write CONTRIBUTING.md and CODE_OF_CONDUCT.md
3. Public README rewrite (current is private-repo stub)
4. GitHub Action: lint + test on push (single workflow, no matrix until Gate 3 PASS)
5. Make repo public on GitHub
6. Soft launch on HN (Show HN) and X — `/council` first per `feedback-council-before-posting.md`

## Repository layout

```
~/code/substrate/
├── cli.py                  ← 9 commands: init, add, list, search, get, use, log, edit, history
├── mcp_server.py           ← v1.0 MCP server: 5 tools + resources + prompts (stdio)
├── pyproject.toml          ← packaging (substrate, substrate-mcp console scripts)
├── uv.lock                 ← reproducible deps (mcp, typer, pyyaml, rich)
├── .gitignore
├── README.md               ← private-repo stub (polish gated to Gate 3)
├── one-pager.md            ← product framing, council verdict, dissent path
├── SPEC.md                 ← full technical spec (6 sections + appendices)
├── HANDOFF.md              ← this file
├── scripts/smoke.sh        ← 6-command end-to-end smoke
└── tests/
    ├── test_helpers.py     ← cli.py helpers (slug, frontmatter, find, snippet, search)
    └── test_mcp_server.py  ← MCP tools + call_tool wrapper + stdio round-trip
```

Bundle store lives separately at `~/.substrate/` (git-versioned, do not confuse with project repo). `usage.log` is gitignored.

Public GitHub repo: `github.com/xlreon/substrate` (PRIVATE until Gate 3 PASS).

## Session log

### 2026-05-11 (Sunday)

**Worked through with Sid in one session:**
1. Surveyed market — prompt management vs agentic SDLC vs orchestration.
2. Drafted one-pager identifying four moats: MCP-native, temporal addressing, skill analytics, Indian compliance.
3. Ran 5-advisor council. Verdict: don't build as separate product. Sid chose Executor's dissent path (Friday gate or fold).
4. Built v0: `cli.py` (8 commands), `pyproject.toml`, installed via `uv tool install --editable`.
5. Sid revealed staff engineer + blogger context. Revised gate from Guvio-only to any-named-artifact.
6. Dispatched 6 parallel agents to draft SPEC sections. Synthesized into SPEC.md (666 lines).

### 2026-05-15 (Friday) — Gate 0 day

- Heavy Guvio wave-work day: 3 waves of agent dispatching (PRs #7–#13 on guvio-backend, plus guvio-mcp v0.1.0 → v0.2.0).
- Each wave closed with `substrate use --note "<wave summary referencing PRs>"`.
- Final Gate 0 count: **5** — exactly the PASS threshold. No negotiation.
- 17 KB bundles authored during the day across protocol/template/gotcha/convention/reference categories.

### 2026-05-16 (Saturday) — Gate 1 day

- Added `substrate search` CLI command (Phase 0 linear scan, id×3 + tag×2 + body×1 ranking).
- Initialized git repo at `~/code/substrate` (was un-tracked), pushed to `github.com/xlreon/substrate` as PRIVATE.
- Built `mcp_server.py` — 5 tools (`list_bundles`, `get_bundle`, `search_bundles`, `get_by_date`, `log_use`), resources (`substrate://bundle/{id}`), prompts (bundles tagged `pinned`).
- Two bugs surfaced and fixed by real-store stdio smoke:
  1. `get_bundle.metadata` returned raw YAML — datetime in `created` broke JSON serialization. Fixed via `json.dumps(..., default=str)` coercion.
  2. Error path returned `list[TextContent]` — SDK rejected when `outputSchema` declared. Fixed via `CallToolResult(isError=True)`.
- Registered `substrate-mcp` user-scoped in `~/.claude.json`. `claude mcp list` reports `✓ Connected`.
- **Gate 1 verified end-to-end from fresh Claude Code session:** `get_by_date` → `get_bundle` → `log_use note=mcp-e2e` chain executed; usage.log shows `2026-05-16T00:23:45+05:30 ... [claude-code] mcp-e2e`.
- 56 tests passing (29 cli + 27 mcp). 4 commits on main (init, badge, MCP v1.0, MCP fixes).

**What's NOT decided / open questions (unchanged from prior session):**
- Final product name (Substrate is working title)
- Whether to fold into Guvio as "Practice Knowledge" feature if Gate 2 fails
- Authoring app stack (Tauri vs Electron vs raw Swift) — Gate 4 decision

**What needs to happen between now and Gate 2:**
- Sid uses Substrate daily for Guvio work, bundles for prompts/research/recipes
- Every `claude` invocation that pulls from Substrate gets `log_use` called by the MCP client
- Mon Jun 1, 6 PM IST: Gate 2 verdict (25+ bundles, 50+ uses, +30% Guvio velocity)

## Discipline rules (lifted from council verdict, updated for Gate 2)

1. **Memory before assumption.** Before adding any feature, check this file + SPEC §6. If the work isn't authorized by the current gate, don't do it.
2. **Falsifiability over vibes.** The metric is a `wc -l` + a yes/no on velocity. Trust the numbers, not the feeling.
3. **No public talk pre-Gate-3.** No HN post, no tweet, no blog, no demo to friends. Substrate is private GitHub + private use until Gate 3 unlocks OSS prep.
4. **Gate verdicts are binary.** 25 bundles + 50 uses + yes-velocity = PASS. Less = FAIL. There is no "almost," no "let's give it another week."
5. **If you find yourself wanting to add a feature, author a bundle instead.** This rule got harder, not easier, after Gates 0+1 passed.

## Memory pointers for the next session

- `~/.claude/projects/-Users-sidharthsatapathy-code/memory/MEMORY.md` — Sid's identity, preferences, active projects index
- `~/.claude/CLAUDE.md` — global instructions (graph routing, frontend workflow, orchestration playbook)
- `~/CLAUDE.md` — project-root instructions (Guvio context, persona)
- `feedback-no-coauthor.md` — no `Co-Authored-By` in commits (already violated twice, lazy-fix accepted)
- `feedback-no-guvio-public.md` — never mention Guvio/DPDPA/legal in public content (applies to Substrate posts too — relevant post-Gate-3)
- `feedback-council-before-posting.md` — `/council` before any public post (Gate 3)
- `feedback_no_main_commits.md` — global hook blocks direct main commits; substrate uses feature branches + squash merge

## One-line summary if you only read this

> **Use Substrate daily on real Guvio work, log every execution via the MCP client. 25 bundles + 50 uses + yes-velocity by Mon Jun 1 = PASS. Less = fold into Guvio. Do not add features.**

---

## Appendix A: Gate 0 (PASSED, historical record)

Gate 0 was the Friday May 15, 6 PM IST gate. The criterion was ≥5 `substrate use` entries with notes naming a real shipped artifact (Guvio PR, blog post draft, day-job RFC).

**Outcome: PASS at exactly 5 entries**, all generated by the May 15 Guvio agent-wave work. Sid acknowledged this is the bare threshold and not over-margined.

The full Gate 0 verdict block is preserved in git history at commits prior to `d6589f9`.

## Appendix B: Gate 1 (PASSED, 4 days early)

Gate 1 was the Wednesday May 20 gate. The criterion was a fresh Claude Code session resolving "look at my notes from May X and execute" through Substrate's MCP server, with `mcp-e2e` captured in `usage.log`.

**Outcome: PASS on Saturday May 16.** Evidence:

```
2026-05-16T00:23:45+05:30	2026-05-15-kb-mvp-first-principle	[claude-code] mcp-e2e
```

Implementation: `mcp_server.py`, 5 tools, shipped in PR #2 (`b3c280a`) and bug-fixed in PR #3 (`d6589f9`). 56 tests passing. User-scoped registration in `~/.claude.json` via `claude mcp add --scope user substrate -- substrate-mcp`.
