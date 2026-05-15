from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def store(tmp_path: Path, monkeypatch) -> Path:
    """Initialised substrate store with 3 fixture bundles."""
    root = tmp_path / "substrate"
    bundles = root / "bundles"
    bundles.mkdir(parents=True)
    (bundles / "2026-05-11").mkdir()
    (bundles / "2026-05-12").mkdir()
    (bundles / "2026-05-11" / "router.md").write_text(
        "---\nid: 2026-05-11-router\ntags: [router, pinned]\n---\n"
        "# Prompt\nFix the router handler.\n"
    )
    (bundles / "2026-05-11" / "search.md").write_text(
        "---\nid: 2026-05-11-search-design\ntags: [search]\n---\n# Prompt\nDesign search ranking.\n"
    )
    (bundles / "2026-05-12" / "auth.md").write_text(
        "---\nid: 2026-05-12-auth\ntags: [auth]\n---\n# Prompt\nFix auth middleware.\n"
    )
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.email=t@t",
            "-c",
            "user.name=t",
            "commit",
            "-q",
            "-m",
            "fixture",
        ],
        check=True,
    )
    monkeypatch.setenv("SUBSTRATE_HOME", str(root))
    # Force the cli module to re-read SUBSTRATE_HOME for any already-imported state.
    import importlib

    import cli as cli_mod
    import mcp_server as mcp_mod

    importlib.reload(cli_mod)
    importlib.reload(mcp_mod)
    return root


@pytest.fixture
def mcp(store: Path):
    """An imported mcp_server module bound to the test store."""
    import mcp_server

    return mcp_server


class TestListBundles:
    def test_lists_all(self, mcp):
        out = mcp._do_list_bundles({})
        ids = [b["id"] for b in out["bundles"]]
        assert sorted(ids) == [
            "2026-05-11-router",
            "2026-05-11-search-design",
            "2026-05-12-auth",
        ]

    def test_filter_by_tag(self, mcp):
        out = mcp._do_list_bundles({"tag": "router"})
        assert [b["id"] for b in out["bundles"]] == ["2026-05-11-router"]

    def test_filter_by_date(self, mcp):
        out = mcp._do_list_bundles({"date": "2026-05-12"})
        assert [b["id"] for b in out["bundles"]] == ["2026-05-12-auth"]

    def test_limit(self, mcp):
        out = mcp._do_list_bundles({"limit": 1})
        assert len(out["bundles"]) == 1


class TestGetBundle:
    def test_exact_id(self, mcp):
        out = mcp._do_get_bundle({"id": "2026-05-11-router"})
        assert out["id"] == "2026-05-11-router"
        assert "Fix the router handler" in out["body"]
        assert out["metadata"]["tags"] == ["router", "pinned"]

    def test_strip_frontmatter(self, mcp):
        out = mcp._do_get_bundle({"id": "2026-05-11-router", "strip_frontmatter": True})
        assert not out["body"].startswith("---")
        assert out["body"].startswith("# Prompt")

    def test_not_found(self, mcp):
        with pytest.raises(mcp.SubstrateError) as exc:
            mcp._do_get_bundle({"id": "nope-nope-nope"})
        assert exc.value.code == "not_found"

    def test_path_traversal_rejected(self, mcp):
        with pytest.raises(mcp.SubstrateError) as exc:
            mcp._do_get_bundle({"id": "../../../etc/passwd"})
        assert exc.value.code == "invalid_id"


class TestSearchBundles:
    def test_finds_by_body(self, mcp):
        out = mcp._do_search_bundles({"query": "ranking"})
        assert len(out["results"]) == 1
        assert out["results"][0]["id"] == "2026-05-11-search-design"

    def test_tag_filter(self, mcp):
        out = mcp._do_search_bundles({"query": "fix", "tag": "auth"})
        assert [r["id"] for r in out["results"]] == ["2026-05-12-auth"]

    def test_since_until(self, mcp):
        out = mcp._do_search_bundles({"query": "fix", "until": "2026-05-11"})
        ids = [r["id"] for r in out["results"]]
        assert "2026-05-12-auth" not in ids


