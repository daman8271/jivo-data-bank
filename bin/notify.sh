#!/usr/bin/env bash
# =============================================================================
# notify.sh — Telegram notifier for the JIVO Data Bank daily rebuild.
#
# One small, dependency-light helper that the cron-driven daily_rebuild.sh (and
# a human) can call to push status to the owner over Telegram. It is BEST-EFFORT
# by contract: a delivery failure must NEVER mask or abort the rebuild, so every
# call site appends `|| true`. The script itself returns a meaningful exit code
# (see each subcommand) so a caller that *wants* to branch on "did it alert?"
# can, but daily_rebuild treats it as fire-and-forget.
#
# Credentials are read at RUNTIME from ~/.config/tg/env
#   TELEGRAM_BOT_TOKEN=...     TELEGRAM_CHAT_ID=...
# The bot token is passed to curl via a config file on STDIN (never on argv),
# so it does not appear in `ps`. CARDINAL RULE: this script never prints a token
# and never writes any secret to disk, source, docs, or git.
#
# Generic form (the documented contract):
#   notify.sh <STATUS> <message...>     # STATUS in {OK,SUCCESS,WARN,FAIL,
#                                       #   ERROR,ALERT,INFO,...}; picks an emoji
#
# Helper subcommands (lowercase, reserved — they COMPUTE their own message):
#   notify.sh success   [--repo DIR] [--vault DIR] [--verify-json FILE]
#       daily SUCCESS: product/hub/source-note + link counts + commit hash.
#   notify.sh failure   <reason...>            [--log FILE] [--tail N]
#       rebuild ABORT with the reason (+ optional last N lines of the log).
#   notify.sh staleness [--src DIR] [--days N] [--force]
#       alert ONLY if the JIVO source vault's newest data file is older than N
#       days (default 2). Quiet (no send) when fresh, unless --force.
#   notify.sh token     [--config FILE] [--hours H] [--force]
#       JIVO bearer token (~24h life) expiry reminder: alert when <= H hours
#       remain (default 6) or already expired. Quiet when healthy, unless --force.
#
# Testing without spamming Telegram:
#   NOTIFY_DRY_RUN=1 notify.sh ...      # prints the message to stdout, no send.
#
# Reversible: this file is standalone state-free; remove it to fully revert.
# =============================================================================
set -uo pipefail

# ---- config (override via env) ----------------------------------------------
TG_ENV="${TG_ENV:-$HOME/.config/tg/env}"
JDB_REPO="${JDB_REPO:-/root/jivo-data-bank}"
JIVO_SRC="${JDB_JIVO_SRC:-/root/jivo-intel/vault}"
JIVO_TOKEN_CFG="${JIVO_TOKEN_CFG:-$HOME/.config/jivo-ecom-pp-cli/config.toml}"
NOTIFY_LOG="${NOTIFY_LOG:-}"            # optional: append a one-line audit record
DRY_RUN="${NOTIFY_DRY_RUN:-0}"

HOST="$(hostname 2>/dev/null || echo vps)"

logline() {
    [ -n "$NOTIFY_LOG" ] || return 0
    printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >>"$NOTIFY_LOG" 2>/dev/null || true
}

# Insert thousands separators into a bare integer (locale-free).
comma() { printf '%s' "${1:-0}" | sed -E ':a;s/([0-9])([0-9]{3})($|[^0-9])/\1,\2\3/;ta'; }

