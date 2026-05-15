"""Substrate MCP server — exposes the bundle store over stdio JSON-RPC."""

from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime
from typing import Any

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from cli import (
    BUNDLES,
    ROOT,
    USAGE_LOG,
    _find_bundle,
    _parse_frontmatter,
    _search_bundles,
    _strip_frontmatter,
)

server = Server(
    "substrate",
    version="1.0.0",
    instructions=(
        "Substrate is a local prompt+context bundle store. Use list_bundles to enumerate, "
        "get_by_date for temporal queries ('notes from May 11'), search_bundles for "
        "substring lookup, get_bundle to fetch a bundle by id, and log_use to record "
        "that you executed one. Bundles are read-only over MCP; authoring is CLI-only."
    ),
)

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DATE_RANGE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.\.(\d{4}-\d{2}-\d{2})$")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9\-]*$")


class SubstrateError(Exception):
    """Domain error returned to clients as structured isError content."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _check_init() -> None:
    if not (ROOT / ".git").exists():
        raise SubstrateError(
            "not_initialized",
            f"substrate not initialized at {ROOT}; run `substrate init`",
        )


def _bundle_summary(f, meta: dict) -> dict:
    return {
        "id": str(meta.get("id") or f.stem),
        "tags": [str(t) for t in (meta.get("tags") or [])],
        "path": str(f.relative_to(BUNDLES)),
        "created": str(meta.get("created") or f.parent.name),
    }


def _parse_date_arg(date: str) -> tuple[str, str]:
    """Return (since, until) inclusive bounds. Accepts YYYY-MM-DD or YYYY-MM-DD..YYYY-MM-DD."""
    m = DATE_RANGE_RE.match(date)
    if m:
        return m.group(1), m.group(2)
    if DATE_RE.match(date):
        return date, date
    raise SubstrateError(
        "invalid_date", f"expected YYYY-MM-DD or YYYY-MM-DD..YYYY-MM-DD, got {date!r}"
    )


def _error(code: str, message: str) -> list[types.TextContent]:
    """Errors return UnstructuredContent so they bypass outputSchema validation."""
    return [types.TextContent(type="text", text=json.dumps({"error": code, "message": message}))]


TOOLS: list[types.Tool] = [
    types.Tool(
        name="list_bundles",
        description="Enumerate bundles, optionally filtered by tag and/or date.",
        inputSchema={
            "type": "object",
            "properties": {
                "tag": {"type": "string"},
                "date": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$"},
                "limit": {"type": "integer", "default": 50, "minimum": 1, "maximum": 500},
            },
            "additionalProperties": False,
        },
        outputSchema={
            "type": "object",
            "properties": {
                "bundles": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "tags": {"type": "array", "items": {"type": "string"}},
                            "path": {"type": "string"},
                            "created": {"type": "string"},
                        },
                        "required": ["id", "path"],
                    },
                }
            },
            "required": ["bundles"],
        },
    ),
    types.Tool(
        name="get_bundle",
        description="Fetch a bundle by exact id (or unambiguous stem prefix).",
        inputSchema={
            "type": "object",
            "required": ["id"],
            "properties": {
                "id": {"type": "string"},
                "strip_frontmatter": {"type": "boolean", "default": False},
            },
            "additionalProperties": False,
        },
        outputSchema={
            "type": "object",
            "required": ["id", "body", "metadata"],
            "properties": {
                "id": {"type": "string"},
                "body": {"type": "string"},
                "metadata": {"type": "object"},
            },
        },
    ),
    types.Tool(
        name="search_bundles",
        description="Substring search across id, tags, and body. Ranked id×3 + tag×2 + body×1.",
        inputSchema={
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {"type": "string", "minLength": 1},
                "tag": {"type": "string"},
                "since": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$"},
                "until": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$"},
                "limit": {"type": "integer", "default": 10, "minimum": 1, "maximum": 100},
            },
            "additionalProperties": False,
        },
        outputSchema={
            "type": "object",
            "properties": {
                "results": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["id", "score"],
                        "properties": {
                            "id": {"type": "string"},
                            "score": {"type": "number"},
                            "snippet": {"type": "string"},
                            "tags": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                }
            },
            "required": ["results"],
        },
    ),
    types.Tool(
        name="get_by_date",
        description=(
            "Temporal lookup. 'date' accepts YYYY-MM-DD or YYYY-MM-DD..YYYY-MM-DD. "
            "The killer query: ask for 'my notes from May 11'."
        ),
        inputSchema={
            "type": "object",
            "required": ["date"],
            "properties": {
                "date": {"type": "string"},
                "tag": {"type": "string"},
            },
            "additionalProperties": False,
        },
        outputSchema={
            "type": "object",
            "properties": {
                "bundles": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "tags": {"type": "array", "items": {"type": "string"}},
                            "path": {"type": "string"},
                            "created": {"type": "string"},
                        },
                        "required": ["id", "path"],
                    },
                }
            },
            "required": ["bundles"],
        },
    ),
    types.Tool(
        name="log_use",
        description="Record a bundle execution. Appends to usage.log — the falsifiable metric.",
        inputSchema={
            "type": "object",
            "required": ["id"],
            "properties": {
                "id": {"type": "string"},
                "note": {"type": "string"},
                "client": {
                    "type": "string",
                    "description": "originating client, e.g. claude-code, cursor, zed",
                },
            },
            "additionalProperties": False,
        },
        outputSchema={
            "type": "object",
            "required": ["logged", "ts"],
            "properties": {
                "logged": {"type": "boolean"},
                "ts": {"type": "string"},
                "id": {"type": "string"},
            },
        },
    ),
]


def _do_list_bundles(args: dict) -> dict:
    _check_init()
    tag = args.get("tag")
    date = args.get("date")
    limit = int(args.get("limit") or 50)
    out: list[dict] = []
    for f in sorted(BUNDLES.rglob("*.md")):
        if date and f.parent.name != date:
            continue
        meta = _parse_frontmatter(f)
        tags = [str(t) for t in (meta.get("tags") or [])]
        if tag and tag not in tags:
            continue
        out.append(_bundle_summary(f, meta))
        if len(out) >= limit:
            break
    return {"bundles": out}


def _do_get_bundle(args: dict) -> dict:
    _check_init()
    bid = args["id"]
    if not ID_RE.match(bid):
        raise SubstrateError("invalid_id", f"bundle id must match [a-z0-9-]+, got {bid!r}")
    f = _find_bundle(bid)
    if f is None:
        raise SubstrateError("not_found", f"no bundle matches id {bid!r}")
    text = f.read_text()
    meta = _parse_frontmatter(f)
    body = _strip_frontmatter(text) if args.get("strip_frontmatter") else text
    return {"id": str(meta.get("id") or f.stem), "body": body, "metadata": meta}


def _do_search_bundles(args: dict) -> dict:
    _check_init()
    results = _search_bundles(
        BUNDLES,
        args["query"],
        tag=args.get("tag"),
        since=args.get("since"),
        until=args.get("until"),
        limit=int(args.get("limit") or 10),
    )
    out = [
        {
            "id": str(meta.get("id") or f.stem),
            "score": int(score),
            "snippet": snippet,
            "tags": [str(t) for t in (meta.get("tags") or [])],
        }
        for score, f, meta, snippet in results
    ]
    return {"results": out}


def _do_get_by_date(args: dict) -> dict:
    _check_init()
    since, until = _parse_date_arg(args["date"])
    tag = args.get("tag")
    out: list[dict] = []
    for f in sorted(BUNDLES.rglob("*.md")):
        date = f.parent.name
        if date < since or date > until:
            continue
        meta = _parse_frontmatter(f)
        tags = [str(t) for t in (meta.get("tags") or [])]
        if tag and tag not in tags:
            continue
        out.append(_bundle_summary(f, meta))
    return {"bundles": out}


def _do_log_use(args: dict) -> dict:
    _check_init()
    bid = args["id"]
    if not ID_RE.match(bid):
        raise SubstrateError("invalid_id", f"bundle id must match [a-z0-9-]+, got {bid!r}")
    f = _find_bundle(bid)
    if f is None:
        raise SubstrateError("not_found", f"no bundle matches id {bid!r}")
    canonical = str(_parse_frontmatter(f).get("id") or f.stem)
    ts = datetime.now().astimezone().isoformat(timespec="seconds")
    note = args.get("note", "")
    client = args.get("client")
    if client:
        note = f"[{client}] {note}".rstrip()
    USAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with USAGE_LOG.open("a") as fp:
        fp.write(f"{ts}\t{canonical}\t{note}\n")
    return {"logged": True, "ts": ts, "id": canonical}


DISPATCH = {
    "list_bundles": _do_list_bundles,
    "get_bundle": _do_get_bundle,
    "search_bundles": _do_search_bundles,
    "get_by_date": _do_get_by_date,
    "log_use": _do_log_use,
}


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any] | None) -> dict | list[types.TextContent]:
    handler = DISPATCH.get(name)
    if handler is None:
        return _error("unknown_tool", f"no such tool: {name}")
    try:
        return handler(arguments or {})
    except SubstrateError as e:
        return _error(e.code, str(e))
    except Exception as e:  # noqa: BLE001 — surface any other failure as a structured error
        return _error("internal", f"{type(e).__name__}: {e}")


@server.list_resources()
async def list_resources() -> list[types.Resource]:
    _check_init()
    out: list[types.Resource] = []
    for f in sorted(BUNDLES.rglob("*.md"), reverse=True)[:200]:
        meta = _parse_frontmatter(f)
        bid = str(meta.get("id") or f.stem)
        out.append(
            types.Resource(
                uri=f"substrate://bundle/{bid}",
                name=bid,
                description=", ".join(str(t) for t in (meta.get("tags") or [])) or None,
                mimeType="text/markdown",
            )
        )
    return out


@server.read_resource()
async def read_resource(uri) -> str:
    _check_init()
    s = str(uri)
    prefix = "substrate://bundle/"
    if not s.startswith(prefix):
        raise SubstrateError("not_found", f"unknown resource uri: {s}")
    bid = s[len(prefix) :]
    f = _find_bundle(bid)
    if f is None:
        raise SubstrateError("not_found", f"no bundle matches id {bid!r}")
    return f.read_text()


@server.list_prompts()
async def list_prompts() -> list[types.Prompt]:
    _check_init()
    out: list[types.Prompt] = []
    for f in sorted(BUNDLES.rglob("*.md")):
        meta = _parse_frontmatter(f)
        tags = [str(t) for t in (meta.get("tags") or [])]
        if "pinned" not in tags:
            continue
        bid = str(meta.get("id") or f.stem)
        out.append(
            types.Prompt(
                name=bid,
                description=", ".join(tags),
            )
        )
    return out


@server.get_prompt()
async def get_prompt(name: str, arguments: dict[str, str] | None) -> types.GetPromptResult:
    _check_init()
    f = _find_bundle(name)
    if f is None:
        raise SubstrateError("not_found", f"no prompt matches id {name!r}")
    body = _strip_frontmatter(f.read_text())
    return types.GetPromptResult(
        description=name,
        messages=[
            types.PromptMessage(
                role="user",
                content=types.TextContent(type="text", text=body),
            )
        ],
    )


async def _run() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    """Console-script entry point. `substrate-mcp` runs this."""
    asyncio.run(_run())


if __name__ == "__main__":
    main()
