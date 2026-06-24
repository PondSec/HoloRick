#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cp "$ROOT/security/hooks/pre-commit" "$ROOT/.git/hooks/pre-commit"
cp "$ROOT/security/hooks/pre-push" "$ROOT/.git/hooks/pre-push"
chmod +x "$ROOT/.git/hooks/pre-commit" "$ROOT/.git/hooks/pre-push"
echo "Installed Holo Rick security git hooks."
