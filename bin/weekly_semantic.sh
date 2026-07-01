#!/usr/bin/env bash
# =============================================================================
# weekly_semantic.sh — WEEKLY refresh of the 8-domain SEMANTIC cross-vault link
# cache for the JIVO Data Bank.
#
# WHAT THIS OWNS (and nothing else): the EXPENSIVE regeneration of the
# .links/domain-*.json fan-out cache. The daily pipeline (daily_rebuild.sh) only
# cheaply RE-APPLIES whatever cache is on disk; producing a fresh cache needs an
# LLM (fuzzy product identity, sibling/tier substitution, price-floor reading),
# so that discovery is driven headless via `claude -p` here, once a week.
#
# PIPELINE:
#   1. Snapshot the current authoritative .links cache (reversible backup).
#   2. DISCOVER: run `claude -p` with a self-contained discovery prompt that
#      rewrites all 8 domain files (domain-0..domain-7.json) into a STAGING dir.
#         * If `claude` is unavailable  -> FALL BACK: keep the existing cache,
#           LOG that semantic re-discovery was SKIPPED, and still re-inject +
#           rebuild + verify so the vault gets a clean weekly heartbeat commit.
#         * If the staged output fails validation (bad JSON / collapsed counts)
#           -> same fallback (never inject unvalidated junk).
#   3. On valid staging: atomically swap it into the authoritative cache
#      ($COMBINED/.links) and mirror it to $REPO/.links.
#   4. REBUILD + VERIFY + COMMIT via daily_rebuild.sh — the single, proven
#      fail-closed engine (it runs combined_inject_links.py, rebuilds the
#      backbone, runs verify_databank.py, and commits ONLY if every gate passes).
#
# FAIL-CLOSED: a regressed vault is NEVER committed (daily_rebuild.sh enforces
# this and leaves git clean on any gate failure). Additionally, if the rebuild
# fails AFTER we swapped in a freshly-discovered cache, we RESTORE the snapshot
# so a bad cache can never poison the next daily run.
#
# DOES NOT PUSH. Pushing the verified commit is the daily pipeline's / owner's
# job (run_daily.sh stage 2). install_cron.sh schedules this at 15:00 IST Sunday,
# AFTER that day's daily rebuild, so the fresh cache is on disk and the day's data
# is complete.
#
# IDEMPOTENT (single-flight lock; re-runnable) and REVERSIBLE (timestamped cache
# snapshots are retained under the log dir; --uninstall is N/A — this script
# installs nothing). Absolute paths throughout. Nothing here is enabled live.
#
# Usage:
#   weekly_semantic.sh                 # full weekly refresh (discover -> rebuild)
#   weekly_semantic.sh --no-discovery  # force fallback: re-inject existing cache
#   weekly_semantic.sh --dry-run       # discover + validate only; NO swap/commit
#   weekly_semantic.sh --status        # show cache + last backup, then exit
#   weekly_semantic.sh --help
#
# Env overrides (all optional):
#   JDB_REPO JDB_COMBINED JDB_GEN_DIR JDB_PYTHON
#   JDB_CLAUDE          (claude binary; default: claude)
#   JDB_CLAUDE_MODEL    (passed as --model if set; default: account default)
#   JDB_CLAUDE_TIMEOUT  (seconds for the discovery pass; default: 1800)
#   JDB_CLAUDE_MAXTURNS (--max-turns for the agent; default: 80)
#   JDB_CLAUDE_PERM     (--permission-mode; default: bypassPermissions)
#   JDB_SEM_FLOOR       (min fraction of the prior TOTAL link count the staged
#                        cache must reach to be accepted; default: 0.50)
#   JDB_SEM_MIN_DOMAINS (min number of non-empty domain files; default: 5)
#   JDB_LOGDIR JDB_WEEKLY_LOG JDB_WEEKLY_LOCK JDB_BACKUP_KEEP
# =============================================================================
set -euo pipefail