class TestGetByDate:
    def test_single_date(self, mcp):
        out = mcp._do_get_by_date({"date": "2026-05-11"})
        ids = sorted(b["id"] for b in out["bundles"])
        assert ids == ["2026-05-11-router", "2026-05-11-search-design"]

    def test_date_range(self, mcp):
        out = mcp._do_get_by_date({"date": "2026-05-11..2026-05-12"})
        assert len(out["bundles"]) == 3

    def test_invalid_date(self, mcp):
        with pytest.raises(mcp.SubstrateError) as exc:
            mcp._do_get_by_date({"date": "yesterday"})
        assert exc.value.code == "invalid_date"

    def test_tag_filter(self, mcp):
        out = mcp._do_get_by_date({"date": "2026-05-11..2026-05-12", "tag": "auth"})
        assert [b["id"] for b in out["bundles"]] == ["2026-05-12-auth"]


class TestLogUse:
    def test_appends_to_usage_log(self, mcp, store: Path):
        out = mcp._do_log_use({"id": "2026-05-11-router", "note": "test-run"})
        assert out["logged"] is True
        log = (store / "usage.log").read_text()
        assert "2026-05-11-router" in log
        assert "test-run" in log

    def test_client_prefix(self, mcp, store: Path):
        mcp._do_log_use({"id": "2026-05-11-router", "note": "x", "client": "claude-code"})
        assert "[claude-code] x" in (store / "usage.log").read_text()

    def test_not_found(self, mcp):
        with pytest.raises(mcp.SubstrateError) as exc:
            mcp._do_log_use({"id": "does-not-exist"})
        assert exc.value.code == "not_found"


class TestSchemas:
    def test_all_tools_have_complete_schemas(self, mcp):
        names = {t.name for t in mcp.TOOLS}
        assert names == {"list_bundles", "get_bundle", "search_bundles", "get_by_date", "log_use"}
        for tool in mcp.TOOLS:
            assert tool.description
            assert tool.inputSchema["type"] == "object"
            assert tool.outputSchema is not None

    def test_dispatch_covers_all_tools(self, mcp):
        assert set(mcp.DISPATCH.keys()) == {t.name for t in mcp.TOOLS}


class TestStdioEndToEnd:
    """Boot substrate-mcp as a subprocess, speak JSON-RPC, verify the round-trip.

    This is the Gate 1 contract: a fresh process answers tools/list and tools/call
    over stdio without crashing.
    """

    def test_initialize_and_list_tools(self, store: Path):
        env = {**os.environ, "SUBSTRATE_HOME": str(store)}
        proc = subprocess.Popen(
            ["uv", "run", "python", "-m", "mcp_server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            cwd=str(Path(__file__).parent.parent),
        )
        try:
            init = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "0"},
                },
            }
            proc.stdin.write(json.dumps(init) + "\n")
            proc.stdin.flush()
            line = proc.stdout.readline()
            assert line, f"no response; stderr: {proc.stderr.read()}"
            resp = json.loads(line)
            assert resp["id"] == 1
            assert "result" in resp

            initialized = {"jsonrpc": "2.0", "method": "notifications/initialized"}
            proc.stdin.write(json.dumps(initialized) + "\n")
            proc.stdin.flush()

            list_req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
            proc.stdin.write(json.dumps(list_req) + "\n")
            proc.stdin.flush()
            line = proc.stdout.readline()
            resp = json.loads(line)
            names = {t["name"] for t in resp["result"]["tools"]}
            assert names == {
                "list_bundles",
                "get_bundle",
                "search_bundles",
                "get_by_date",
                "log_use",
            }
        finally:
            proc.stdin.close()
            proc.terminate()
            proc.wait(timeout=5)
