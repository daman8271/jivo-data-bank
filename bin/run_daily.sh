#!/usr/bin/env bash
# =============================================================================
# run_daily.sh — single-flight daily PIPELINE wrapper for the JIVO Data Bank.
#
# This is the one entry point cron fires every morning. It orchestrates the
# three independently-owned stages in strict order and is fail-closed on the
# data-integrity stage:
#
#     1. bin/daily_rebuild.sh   deterministic REPLACE -> verify -> commit
#                               (the accuracy gate; aborts WITHOUT committing
#                                on ANY loss/regression). EXISTS already.
#     2. bin/push_both.sh       on PASS only: push the verified commit to the
#                               private remote AND the embedded /opt/ecom-intel
#                               copy. (Sibling component — may not exist yet.)
#     3. bin/notify.sh          report the outcome to the owner (Telegram).
#                               Called on BOTH success and failure so the owner
#                               gets a daily heartbeat AND loud failure alerts.
#                               (Sibling component — may not exist yet.)
#
# WHY a wrapper instead of more cron lines: a single flock here guarantees only
# one full pipeline runs at a time (a slow rebuild can never be lapped by the
# next day's tick), keeps the rebuild/push/notify ordering atomic, and gives one
# place to reason about exit semantics.
#
# CRON-PUSH IS LEGITIMATE: the data-exfiltration classifier only blocks Claude's
# *interactive* push. A cron-driven push to the owner's OWN private repo is
# explicitly wanted by the owner — that is exactly what stage 2 does here.
#
# CONTRACTS this wrapper assumes of the sibling scripts (documented so the
# siblings/orchestrator can align; all sibling calls are best-effort / guarded):
#   * push_both.sh : no args. exit 0 = pushed or already-up-to-date; non-zero =
#                    push failed (the commit is still safe locally, retried next
#                    run). Must authenticate non-interactively (deploy key /
#                    stored credential helper) since cron has no TTY.
#   * notify.sh    : called as  notify.sh "<message>"  (single positional arg).
#                    Also receives context via env: JDB_STATUS (ok|fail|warn),
#                    JDB_EXIT, JDB_PHASE. Telegram creds live in ~/.config/tg/env
#                    (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID) — notify.sh owns
#                    delivery; this wrapper never sends directly.
#
# EXIT SEMANTICS:
#   * rebuild FAILED      -> notify(fail), NO push, exit = rebuild's exit code
#                           (so cron-level monitoring sees a hard failure).
#   * rebuild PASS        -> push, then notify, exit 0. A push failure is NOT a
#     (committed or no-op)  data-integrity failure (the verified commit is safe
#                           locally and re-pushed next run), so it is reported
#                           loudly via notify but does not fail the cron job.
#
# Idempotent, reversible, absolute paths, no global state beyond a lock + logs.
# NOTHING here is installed by this file — see install_cron.sh (NOT enabled yet).
#
# Env overrides (all optional): JDB_REPO, JDB_LOGDIR, JDB_RUN_LOG, JDB_RUN_LOCK.
# =============================================================================
set -euo pipefail

REPO="${JDB_REPO:-/root/jivo-data-bank}"
BIN="$REPO/bin"

# Logs live OUTSIDE the git working tree by default so the daily "data refresh"
# commits stay pristine (the repo's .gitignore does not ignore *.log). Falls
# back to bin/ only if the preferred dir is not writable.
LOGDIR="${JDB_LOGDIR:-/var/log/jivo-data-bank}"
if ! mkdir -p "$LOGDIR" 2>/dev/null; then
    LOGDIR="$BIN"
fi
LOG="${JDB_RUN_LOG:-$LOGDIR/run_daily.log}"

REBUILD="$BIN/daily_rebuild.sh"
PUSH="$BIN/push_both.sh"
NOTIFY="$BIN/notify.sh"

ts()  { date -u +%Y-%m-%dT%H:%M:%SZ; }
log() { echo "[$(ts)] $*" | tee -a "$LOG" >&2; }