# ---- raw Telegram sendMessage (token kept off argv) --------------------------
# stdin: full message text. returns 0 on Telegram ok:true, 1 otherwise.
send_telegram() {
    local text; text="$(cat)"

    if [ "$DRY_RUN" = "1" ]; then
        printf -- '--- NOTIFY DRY RUN (no send) ---\n%s\n--------------------------------\n' "$text"
        logline "DRY_RUN: ${text%%$'\n'*}"
        return 0
    fi

    if [ ! -f "$TG_ENV" ]; then
        printf 'notify: missing creds file: %s\n' "$TG_ENV" >&2
        logline "FAILED: missing $TG_ENV"
        return 1
    fi
    set -a
    # shellcheck disable=SC1090
    . "$TG_ENV" 2>/dev/null || true
    set +a
    if [ -z "${TELEGRAM_BOT_TOKEN:-}" ] || [ -z "${TELEGRAM_CHAT_ID:-}" ]; then
        printf 'notify: TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set in %s\n' "$TG_ENV" >&2
        logline "FAILED: creds unset in $TG_ENV"
        return 1
    fi

    local bodyfile resp
    bodyfile="$(mktemp 2>/dev/null)" || { echo "notify: mktemp failed" >&2; return 1; }
    printf '%s' "$text" >"$bodyfile"

    # URL (with the secret token) goes via --config on STDIN, NOT argv.
    resp="$(printf 'url = "https://api.telegram.org/bot%s/sendMessage"\n' "$TELEGRAM_BOT_TOKEN" \
        | curl -sS -m 15 --config - \
            --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
            --data-urlencode "disable_web_page_preview=true" \
            --data-urlencode "text@${bodyfile}" 2>/dev/null)"
    rm -f "$bodyfile"

    case "$resp" in
        *'"ok":true'*) logline "sent ok"; return 0 ;;
        *) printf 'notify: telegram send failed: %s\n' "${resp:0:200}" >&2
           logline "FAILED: ${resp:0:160}"; return 1 ;;
    esac
}

# ---- compose footer + dispatch to send --------------------------------------
# args: <emoji> <title> <body...>
build_and_send() {
    local emoji="$1" title="$2"; shift 2
    local body="$*"
    local stamp; stamp="$(date '+%Y-%m-%d %H:%M:%S %Z' 2>/dev/null || date)"
    printf '%s %s\n%s\n\n🖥 %s · 🕒 %s\n' \
        "$emoji" "$title" "$body" "$HOST" "$stamp" | send_telegram
}

emoji_for() {
    case "$(printf '%s' "${1:-}" | tr '[:lower:]' '[:upper:]')" in
        OK|SUCCESS|DONE|PASS)        echo "✅" ;;
        WARN|WARNING|STALE|STALENESS)echo "⚠️" ;;
        FAIL|FAILURE|ERROR|ABORT)    echo "❌" ;;
        ALERT|CRITICAL)              echo "🚨" ;;
        TOKEN|AUTH|KEY)              echo "🔑" ;;
        *)                           echo "ℹ️" ;;
    esac
}

# =============================================================================
# HELPER: success — product/hub/source-note + link counts + commit hash
# =============================================================================
cmd_success() {
    local repo="$JDB_REPO" vault="" verify_json=""
    while [ $# -gt 0 ]; do
        case "$1" in
            --repo) repo="$2"; shift 2 ;;
            --vault) vault="$2"; shift 2 ;;
            --verify-json) verify_json="$2"; shift 2 ;;
            *) shift ;;
        esac
    done
    [ -n "$vault" ] || vault="$repo"

    # filesystem counts (always available)
    local products hubs
    products="$(ls "$repo"/products/*.md 2>/dev/null | wc -l | tr -d ' ')"
    hubs="$(ls "$repo"/hubs/*.md 2>/dev/null | wc -l | tr -d ' ')"

    # source-note total from the rebuild manifest
    local source_notes="?"
    if [ -f "$vault/.manifest.json" ]; then
        source_notes="$(jq -r '.summary.combined_dest_notes // empty' "$vault/.manifest.json" 2>/dev/null)"
        [ -n "$source_notes" ] || source_notes="?"
    fi

    # link counts: prefer a provided verify JSON, else run verify read-only.
    local links="?" broken="?" vjson=""
    if [ -n "$verify_json" ] && [ -f "$verify_json" ]; then
        vjson="$(cat "$verify_json" 2>/dev/null)"
    elif [ -x "$repo/bin/verify_databank.py" ] || [ -f "$repo/bin/verify_databank.py" ]; then
        vjson="$(python3 "$repo/bin/verify_databank.py" --vault "$vault" 2>/dev/null)"
    fi
    if [ -n "$vjson" ]; then
        links="$(printf '%s' "$vjson"  | jq -r '.info.generated_links_checked // empty' 2>/dev/null)"
        broken="$(printf '%s' "$vjson" | jq -r '.info.broken_links // empty' 2>/dev/null)"
        # let verify's own (authoritative) counts win when present
        local vp vh vs
        vp="$(printf '%s' "$vjson" | jq -r '.info.products // empty' 2>/dev/null)"
        vh="$(printf '%s' "$vjson" | jq -r '.info.hubs // empty' 2>/dev/null)"
        vs="$(printf '%s' "$vjson" | jq -r '.info.source_notes // empty' 2>/dev/null)"
        [ -n "$vp" ] && products="$vp"
        [ -n "$vh" ] && hubs="$vh"
        [ -n "$vs" ] && source_notes="$vs"
        [ -n "$links" ]  || links="?"
        [ -n "$broken" ] || broken="?"
    fi

    # git commit identity
    local hash subj cdate
    hash="$(git -C "$repo" rev-parse --short HEAD 2>/dev/null || echo '?')"
    subj="$(git -C "$repo" log -1 --pretty=%s 2>/dev/null || echo '(no commit)')"
    cdate="$(git -C "$repo" log -1 --pretty=%cd --date=short 2>/dev/null || date -u +%Y-%m-%d)"

    local body
    body="$(printf '%s\n\n📦 products: %s\n🗂 hubs: %s\n📝 source notes: %s\n🔗 links checked: %s (broken: %s)\n🔖 commit: %s — %s' \
        "Deterministic rebuild verified, committed, ready to push." \
        "$(comma "$products")" "$(comma "$hubs")" "$(comma "$source_notes")" \
        "$(comma "$links")" "$broken" "$hash" "$subj")"

    build_and_send "✅" "JIVO Data Bank — daily rebuild OK ($cdate)" "$body"
}

