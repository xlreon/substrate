# [Working title: Substrate] — One-Pager

**Tagline:** *Prompt+context source-of-truth. MCP-served. Agent-agnostic.*

---

## Problem

Every team using AI seriously hits the same wall: the prompts and context that produce good output are **buried in chats, copy-pasted across tools, lost between sessions, and impossible to govern**. As more agents (Claude Code, Cursor, Devin, Rovo) enter the workflow, the problem multiplies — each tool reinvents its own context plumbing. There is no shared substrate.

## Insight

Companies don't actually need another agent. They need a **versioned, reviewable, MCP-callable layer of prompt+context bundles** that any agent can consume. The agents change every quarter. The way work gets defined, approved, and learned from shouldn't.

## Product (v1)

A local-first **MCP-native prompt+context library** with three primitives:

1. **Bundles** — markdown prompt + pinned context refs (files, graph queries, memory, URLs) + metadata (date, tags, author).
2. **Authoring app** — write a prompt, see live context suggestions from your existing knowledge (graphify/GitNexus/claude-mem substrate), pin what helps, save.
3. **MCP server** — exposes `search_by_date`, `search_by_tag`, `get_bundle` to any MCP client. Claude Code, Cursor, Zed, Claude Desktop all become consumers.

> *"Look at my notes from May 10 and execute"* → Claude resolves the bundle via MCP → runs with full context.

## Why now

- MCP shipped in 2024, hit critical mass in late 2025. Every major AI client supports it.
- Anthropic's memory tool + Claude Projects validates the personal-context surface but ships flat (no temporal addressing, no cross-client portability).
- Agent count per developer is exploding. Each one needs context. Nobody owns the substrate.

## Why me

- **Built the substrate already** — graphify, GitNexus, claude-mem, auto-memory layered for personal use. The retrieval layer that competitors take 6 months to build, I've been running for months.
- **Dogfood loop** — Guvio (legal SaaS) is mid-launch. Building v1 lets me ship Guvio faster with reusable bundles. Same builder, same week, two products improving each other.
- **Compliance instincts** — Guvio's DPDPA scar tissue maps directly onto the enterprise edition's audit/RBAC/on-prem requirements that Western incumbents will deprioritize for 2 years.

## Wedge sequence

| Phase | Surface | Buyer | Goal |
|---|---|---|---|
| **v1 — Personal (OSS, free)** | CLI + MCP server + folder convention | Individual builders | Distribution + dogfood + community |
| **v2 — Authoring app + analytics** | Tauri/Electron + skill diagnostics from exports | $20/seat indie/SMB | First revenue, proves coaching layer |
| **v3 — Team workspaces** | Shared bundles, approval workflow, eval scoring | $50/seat startups | Recurring SaaS |
| **v4 — Enterprise CI/CD** | Jira/Linear → approved bundle → agent dispatch → audit | $50K+/yr Indian regulated, then global | Defensible enterprise moat |

## Moat

- **MCP-native distribution.** Lives wherever the user's AI lives. Incumbents are SDK/login-gated.
- **Temporal addressing.** Journal-style UX nobody else has shipped.
- **Skill analytics from exports.** Anthropic won't build this — surfaces inefficiency. CFO line item.
- **Compliance-first variant.** DPDPA/RBI/SEBI shape known from Guvio. Western incumbents 18-24 months behind.

## Market & competition (compressed)

- **Direct (prompt mgmt):** Langfuse, Braintrust, PromptLayer, Maxim, Humanloop. All team-SaaS, none MCP-native, none personal-first, none coach-aware.
- **Adjacent (agentic SDLC):** Devin, Cursor BG, Rovo Dev, GitHub Copilot Agent. **Not competitors — consumers.** Substrate fuels them.
- **Existential threat:** Anthropic ships Projects+memory expansion that absorbs v1. Mitigation: model-agnostic via MCP. If they win Claude, you still have Cursor, Zed, ChatGPT, internal agents.

## Mission

> Make every prompt and context decision a person or company makes a versioned, reviewable, reusable asset — fuel for any AI agent, traceable across every workflow.

## Vision

> The governance layer for the AI-first enterprise. The agents will change. The way work gets defined, approved, and learned from doesn't have to.

## 90-day milestones

- **Week 1–2:** v1 ships. Folder convention + CLI + MCP server. Used personally on Guvio backlog.
- **Week 3–6:** Measure Guvio velocity delta vs prior 6 weeks. Target: **30%+ faster on similar-shaped tasks** (eng or doc).
- **Week 7–10:** Open-source release. Soft launch on HN/X. Goal: 200 GitHub stars, 20 active users telling you what hurts.
- **Week 11–12:** Decide v2 build-or-fold based on (a) personal velocity proof, (b) external pull, (c) Guvio launch state.

## Risks & mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Anthropic ships equivalent | High | Model-agnostic from day one. Distribution moat via MCP, not product. |
| Distraction from Guvio | High | Dogfood-or-die rule: if v1 isn't speeding up Guvio by week 6, kill it. |
| Cursor/Continue absorb the live-suggest UX | Medium | Substrate ≠ editor. They'd need to ship MCP server + cross-client. Adjacent, not equivalent. |
| Indian compliance moat is narrower than I think | Medium | Validate with 3 lawyer/CA/CS firms in Bangalore (Guvio network) before v4. |
| OSS gives away the moat | Low | The moat is not the code — it's the bundle network effect, the analytics IP, and the compliance edition. |

## Single decision criterion

> *Does v1 measurably speed up Guvio shipping over 6 weeks?*

Yes → v2 in Q3.
No → fold it into Guvio as the lawyer-AI-coach module and stop calling it a separate product.
