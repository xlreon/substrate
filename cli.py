"""Substrate — local prompt+context bundles with git-backed versioning."""

from __future__ import annotations

import html
import json
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

import typer
import yaml
from markdown_it import MarkdownIt
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Local prompt+context bundles with versioning.", no_args_is_help=True)
console = Console()

ROOT = Path(os.environ.get("SUBSTRATE_HOME", Path.home() / ".substrate"))
BUNDLES = ROOT / "bundles"
USAGE_LOG = ROOT / "usage.log"

TEMPLATE = """---
id: {id}
created: {ts}
tags: {tags}
context_refs: []
---

# Prompt

<write your prompt here>

# Context

<paste files, graph queries, or notes here>
"""


def _ensure_init() -> None:
    if not (ROOT / ".git").exists():
        typer.echo("substrate not initialized. run: substrate init", err=True)
        raise typer.Exit(1)


def _git(*args: str) -> None:
    subprocess.run(["git", *args], cwd=ROOT, check=False, capture_output=True)


def _commit(msg: str) -> None:
    _git("add", "-A")
    _git("commit", "-m", msg, "--allow-empty")


def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "untitled"


def _parse_frontmatter(path: Path) -> dict:
    text = path.read_text()
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    return yaml.safe_load(text[3:end]) or {}


def _strip_frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return text
    end = text.find("\n---", 3)
    if end < 0:
        return text
    return text[end + 4 :].lstrip()


def _find_bundle(bundle_id: str) -> Path | None:
    for f in BUNDLES.rglob("*.md"):
        if _parse_frontmatter(f).get("id") == bundle_id:
            return f
    matches = [f for f in BUNDLES.rglob("*.md") if bundle_id in f.stem]
    if len(matches) == 1:
        return matches[0]
    return None


