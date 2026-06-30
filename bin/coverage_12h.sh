#!/usr/bin/env bash
# =============================================================================
# coverage_12h.sh — the every-12h job (cron entrypoint).
#   1. coverage_sync.sh : ensure ecom-intel's latest coverage ledger is in the
#                         data bank; push if missing (deterministic, fail-safe).
#   2. wake Claude       : a bounded headless monitor verifies the full chain
#                         (ecom-intel -> data bank -> live app) and Telegrams a
#                         one-line verdict ("you wake up and monitor this thing").
# Root-safe: headless `claude -p` runs as root in auto mode (no --dangerously-skip).
# =============================================================================
set -uo pipefail
BIN=/root/jivo-data-bank/bin
MON_LOG=/var/log/jivo-data-bank/coverage_monitor.log
mkdir -p "$(dirname "$MON_LOG")"

# 1) deterministic sync (its own logging + telegram on sync-event/error)
"$BIN/coverage_sync.sh"; SYNC_RC=$?

# 2) wake the Claude monitor (bounded; reports via Telegram; never mutates)
echo "[$(date -u +%FT%TZ)] === waking Claude monitor (sync rc=$SYNC_RC) ===" >> "$MON_LOG"
if command -v claude >/dev/null 2>&1; then
  timeout 360 claude -p "$(cat "$BIN/coverage_monitor.prompt")" < /dev/null >> "$MON_LOG" 2>&1 \
    || echo "[$(date -u +%FT%TZ)] WARN monitor claude exited nonzero" >> "$MON_LOG"
else
  echo "[$(date -u +%FT%TZ)] WARN claude not found; skipped monitor" >> "$MON_LOG"
fi
exit 0
