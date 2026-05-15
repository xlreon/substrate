# Substrate — Implementation Handoff

> For the next Claude (or future Sid) picking this up. Read top-to-bottom once, then refer back.

**Owner:** Sid — solo, also staff engineer + blogger + Guvio founder
**Last session ended:** May 11, 2026 (Sunday) — v0 shipped + SPEC.md drafted
**Hard gate:** **Gate 0 — Friday May 15, 6:00 PM IST**
**Authoritative docs:** [`SPEC.md`](./SPEC.md) (full spec), [`one-pager.md`](./one-pager.md) (product framing + council verdict)

---

## Read these first (in order, ~10 min)

1. **This file** — orientation
2. **`SPEC.md` §6** — gates and kill criteria (the rules)
3. **`SPEC.md` §5** — what tests/patches are allowed pre-Gate-0
4. **`one-pager.md`** "Dissent Worth Noting" section — the constraint you're operating under
5. **`cli.py`** — current implementation, 8 commands

## Where are we right now?

Run these three to orient yourself before doing anything:

```bash
date                                            # what day is it
substrate log --since 2026-05-11                # the metric
substrate log --since 2026-05-11 | grep -cE "guvio|blog|dayjob|rfc|pr-?#"   # gate-counting entries
substrate list                                  # what bundles exist
git -C ~/.substrate log --oneline | head -10    # recent authoring activity
```

Decision tree:

| Today is | Action |
|---|---|
| Mon May 11 → Thu May 14 | Trial week. See "Allowed work this week" below. |
| Fri May 15, before 6 PM IST | Push remaining real-use bundles. Last chance for the metric. |
| Fri May 15, after 6 PM IST | **Verify Gate 0.** See "Gate 0 verdict" below. |
| Sat May 16 → if Gate FAIL | Execute kill action (see below). Do not negotiate. |
| Sat May 16 → if Gate PASS | Open `SPEC.md` §3, begin MCP server. Gate 1 deadline = Wed May 20. |

## Allowed work this week (pre-Gate-0)

These are the **only** code changes allowed between now and Friday May 15, 6 PM IST. Anything else is scope creep the council explicitly forbade.

1. **`cli.py` patch (Section 5.3 / Appendix A of SPEC):**
   ```python
   ROOT = Path(os.environ.get("SUBSTRATE_HOME", Path.home() / ".substrate"))
   ```
   Add `import os` at top. One line change. Required for test isolation.

2. **`scripts/smoke.sh` (SPEC §5.5):** the six-command end-to-end smoke. Run before any change.

3. **`tests/test_helpers.py`:** unit tests for `_slug`, `_parse_frontmatter`, `_strip_frontmatter`, `_find_bundle`. Tight TDD. Use the `store` fixture pattern from SPEC §5.3.

4. **`pyproject.toml`:** add `[project.optional-dependencies] dev = ["pytest>=8", "pytest-cov", "ruff>=0.6", "mypy>=1.10"]`. Plus `[tool.ruff]` config (line-length 100, select `E,F,I,N,UP,B,SIM`).

5. **`README.md`:** stub only — just install + 5 example commands. Polish post-gate.

**Time budget:** 2–3 hours total across the week. Bundle authoring is the work, not tool-building.

## Forbidden this week

If you're tempted toward any of these before Friday 6 PM IST, **stop**. The council called this exact pattern out as escapism.

- ❌ MCP server (post-Wednesday conditional, not this week)
- ❌ `search` / `import` / `export` / `pin` / `link` / `stats` commands
- ❌ SQLite indexer
- ❌ Authoring app, Tauri, Electron, web UI
- ❌ GitHub Actions / CI
- ❌ OSS prep, license, contribution guide
- ❌ Landing page, marketing copy
- ❌ Renaming "Substrate" to something else (the name decision is post-gate)
- ❌ Adding context_refs to graphify/GitNexus/claude-mem
- ❌ Writing a blog post about Substrate
- ❌ Any work in `~/code/lattice/`, `~/code/billion/` plans, or other side projects (kill-list still applies)

## The metric, precisely

The only number that matters Friday 6 PM IST:

```bash
substrate log --since 2026-05-11 | grep -cE "guvio|blog|dayjob|rfc|pr-?#|design-doc"
```

Each line counted must be a `substrate use` invocation whose `--note` references a **real, named, shipped artifact** someone other than Sid has seen:
- `guvio-be-PR#142` (Guvio backend PR, merged or in review)
- `guvio-ui-PR#88`
- `blog-ai-coding-workflow-draft1` (blog post draft submitted or published)
- `dayjob-rfc-payments-v2` (RFC sent to a doc that teammates can comment on)
- `dayjob-pr-NNN`

Does NOT count:
- Empty notes, `test`, `experiment`, `trying it`, `me-playing`
- Notes for bundles you never shipped to anyone
- Bundles authored but never `used`

**Target: ≥5.** Less than 5 → FAIL. Five or more → PASS.

## Gate 0 verdict (run at 6 PM IST Friday May 15)

```bash
COUNT=$(substrate log --since 2026-05-11 | grep -cE "guvio|blog|dayjob|rfc|pr-?#|design-doc")
echo "Gate 0 count: $COUNT"
if [ "$COUNT" -ge 5 ]; then echo "PASS"; else echo "FAIL"; fi
```