def _snippet(body: str, needle: str, width: int = 60) -> str:
    """One-line excerpt of ~width chars around the first match of needle in body."""
    if not needle:
        return ""
    idx = body.lower().find(needle.lower())
    if idx < 0:
        return ""
    start = max(0, idx - width // 2)
    end = min(len(body), idx + len(needle) + width // 2)
    excerpt = " ".join(body[start:end].split())
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(body) else ""
    return f"{prefix}{excerpt}{suffix}"


def _search_bundles(
    bundles_root: Path,
    query: str,
    tag: str | None = None,
    since: str | None = None,
    until: str | None = None,
    limit: int = 20,
) -> list[tuple[int, Path, dict, str]]:
    """Linear-scan search. Returns [(score, path, meta, snippet), ...] ranked desc.

    Phase 0 ranking: id hits ×3, tag hits ×2, body hits ×1. FTS5 lands in v1.0 (SPEC §4).
    """
    needle = query.lower()
    results: list[tuple[int, Path, dict, str]] = []
    for f in bundles_root.rglob("*.md"):
        date = f.parent.name
        if since and date < since:
            continue
        if until and date > until:
            continue
        meta = _parse_frontmatter(f)
        tags = [str(t) for t in (meta.get("tags") or [])]
        if tag and tag not in tags:
            continue
        bundle_id = str(meta.get("id") or f.stem)
        body = _strip_frontmatter(f.read_text())
        id_hits = bundle_id.lower().count(needle)
        tag_hits = sum(t.lower().count(needle) for t in tags)
        body_hits = body.lower().count(needle)
        if id_hits + tag_hits + body_hits == 0:
            continue
        score = id_hits * 3 + tag_hits * 2 + body_hits
        snippet = _snippet(body, needle) or (bundle_id if id_hits else ", ".join(tags))
        results.append((score, f, meta, snippet))
    results.sort(key=lambda r: (-r[0], str(r[1])))
    return results[:limit]


@app.command()
def init() -> None:
    """Initialize ~/.substrate as a versioned bundle store."""
    if (ROOT / ".git").exists():
        typer.echo(f"already initialized at {ROOT}")
        raise typer.Exit(1)
    BUNDLES.mkdir(parents=True, exist_ok=True)
    USAGE_LOG.touch()
    (ROOT / ".gitignore").write_text("usage.log\n")
    subprocess.run(["git", "init", "-b", "main"], cwd=ROOT, check=True, capture_output=True)
    _commit("init")
    typer.echo(f"initialized: {ROOT}")


@app.command()
def add(
    name: str,
    tag: list[str] = typer.Option([], "--tag", "-t", help="tag (repeatable)"),
) -> None:
    """Create a new bundle in today's folder and open it in $EDITOR."""
    _ensure_init()
    today = datetime.now().strftime("%Y-%m-%d")
    folder = BUNDLES / today
    folder.mkdir(exist_ok=True)
    slug = _slug(name)
    bundle_id = f"{today}-{slug}"
    path = folder / f"{slug}.md"
    if path.exists():
        typer.echo(f"already exists: {path}", err=True)
        raise typer.Exit(1)
    ts = datetime.now().astimezone().isoformat(timespec="seconds")
    path.write_text(TEMPLATE.format(id=bundle_id, ts=ts, tags=list(tag)))
    editor = os.environ.get("EDITOR", "nvim")
    subprocess.call([editor, str(path)])
    _commit(f"add {bundle_id}")
    typer.echo(f"saved: {bundle_id}")


@app.command(name="list")
def list_cmd(
    tag: str = typer.Option(None, "--tag", "-t"),
    date: str = typer.Option(None, "--date", "-d", help="YYYY-MM-DD"),
) -> None:
    """List bundles, optionally filtered by tag or date."""
    _ensure_init()
    table = Table(show_header=True, header_style="bold")
    table.add_column("id", style="cyan")
    table.add_column("tags", style="dim")
    table.add_column("path")
    rows = 0
    for f in sorted(BUNDLES.rglob("*.md")):
        meta = _parse_frontmatter(f)
        if date and date != f.parent.name:
            continue
        tags = meta.get("tags") or []
        if tag and tag not in tags:
            continue
        table.add_row(
            meta.get("id", f.stem),
            ", ".join(tags),
            str(f.relative_to(BUNDLES)),
        )
        rows += 1
    console.print(table)
    if rows == 0:
        typer.echo("(no bundles)")


@app.command()
def search(
    query: str = typer.Argument(..., help="substring to find (case-insensitive)"),
    tag: str = typer.Option(None, "--tag", "-t"),
    since: str = typer.Option(None, "--since", "-s", help="YYYY-MM-DD (inclusive)"),
    until: str = typer.Option(None, "--until", "-u", help="YYYY-MM-DD (inclusive)"),
    limit: int = typer.Option(20, "--limit", "-l"),
) -> None:
    """Find bundles by substring match across id, tags, and body."""
    _ensure_init()
    results = _search_bundles(BUNDLES, query, tag=tag, since=since, until=until, limit=limit)
    if not results:
        typer.echo("(no matches)")
        return
    table = Table(show_header=True, header_style="bold", title=f"{len(results)} match(es)")
    table.add_column("id", style="cyan")
    table.add_column("tags", style="dim")
    table.add_column("match")
    for _, f, meta, snippet in results:
        table.add_row(
            str(meta.get("id") or f.stem),
            ", ".join(str(t) for t in (meta.get("tags") or [])),
            snippet,
        )
    console.print(table)


@app.command()
def get(bundle_id: str) -> None:
    """Print a bundle to stdout (pipe-friendly)."""
    _ensure_init()
    f = _find_bundle(bundle_id)
    if not f:
        typer.echo(f"not found: {bundle_id}", err=True)
        raise typer.Exit(1)
    sys.stdout.write(f.read_text())


@app.command()
def use(
    bundle_id: str,
    note: str = typer.Option("", "--note", "-n", help="why you used it (e.g. Guvio PR #)"),
) -> None:
    """Copy a bundle to clipboard (without frontmatter) and log the use."""
    _ensure_init()
    f = _find_bundle(bundle_id)
    if not f:
        typer.echo(f"not found: {bundle_id}", err=True)
        raise typer.Exit(1)
    body = _strip_frontmatter(f.read_text())
    subprocess.run(["pbcopy"], input=body, text=True, check=False)
    meta = _parse_frontmatter(f)
    ts = datetime.now().astimezone().isoformat(timespec="seconds")
    with USAGE_LOG.open("a") as fp:
        fp.write(f"{ts}\t{meta.get('id', f.stem)}\t{note}\n")
    typer.echo(f"copied: {meta.get('id', f.stem)}")


@app.command()
def log(since: str = typer.Option(None, "--since", "-s", help="YYYY-MM-DD")) -> None:
    """Show usage log. This is the falsifiable metric."""
    _ensure_init()
    if not USAGE_LOG.exists() or USAGE_LOG.stat().st_size == 0:
        typer.echo("(no usage yet)")
        return
    lines = [l for l in USAGE_LOG.read_text().splitlines() if l]
    if since:
        lines = [l for l in lines if l.split("\t", 1)[0] >= since]
    table = Table(show_header=True, header_style="bold", title=f"{len(lines)} uses")
    table.add_column("when")
    table.add_column("bundle", style="cyan")
    table.add_column("note", style="dim")
    for line in lines:
        parts = line.split("\t")
        while len(parts) < 3:
            parts.append("")
        table.add_row(parts[0], parts[1], parts[2])
    console.print(table)


@app.command()
def edit(bundle_id: str) -> None:
    """Edit an existing bundle."""
    _ensure_init()
    f = _find_bundle(bundle_id)
    if not f:
        typer.echo(f"not found: {bundle_id}", err=True)
        raise typer.Exit(1)
    editor = os.environ.get("EDITOR", "nvim")
    subprocess.call([editor, str(f)])
    _commit(f"edit {_parse_frontmatter(f).get('id', f.stem)}")


_MEMORY_MD = Path.home() / ".claude/projects/-Users-sidharthsatapathy-code/memory/MEMORY.md"


def _read_memory_text() -> str:
    try:
        return _MEMORY_MD.read_text() if _MEMORY_MD.exists() else ""
    except Exception:
        return ""


def _find_active_bundle_id(memory_text: str) -> str | None:
    """Extract the bundle id behind the most recent 'NEXT SESSION KICKOFF' line."""
    for line in memory_text.splitlines():
        if "NEXT SESSION KICKOFF" not in line:
            continue
        m = re.search(r"~/\.substrate/bundles/(\d{4}-\d{2}-\d{2})/([^`\s/]+)\.md", line)
        if m:
            stem = m.group(2)
            return stem if stem.startswith(m.group(1)) else f"{m.group(1)}-{stem}"
    return None


def _commit_counts() -> dict[str, int]:
    """Return {bundles/YYYY-MM-DD/file.md: commit_count} via one git-log scan."""
    if not (ROOT / ".git").exists():
        return {}
    r = subprocess.run(
        ["git", "log", "--pretty=format:", "--name-only"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    counts: dict[str, int] = {}
    for raw in r.stdout.splitlines():
        line = raw.strip()
        if line.startswith("bundles/") and line.endswith(".md"):
            counts[line] = counts.get(line, 0) + 1
    return counts


def _usage_counts() -> dict[str, int]:
    """Return {bundle_id: count} from usage.log if present (legacy signal)."""
    if not USAGE_LOG.exists():
        return {}
    counts: Counter[str] = Counter()
    for line in USAGE_LOG.read_text().splitlines():
        parts = line.split("\t")
        if len(parts) >= 2 and parts[1]:
            counts[parts[1]] += 1
    return dict(counts)


def _short_id(bundle_id: str, day: str) -> str:
    return bundle_id[len(day) + 1 :] if day and bundle_id.startswith(day + "-") else bundle_id


def _build_chart(counts_by_day: dict[str, int], days: int = 30) -> tuple[str, str]:
    today = date.today()
    seq = [today - timedelta(days=i) for i in range(days - 1, -1, -1)]
    counts = [counts_by_day.get(d.isoformat(), 0) for d in seq]
    maxc = max(counts) or 1
    w, h = 400.0, 80.0
    gap = 2.0
    bar_w = (w - gap * (days - 1)) / days
    bars: list[str] = []
    for i, (d, c) in enumerate(zip(seq, counts)):
        bh = (c / maxc) * (h - 8) if c else 2.0
        x = i * (bar_w + gap)
        y = h - bh
        cls = "bar" if c else "bar zero"
        weekday = d.strftime("%a")
        bars.append(
            f'<rect class="{cls}" x="{x:.2f}" y="{y:.2f}" '
            f'width="{bar_w:.2f}" height="{bh:.2f}" rx="1.5">'
            f"<title>{d.isoformat()} ({weekday}) · {c} bundle{'s' if c != 1 else ''}</title></rect>"
        )
    svg = f'<svg viewBox="0 0 {w} {h}" preserveAspectRatio="none">{"".join(bars)}</svg>'
    return svg, seq[0].strftime("%d %b")


_DAY_LABELS = {0: "today", 1: "1 day ago", 2: "2 days ago"}


def _relative_label(day_str: str) -> str:
    try:
        d = date.fromisoformat(day_str)
    except ValueError:
        return ""
    delta = (date.today() - d).days
    return _DAY_LABELS.get(delta) or f"{delta} days ago"


_UI_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>substrate · {count} bundles</title>
<style>
:root {{
  --bg:#0a0c0f; --bg-elev:#12151a; --bg-hover:#1a1e25;
  --fg:#e8eaed; --dim:#8a8f98; --mute:#5a5f68;
  --line:#1f2329; --line-soft:#181b20;
  --accent:#ff8c42; --accent-2:#ffaa6a;
  --accent-soft:rgba(255,140,66,0.12); --accent-line:rgba(255,140,66,0.45);
  --success:#4ade80;
}}
*{{box-sizing:border-box}}
html,body{{margin:0;padding:0}}
body{{
  background:var(--bg);color:var(--fg);
  font:14px/1.55 -apple-system,BlinkMacSystemFont,"SF Pro Text",system-ui,sans-serif;
  font-feature-settings:"ss01","cv11";
  -webkit-font-smoothing:antialiased;
}}
.mono{{font-family:"SF Mono","JetBrains Mono",Menlo,monospace}}
button,input,textarea{{font-family:inherit;font-size:inherit;color:inherit}}
::-webkit-scrollbar{{width:10px;height:10px}}
::-webkit-scrollbar-thumb{{background:var(--line);border-radius:5px}}
::-webkit-scrollbar-thumb:hover{{background:#2a2f37}}

.app{{display:grid;grid-template-columns:320px 1fr;min-height:100vh}}
aside.sidebar{{
  position:sticky;top:0;height:100vh;overflow-y:auto;
  border-right:1px solid var(--line);background:var(--bg);
  padding:18px 16px 36px;
  display:flex;flex-direction:column;gap:22px;
}}
main.content{{padding:18px 28px 80px;max-width:920px;min-width:0}}

.brand{{display:flex;align-items:center;gap:9px}}
.brand .logo{{
  width:26px;height:26px;border-radius:7px;
  background:linear-gradient(135deg,var(--accent),#ff5e3a);
  display:inline-flex;align-items:center;justify-content:center;
  font-size:13px;font-weight:700;color:#1a0d04;letter-spacing:-0.04em;
}}
.brand h1{{margin:0;font-size:16px;font-weight:600;letter-spacing:-0.01em}}
.brand .count{{
  color:var(--dim);font-size:11.5px;margin-left:auto;
  font-variant-numeric:tabular-nums;
  background:var(--bg-elev);padding:2px 8px;border-radius:8px;
}}

.s-section h2{{
  margin:0 0 9px;font-size:10.5px;font-weight:600;
  text-transform:uppercase;letter-spacing:0.1em;color:var(--mute);
}}

.stats-grid{{display:grid;grid-template-columns:1fr 1fr;gap:6px}}
.stat{{
  background:var(--bg-elev);border:1px solid var(--line-soft);
  border-radius:8px;padding:10px 12px;
}}
.stat .label{{
  font-size:10px;color:var(--mute);
  text-transform:uppercase;letter-spacing:0.08em;
}}
.stat .value{{
  font-size:22px;font-weight:600;margin-top:1px;
  font-variant-numeric:tabular-nums;letter-spacing:-0.02em;
}}
.stat .sub{{font-size:11px;color:var(--dim);margin-top:0}}

.chart-wrap{{
  background:var(--bg-elev);border:1px solid var(--line-soft);
  border-radius:8px;padding:12px;
}}
.chart svg{{width:100%;height:80px;display:block;overflow:visible}}
.chart .bar{{fill:var(--accent);transition:fill 0.12s}}
.chart .bar.zero{{fill:#222731}}
.chart .bar:hover{{fill:var(--accent-2)}}
.chart-axis{{
  display:flex;justify-content:space-between;margin-top:6px;
  font-size:10px;color:var(--mute);font-variant-numeric:tabular-nums;
}}

.hot-list{{display:flex;flex-direction:column;gap:1px}}
.hot-item{{
  display:grid;grid-template-columns:1fr auto;gap:8px;align-items:center;
  padding:6px 9px;border-radius:6px;cursor:pointer;
  transition:background 0.1s;
}}
.hot-item:hover{{background:var(--bg-elev)}}
.hot-item .h-id{{
  color:var(--fg);overflow:hidden;text-overflow:ellipsis;
  white-space:nowrap;font-family:"SF Mono",Menlo,monospace;font-size:11.5px;
}}
.hot-item .h-score{{
  color:var(--accent);background:var(--accent-soft);
  font-size:10.5px;font-weight:600;padding:1px 7px;border-radius:8px;
  font-variant-numeric:tabular-nums;
}}

.tag-chips{{display:flex;flex-wrap:wrap;gap:4px}}
.tag-chip{{
  display:inline-flex;align-items:center;gap:5px;
  background:var(--bg-elev);color:var(--dim);
  border:1px solid var(--line-soft);
  border-radius:14px;padding:2px 9px;font-size:11px;
  cursor:pointer;user-select:none;transition:all 0.1s;
}}
.tag-chip:hover{{color:var(--fg);border-color:var(--line)}}
.tag-chip.active{{
  background:var(--accent-soft);color:var(--accent);
  border-color:var(--accent-line);
}}
.tag-chip .n{{
  color:var(--mute);font-size:10px;font-variant-numeric:tabular-nums;
}}
.tag-chip.active .n{{color:var(--accent)}}

.btn-add{{
  width:100%;padding:10px 14px;border:1px dashed var(--accent-line);
  background:transparent;color:var(--accent);
  border-radius:8px;cursor:pointer;font-weight:500;font-size:13px;
  display:flex;align-items:center;justify-content:center;gap:6px;
  transition:all 0.12s;
}}
.btn-add:hover{{background:var(--accent-soft);border-style:solid}}

.search-bar{{
  position:sticky;top:0;background:var(--bg);
  padding:2px 0 14px;z-index:5;
  border-bottom:1px solid transparent;transition:border-color 0.2s;
}}
.search-bar.scrolled{{border-bottom-color:var(--line)}}
.search-bar input{{
  width:100%;max-width:560px;
  background:var(--bg-elev);color:var(--fg);
  border:1px solid var(--line);
  border-radius:8px;padding:9px 12px;
  font-size:13.5px;
}}
.search-bar input:focus{{outline:none;border-color:var(--accent)}}
.search-bar .kbd{{
  position:absolute;right:calc(100% - 560px + 12px);top:50%;
  transform:translateY(-50%);
  font-family:"SF Mono",monospace;font-size:11px;color:var(--mute);
  background:var(--bg);padding:1px 5px;border:1px solid var(--line);
  border-radius:4px;pointer-events:none;
}}

.day-group{{margin-bottom:24px}}
.day-head{{
  position:sticky;top:48px;background:var(--bg);
  display:flex;align-items:baseline;gap:10px;
  padding:10px 0 8px;margin-bottom:6px;
  border-bottom:1px solid var(--line-soft);z-index:4;
}}
.day-head .date{{
  font-size:13px;font-weight:600;color:var(--fg);
  font-variant-numeric:tabular-nums;
}}
.day-head .weekday{{
  font-size:11px;color:var(--dim);
  text-transform:uppercase;letter-spacing:0.08em;
}}
.day-head .rel{{font-size:11px;color:var(--mute)}}
.day-head .n{{
  font-size:11px;color:var(--mute);margin-left:auto;
  font-variant-numeric:tabular-nums;
}}

.card{{
  background:var(--bg-elev);border:1px solid var(--line-soft);
  border-radius:10px;margin-bottom:7px;
  transition:border-color 0.12s,box-shadow 0.12s;
}}
.card:hover{{border-color:var(--line)}}
.card.active{{
  border-color:var(--accent-line);
  background:linear-gradient(180deg,rgba(255,140,66,0.05) 0%,var(--bg-elev) 60%);
  box-shadow:0 0 0 1px var(--accent-line),0 6px 24px -16px rgba(255,140,66,0.3);
}}
.card-head{{
  padding:10px 14px;
  display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:10px;
  cursor:pointer;
}}
.card-head .pill{{
  background:var(--accent);color:#1a0d04;
  font-size:9.5px;font-weight:700;padding:2px 7px;
  border-radius:8px;text-transform:uppercase;letter-spacing:0.06em;
}}
.card-head .id{{
  font-family:"SF Mono",Menlo,monospace;
  font-size:12.5px;color:var(--fg);font-weight:500;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0;
}}
.card.active .card-head .id{{color:var(--accent)}}
.card-head .meta-tags{{
  display:flex;flex-wrap:wrap;gap:4px;justify-content:flex-end;
  max-width:260px;
}}
.card-head .meta-tags span{{
  color:var(--mute);font-size:10.5px;
  background:var(--bg);padding:1px 7px;border-radius:6px;
  white-space:nowrap;
}}
.card-body{{
  display:none;padding:6px 18px 16px;
  border-top:1px solid var(--line-soft);color:#c8ccd2;
}}
.card.open .card-body{{display:block}}
.card-body h1,.card-body h2,.card-body h3{{color:var(--fg);margin:14px 0 6px}}
.card-body h1{{font-size:15px}}
.card-body h2{{font-size:13.5px}}
.card-body h3{{font-size:12.5px}}
.card-body p{{margin:6px 0}}
.card-body code{{
  background:var(--bg);padding:1px 5px;border-radius:3px;font-size:12px;
}}
.card-body pre{{
  background:var(--bg);padding:10px 12px;border-radius:6px;
  overflow-x:auto;border:1px solid var(--line);
  font-size:12px;line-height:1.5;
}}
.card-body pre code{{background:none;padding:0}}
.card-body a{{color:var(--accent)}}
.card-body ul,.card-body ol{{padding-left:22px;margin:6px 0}}
.card-body table{{border-collapse:collapse;margin:10px 0;font-size:12.5px}}
.card-body th,.card-body td{{border:1px solid var(--line);padding:4px 10px}}
.card-body th{{background:var(--bg);color:var(--fg)}}
.card-body blockquote{{
  border-left:3px solid var(--line);
  padding-left:12px;color:var(--dim);margin:8px 0;
}}
.empty{{color:var(--dim);padding:60px;text-align:center;font-size:13px}}

dialog.modal{{
  background:var(--bg-elev);border:1px solid var(--line);
  border-radius:12px;color:var(--fg);padding:0;
  width:min(880px,92vw);max-height:88vh;overflow:hidden;
  box-shadow:0 40px 80px -20px rgba(0,0,0,0.65);
}}
dialog.modal::backdrop{{
  background:rgba(0,0,0,0.6);backdrop-filter:blur(2px);
}}
.m-head{{
  padding:16px 20px;border-bottom:1px solid var(--line);
  display:flex;align-items:center;justify-content:space-between;
}}
.m-head h2{{margin:0;font-size:15px;font-weight:600}}
.m-head .close-btn{{
  background:transparent;color:var(--dim);border:none;
  cursor:pointer;font-size:16px;padding:4px 10px;border-radius:5px;
}}
.m-head .close-btn:hover{{color:var(--fg);background:var(--bg-hover)}}
.m-body{{
  padding:16px 20px;
  display:grid;grid-template-columns:1fr 1fr;gap:18px;
  max-height:calc(88vh - 130px);overflow-y:auto;
}}
.m-form{{display:flex;flex-direction:column;gap:11px}}
.m-form label{{display:flex;flex-direction:column;gap:4px}}
.m-form .field-label{{
  font-size:10.5px;color:var(--mute);
  text-transform:uppercase;letter-spacing:0.08em;
}}
.m-form input,.m-form textarea{{
  background:var(--bg);color:var(--fg);
  border:1px solid var(--line);border-radius:6px;
  padding:8px 10px;font-size:13px;
}}
.m-form input:focus,.m-form textarea:focus{{outline:none;border-color:var(--accent)}}
.m-form textarea{{
  min-height:220px;resize:vertical;
  font-family:"SF Mono",Menlo,monospace;font-size:12.5px;
}}
.m-form .hint{{font-size:11px;color:var(--mute);margin-top:-1px}}
.m-form .hint .mono{{color:var(--dim)}}
.m-preview{{
  background:var(--bg);border:1px solid var(--line);
  border-radius:6px;padding:12px 14px;overflow-y:auto;
}}
.m-preview .pv-label{{
  font-size:10px;color:var(--mute);
  text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;
}}
.m-preview pre{{
  font-family:"SF Mono",Menlo,monospace;font-size:11.5px;
  white-space:pre-wrap;word-break:break-word;color:var(--dim);margin:0;
}}
.m-foot{{
  padding:12px 20px;border-top:1px solid var(--line);
  display:flex;gap:8px;justify-content:flex-end;
}}
.btn{{
  background:var(--bg);color:var(--fg);
  border:1px solid var(--line);border-radius:6px;
  padding:7px 14px;font-size:12.5px;cursor:pointer;
  transition:all 0.12s;
}}
.btn:hover{{background:var(--bg-hover);border-color:var(--dim)}}
.btn-primary{{
  background:var(--accent);color:#1a0d04;
  border-color:var(--accent);font-weight:600;
}}
.btn-primary:hover{{background:var(--accent-2);border-color:var(--accent-2)}}

.toast{{
  position:fixed;bottom:24px;left:50%;transform:translateX(-50%) translateY(8px);
  background:var(--bg-elev);border:1px solid var(--accent-line);
  color:var(--fg);padding:9px 16px;border-radius:8px;font-size:13px;
  opacity:0;pointer-events:none;
  transition:opacity 0.18s,transform 0.18s;
  box-shadow:0 12px 32px -12px rgba(0,0,0,0.6);
}}
.toast.show{{opacity:1;transform:translateX(-50%) translateY(0)}}

@media (prefers-reduced-motion:reduce){{
  *{{transition:none !important}}
}}
@media (max-width:880px){{
  .app{{grid-template-columns:1fr}}
  aside.sidebar{{position:relative;height:auto;border-right:none;border-bottom:1px solid var(--line)}}
  .m-body{{grid-template-columns:1fr}}
}}
</style>
</head>
<body>
<div class="app">
  <aside class="sidebar">
    <div class="brand">
      <span class="logo">S</span>
      <h1>substrate</h1>
      <span class="count" id="brand-count">{count}</span>
    </div>

    <div class="s-section">
      <h2>Overview</h2>
      <div class="stats-grid">
        <div class="stat"><div class="label">Total</div><div class="value">{count}</div><div class="sub">bundles</div></div>
        <div class="stat"><div class="label">This week</div><div class="value">{this_week}</div><div class="sub">added</div></div>
        <div class="stat"><div class="label">Today</div><div class="value">{today_n}</div><div class="sub">new</div></div>
        <div class="stat"><div class="label">Last activity</div><div class="value">{last_n}</div><div class="sub">{last_label}</div></div>
      </div>
    </div>

    <div class="s-section">
      <h2>Activity · 30 days</h2>
      <div class="chart-wrap">
        <div class="chart">{chart_svg}</div>
        <div class="chart-axis"><span>{chart_start}</span><span>today</span></div>
      </div>
    </div>

    <div class="s-section">
      <h2>Most referenced</h2>
      <div class="hot-list">{hot_list}</div>
    </div>

    <div class="s-section">
      <h2>Tags</h2>
      <div class="tag-chips" id="tags-bar">{tag_chips}</div>
    </div>

    <button class="btn-add" id="add-btn">+&nbsp; New bundle</button>
  </aside>

  <main class="content">
    <div class="search-bar"><input id="q" type="text" placeholder="search id, tags, body…  (press /)" autocomplete="off"></div>
    <div id="timeline">{timeline}</div>
  </main>
</div>

<dialog class="modal" id="add-modal">
  <div class="m-head">
    <h2>New bundle</h2>
    <button class="close-btn" id="modal-close" aria-label="Close">✕</button>
  </div>
  <div class="m-body">
    <div class="m-form">
      <label>
        <span class="field-label">Name</span>
        <input id="f-name" type="text" placeholder="e.g. fly-staging-landmines" autocomplete="off">
        <span class="hint">→ <span class="mono" id="f-slug-preview">…</span></span>
      </label>
      <label>
        <span class="field-label">Tags (comma-separated)</span>
        <input id="f-tags" type="text" placeholder="e.g. handoff, guvio-backend, fly">
      </label>
      <label>
        <span class="field-label">Body (markdown)</span>
        <textarea id="f-body" placeholder="# Prompt&#10;&#10;<write here>&#10;&#10;# Context&#10;&#10;…"></textarea>
      </label>
    </div>
    <div class="m-preview">
      <div class="pv-label">Bundle file</div>
      <pre id="pv-content"></pre>
    </div>
  </div>
  <div class="m-foot">
    <button class="btn" id="btn-copy-md">Copy markdown</button>
    <button class="btn btn-primary" id="btn-copy-cmd">Copy bash command</button>
  </div>
</dialog>

<div class="toast" id="toast"></div>

<script>
const DATA = {data_json};
let activeTag = null;

const q = document.getElementById('q');
const tagsBar = document.getElementById('tags-bar');
const searchBar = document.querySelector('.search-bar');
const brandCount = document.getElementById('brand-count');
const TOTAL = {count};

function filter() {{
  const needle = q.value.trim().toLowerCase();
  let shown = 0;
  document.querySelectorAll('.card').forEach((el) => {{
    const i = parseInt(el.dataset.idx, 10);
    const d = DATA[i];
    const matchesText = !needle ||
      d.id.toLowerCase().includes(needle) ||
      d.tags.some(t => t.toLowerCase().includes(needle)) ||
      d.body_text.toLowerCase().includes(needle);
    const matchesTag = !activeTag || d.tags.includes(activeTag);
    const show = matchesText && matchesTag;
    el.style.display = show ? '' : 'none';
    if (show) shown++;
  }});
  document.querySelectorAll('.day-group').forEach(g => {{
    const anyVisible = [...g.querySelectorAll('.card')].some(c => c.style.display !== 'none');
    g.style.display = anyVisible ? '' : 'none';
  }});
  brandCount.textContent = (shown === TOTAL) ? TOTAL : (shown + ' / ' + TOTAL);
}}
q.addEventListener('input', filter);

tagsBar.querySelectorAll('.tag-chip').forEach(chip => {{
  chip.addEventListener('click', () => {{
    const t = chip.dataset.tag;
    activeTag = (activeTag === t) ? null : t;
    tagsBar.querySelectorAll('.tag-chip').forEach(c =>
      c.classList.toggle('active', c.dataset.tag === activeTag));
    filter();
  }});
}});

document.querySelectorAll('.hot-item').forEach(item => {{
  item.addEventListener('click', () => {{
    const id = item.dataset.id;
    const card = document.querySelector(`.card[data-id="${{id}}"]`);
    if (card) {{
      card.classList.add('open');
      card.scrollIntoView({{behavior:'smooth', block:'center'}});
      card.style.outline = '1px solid var(--accent)';
      setTimeout(() => card.style.outline = '', 1200);
    }}
  }});
}});

document.querySelectorAll('.card-head').forEach(h => {{
  h.addEventListener('click', () => h.parentElement.classList.toggle('open'));
}});

const activeCard = document.querySelector('.card.active');
if (activeCard) activeCard.classList.add('open');

window.addEventListener('scroll', () => {{
  searchBar.classList.toggle('scrolled', window.scrollY > 6);
}}, {{passive:true}});

const toast = document.getElementById('toast');
function showToast(msg) {{
  toast.textContent = msg;
  toast.classList.add('show');
  clearTimeout(showToast._t);
  showToast._t = setTimeout(() => toast.classList.remove('show'), 1800);
}}

const modal = document.getElementById('add-modal');
const fName = document.getElementById('f-name');
const fTags = document.getElementById('f-tags');
const fBody = document.getElementById('f-body');
const slugPreview = document.getElementById('f-slug-preview');
const pvContent = document.getElementById('pv-content');

const today = new Date().toISOString().slice(0, 10);
function nowIso() {{
  const d = new Date();
  const tz = -d.getTimezoneOffset();
  const sign = tz >= 0 ? '+' : '-';
  const hh = String(Math.floor(Math.abs(tz)/60)).padStart(2,'0');
  const mm = String(Math.abs(tz)%60).padStart(2,'0');
  return d.toISOString().slice(0,19) + sign + hh + ':' + mm;
}}
function slugify(s) {{
  return (s||'').toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/(^-|-$)/g,'') || 'untitled';
}}
function buildBundle() {{
  const slug = slugify(fName.value);
  const id = `${{today}}-${{slug}}`;
  const tags = fTags.value.split(',').map(t => t.trim()).filter(Boolean);
  const body = fBody.value || '# Prompt\\n\\n<write here>\\n';
  const tagYaml = '[' + tags.map(t => JSON.stringify(t)).join(', ') + ']';
  const fm = `---\\nid: ${{id}}\\ncreated: ${{nowIso()}}\\ntags: ${{tagYaml}}\\ncontext_refs: []\\n---\\n\\n${{body}}\\n`;
  slugPreview.textContent = id;
  pvContent.textContent = fm;
  return {{slug, id, fm}};
}}
[fName, fTags, fBody].forEach(el => el.addEventListener('input', buildBundle));

document.getElementById('add-btn').addEventListener('click', () => {{
  buildBundle();
  modal.showModal();
  fName.focus();
}});
document.getElementById('modal-close').addEventListener('click', () => modal.close());
modal.addEventListener('click', (e) => {{
  if (e.target === modal) modal.close();
}});

document.getElementById('btn-copy-md').addEventListener('click', async () => {{
  const {{fm}} = buildBundle();
  await navigator.clipboard.writeText(fm);
  showToast('Markdown copied');
}});
document.getElementById('btn-copy-cmd').addEventListener('click', async () => {{
  const {{slug, id, fm}} = buildBundle();
  const cmd = `mkdir -p ~/.substrate/bundles/${{today}} && cat > ~/.substrate/bundles/${{today}}/${{slug}}.md <<'BUNDLE_EOF'\\n${{fm}}BUNDLE_EOF\\n( cd ~/.substrate && git add -A && git commit -m "add ${{id}}" ) && substrate ui`;
  await navigator.clipboard.writeText(cmd);
  showToast('Bash command copied — paste & run');
}});

document.addEventListener('keydown', (e) => {{
  if (e.key === '/' && document.activeElement !== q && !modal.open) {{
    e.preventDefault(); q.focus();
  }}
  if (e.key === 'Escape' && modal.open) modal.close();
}});
</script>
</body>
</html>
"""


def _render_card(b: dict, is_active: bool, idx: int) -> str:
    tag_html = "".join(f"<span>{html.escape(t)}</span>" for t in b["tags"][:5])
    pill = '<span class="pill">active</span>' if is_active else ""
    return (
        f'<div class="card{" active" if is_active else ""}" '
        f'data-idx="{idx}" data-id="{html.escape(b["id"])}">'
        f'<div class="card-head">'
        f"{pill or '<span></span>'}"
        f'<span class="id">{html.escape(b["id"])}</span>'
        f'<span class="meta-tags">{tag_html}</span>'
        f"</div>"
        f'<div class="card-body">{b["body_html"]}</div>'
        f"</div>"
    )


@app.command()
def ui(
    output: Path = typer.Option(
        None, "--output", "-o", help="output html path (default ~/.substrate/index.html)"
    ),
    open_browser: bool = typer.Option(False, "--open", help="open in browser after writing"),
) -> None:
    """Generate a static HTML dashboard of all bundles."""
    _ensure_init()
    out_path = output or (ROOT / "index.html")
    md = MarkdownIt("commonmark", {"html": False, "linkify": True, "typographer": True}).enable(
        "table"
    )

    memory_text = _read_memory_text()
    commit_counts = _commit_counts()
    usage_counts = _usage_counts()
    active_id = _find_active_bundle_id(memory_text)

    bundles: list[dict] = []
    for f in BUNDLES.rglob("*.md"):
        text = f.read_text()
        meta = _parse_frontmatter(f)
        body = _strip_frontmatter(text)
        tags = [str(t) for t in (meta.get("tags") or [])]
        day = f.parent.name if re.match(r"^\d{4}-\d{2}-\d{2}$", f.parent.name) else ""
        meta_id = meta.get("id")
        if meta_id:
            bundle_id = str(meta_id)
        elif day and not f.stem.startswith(day):
            bundle_id = f"{day}-{f.stem}"
        else:
            bundle_id = f.stem
        rel = str(f.relative_to(ROOT))
        short = _short_id(bundle_id, day)
        mentions = (
            (
                memory_text.count(bundle_id)
                + (memory_text.count(short) if short != bundle_id else 0)
                + memory_text.count(rel)
            )
            if memory_text
            else 0
        )
        commits = commit_counts.get(rel, 0)
        uses = usage_counts.get(bundle_id, 0)
        hot = mentions * 4 + commits + uses * 2 + (8 if bundle_id == active_id else 0)
        bundles.append(
            {
                "id": bundle_id,
                "tags": tags,
                "day": day,
                "mtime": f.stat().st_mtime,
                "body_html": md.render(body),
                "body_text": body,
                "mentions": mentions,
                "commits": commits,
                "uses": uses,
                "hot": hot,
            }
        )
    bundles.sort(key=lambda b: b["mtime"], reverse=True)

    tag_counts: Counter[str] = Counter()
    counts_by_day: Counter[str] = Counter()
    today_str = date.today().isoformat()
    week_ago = (date.today() - timedelta(days=6)).isoformat()
    for b in bundles:
        tag_counts.update(b["tags"])
        if b["day"]:
            counts_by_day[b["day"]] += 1

    this_week = sum(c for d, c in counts_by_day.items() if d >= week_ago)
    today_n = counts_by_day.get(today_str, 0)
    last_day = max(counts_by_day.keys(), default="")
    last_n = counts_by_day.get(last_day, 0)
    last_label = _relative_label(last_day) if last_day else "—"

    chart_svg, chart_start = _build_chart(dict(counts_by_day))

    hot_items = sorted(bundles, key=lambda b: (-b["hot"], -b["mtime"]))[:8]
    hot_html = (
        "".join(
            f'<div class="hot-item" data-id="{html.escape(b["id"])}">'
            f'<span class="h-id">{html.escape(_short_id(b["id"], b["day"]) or b["id"])}</span>'
            f'<span class="h-score">{b["hot"]}</span>'
            f"</div>"
            for b in hot_items
            if b["hot"] > 0
        )
        or '<div class="hot-item"><span class="h-id" style="color:var(--mute)">no signal yet</span></div>'
    )

    tag_chips_html = "".join(
        f'<span class="tag-chip" data-tag="{html.escape(t)}">'
        f'{html.escape(t)}<span class="n">{n}</span></span>'
        for t, n in tag_counts.most_common(20)
    )

    groups: dict[str, list[dict]] = {}
    for i, b in enumerate(bundles):
        b["_idx"] = i
        groups.setdefault(b["day"] or "undated", []).append(b)
    ordered_days = sorted(groups.keys(), reverse=True)

    timeline_parts: list[str] = []
    for day in ordered_days:
        day_bundles = groups[day]
        if day == "undated":
            head = (
                '<div class="day-head"><span class="date">Undated</span>'
                f'<span class="n">{len(day_bundles)}</span></div>'
            )
        else:
            try:
                d = date.fromisoformat(day)
                weekday = d.strftime("%a")
                pretty = d.strftime("%d %b %Y")
                rel = _relative_label(day)
                head = (
                    f'<div class="day-head">'
                    f'<span class="weekday">{weekday}</span>'
                    f'<span class="date">{pretty}</span>'
                    f'<span class="rel">· {rel}</span>'
                    f'<span class="n">{len(day_bundles)} bundle{"s" if len(day_bundles) != 1 else ""}</span>'
                    f"</div>"
                )
            except ValueError:
                head = f'<div class="day-head"><span class="date">{html.escape(day)}</span></div>'
        cards = "".join(_render_card(b, b["id"] == active_id, b["_idx"]) for b in day_bundles)
        timeline_parts.append(f'<div class="day-group">{head}{cards}</div>')

    data_json = json.dumps(
        [{"id": b["id"], "tags": b["tags"], "body_text": b["body_text"]} for b in bundles]
    )
    rendered = _UI_TEMPLATE.format(
        count=len(bundles),
        this_week=this_week,
        today_n=today_n,
        last_n=last_n,
        last_label=html.escape(last_label),
        chart_svg=chart_svg,
        chart_start=html.escape(chart_start),
        hot_list=hot_html,
        tag_chips=tag_chips_html,
        timeline="".join(timeline_parts)
        or '<div class="empty">no bundles yet — click <span class="mono">+ New bundle</span></div>',
        data_json=data_json,
    )
    out_path.write_text(rendered)
    typer.echo(
        f"wrote {out_path} · {len(bundles)} bundles · "
        f"active: {active_id or '—'} · this week: {this_week}"
    )
    if open_browser:
        subprocess.run(["open", str(out_path)], check=False)


@app.command()
def history(bundle_id: str) -> None:
    """Show git history for a bundle."""
    _ensure_init()
    f = _find_bundle(bundle_id)
    if not f:
        typer.echo(f"not found: {bundle_id}", err=True)
        raise typer.Exit(1)
    rel = f.relative_to(ROOT)
    subprocess.run(
        ["git", "log", "--oneline", "--", str(rel)],
        cwd=ROOT,
        check=False,
    )


if __name__ == "__main__":
    app()
