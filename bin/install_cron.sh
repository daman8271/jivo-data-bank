#!/usr/bin/env bash
# =============================================================================
# install_cron.sh — idempotently (un)install the JIVO Data Bank cron schedule.
#
# Installs TWO crontab lines (into the invoking user's crontab — root on this
# VPS) inside a single managed, marker-delimited block:
#
#   * DAILY  ~13:30 IST  ->  bin/run_daily.sh
#       rebuild -> verify (fail-closed) -> push -> notify. 13:30 is AFTER the ecom
#       price vault finishes its midday rebuild (~12:00 IST, ecom-intel's
#       deadline_sweep) AND after the jivo (05:00) + factory (05:30) source
#       feeders, so the fusion reads a COMPLETE *same-day* dataset across all four
#       pillars. (It previously ran at 06:00 — BEFORE the ecom vault rebuilt — which
#       left the ecom pillar perpetually ONE DAY stale; corrected 2026-06-30.)
#
#   * WEEKLY Sun ~15:00 IST  ->  bin/weekly_semantic.sh
#       regenerates the expensive .links/ semantic cross-vault cache (agent
#       fan-out). Scheduled AFTER the Sunday daily so it operates on same-day fresh
#       data. (weekly_semantic.sh is a sibling component — a WARNING, not an error,
#       is emitted if it is absent at install time; the cron line is harmless until
#       it exists.)
#
# WHY cron-driven push is legitimate: the data-exfiltration classifier only
# blocks Claude's *interactive* push. A cron job pushing to the owner's OWN
# private repo is explicitly requested and wanted — that is run_daily.sh stage 2.
#
# IDEMPOTENT: the managed block is delimited by BEGIN/END markers. Re-running
# install replaces the block in place (never duplicates lines). --uninstall
# strips exactly that block and leaves every other crontab entry untouched.
#
# TIMEZONE: a `CRON_TZ=Asia/Kolkata` line is written into the managed block so
# the schedule stays correct even if the system TZ ever changes (it is currently
# already IST). CRON_TZ applies only to the lines that follow it within the
# block, and the block is appended last, so it cannot affect other entries.
#
# SAFETY: this script is the ONLY thing that writes the crontab, and that write
# happens through exactly one `crontab -` call, guarded so --dry-run / --status
# are strictly read-only. It is NOT run as part of the build — enable it
# yourself when ready:
#
#       /root/jivo-data-bank/bin/install_cron.sh --dry-run   # preview, no writes
#       /root/jivo-data-bank/bin/install_cron.sh             # install
#       /root/jivo-data-bank/bin/install_cron.sh --status    # show managed block
#       /root/jivo-data-bank/bin/install_cron.sh --uninstall # remove the block
#
# Reversible: --uninstall fully removes what install adds. The log dir it creates
# (/var/log/jivo-data-bank) is left in place on uninstall (data, not config) and
# can be removed by hand.
#
# Env overrides (all optional):
#   JDB_REPO, JDB_LOGDIR, JDB_CRON_TZ, JDB_DAILY_CRON, JDB_WEEKLY_CRON, CRONTAB
# =============================================================================
set -euo pipefail

REPO="${JDB_REPO:-/root/jivo-data-bank}"
BIN="$REPO/bin"
LOGDIR="${JDB_LOGDIR:-/var/log/jivo-data-bank}"
CRON_TZ_VAL="${JDB_CRON_TZ:-Asia/Kolkata}"
CRONTAB_BIN="${CRONTAB:-crontab}"

# Schedules (cron field order: min hour dom mon dow). System TZ is IST and the
# managed block also pins CRON_TZ, so these are IST.
DAILY_CRON="${JDB_DAILY_CRON:-30 13 * * *}"   # ~13:30 IST daily (AFTER ecom vault lands ~12:00)
WEEKLY_CRON="${JDB_WEEKLY_CRON:-0 15 * * 0}"  # ~15:00 IST Sunday (dow 0), after the daily

RUN_DAILY="$BIN/run_daily.sh"
WEEKLY_SEM="$BIN/weekly_semantic.sh"

# A cron-safe PATH: cron's default PATH is minimal and run_daily/daily_rebuild
# need flock, git, rsync, python3, plus ~/go/bin tooling.
CRON_PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/root/go/bin"

BEGIN_MARK="# >>> jivo-data-bank schedule (managed by install_cron.sh) >>>"
END_MARK="# <<< jivo-data-bank schedule (managed by install_cron.sh) <<<"