### If FAIL — kill action

Do not negotiate. Do not extend. Do not move the goalposts.

```bash
# 1. Archive the code
mkdir -p ~/code/archive
mv ~/code/substrate ~/code/archive/substrate-2026-05

# 2. Delete the store
rm -rf ~/.substrate

# 3. Uninstall the CLI
uv tool uninstall substrate

# 4. Write postmortem (200 words max)
$EDITOR ~/code/billion/substrate-postmortem.md
```

The postmortem should answer three questions only:
- What did I think was true that turned out not to be?
- What did I avoid doing in Guvio this week to play with this?
- What's the rule I'll follow next time before starting project N+1?

Then update `~/.claude/projects/-Users-sidharthsatapathy/memory/MEMORY.md` with a new entry: `feedback-pre-launch-side-projects.md` pointing to the lesson.

### If PASS — next session opens to Gate 1

`SPEC.md §3` is the spec. `SPEC.md §6 Gate 1` is the deadline: Wednesday May 20. The natural-language test is:

> Open Claude Code in a fresh session, type *"look at my notes from May 11 and execute"*. Substrate's MCP server should resolve a bundle and run it end-to-end. Log entry note: `mcp-e2e`.

Implementation order for Gate 1 work:
1. Add `substrate-mcp` entrypoint in `pyproject.toml`
2. Implement `mcp_server.py` using the `mcp` Python SDK (see SPEC §3.3–3.4)
3. Register with Claude Code: `claude mcp add substrate -- substrate-mcp`
4. Contract tests (SPEC §3.9)
5. Manual cross-client smoke in Cursor + Zed before tagging v1.0

## Repository layout

```
~/code/substrate/
├── cli.py              ← v0 CLI, working, do not refactor pre-gate
├── pyproject.toml      ← packaging
├── .gitignore
├── one-pager.md        ← product framing, council verdict, dissent path
├── SPEC.md             ← full technical spec (6 sections + appendices)
└── HANDOFF.md          ← this file
```

Bundle store lives separately at `~/.substrate/` (git-versioned, do not confuse with project repo).

## Session log

### 2026-05-11 (Sunday)

**Worked through with Sid in one session:**
1. Surveyed market — prompt management (Langfuse/Braintrust/PromptLayer/Maxim/Humanloop) vs agentic SDLC (Devin/Rovo/Cursor BG) vs orchestration (ServiceNow/Domo).
2. Drafted one-pager identifying four moats: MCP-native, temporal addressing, skill analytics, Indian compliance.
3. Ran 5-advisor council. **Verdict: don't build as separate product.** Peer reviewer ranked Outsider strongest ("you've invented a parent company for a feature"). Chairman flagged universal blind spot: nobody asked which existing project dies.
4. Sid acknowledged council, chose **Executor's dissent path** (Friday gate or fold).
5. Built v0: `cli.py` (8 commands), `pyproject.toml`, installed via `uv tool install --editable`. Verified end-to-end smoke with manually-written bundle.
6. Sid revealed staff engineer + blogger context. Revised gate from Guvio-only to any-named-artifact (Guvio PR / blog post / day-job RFC).
7. Dispatched 6 parallel agents to draft SPEC sections. Synthesized into SPEC.md (666 lines).
8. Wrote this handoff.

**What's NOT decided / open questions:**
- Final product name (Substrate is working title)
- Whether to fold into Guvio as "Practice Knowledge" feature if Gate 2 passes but Gate 3 fails
- Authoring app stack (Tauri vs Electron vs raw Swift) — Gate 4 decision

**What needs to happen between now and next session:**
- Sid uses Substrate daily Mon–Fri authoring real bundles
- Sid notes each `use` with a real artifact reference
- Friday 6 PM IST: Gate 0 verdict run

## Discipline rules (lifted from council verdict)

1. **Memory before assumption.** Before adding any feature, check this file + SPEC §6 Gates. If the work isn't authorized by the current gate, don't do it.
2. **Falsifiability over vibes.** The metric is a `grep | wc -l`. Trust the number, not the feeling.
3. **No public talk pre-Gate-3.** No HN post, no tweet, no blog, no demo to friends. Substrate doesn't exist outside this folder until OSS prep is gate-authorized.
4. **The Friday gate is binary.** Five = PASS. Four = FAIL. There is no "almost," no "let's give it another week."
5. **If you find yourself wanting to add a feature, author a bundle instead.** That's the test.

## Memory pointers for the next session

- `~/.claude/projects/-Users-sidharthsatapathy/memory/MEMORY.md` — Sid's identity, preferences, active projects index
- `~/.claude/CLAUDE.md` — global instructions (graph routing, frontend workflow, orchestration playbook)
- `~/CLAUDE.md` — project-root instructions (Guvio context, telegram rules, persona)
- `feedback-no-coauthor.md` — no Co-Authored-By in commits
- `feedback-no-guvio-public.md` — never mention Guvio/DPDPA/legal in public content (applies to Substrate posts too)
- `feedback-council-before-posting.md` — `/council` before any public post

## One-line summary if you only read this

> **Author bundles, log uses with real artifact names, count on Friday. ≥5 named-artifact entries = continue. Less = archive Saturday. Do not build features this week.**