# ---- configuration ----------------------------------------------------------
REPO="${JDB_REPO:-/root/jivo-data-bank}"
COMBINED="${JDB_COMBINED:-/opt/ecom-intel/combined-vault}"
GEN_DIR="${JDB_GEN_DIR:-/opt/ecom-intel/bin}"
PY="${JDB_PYTHON:-python3}"

CLAUDE_BIN="${JDB_CLAUDE:-claude}"
CLAUDE_MODEL="${JDB_CLAUDE_MODEL:-}"
CLAUDE_TIMEOUT="${JDB_CLAUDE_TIMEOUT:-1800}"
CLAUDE_MAXTURNS="${JDB_CLAUDE_MAXTURNS:-80}"
CLAUDE_PERM="${JDB_CLAUDE_PERM:-bypassPermissions}"

SEM_FLOOR="${JDB_SEM_FLOOR:-0.50}"
SEM_MIN_DOMAINS="${JDB_SEM_MIN_DOMAINS:-5}"
N_DOMAINS=8                                   # domain-0 .. domain-7

REPO_LINKS="$REPO/.links"
COMBINED_LINKS="$COMBINED/.links"            # the AUTHORITATIVE cache (inject reads here)
REBUILD="$REPO/bin/daily_rebuild.sh"
INJECT="$GEN_DIR/combined_inject_links.py"
NOTIFY_REPO="$REPO/bin/notify.sh"
NOTIFY_HOOK="/root/.claude/hooks/notify.sh"

# Logs + scratch live OUTSIDE the git tree so weekly commits stay pristine.
LOGDIR="${JDB_LOGDIR:-/var/log/jivo-data-bank}"
if ! mkdir -p "$LOGDIR" 2>/dev/null; then
    LOGDIR="$(mktemp -d "${TMPDIR:-/tmp}/jdb-weekly.XXXXXX")"
fi
LOG="${JDB_WEEKLY_LOG:-$LOGDIR/weekly_semantic.log}"
STAGE="$LOGDIR/links-staging"                # claude writes the new cache here
BACKUP_ROOT="$LOGDIR/links-backups"          # timestamped cache snapshots
BACKUP_KEEP="${JDB_BACKUP_KEEP:-4}"

ts()  { date -u +%Y-%m-%dT%H:%M:%SZ; }
log() { echo "[$(ts)] $*" | tee -a "$LOG" >&2; }

# ---- args -------------------------------------------------------------------
# ACTION is the verb; DRYRUN and DISCOVER are orthogonal modifiers (so e.g.
# `--dry-run --no-discovery` is valid and safe to test with no LLM/commit).
ACTION="run"        # run | status
DRYRUN=0            # 1 => discover/validate only, NO swap/rebuild/commit
DISCOVER="auto"     # auto => run claude -p discovery | off => force fallback
for arg in "$@"; do
    case "$arg" in
        --no-discovery|--no-discover) DISCOVER="off" ;;
        --dry-run|-n)                 DRYRUN=1 ;;
        --status|--show)              ACTION="status" ;;
        -h|--help)
            sed -n '2,72p' "$0" | sed 's/^# \{0,1\}//'
            exit 0 ;;
        *) echo "weekly_semantic.sh: unknown argument: $arg" >&2
           echo "usage: weekly_semantic.sh [--no-discovery] [--dry-run] [--status]" >&2
           exit 2 ;;
    esac
done

# ---- owner notification (best-effort; NEVER fails the job) ------------------
# Prefer the repo notifier (Telegram via ~/.config/tg/env), then the global
# hook, else just log. Mirrors run_daily.sh's contract.
notify() {
    local status="$1" msg="$2"
    if [ -x "$NOTIFY_REPO" ]; then
        JDB_STATUS="$status" JDB_PHASE="weekly_semantic" \
            "$NOTIFY_REPO" "$msg" >>"$LOG" 2>&1 || log "notify.sh non-zero (non-fatal)"
    elif [ -x "$NOTIFY_HOOK" ]; then
        "$NOTIFY_HOOK" "$msg" >/dev/null 2>&1 || true
    else
        log "no notifier available; msg was: $msg"
    fi
}

