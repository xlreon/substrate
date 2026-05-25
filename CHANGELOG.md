# Changelog

All notable changes to this project will be documented in this file. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.2] - 2026-05-25

### Added
- `substrate --version` / `-V` — prints the installed package version and exits. Reads from `importlib.metadata` so it always matches what `pip show substrate-kb` reports.
- `SUBSTRATE_ACTIVE_FILE` marker now accepts a bare bundle id (`YYYY-MM-DD-stem`) in addition to the legacy path-fragment form (`bundles/YYYY-MM-DD/stem.md`). The bare-id form matches what `substrate list` prints, so a marker line like `ACTIVE BUNDLE: 2026-05-25-my-bundle` now works out of the box.

### Changed
- Documented the active-bundle marker format explicitly in the README (was only inferable from source).

## [0.2.1] - 2026-05-25

### Added
- `substrate add` now supports non-interactive input channels:
  - `--body TEXT` / `-b` — inline body string
  - `--from FILE` / `-f` — read body from a file path
  - `--from -` — read body from stdin (pipe-friendly)
  - `--edit` — force open `$EDITOR` after pre-fill (otherwise editor is skipped when a body source is provided)
- `_resolve_body()` helper for resolving content from `--body`/`--from`, including stdin and frontmatter-stripping when the source file already has YAML frontmatter.
- `.github/workflows/release.yml` — publishes to PyPI on `v*` tag push via OIDC Trusted Publishing; drafts a GitHub Release with attached `sdist` + `wheel`.

### Changed
- `SECURITY.md` and `CODE_OF_CONDUCT.md` now name a concrete maintainer email as the disclosure / enforcement contact (was a vague "GitHub profile" pointer).

### Removed
- `landing/` folder — the canonical landing page now lives at `sidharthsatapathy.com/substrate`; keeping a stale copy in the repo invited drift.

## [0.2.0] - 2026-05-24

### Added
- `substrate ui` — static HTML dashboard with day-grouped timeline, 30-day activity bar chart, "most referenced" leaderboard, tag filter chips, and a modal form to draft new bundles via copy-paste-able shell heredoc.
- `SUBSTRATE_ACTIVE_FILE` env var — point at any markdown file (`AGENTS.md`, `CLAUDE.md`, custom) where an `ACTIVE BUNDLE` marker declares the current active bundle. Dashboard highlights it.
- `SUBSTRATE_ACTIVE_MARKER` env var — customize the marker text (default: `ACTIVE BUNDLE`).
- "Most referenced" score computed without `log_use` dependency: mentions in the active file × 4 + git commit count + (legacy `log_use` count × 2) + active-session bonus.

### Changed
- README rewritten for open-source release; removed personal examples and internal references.
- Active-session detection is no longer hardcoded to any personal file path.

### Fixed
- Bundles without YAML frontmatter now get their id reconstructed as `{date}-{stem}` so they match active-session references and external-file path-extracted ids.

## [0.1.0] - 2026-05-11

### Added
- Initial CLI: `init`, `add`, `list`, `search`, `get`, `use`, `log`, `edit`, `history`.
- MCP server (`substrate-mcp`) exposing `list_bundles`, `get_bundle`, `search_bundles`, `get_by_date`, `log_use`.
- Git-backed bundle store under `~/.substrate/` (override via `SUBSTRATE_HOME`).
- Markdown + YAML frontmatter bundle format.
- Append-only `usage.log` as the falsifiable retrieval metric.

[Unreleased]: https://github.com/xlreon/substrate/compare/v0.2.2...HEAD
[0.2.2]: https://github.com/xlreon/substrate/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/xlreon/substrate/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/xlreon/substrate/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/xlreon/substrate/releases/tag/v0.1.0