# =============================================================================
# HELPER: failure — abort reason (+ optional tail of the rebuild log)
# =============================================================================
cmd_failure() {
    local logf="" tail_n=10 reason=""
    while [ $# -gt 0 ]; do
        case "$1" in
            --log) logf="$2"; shift 2 ;;
            --tail) tail_n="$2"; shift 2 ;;
            *) reason="${reason:+$reason }$1"; shift ;;
        esac
    done
    [ -n "$reason" ] || reason="(no reason given)"

    local body="Rebuild ABORTED — nothing committed, last good commit stands.

reason: $reason"
    if [ -n "$logf" ] && [ -f "$logf" ] && [ "${tail_n:-0}" -gt 0 ] 2>/dev/null; then
        body="$body

— last $tail_n log lines —
$(tail -n "$tail_n" "$logf" 2>/dev/null)"
    fi
    build_and_send "❌" "JIVO Data Bank — rebuild FAILED" "$body"
}

# =============================================================================
# HELPER: staleness — JIVO source vault older than N days (quiet when fresh)
# =============================================================================
# exit: 0 fresh (no send) | 10 stale (alert sent) | 2 error
cmd_staleness() {
    local src="$JIVO_SRC" days=2 force=0
    while [ $# -gt 0 ]; do
        case "$1" in
            --src) src="$2"; shift 2 ;;
            --days) days="$2"; shift 2 ;;
            --force) force=1; shift ;;
            *) shift ;;
        esac
    done

    if [ ! -d "$src" ]; then
        build_and_send "⚠️" "JIVO Data Bank — source MISSING" \
            "JIVO source vault not found at: $src
The daily rebuild has no fresh app data to build from."
        return 10
    fi

    # newest data file mtime, EXCLUDING the hand-edited SESSION-MEMORY.md note
    local newest
    newest="$(find "$src" -type f -name '*.md' ! -name 'SESSION-MEMORY.md' \
                -printf '%T@\n' 2>/dev/null | sort -rn | head -1)"
    if [ -z "$newest" ]; then
        build_and_send "⚠️" "JIVO Data Bank — source EMPTY" \
            "No .md data files under: $src"
        return 10
    fi

    local now age_days age_iso
    now="$(date +%s)"
    age_days="$(awk -v n="$now" -v m="$newest" 'BEGIN{printf "%d", (n-m)/86400}')"
    age_iso="$(date -d "@${newest%.*}" '+%Y-%m-%d %H:%M' 2>/dev/null || echo '?')"

    if [ "$age_days" -gt "$days" ] || [ "$force" = "1" ]; then
        local title="JIVO Data Bank — source STALE"
        [ "$age_days" -gt "$days" ] || title="JIVO Data Bank — source freshness"
        build_and_send "⚠️" "$title" \
            "JIVO app source last refreshed: $age_iso (${age_days}d ago, threshold ${days}d).
