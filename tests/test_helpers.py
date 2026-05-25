from __future__ import annotations

from pathlib import Path

import pytest

from cli import (
    _find_bundle,
    _parse_frontmatter,
    _search_bundles,
    _slug,
    _snippet,
    _strip_frontmatter,
)


class TestSlug:
    def test_collapses_punctuation(self):
        assert _slug("Hello, World!") == "hello-world"

    def test_strips_edge_dashes(self):
        assert _slug("--foo--bar--") == "foo-bar"

    def test_empty_falls_back_to_untitled(self):
        assert _slug("") == "untitled"
        assert _slug("!!!") == "untitled"

    def test_unicode_passthrough(self):
        # Non-ASCII chars are non-alphanumeric under [a-z0-9]+, so they collapse.
        assert _slug("café") == "caf"
        assert _slug("नमस्ते test") == "test"


class TestParseFrontmatter:
    def test_missing_returns_empty(self, tmp_path: Path):
        p = tmp_path / "x.md"
        p.write_text("just a body, no frontmatter\n")
        assert _parse_frontmatter(p) == {}

    def test_malformed_returns_empty(self, tmp_path: Path):
        p = tmp_path / "x.md"
        p.write_text("---\nid: oops\nno closing fence\n")
        assert _parse_frontmatter(p) == {}

    def test_empty_frontmatter(self, tmp_path: Path):
        p = tmp_path / "x.md"
        p.write_text("---\n\n---\nbody\n")
        assert _parse_frontmatter(p) == {}

    def test_well_formed(self, tmp_path: Path):
        p = tmp_path / "x.md"
        p.write_text("---\nid: 2026-05-11-foo\ntags: [a, b]\n---\nbody\n")
        meta = _parse_frontmatter(p)
        assert meta["id"] == "2026-05-11-foo"
        assert meta["tags"] == ["a", "b"]


class TestStripFrontmatter:
    def test_no_frontmatter_passthrough(self):
        assert _strip_frontmatter("just body") == "just body"

    def test_strips_well_formed(self):
        text = "---\nid: x\n---\nbody line\n"
        assert _strip_frontmatter(text) == "body line\n"

    def test_round_trip_with_parse(self, tmp_path: Path):
        original = "---\nid: 2026-05-11-foo\ntags: [a]\n---\n# Prompt\n\nhello\n"
        p = tmp_path / "x.md"
        p.write_text(original)
        meta = _parse_frontmatter(p)
        body = _strip_frontmatter(p.read_text())
        assert meta["id"] == "2026-05-11-foo"
        assert body.startswith("# Prompt")


class TestFindBundle:
    @pytest.fixture
    def bundles(self, tmp_path: Path, monkeypatch):
        root = tmp_path / "substrate"
        bundles_dir = root / "bundles" / "2026-05-11"
        bundles_dir.mkdir(parents=True)
        (bundles_dir / "alpha.md").write_text("---\nid: 2026-05-11-alpha\ntags: []\n---\nbody\n")
        (bundles_dir / "beta.md").write_text("---\nid: 2026-05-11-beta\ntags: []\n---\nbody\n")
        (bundles_dir / "alpha-extra.md").write_text(
            "---\nid: 2026-05-11-alpha-extra\ntags: []\n---\nbody\n"
        )
        monkeypatch.setattr("cli.BUNDLES", root / "bundles")
        return root

    def test_exact_id_match(self, bundles):
        f = _find_bundle("2026-05-11-alpha")
        assert f is not None
        assert f.stem == "alpha"

    def test_missing_returns_none(self, bundles):
        assert _find_bundle("does-not-exist") is None

    def test_ambiguous_stem_returns_none(self, bundles):
        # "alpha" is a substring of two stems (alpha, alpha-extra). No exact id match.
        # _find_bundle should return None for the ambiguous fallback.
        assert _find_bundle("alpha-fragment") is None


class TestSnippet:
    def test_no_match_returns_empty(self):
        assert _snippet("hello world", "zzz") == ""

    def test_empty_needle_returns_empty(self):
        assert _snippet("hello world", "") == ""

    def test_case_insensitive(self):
        assert "Hello" in _snippet("Hello World", "hello")

    def test_collapses_newlines(self):
        s = _snippet("line one\nline TWO match here\nline three", "match")
        assert "\n" not in s
        assert "match" in s

    def test_ellipses_on_truncation(self):
        body = "x" * 100 + " match " + "y" * 100
        s = _snippet(body, "match", width=20)
        assert s.startswith("…") and s.endswith("…")


