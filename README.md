# Substrate

![private](https://img.shields.io/badge/repo-private-red?logo=github)

Local prompt+context bundles with git-backed versioning. CLI-first, single file.

## Install

```bash
uv tool install --editable .
```

## Five commands you'll actually use

```bash
substrate init                                       # one-time, creates ~/.substrate
substrate add "guvio rate limit middleware"          # opens $EDITOR on a new bundle
substrate use 2026-05-11-guvio-rate-limit-middleware --note guvio-be-PR#142
substrate list --tag guvio
substrate log --since 2026-05-11
```

See `SPEC.md` for the full surface and `HANDOFF.md` for current gate status.