Owner action: re-auth the JIVO CLI and re-pull the app vault so the data bank
does not freeze on yesterday's data.
  jivo-ecom-pp-cli auth login   # then re-run the jivo-intel pull"
        [ "$age_days" -gt "$days" ] && return 10
        return 0
    fi
    printf 'notify: source fresh (%dd <= %dd); no alert sent\n' "$age_days" "$days" >&2
    logline "staleness: fresh (${age_days}d)"
    return 0
}

# =============================================================================
# HELPER: token — JIVO bearer token (~24h) expiry reminder (quiet when healthy)
# =============================================================================
# exit: 0 healthy (no send) | 11 reminder sent | 2 error
cmd_token() {
    local cfg="$JIVO_TOKEN_CFG" hours=6 force=0
    while [ $# -gt 0 ]; do
        case "$1" in
            --config) cfg="$2"; shift 2 ;;
            --hours) hours="$2"; shift 2 ;;
            --force) force=1; shift ;;
            *) shift ;;
        esac
    done

    if [ ! -f "$cfg" ]; then
        build_and_send "🔑" "JIVO Data Bank — token config MISSING" \
            "No JIVO CLI config at: $cfg
Owner must run: jivo-ecom-pp-cli auth login"
        return 11
    fi

    # parse the bare TOML datetime; NEVER read or print the token itself
    local exp_raw exp_epoch now secs_left hours_left
    exp_raw="$(grep -E '^[[:space:]]*token_expiry[[:space:]]*=' "$cfg" 2>/dev/null \
                | head -1 | sed -E 's/^[^=]*=[[:space:]]*//; s/^["'\'']//; s/["'\'']$//' \
                | tr -d '[:space:]')"
    if [ -z "$exp_raw" ]; then
        build_and_send "🔑" "JIVO Data Bank — token expiry unknown" \
            "Could not read token_expiry from $cfg.
Owner should verify auth: jivo-ecom-pp-cli auth login"
        return 11
    fi
    exp_epoch="$(date -d "$exp_raw" +%s 2>/dev/null)"
    if [ -z "$exp_epoch" ]; then
        build_and_send "🔑" "JIVO Data Bank — token expiry unparseable" \
            "token_expiry value '$exp_raw' could not be parsed."
        return 11
    fi

    now="$(date +%s)"
    secs_left=$(( exp_epoch - now ))
    hours_left=$(( secs_left / 3600 ))

    if [ "$secs_left" -le 0 ]; then
        build_and_send "🔑" "JIVO Data Bank — token EXPIRED" \
            "The JIVO bearer token expired $(( -hours_left ))h ago ($exp_raw).
Pulls will fail until re-auth. Owner action:
  jivo-ecom-pp-cli auth login"
        return 11
    fi

    if [ "$secs_left" -le $(( hours * 3600 )) ] || [ "$force" = "1" ]; then
        build_and_send "🔑" "JIVO Data Bank — token expiry reminder" \
            "JIVO bearer token expires in ~${hours_left}h (at $exp_raw).
The token lives ~24h; re-auth before the next pull so the data bank stays fresh:
  jivo-ecom-pp-cli auth login"
        [ "$force" = "1" ] && [ "$secs_left" -gt $(( hours * 3600 )) ] && return 0
        return 11
    fi
    printf 'notify: token healthy (~%dh left > %dh); no reminder sent\n' "$hours_left" "$hours" >&2
    logline "token: healthy (~${hours_left}h)"
    return 0
}

# =============================================================================
# usage
# =============================================================================
usage() {
    sed -n '2,60p' "$0" | sed 's/^# \{0,1\}//'
}

# =============================================================================
# dispatch
# =============================================================================
main() {
    local cmd="${1:-}"
    case "$cmd" in
        ""|-h|--help|help) usage; return 0 ;;
        success)   shift; cmd_success "$@" ;;
        failure)   shift; cmd_failure "$@" ;;
        staleness) shift; cmd_staleness "$@" ;;
        token)     shift; cmd_token "$@" ;;
        *)
            # generic: notify.sh <STATUS> <message...>
            shift || true
            local status="$cmd" msg="$*"
            [ -n "$msg" ] || msg="(no message)"
            build_and_send "$(emoji_for "$status")" "JIVO Data Bank — $status" "$msg"
            ;;
    esac
}

main "$@"
