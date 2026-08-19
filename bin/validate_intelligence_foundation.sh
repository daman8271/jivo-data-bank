#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec python3 "$REPO_ROOT/intelligence/hermes-orchestration/tools/validate_foundation.py" \
  --root "$REPO_ROOT/intelligence/hermes-orchestration"