class TestSearchBundles:
    @pytest.fixture
    def bundles_root(self, tmp_path: Path) -> Path:
        root = tmp_path / "bundles"
        (root / "2026-05-10").mkdir(parents=True)
        (root / "2026-05-11").mkdir(parents=True)
        (root / "2026-05-12").mkdir(parents=True)
        (root / "2026-05-10" / "alpha.md").write_text(
            "---\nid: 2026-05-10-alpha-router\ntags: [router, fastapi]\n---\n"
            "# Prompt\nFix the route handler bug.\n"
        )
        (root / "2026-05-11" / "beta.md").write_text(
            "---\nid: 2026-05-11-beta\ntags: [security]\n---\n"
            "# Prompt\nThe router consolidation needs review.\nrouter again.\n"
        )
        (root / "2026-05-12" / "gamma.md").write_text(
            "---\nid: 2026-05-12-gamma\ntags: [docs]\n---\n# Prompt\nUnrelated content.\n"
        )
        return root

    def test_finds_in_body(self, bundles_root: Path):
        results = _search_bundles(bundles_root, "consolidation")
        assert len(results) == 1
        assert results[0][2]["id"] == "2026-05-11-beta"

    def test_finds_in_id(self, bundles_root: Path):
        results = _search_bundles(bundles_root, "alpha-router")
        assert len(results) == 1
        assert results[0][2]["id"] == "2026-05-10-alpha-router"

    def test_finds_in_tag(self, bundles_root: Path):
        results = _search_bundles(bundles_root, "fastapi")
        assert len(results) == 1
        assert results[0][2]["id"] == "2026-05-10-alpha-router"

    def test_id_match_outranks_body_match(self, bundles_root: Path):
        # alpha-router: id has 1x "router" (×3=3) + tag has 1x "router" (×2=2) + body 0 -> 5
        # beta:        id 0 + tags 0 + body 2x "router" -> 2
        results = _search_bundles(bundles_root, "router")
        assert results[0][2]["id"] == "2026-05-10-alpha-router"
        assert results[1][2]["id"] == "2026-05-11-beta"

    def test_tag_filter(self, bundles_root: Path):
        results = _search_bundles(bundles_root, "router", tag="security")
        assert len(results) == 1
        assert results[0][2]["id"] == "2026-05-11-beta"

    def test_since_filter(self, bundles_root: Path):
        results = _search_bundles(bundles_root, "router", since="2026-05-11")
        ids = [r[2]["id"] for r in results]
        assert "2026-05-10-alpha-router" not in ids
        assert "2026-05-11-beta" in ids

    def test_until_filter(self, bundles_root: Path):
        results = _search_bundles(bundles_root, "router", until="2026-05-10")
        ids = [r[2]["id"] for r in results]
        assert ids == ["2026-05-10-alpha-router"]

    def test_limit(self, bundles_root: Path):
        results = _search_bundles(bundles_root, "router", limit=1)
        assert len(results) == 1

    def test_no_match_returns_empty(self, bundles_root: Path):
        assert _search_bundles(bundles_root, "nonexistent-needle") == []

    def test_case_insensitive(self, bundles_root: Path):
        results = _search_bundles(bundles_root, "ROUTER")
        assert len(results) >= 2


class TestFindActiveBundleId:
    """Cover both reference formats: path fragment + bare id."""

    def setup_method(self):
        # Ensure the default marker is in effect for these tests.
        import os

        self._saved = os.environ.pop("SUBSTRATE_ACTIVE_MARKER", None)

    def teardown_method(self):
        import os

        if self._saved is not None:
            os.environ["SUBSTRATE_ACTIVE_MARKER"] = self._saved

    def test_path_shape(self):
        from cli import _find_active_bundle_id

        assert (
            _find_active_bundle_id("ACTIVE BUNDLE: bundles/2026-05-25/stdin-body-test.md")
            == "2026-05-25-stdin-body-test"
        )

    def test_bare_id(self):
        from cli import _find_active_bundle_id

        assert (
            _find_active_bundle_id("ACTIVE BUNDLE: 2026-05-25-stdin-body-test")
            == "2026-05-25-stdin-body-test"
        )

    def test_bare_id_inline_prose(self):
        from cli import _find_active_bundle_id

        assert (
            _find_active_bundle_id(
                "The ACTIVE BUNDLE for this session is 2026-05-25-my-bundle which covers..."
            )
            == "2026-05-25-my-bundle"
        )

    def test_custom_marker_with_bare_id(self):
        import os

        from cli import _find_active_bundle_id

        os.environ["SUBSTRATE_ACTIVE_MARKER"] = "PINNED"
        assert _find_active_bundle_id("PINNED: 2026-05-25-foo") == "2026-05-25-foo"

    def test_no_marker_line(self):
        from cli import _find_active_bundle_id

        assert _find_active_bundle_id("nothing here") is None

    def test_marker_without_id(self):
        from cli import _find_active_bundle_id

        assert _find_active_bundle_id("ACTIVE BUNDLE: <empty>") is None

    def test_empty_text(self):
        from cli import _find_active_bundle_id

        assert _find_active_bundle_id("") is None

    def test_path_shape_wins_when_both_present(self):
        from cli import _find_active_bundle_id

        line = "ACTIVE BUNDLE: bundles/2026-05-25/foo.md (was: 2026-05-24-bar)"
        assert _find_active_bundle_id(line) == "2026-05-25-foo"

    def test_first_marker_line_wins(self):
        from cli import _find_active_bundle_id

        text = "\n".join(
            [
                "preamble",
                "ACTIVE BUNDLE: 2026-05-25-first",
                "later mention ACTIVE BUNDLE: 2026-05-25-second",
            ]
        )
        assert _find_active_bundle_id(text) == "2026-05-25-first"


class TestVersionFlag:
    def test_version_prints_and_exits(self):
        from typer.testing import CliRunner

        from cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert result.output.startswith("substrate ")
        # version string should contain at least one dot (a la 0.2.2)
        # or be "unknown" when running pre-install.
        rest = result.output.strip().split(" ", 1)[1]
        assert "." in rest or rest == "unknown"

    def test_short_flag_alias(self):
        from typer.testing import CliRunner

        from cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["-V"])
        assert result.exit_code == 0
        assert result.output.startswith("substrate ")
