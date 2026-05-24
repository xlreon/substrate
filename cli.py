"""Substrate — local prompt+context bundles with git-backed versioning."""

from __future__ import annotations

import html
import json
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime
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


def _find_active_bundle_id() -> str | None:
    """Read MEMORY.md and extract the bundle filename behind 'NEXT SESSION KICKOFF'."""
    if not _MEMORY_MD.exists():
        return None
    for line in _MEMORY_MD.read_text().splitlines():
        if "NEXT SESSION KICKOFF" not in line:
            continue
        m = re.search(r"~/\.substrate/bundles/(\d{4}-\d{2}-\d{2})/([^`\s/]+)\.md", line)
        if m:
            return (
                f"{m.group(1)}-{m.group(2)}"
                if not m.group(2).startswith(m.group(1))
                else m.group(2)
            )
    return None


_UI_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>substrate — {count} bundles</title>
<style>
  :root {{
    --bg: #0d0f12; --fg: #e4e6eb; --dim: #8a8f98; --line: #1f2329;
    --accent: #ff8c42; --accent-dim: #4a3120; --card: #14171c; --hover: #1a1e25;
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; padding: 0; background: var(--bg); color: var(--fg);
          font: 14px/1.55 -apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif; }}
  code, pre, .mono {{ font: 13px/1.5 "SF Mono", Menlo, monospace; }}
  header {{ position: sticky; top: 0; background: var(--bg); border-bottom: 1px solid var(--line);
            padding: 14px 22px; z-index: 10; }}
  header h1 {{ margin: 0 0 8px; font-size: 16px; font-weight: 600; }}
  header h1 .meta {{ color: var(--dim); font-weight: 400; margin-left: 10px; font-size: 13px; }}
  header input {{ width: 100%; max-width: 480px; background: var(--card); color: var(--fg);
                  border: 1px solid var(--line); border-radius: 6px; padding: 7px 10px; font-size: 13px; }}
  header input:focus {{ outline: none; border-color: var(--accent); }}
  .tags-bar {{ margin-top: 10px; display: flex; flex-wrap: wrap; gap: 6px; }}
  .tag-chip {{ background: var(--card); color: var(--dim); border: 1px solid var(--line);
               border-radius: 12px; padding: 2px 9px; font-size: 11px; cursor: pointer;
               user-select: none; transition: all 0.15s; }}
  .tag-chip:hover {{ color: var(--fg); border-color: var(--dim); }}
  .tag-chip.active {{ background: var(--accent-dim); color: var(--accent); border-color: var(--accent); }}
  main {{ padding: 20px 22px 60px; max-width: 980px; }}
  .card {{ background: var(--card); border: 1px solid var(--line); border-radius: 8px;
           margin-bottom: 12px; transition: border-color 0.15s; }}
  .card:hover {{ border-color: #2a2f37; }}
  .card.active {{ border-color: var(--accent); background: linear-gradient(180deg, #1c1410 0%, var(--card) 60%); }}
  .card-head {{ padding: 12px 16px; cursor: pointer; display: flex; align-items: baseline;
                gap: 10px; flex-wrap: wrap; }}
  .card-head .id {{ color: var(--fg); font-weight: 500; font-size: 13.5px; }}
  .card.active .card-head .id {{ color: var(--accent); }}
  .card-head .date {{ color: var(--dim); font-size: 12px; }}
  .card-head .tags {{ margin-left: auto; display: flex; gap: 4px; flex-wrap: wrap; }}
  .card-head .tags span {{ color: var(--dim); font-size: 11px;
                            background: var(--bg); padding: 1px 6px; border-radius: 8px; }}
  .card-body {{ display: none; padding: 4px 22px 18px; border-top: 1px solid var(--line);
                color: #cbd0d6; }}
  .card.open .card-body {{ display: block; }}
  .card-body h1, .card-body h2, .card-body h3 {{ color: var(--fg); margin: 18px 0 8px; }}
  .card-body h1 {{ font-size: 16px; }}
  .card-body h2 {{ font-size: 14.5px; }}
  .card-body h3 {{ font-size: 13.5px; }}
  .card-body p {{ margin: 8px 0; }}
  .card-body code {{ background: var(--bg); padding: 1px 5px; border-radius: 3px; }}
  .card-body pre {{ background: var(--bg); padding: 10px 12px; border-radius: 5px; overflow-x: auto;
                    border: 1px solid var(--line); }}
  .card-body pre code {{ background: none; padding: 0; }}
  .card-body a {{ color: var(--accent); }}
  .card-body ul, .card-body ol {{ padding-left: 22px; }}
  .card-body table {{ border-collapse: collapse; margin: 10px 0; }}
  .card-body th, .card-body td {{ border: 1px solid var(--line); padding: 4px 10px; font-size: 13px; }}
  .card-body blockquote {{ border-left: 3px solid var(--line); padding-left: 12px; color: var(--dim); margin: 8px 0; }}
  .empty {{ color: var(--dim); padding: 40px; text-align: center; }}
  .pill {{ background: var(--accent); color: var(--bg); font-size: 10px; font-weight: 600;
           padding: 1px 7px; border-radius: 8px; text-transform: uppercase; letter-spacing: 0.3px; }}
</style>
</head>
<body>
<header>
  <h1>substrate <span class="meta">{count} bundles · regenerated {built_at}</span></h1>
  <input id="q" type="text" placeholder="search id, tags, body…" autocomplete="off">
  <div class="tags-bar" id="tags-bar"></div>
</header>
<main id="cards">{cards}</main>
<script>
  const DATA = {data_json};
  const cards = document.getElementById('cards');
  const q = document.getElementById('q');
  const tagsBar = document.getElementById('tags-bar');
  let activeTag = null;

  // Build tag chips, sorted by count desc
  const tagCounts = {tag_counts_json};
  Object.entries(tagCounts).sort((a,b) => b[1]-a[1]).slice(0, 30).forEach(([t, n]) => {{
    const chip = document.createElement('span');
    chip.className = 'tag-chip';
    chip.textContent = t + ' ' + n;
    chip.dataset.tag = t;
    chip.addEventListener('click', () => {{
      activeTag = (activeTag === t) ? null : t;
      [...tagsBar.children].forEach(c => c.classList.toggle('active', c.dataset.tag === activeTag));
      filter();
    }});
    tagsBar.appendChild(chip);
  }});

  function filter() {{
    const needle = q.value.trim().toLowerCase();
    let shown = 0;
    document.querySelectorAll('.card').forEach((el, i) => {{
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
    document.querySelector('header h1 .meta').textContent =
      shown + ' of {count} bundles · regenerated {built_at}';
  }}

  q.addEventListener('input', filter);

  // Click to expand
  document.querySelectorAll('.card-head').forEach(h => {{
    h.addEventListener('click', () => h.parentElement.classList.toggle('open'));
  }});

  // Auto-expand the active card
  const active = document.querySelector('.card.active');
  if (active) active.classList.add('open');
</script>
</body>
</html>
"""


def _render_card(b: dict, is_active: bool) -> str:
    tag_html = "".join(f"<span>{html.escape(t)}</span>" for t in b["tags"][:6])
    pill = '<span class="pill">active</span> ' if is_active else ""
    return (
        f'<div class="card{" active" if is_active else ""}">'
        f'<div class="card-head">{pill}'
        f'<span class="id mono">{html.escape(b["id"])}</span>'
        f'<span class="date">{html.escape(b["date"])}</span>'
        f'<span class="tags">{tag_html}</span>'
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

    bundles: list[dict] = []
    for f in BUNDLES.rglob("*.md"):
        text = f.read_text()
        meta = _parse_frontmatter(f)
        body = _strip_frontmatter(text)
        tags = [str(t) for t in (meta.get("tags") or [])]
        bundle_id = str(meta.get("id") or f.stem)
        bundles.append(
            {
                "id": bundle_id,
                "tags": tags,
                "date": f.parent.name if re.match(r"^\d{4}-\d{2}-\d{2}$", f.parent.name) else "",
                "mtime": f.stat().st_mtime,
                "body_html": md.render(body),
                "body_text": body,
            }
        )
    bundles.sort(key=lambda b: b["mtime"], reverse=True)

    active_id = _find_active_bundle_id()
    tag_counts: Counter[str] = Counter()
    for b in bundles:
        tag_counts.update(b["tags"])

    cards_html = "".join(_render_card(b, b["id"] == active_id) for b in bundles)
    data_json = json.dumps(
        [{"id": b["id"], "tags": b["tags"], "body_text": b["body_text"]} for b in bundles]
    )
    built_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    rendered = _UI_TEMPLATE.format(
        count=len(bundles),
        built_at=built_at,
        cards=cards_html or '<div class="empty">no bundles yet</div>',
        data_json=data_json,
        tag_counts_json=json.dumps(dict(tag_counts)),
    )
    out_path.write_text(rendered)
    typer.echo(f"wrote {out_path} ({len(bundles)} bundles, active: {active_id or '—'})")
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