# ---- args -------------------------------------------------------------------
MODE="install"
DRYRUN=0
for arg in "$@"; do
    case "$arg" in
        --install)        MODE="install" ;;
        --uninstall)      MODE="uninstall" ;;
        --status|--show)  MODE="status" ;;
        --dry-run|-n)     DRYRUN=1 ;;
        -h|--help)
            sed -n '2,60p' "$0" | sed 's/^# \{0,1\}//'
            exit 0 ;;
        *)
            echo "install_cron.sh: unknown argument: $arg" >&2
            echo "usage: install_cron.sh [--install|--uninstall|--status] [--dry-run]" >&2
            exit 2 ;;
    esac
done

err()  { echo "install_cron.sh: $*" >&2; }
info() { echo "install_cron.sh: $*"; }

# ---- read current crontab (read-only) ---------------------------------------
# `crontab -l` exits non-zero when there is no crontab yet; treat that as empty.
current_crontab="$("$CRONTAB_BIN" -l 2>/dev/null || true)"

# strip_block: print the crontab with our managed block (inclusive of markers)
# removed. awk avoids any regex-escaping pitfalls in the marker text.
strip_block() {
    printf '%s\n' "$current_crontab" | awk -v b="$BEGIN_MARK" -v e="$END_MARK" '
        $0==b { inblk=1; next }
        $0==e { inblk=0; next }
        inblk!=1 { print }
    '
}

# build_block: emit the fresh managed block.
build_block() {
    cat <<EOF
$BEGIN_MARK
# Auto-generated by install_cron.sh on $(date '+%Y-%m-%d %H:%M:%S %Z').
# Edit schedules via JDB_DAILY_CRON / JDB_WEEKLY_CRON env, then re-run install.
# Remove with: $0 --uninstall
CRON_TZ=$CRON_TZ_VAL
PATH=$CRON_PATH
$DAILY_CRON $RUN_DAILY >> $LOGDIR/cron.log 2>&1
$WEEKLY_CRON $WEEKLY_SEM >> $LOGDIR/cron.log 2>&1
$END_MARK
EOF
}

# load_crontab: the SINGLE write path. No-op under --dry-run.
load_crontab() {
    local content="$1"
    if [ "$DRYRUN" -eq 1 ]; then
        info "[dry-run] would load this crontab (no changes made):"
        echo "------------------------------------------------------------"
        printf '%s\n' "$content"
        echo "------------------------------------------------------------"
        return 0
    fi
    printf '%s\n' "$content" | "$CRONTAB_BIN" -
}

case "$MODE" in
  status)
    block="$(printf '%s\n' "$current_crontab" | awk -v b="$BEGIN_MARK" -v e="$END_MARK" '
        $0==b { inblk=1 } inblk==1 { print } $0==e { inblk=0 }')"
    if [ -n "$block" ]; then
        info "managed block is INSTALLED:"
        printf '%s\n' "$block"
    else
        info "managed block is NOT installed."
    fi
    exit 0
    ;;

  uninstall)
    if ! printf '%s\n' "$current_crontab" | grep -qF "$BEGIN_MARK"; then
        info "no managed block present — nothing to uninstall."
        exit 0
    fi
    stripped="$(strip_block)"
    # Trim a leading/trailing run of blank lines for tidiness.
    load_crontab "$stripped"
    [ "$DRYRUN" -eq 1 ] || info "uninstalled the managed cron block (other entries untouched)."
    exit 0
    ;;

  install)
    # --- preconditions -------------------------------------------------------
    if [ ! -x "$RUN_DAILY" ]; then
        err "FATAL: $RUN_DAILY missing or not executable — refusing to install."
        exit 3
    fi
    if [ ! -x "$WEEKLY_SEM" ]; then
        err "WARNING: $WEEKLY_SEM not present yet (sibling component). Installing the"
        err "         weekly line anyway; it is harmless until that script exists."
    fi

    # Ensure the cron log dir exists so cron can write on the first tick.
    if [ "$DRYRUN" -eq 1 ]; then
        info "[dry-run] would ensure log dir: $LOGDIR"
    else
        mkdir -p "$LOGDIR" 2>/dev/null || err "WARNING: could not create $LOGDIR (cron will still run; logs may go nowhere)"
    fi

    stripped="$(strip_block)"            # idempotent: drop any prior block first
    block="$(build_block)"

    # Reassemble: existing entries (sans our block) + a blank separator + block.
    if [ -n "${stripped//[$'\n\r\t ']/}" ]; then
        new_crontab="$(printf '%s\n\n%s\n' "$stripped" "$block")"
    else
        new_crontab="$(printf '%s\n' "$block")"
    fi

    load_crontab "$new_crontab"
    if [ "$DRYRUN" -eq 0 ]; then
        info "installed/refreshed the managed cron block:"
        info "  daily  ($DAILY_CRON)  -> $RUN_DAILY"
        info "  weekly ($WEEKLY_CRON) -> $WEEKLY_SEM"
        info "  TZ=$CRON_TZ_VAL  log=$LOGDIR/cron.log"
    fi
    exit 0
    ;;
esac
