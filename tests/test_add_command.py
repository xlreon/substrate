"""End-to-end tests for `substrate add` covering all input channels."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

import cli


@pytest.fixture
def isolated_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point substrate at a temporary store and initialize it.

    `cli.ROOT`/`BUNDLES`/`USAGE_LOG` are module-level constants captured at
    import time, so we monkeypatch the module attributes directly rather
    than just setting the env var.
    """
    store = tmp_path / "store"
    monkeypatch.setenv("SUBSTRATE_HOME", str(store))
    monkeypatch.setattr(cli, "ROOT", store)
    monkeypatch.setattr(cli, "BUNDLES", store / "bundles")
    monkeypatch.setattr(cli, "USAGE_LOG", store / "usage.log")

    runner = CliRunner()
    result = runner.invoke(cli.app, ["init"])
    assert result.exit_code == 0, result.output
    return store


def _find_added_bundle(store: Path) -> Path:
    matches = list((store / "bundles").rglob("*.md"))
    assert len(matches) == 1, f"expected exactly one bundle, got {matches}"
    return matches[0]


class TestAddEditorFallback:
    def test_no_source_opens_editor(self, isolated_store: Path, monkeypatch: pytest.MonkeyPatch):
        calls: list[list[str]] = []
        monkeypatch.setattr(subprocess, "call", lambda cmd: calls.append(cmd) or 0)
        runner = CliRunner()
        result = runner.invoke(cli.app, ["add", "my note"])
        assert result.exit_code == 0, result.output
        assert len(calls) == 1, "editor should have been launched"
        bundle = _find_added_bundle(isolated_store)
        assert "<write your prompt here>" in bundle.read_text()


class TestAddFromBody:
    def test_inline_body_skips_editor(self, isolated_store: Path, monkeypatch: pytest.MonkeyPatch):
        calls: list[list[str]] = []
        monkeypatch.setattr(subprocess, "call", lambda cmd: calls.append(cmd) or 0)
        runner = CliRunner()
        result = runner.invoke(cli.app, ["add", "from body", "-b", "the actual body"])
        assert result.exit_code == 0, result.output
        assert calls == [], "editor should NOT have been launched"
        bundle = _find_added_bundle(isolated_store)
        text = bundle.read_text()
        assert "the actual body" in text
        assert "<write your prompt here>" not in text, "placeholder should be gone"
        assert text.startswith("---"), "frontmatter should be present"

    def test_body_preserves_tags(self, isolated_store: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(subprocess, "call", lambda cmd: 0)
        runner = CliRunner()
        result = runner.invoke(
            cli.app, ["add", "tagged note", "-b", "hello", "-t", "alpha", "-t", "beta"]
        )
        assert result.exit_code == 0, result.output
        bundle = _find_added_bundle(isolated_store)
        meta = cli._parse_frontmatter(bundle)
        assert meta["tags"] == ["alpha", "beta"]


class TestAddFromFile:
    def test_reads_file_body(
        self, isolated_store: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(subprocess, "call", lambda cmd: 0)
        source = tmp_path / "source.md"
        source.write_text("# pre-written content\n\nLine two.\n")
        runner = CliRunner()
        result = runner.invoke(cli.app, ["add", "from file", "--from", str(source)])
        assert result.exit_code == 0, result.output
        bundle = _find_added_bundle(isolated_store)
        text = bundle.read_text()
        assert "pre-written content" in text
        assert "Line two." in text

    def test_strips_existing_frontmatter(
        self, isolated_store: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(subprocess, "call", lambda cmd: 0)
        source = tmp_path / "with-fm.md"
        source.write_text(
            "---\nid: someone-elses-id\ntags: [foo]\n---\n\nThe real body lives here.\n"
        )
        runner = CliRunner()
        result = runner.invoke(cli.app, ["add", "fm strip", "--from", str(source)])
        assert result.exit_code == 0, result.output
        bundle = _find_added_bundle(isolated_store)
        meta = cli._parse_frontmatter(bundle)
        assert "someone-elses-id" not in meta.get("id", "")
        text = bundle.read_text()
        assert "The real body lives here." in text
        assert "someone-elses-id" not in text

    def test_missing_file_errors(self, isolated_store: Path):
        runner = CliRunner()
        result = runner.invoke(cli.app, ["add", "missing", "--from", "/no/such/file.md"])
        assert result.exit_code == 1
        assert "file not found" in result.output


class TestAddFromStdin:
    def test_dash_reads_stdin(self, isolated_store: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(subprocess, "call", lambda cmd: 0)
        runner = CliRunner()
        result = runner.invoke(
            cli.app, ["add", "piped", "--from", "-"], input="piped content here\n"
        )
        assert result.exit_code == 0, result.output
        bundle = _find_added_bundle(isolated_store)
        assert "piped content here" in bundle.read_text()


class TestAddMutex:
    def test_body_and_from_are_mutually_exclusive(self, isolated_store: Path):
        runner = CliRunner()
        result = runner.invoke(cli.app, ["add", "conflict", "-b", "hello", "--from", "anything"])
        assert result.exit_code == 2
        assert "mutually exclusive" in result.output


class TestAddEditFlag:
    def test_edit_flag_opens_editor_after_prefill(
        self, isolated_store: Path, monkeypatch: pytest.MonkeyPatch
    ):
        calls: list[list[str]] = []
        monkeypatch.setattr(subprocess, "call", lambda cmd: calls.append(cmd) or 0)
        runner = CliRunner()
        result = runner.invoke(
            cli.app, ["add", "prefilled then edit", "-b", "draft body", "--edit"]
        )
        assert result.exit_code == 0, result.output
        assert len(calls) == 1, "editor should launch when --edit is passed alongside --body"
        bundle = _find_added_bundle(isolated_store)
        assert "draft body" in bundle.read_text()


class TestAddDuplicateGuard:
    def test_duplicate_slug_on_same_day_fails(
        self, isolated_store: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(subprocess, "call", lambda cmd: 0)
        runner = CliRunner()
        first = runner.invoke(cli.app, ["add", "twice", "-b", "first"])
        assert first.exit_code == 0, first.output
        second = runner.invoke(cli.app, ["add", "twice", "-b", "second"])
        assert second.exit_code == 1
        assert "already exists" in second.output