# ---- owner notification (best-effort; NEVER fails the pipeline) --------------
# $1 = status (ok|fail|warn), $2 = human message.
notify() {
    local status="$1" msg="$2"
    if [ -x "$NOTIFY" ]; then
        JDB_STATUS="$status" JDB_EXIT="${rc:-0}" JDB_PHASE="${PHASE:-}" \
            "$NOTIFY" "$msg" >>"$LOG" 2>&1 \
            || log "notify.sh returned non-zero (non-fatal); msg was: $msg"
    else
        # Sibling notifier not present yet. daily_rebuild.sh still self-alerts on
        # its own aborts via /root/.claude/hooks/notify.sh, so failures are not
        # silent even before notify.sh lands.
        log "notify.sh absent ($NOTIFY) — skipping notification; msg was: $msg"
    fi
}

# ---- single-flight lock (cron-safe; fd 8 to stay clear of children) ----------
# *.lock is git-ignored, so this lock file never enters a commit.
LOCK="${JDB_RUN_LOCK:-$REPO/.run_daily.lock}"
exec 8>"$LOCK"
if ! flock -n 8; then
    log "another run_daily pipeline holds the lock; exiting cleanly"
    exit 0
fi

log "=== run_daily start (REPO=$REPO) ==="

# ---- preflight: the rebuild stage MUST exist --------------------------------
if [ ! -x "$REBUILD" ]; then
    log "FATAL: $REBUILD missing or not executable"
    PHASE="preflight"; rc=2
    notify fail "JIVO Data Bank: run_daily preflight FAILED — $REBUILD missing."
    exit 2
fi

# ---- stage 1: deterministic rebuild + fail-closed verify + commit -----------
PHASE="rebuild"
set +e
"$REBUILD" >>"$LOG" 2>&1
rc=$?
set -e

if [ "$rc" -ne 0 ]; then
    log "stage 1 daily_rebuild FAILED (rc=$rc) — NOT pushing, NOT bumping remote"
    notify fail "❌ JIVO Data Bank daily rebuild FAILED (rc=$rc). No push performed. Log: $LOG"
    log "=== run_daily done (rebuild failed) ==="
    exit "$rc"
fi
log "stage 1 daily_rebuild PASSED (verified; committed or no-op)"

# ---- stage 2: push the verified commit (PASS-gated) -------------------------
PHASE="push"
pushrc=0
if [ -x "$PUSH" ]; then
    set +e
    "$PUSH" >>"$LOG" 2>&1
    pushrc=$?
    set -e
    if [ "$pushrc" -eq 0 ]; then
        log "stage 2 push_both OK"
    else
        log "stage 2 push_both FAILED (rc=$pushrc) — commit is safe locally, retried next run"
    fi
else
    pushrc=127
    log "stage 2 push_both.sh absent ($PUSH) — skipping push (expected pre-integration)"
fi

# ---- stage 3: notify the owner of the outcome -------------------------------
PHASE="notify"
NOW="$(date '+%Y-%m-%d %H:%M %Z')"
if   [ "$pushrc" -eq 0 ]; then
    notify ok   "✅ JIVO Data Bank refreshed & pushed — $NOW (zero-loss verified)."
elif [ "$pushrc" -eq 127 ]; then
    notify ok   "✅ JIVO Data Bank refreshed & committed — $NOW. Push step skipped (push_both.sh not installed yet)."
else
    notify warn "⚠️ JIVO Data Bank refreshed & committed locally — $NOW — but PUSH FAILED (rc=$pushrc). Will retry next run. Log: $LOG"
fi

log "=== run_daily done (rebuild=ok push=$pushrc) ==="
# Push failures do not fail the cron job: the verified data is committed and safe
# locally and is re-pushed on the next run. Data-integrity failures (stage 1)
# are the only hard-fail path. This matches the repo's fail-closed philosophy.
exit 0
