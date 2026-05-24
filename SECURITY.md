# Security Policy

## Supported versions

The latest minor version on the `main` branch receives security updates.

## Reporting a vulnerability

Substrate is a local-first tool — it has no network surface, no daemon, and runs only on the user's machine. The attack surface is small but not zero (path traversal, YAML injection, shell-injection via `$EDITOR` etc.).

If you find a vulnerability, please **do not** open a public issue. Instead, email the maintainer at `sidharth.satapathy5@gmail.com` (or use [GitHub Security Advisories](https://github.com/xlreon/substrate/security/advisories/new) for private disclosure) with:

- A description of the issue
- Steps to reproduce
- The affected version (`substrate --version`)
- Any suggested mitigation

You should expect a first response within 7 days. Confirmed issues will be fixed in a follow-up release with credit (unless you ask to remain anonymous).