# ---- count total links across a .links dir ----------------------------------
count_links() {
    local dir="$1"
    [ -d "$dir" ] || { echo 0; return 0; }
    "$PY" - "$dir" <<'PYEOF' 2>/dev/null || echo 0
import sys, glob, json, os
total = 0
for f in glob.glob(os.path.join(sys.argv[1], "domain-*.json")):
    try:
        with open(f) as fh:
            d = json.load(fh)
        if isinstance(d, list):
            total += len(d)
    except Exception:
        pass
print(total)
PYEOF
}

# ---- status (read-only) -----------------------------------------------------
if [ "$ACTION" = "status" ]; then
    echo "REPO            : $REPO"
    echo "authoritative   : $COMBINED_LINKS"
    if [ -d "$COMBINED_LINKS" ]; then
        echo "domain files    : $(ls "$COMBINED_LINKS"/domain-*.json 2>/dev/null | wc -l | tr -d ' ')"
        echo "total links     : $(count_links "$COMBINED_LINKS")"
    else
        echo "domain files    : (cache absent)"
    fi
    echo "repo mirror      : $REPO_LINKS ($(ls "$REPO_LINKS"/domain-*.json 2>/dev/null | wc -l | tr -d ' ') files)"
    if [ -d "$BACKUP_ROOT" ]; then
        echo "last backups     :"; ls -1dt "$BACKUP_ROOT"/* 2>/dev/null | head -"$BACKUP_KEEP" | sed 's/^/    /'
    else
        echo "last backups     : (none)"
    fi
    echo "claude binary    : $(command -v "$CLAUDE_BIN" 2>/dev/null || echo 'NOT FOUND -> would fall back')"
    exit 0
fi

# ---- single-flight lock (cron-safe; fd 7 to stay clear of daily's fd 8/9) ---
LOCK="${JDB_WEEKLY_LOCK:-$REPO/.weekly_semantic.lock}"
exec 7>"$LOCK"
if ! flock -n 7; then
    log "another weekly_semantic run holds the lock; exiting cleanly"
    exit 0
fi

log "=== weekly_semantic start (discover=$DISCOVER dry_run=$DRYRUN REPO=$REPO) ==="

# ---- preflight: prerequisites must exist ------------------------------------
for p in "$REPO/.git" "$REBUILD" "$INJECT" "$COMBINED" "$REPO/bin/verify_databank.py"; do
    [ -e "$p" ] || { log "ABORT: missing prerequisite: $p";
                     notify fail "❌ JIVO Data Bank weekly_semantic ABORT: missing $p"; exit 2; }
done
mkdir -p "$COMBINED_LINKS" "$REPO_LINKS" "$BACKUP_ROOT"

PREV_TOTAL="$(count_links "$COMBINED_LINKS")"
log "current authoritative cache: $(ls "$COMBINED_LINKS"/domain-*.json 2>/dev/null | wc -l | tr -d ' ') files / $PREV_TOTAL links"

# ---- 1. reversible snapshot of the current cache ----------------------------
BK="$BACKUP_ROOT/$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$BK"
cp -a "$COMBINED_LINKS" "$BK/combined-links" 2>/dev/null || true
[ -d "$REPO_LINKS" ] && cp -a "$REPO_LINKS" "$BK/repo-links" 2>/dev/null || true
log "step 1: snapshotted current cache -> $BK"

restore_cache() {
    # Roll the authoritative cache + repo mirror back to the snapshot so a bad
    # discovery can never poison the next daily run.
    if [ -d "$BK/combined-links" ]; then
        rm -rf "$COMBINED_LINKS"; cp -a "$BK/combined-links" "$COMBINED_LINKS"
    fi
    if [ -d "$BK/repo-links" ]; then
        rm -rf "$REPO_LINKS"; cp -a "$BK/repo-links" "$REPO_LINKS"
    fi
    log "restored cache from snapshot $BK"
}

prune_backups() {
    # Keep only the most recent $BACKUP_KEEP snapshots (data, not config).
    ls -1dt "$BACKUP_ROOT"/* 2>/dev/null | tail -n +"$((BACKUP_KEEP + 1))" \
        | while read -r old; do rm -rf "$old"; done || true
}

# ---- 2. discovery via claude -p (unless fallback/forced off) -----------------
DISCOVERY="skipped"   # skipped | applied
SEM_NOTE=""           # human note about the discovery outcome

run_discovery() {
    # Returns 0 and populates $STAGE with validated domain-*.json on success;
    # returns non-zero (and leaves $STAGE invalid/empty) to signal fallback.
    if ! command -v "$CLAUDE_BIN" >/dev/null 2>&1; then
        SEM_NOTE="claude binary not found ($CLAUDE_BIN)"
        return 10
    fi

    rm -rf "$STAGE"; mkdir -p "$STAGE"

    # --- self-contained discovery prompt (the LLM fan-out) -------------------
    local prompt
    prompt="$(cat <<PROMPT
You are regenerating the 8-domain SEMANTIC cross-vault link cache for the JIVO
Data Bank, a fused Obsidian vault at:

    $COMBINED

Top-level layout inside that vault:
  jivo/      -> JIVO internal e-com app export (skus/, months/, pos/, vendors/, ...)
  ecom/      -> ecom price-intel export (skus/ = platform listings, locations/,
                locations/pincodes/, pricematch/)
  products/  -> one note per canonical Jivo product (generated backbone)
  hubs/      -> "Category - <X>.md", "Platform - <X>.md", "Tier - <X>.md" (backbone)

TASK: write EXACTLY these 8 files, OVERWRITING any existing content:
  $STAGE/domain-0.json  ... $STAGE/domain-7.json

Each file MUST be a single JSON array. Each element MUST be an object:
  {"from": "<vault-relative .md path>", "to": "<vault-relative .md path>",
   "link_type": "D<n>", "reason": "<short why, one line>"}

HARD RULES (accuracy at all costs):
  * "from" and "to" MUST be paths to files that ACTUALLY EXIST under $COMBINED
    (verify on disk; a link whose target does not exist is data loss). Paths are
    relative to the vault root, e.g. "products/MUSTARD 1L POUCH.md".
  * link_type for domain-<n>.json MUST be the string "D<n>" (e.g. "D3" in domain-3.json).
  * Output ONLY the JSON files. No prose, no markdown fences inside the files.
  * Do NOT touch any file outside $STAGE. Do NOT commit anything.

THE 8 DOMAINS (regenerate each from the CURRENT on-disk vault):
  D0  Cross-vault product IDENTITY: an ecom listing (ecom/skus/*.md) and a JIVO
      SKU (jivo/skus/sku-*.md) that are the SAME physical product but were NOT
      fused by the deterministic SKU bridge. Judgment: fuzzy name + pack-size match.
  D1  Product -> Category hub membership: products/*.md -> "hubs/Category - <CAT>.md".
      Deterministic: derive each product's category from its note and link it.
  D2  Product <-> Product SIBLING: same product family / identical ecom platform
      set / pack-size variants (e.g. "A2 GHEE 1L" <-> "A2 GHEE 500G").
  D3  Temporal chain: jivo/months/YYYY-MM.md -> the adjacent calendar month note
      (prev and next), where that neighbour note exists. Deterministic.
  D4  Procurement graph: jivo/pos/po-*.md -> the jivo/vendors/vendor-*.md it was
      procured from (read each PO note's vendor/distributor). Deterministic.
  D5  Geo rollup: ecom/locations/pincodes/<pin>.md -> its ecom/locations/<City>.md.
      Deterministic: read the city from each pincode note.
  D6  Tier SUBSTITUTION: products/*.md <-> products/*.md of the SAME oil type
      across the premium<->commodity tier boundary (substitution candidates).
  D7  Price-floor SIGNAL: ecom/pricematch/pm-*.md -> the "hubs/Tier - <Tier>.md"
      it implicates (read each price-match note's verdict/tier).

METHOD: for the DETERMINISTIC domains (D1, D3, D4, D5) you SHOULD scan the vault
programmatically (write and run a short Python/bash script with your tools) so the
output is complete and exact. For the JUDGMENT domains (D0, D2, D6, D7) read the
relevant notes and use careful product knowledge; prefer PRECISION over recall.

When done, ensure all 8 files parse as JSON arrays and every path exists. Reply
with one line: the per-domain counts.
PROMPT
)"

    # Assemble flags. bypassPermissions + constrained tool set so the headless
    # agent can read the vault and write the staging files but nothing surprising.
    local -a cargs=(-p "$prompt"
                    --output-format text
                    --permission-mode "$CLAUDE_PERM"
                    --max-turns "$CLAUDE_MAXTURNS"
                    --add-dir "$COMBINED" --add-dir "$STAGE"
                    --allowedTools "Read" "Write" "Edit" "Glob" "Grep" "Bash")
    [ -n "$CLAUDE_MODEL" ] && cargs+=(--model "$CLAUDE_MODEL")

    log "step 2: running claude -p discovery (timeout=${CLAUDE_TIMEOUT}s, model=${CLAUDE_MODEL:-default})"
    local crc=0
    ( cd "$STAGE" && timeout "$CLAUDE_TIMEOUT" "$CLAUDE_BIN" "${cargs[@]}" </dev/null ) \
        >>"$LOG" 2>&1 || crc=$?
    if [ "$crc" -ne 0 ]; then
        SEM_NOTE="claude -p exited non-zero (rc=$crc; timeout/error)"
        return 11
    fi

    # --- validate staged output (fail-closed: never inject junk) -------------
    log "step 2: validating staged discovery output"
    local vres
    vres="$("$PY" - "$STAGE" "$N_DOMAINS" "$PREV_TOTAL" "$SEM_FLOOR" "$SEM_MIN_DOMAINS" <<'PYEOF'
import sys, os, json, glob
stage, n_dom, prev_total, floor, min_dom = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4]), int(sys.argv[5])
errs, total, nonempty, per = [], 0, 0, []
for i in range(n_dom):
    p = os.path.join(stage, f"domain-{i}.json")
    if not os.path.isfile(p):
        errs.append(f"domain-{i}.json missing"); per.append(0); continue
    try:
        with open(p) as fh: d = json.load(fh)
    except Exception as e:
        errs.append(f"domain-{i}.json invalid JSON: {e}"); per.append(0); continue
    if not isinstance(d, list):
        errs.append(f"domain-{i}.json not a JSON array"); per.append(0); continue
    bad = 0
    for it in d:
        if not (isinstance(it, dict) and it.get("from") and it.get("to") and it.get("link_type")):
            bad += 1
    if bad:
        errs.append(f"domain-{i}.json: {bad} element(s) missing from/to/link_type")
    per.append(len(d)); total += len(d)
    if d: nonempty += 1
if nonempty < min_dom:
    errs.append(f"only {nonempty} non-empty domain files (< {min_dom})")
if prev_total > 0 and total < floor * prev_total:
    errs.append(f"link count collapsed: {total} < floor {floor:.2f}*{prev_total:.0f}={floor*prev_total:.0f}")
print(json.dumps({"ok": not errs, "total": total, "per": per, "errors": errs}))
PYEOF
)"
    echo "$vres" >>"$LOG"
    local vok
    vok="$("$PY" -c 'import json,sys;print("1" if json.loads(sys.argv[1]).get("ok") else "0")' "$vres" 2>/dev/null || echo 0)"
    if [ "$vok" != "1" ]; then
        SEM_NOTE="staged output failed validation: $vres"
        return 12
    fi
    return 0
}

if [ "$DISCOVER" = "off" ]; then
    log "step 2: discovery DISABLED via --no-discovery; will re-inject existing cache"
    SEM_NOTE="discovery disabled (--no-discovery)"
else
    if run_discovery; then
        DISCOVERY="applied"
        log "step 2: discovery PASSED validation"
    else
        log "step 2: discovery did NOT yield a valid cache -> FALLBACK to existing cache. Reason: ${SEM_NOTE:-unknown}"
    fi
fi

# ---- 3. swap validated staging into the authoritative cache (+ mirror) -------
if [ "$DISCOVERY" = "applied" ]; then
    if [ "$DRYRUN" = "1" ]; then
        log "step 3: [dry-run] would swap $STAGE -> $COMBINED_LINKS (and mirror to $REPO_LINKS)"
    else
        # atomic-ish: build into a temp dir next to the target, then mv into place
        TMPNEW="$COMBINED_LINKS.new.$$"
        rm -rf "$TMPNEW"; cp -a "$STAGE" "$TMPNEW"
        rm -rf "$COMBINED_LINKS"; mv "$TMPNEW" "$COMBINED_LINKS"
        rm -rf "$REPO_LINKS"; cp -a "$COMBINED_LINKS" "$REPO_LINKS"
        log "step 3: swapped freshly-discovered cache into $COMBINED_LINKS ($(count_links "$COMBINED_LINKS") links) + mirrored to repo"
    fi
else
    log "step 3: keeping existing authoritative cache ($PREV_TOTAL links)"
fi

# ---- dry-run stops here (no rebuild, no commit; live cache never swapped) ----
if [ "$DRYRUN" = "1" ]; then
    log "=== weekly_semantic dry-run done (discovery=$DISCOVERY; NO rebuild/commit) ==="
    prune_backups
    notify ok "JIVO Data Bank weekly_semantic DRY-RUN — discovery=$DISCOVERY. No swap/commit performed."
    exit 0
fi

# ---- 4. rebuild + verify + commit via the fail-closed engine ----------------
# daily_rebuild.sh: preserves $COMBINED/.links, runs combined_inject_links.py,
# rebuilds the backbone, runs verify_databank.py, and commits ONLY if every gate
# passes (it leaves git clean on any failure). We force semantic injection ON.
log "step 4: daily_rebuild.sh (inject_links + rebuild + verify + fail-closed commit)"
rc=0
JDB_SEMANTIC=yes "$REBUILD" >>"$LOG" 2>&1 || rc=$?

if [ "$rc" -ne 0 ]; then
    # The vault build regressed. daily_rebuild already refused to commit and left
    # git clean; we additionally roll the cache back so the next daily run uses a
    # known-good cache rather than this run's (possibly bad) discovery.
    log "step 4: rebuild/verify FAILED (rc=$rc) — NOT committed; restoring prior cache"
    if [ "$DISCOVERY" = "applied" ]; then
        restore_cache
    fi
    prune_backups
    notify fail "❌ JIVO Data Bank weekly semantic refresh FAILED (rebuild/verify rc=$rc). Vault NOT committed; cache rolled back. Log: $LOG"
    log "=== weekly_semantic done (FAILED rc=$rc) ==="
    exit "$rc"
fi

prune_backups
NOW="$(date '+%Y-%m-%d %H:%M %Z')"
if [ "$DISCOVERY" = "applied" ]; then
    NEW_TOTAL="$(count_links "$COMBINED_LINKS")"
    log "step 4: rebuild PASSED — fresh semantic cache applied ($NEW_TOTAL links). NOT pushing (daily/owner pushes)."
    notify ok "✅ JIVO Data Bank weekly SEMANTIC refresh OK — $NOW. Re-discovered cache: $NEW_TOTAL links (was $PREV_TOTAL), zero-loss verified & committed. (push happens on the next daily run)"
else
    log "step 4: rebuild PASSED — semantic re-discovery SKIPPED (${SEM_NOTE:-fallback}); existing cache re-injected."
    notify warn "⚠️ JIVO Data Bank weekly refresh OK but semantic re-discovery was SKIPPED ($SEM_NOTE) — existing $PREV_TOTAL-link cache re-injected, zero-loss verified & committed. Log: $LOG"
fi

log "=== weekly_semantic done (rebuild=ok discovery=$DISCOVERY) ==="
# This script NEVER pushes — the verified commit rides out on the next daily
# run_daily.sh (stage 2) or via the owner. See install_cron.sh / RUNBOOK.md.
exit 0
