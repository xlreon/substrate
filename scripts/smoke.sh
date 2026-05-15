#!/usr/bin/env bash
set -euo pipefail
export SUBSTRATE_HOME=$(mktemp -d)
export EDITOR=true
substrate init | grep -q "initialized"
substrate add "demo bundle" --tag test
substrate list | grep -q "demo-bundle"
substrate get "$(date +%Y-%m-%d)-demo-bundle" | grep -q "# Prompt"
PBCOPY_SHIM=$(mktemp); echo '#!/bin/sh' > "$PBCOPY_SHIM"; chmod +x "$PBCOPY_SHIM"
PATH="$(dirname "$PBCOPY_SHIM"):$PATH" substrate use "$(date +%Y-%m-%d)-demo-bundle" --note smoke
substrate log | grep -q "smoke"
echo "smoke: ok"
