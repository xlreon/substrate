"""Substrate — local prompt+context bundles with git-backed versioning."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import typer
import yaml
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
