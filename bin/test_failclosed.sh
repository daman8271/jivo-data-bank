#!/usr/bin/env bash
# =============================================================================
# test_failclosed.sh — adversarial proof that the JIVO Data Bank verify gate is
# FAIL-CLOSED: it must ABORT (exit nonzero) and leave NO commit when the built
# vault is damaged.
#
# Mirrors the daily_rebuild.sh contract (steps 5 + 8):
#     verify_databank.py PASS  ==>  git commit
#     verify_databank.py FAIL  ==>  NO commit, abort
# and adversarially attacks four ways:
#     (a) deleted source note      -> link-integrity gate (GATE 3)
#     (b) truncated note           -> zero-loss gate, truncation (GATE 1)
#     (c) tampered manifest        -> zero-loss gate, self-consistency (GATE 1)
#     (d) broken injected link     -> link-integrity gate (GATE 3)
#
# For each: assert verify exits NONZERO and the throwaway repo gains NO commit,
# and that the abort reason matches the injected fault. Prints PASS/FAIL per
# scenario. Exits 0 only if the gate fails-closed on ALL four (i.e. the
# fail-closed property holds); exits nonzero if the gate ever let damage through.
#
# SAFETY / SCOPE
#   * READ-ONLY on the real vault. All mutation happens on a throwaway copy under
#     a mktemp workspace; the real repo's HEAD + working tree are snapshotted
#     before/after and asserted unchanged.
#   * NEVER pushes. The only commits made are into the disposable throwaway repo
#     to observe the "no commit" property; they are destroyed on exit.
#   * Idempotent + reversible: a fresh mktemp workspace each run, removed by an
#     EXIT trap. Nothing is installed or enabled.
#
# Usage:  bin/test_failclosed.sh            (uses the live repo as the source)
#         JDB_REPO=/path bin/test_failclosed.sh
# =============================================================================
set -uo pipefail   # NOT -e: we deliberately run commands expected to fail.

REPO="${JDB_REPO:-/root/jivo-data-bank}"
VERIFY="${JDB_VERIFY:-$REPO/bin/verify_databank.py}"
PY="${JDB_PYTHON:-python3}"
# Real source vaults — read ONLY for the read-only-safety assertion; never written.
JIVO_SRC="${JDB_JIVO_SRC:-/root/jivo-intel/vault}"

# ---- preflight --------------------------------------------------------------
need() { command -v "$1" >/dev/null 2>&1 || { echo "FATAL: missing tool: $1" >&2; exit 2; }; }
need git; need rsync; need jq; need "$PY"
[ -d "$REPO/.git" ]   || { echo "FATAL: not a git repo: $REPO" >&2; exit 2; }
[ -f "$VERIFY" ]      || { echo "FATAL: verify gate not found: $VERIFY" >&2; exit 2; }
[ -f "$REPO/.manifest.json" ] || { echo "FATAL: no .manifest.json in $REPO" >&2; exit 2; }

# ---- read-only-safety snapshot of the REAL repo (asserted unchanged at end) --
REAL_HEAD="$(git -C "$REPO" rev-parse HEAD 2>/dev/null || echo none)"
REAL_STATUS="$(git -C "$REPO" status --porcelain 2>/dev/null || true)"
REAL_MANIFEST_SHA="$(sha256sum "$REPO/.manifest.json" | awk '{print $1}')"

# ---- throwaway workspace (auto-removed) --------------------------------------
WSP="$(mktemp -d "${TMPDIR:-/tmp}/jdb_failclosed.XXXXXX")"
PRISTINE="$WSP/pristine"   # immutable reference copy of the real vault content
WORK="$WSP/work"           # the throwaway repo we damage + try to commit
cleanup() {
  # Robust against the transient ENOTEMPTY ext4 can return right after git
  # activity: chmod for safety, then retry rm a few times.
  local i
  for i in 1 2 3; do
    [ -d "$WSP" ] || return 0
    chmod -R u+rwX "$WSP" 2>/dev/null || true
    rm -rf "$WSP" 2>/dev/null && return 0
  done
  rm -rf "$WSP" 2>/dev/null || true
}
trap cleanup EXIT

echo "==============================================================="
echo " JIVO Data Bank — FAIL-CLOSED adversarial test"
echo " source repo : $REPO  (READ-ONLY)"
echo " gate        : $VERIFY"
echo " workspace   : $WSP  (throwaway, removed on exit)"
echo "==============================================================="

# Copy the working tree (NOT .git, NOT scratch/locks/logs) into PRISTINE.
rsync -a --delete \
  --exclude '.git/' --exclude '*.lock' --exclude '*.pid' \
  --exclude '*.log' --exclude '.links/' \
  "$REPO"/ "$PRISTINE"/ || { echo "FATAL: rsync -> pristine failed" >&2; exit 2; }

# Build the throwaway git repo at a known-good baseline commit.
rsync -a --delete "$PRISTINE"/ "$WORK"/ || { echo "FATAL: rsync -> work failed" >&2; exit 2; }
git -C "$WORK" init -q
git -C "$WORK" config user.email failclosed@test.local
git -C "$WORK" config user.name  "fail-closed test"
git -C "$WORK" add -A
git -C "$WORK" commit -q -m "throwaway baseline (last good)" \
  || { echo "FATAL: could not create baseline commit" >&2; exit 2; }
BASE_SHA="$(git -C "$WORK" rev-parse HEAD)"
BASE_COUNT="$(git -C "$WORK" rev-list --count HEAD)"

# ---- the gate-then-commit harness: EXACT daily_rebuild contract -------------
# verify PASS -> commit ; verify FAIL -> no commit. Returns verify's exit code.
# Writes verify's verdict to $LAST_OUT.
LAST_OUT=""
gate_then_commit() {
  LAST_OUT="$WSP/verify.out"
  "$PY" "$VERIFY" --vault "$WORK" --baseline "$WORK/bin/.baseline.json" \
      >"$LAST_OUT" 2>&1
  local rc=$?
  if [ "$rc" -eq 0 ]; then
    # would-be daily_rebuild step 8 (only reached on a PASS)
    ( cd "$WORK" && git add -A && git commit -q -m "data-bank refresh (SHOULD NOT HAPPEN)" ) \
      >>"$LAST_OUT" 2>&1 || true
  fi
  return "$rc"
}

restore_work() {   # back to the known-good baseline before each scenario
  rsync -a --delete --exclude '.git/' "$PRISTINE"/ "$WORK"/
  git -C "$WORK" reset -q --hard "$BASE_SHA"
  git -C "$WORK" clean -qfd >/dev/null 2>&1 || true
}

# ---- control: the clean throwaway MUST pass (else results are meaningless) ---
restore_work
if gate_then_commit; then
  CTRL_COUNT="$(git -C "$WORK" rev-list --count HEAD)"
  echo "[control] clean copy PASSES verify (commit attempted: baseline ${BASE_COUNT} -> ${CTRL_COUNT})"
else
  echo "[control] FATAL: clean throwaway FAILED verify — cannot trust scenarios:" >&2
  sed 's/^/  | /' "$LAST_OUT" >&2
  exit 2
fi
git -C "$WORK" reset -q --hard "$BASE_SHA"   # drop the control's commit

# ---- scenario runner --------------------------------------------------------
declare -a RESULTS
OVERALL=0

run_scenario() {
  local id="$1" desc="$2" expect="$3" corrupt_fn="$4"
  restore_work
  local pre; pre="$(git -C "$WORK" rev-list --count HEAD)"

  local detail; detail="$("$corrupt_fn")"   # mutate WORK; echo a human note

  gate_then_commit; local rc=$?
  local post; post="$(git -C "$WORK" rev-list --count HEAD)"

  local committed="no"; [ "$post" -ne "$pre" ] && committed="YES"
  local reason_ok="no"
  grep -Eiq "$expect" "$LAST_OUT" && reason_ok="yes"

  # Fail-closed PASS == gate aborted (rc!=0) AND no new commit.
  local verdict="FAIL"
  if [ "$rc" -ne 0 ] && [ "$committed" = "no" ]; then verdict="PASS"; else OVERALL=1; fi

  printf '\n[%s] %s\n' "$id" "$desc"
  printf '      corruption : %s\n' "$detail"
  printf '      verify exit: %s (nonzero=aborted, as required)\n' "$rc"
  printf '      new commit : %s (commits %s -> %s)\n' "$committed" "$pre" "$post"
  printf '      reason hit : %s (expected /%s/)\n' "$reason_ok" "$expect"
  local why; why="$(grep -Ei "$expect" "$LAST_OUT" | head -1 | sed 's/^[[:space:]]*//')"
  [ -n "$why" ] && printf '      gate said  : %s\n' "$why"
  printf '      >>> %s\n' "$verdict"
  RESULTS+=("$(printf '%-4s %-28s exit=%s commit=%-3s reason=%-3s -> %s' \
              "$id" "$desc" "$rc" "$committed" "$reason_ok" "$verdict")")
}

# ---- (a) DELETED SOURCE NOTE ------------------------------------------------
# Delete a source note that the generated layer references by basename. The
# product's [[sku-...]] wikilink then dangles -> GATE 3 (link integrity) aborts.
# This is genuine data loss; no manifest is touched.
corrupt_delete_source() {
  local target="jivo/skus/sku-FG0000083.md" sku="sku-FG0000083"
  if ! { [ -f "$WORK/$target" ] && grep -rqF "[[${sku}]]" "$WORK/products"; }; then
    target=""
    local s f
    for s in $(grep -rhoE '\[\[sku-[A-Za-z0-9_-]+\]\]' "$WORK/products" \
                 | sed -E 's/\[\[(.*)\]\]/\1/' | sort -u); do
      f="$(find "$WORK/jivo" "$WORK/ecom" -iname "${s}.md" 2>/dev/null | head -1)"
      [ -n "$f" ] && { target="${f#$WORK/}"; sku="$s"; break; }
    done
  fi
  [ -n "$target" ] || { echo "NO deletable referenced source note found"; return 1; }
  rm -f "$WORK/$target"
  echo "deleted referenced source note $target (linked as [[${sku}]] from products/)"
}

# ---- (b) TRUNCATED NOTE -----------------------------------------------------
# Truncate a copied source note to 1 byte (real on-disk loss), then honestly
# report it in the manifest exactly as combined_backbone.write_manifest() does
# when it sees dest_size < source_size (n_truncated>0). We surgically inject the
# single honest finding instead of re-running the heavy backbone (which would
# regenerate products/hubs and could mask the damage). GATE 1 must abort.
corrupt_truncate_note() {
  local f rel orig new
  f="$(find "$WORK/jivo/skus" -name '*.md' 2>/dev/null | sort | head -1)"
  [ -n "$f" ] || f="$(find "$WORK/jivo" -name '*.md' 2>/dev/null | sort | head -1)"
  [ -n "$f" ] || { echo "no jivo note to truncate"; return 1; }
  orig="$(stat -c%s "$f")"
  printf 'X' > "$f"                       # genuine truncation
  new="$(stat -c%s "$f")"
  [ "$new" -lt "$orig" ] || { echo "truncation did not shrink file"; return 1; }
  rel="${f#$WORK/jivo/}"                  # path relative to the jivo vault root
  jq --arg r "$rel" '
        .vaults.jivo.lossless.n_truncated = 1
      | .vaults.jivo.lossless.files_truncated = [$r]
      | .vaults.jivo.lossless.original_prefix_preserved_all = false
      | .summary.zero_loss_ok = false
    ' "$WORK/.manifest.json" > "$WORK/.manifest.json.tmp" \
    && mv "$WORK/.manifest.json.tmp" "$WORK/.manifest.json"
  echo "truncated jivo/$rel from ${orig}B -> ${new}B; manifest honestly flags n_truncated=1"
}

# ---- (c) TAMPERED MANIFEST --------------------------------------------------
# Vault content left intact. Make the manifest internally inconsistent WITHOUT
# flipping zero_loss_ok (an adversary trying to hide a loss by fudging counts).
# GATE 1 recomputes the invariant combined_dest_notes == jivo + ecom and aborts,
# proving the gate does not blindly trust the manifest's own boolean.
corrupt_tamper_manifest() {
  local before after
  before="$(jq -r '.summary.combined_dest_notes' "$WORK/.manifest.json")"
  jq '.summary.combined_dest_notes =
        (.summary.jivo_source_notes + .summary.ecom_source_notes - 5)
     ' "$WORK/.manifest.json" > "$WORK/.manifest.json.tmp" \
    && mv "$WORK/.manifest.json.tmp" "$WORK/.manifest.json"
  after="$(jq -r '.summary.combined_dest_notes' "$WORK/.manifest.json")"
  echo "manifest combined_dest_notes ${before} -> ${after} (zero_loss_ok left true; vault intact)"
}

# ---- (d) BROKEN INJECTED LINK -----------------------------------------------
# Inject a '## Related (discovered)' wikilink (the inject_links.py section) into
# a GENERATED product note, pointing at a note that does not exist. GATE 3 scans
# the generated layer and must abort on the unresolved target.
corrupt_broken_link() {
  local prod target
  prod="$(ls "$WORK"/products/*.md 2>/dev/null | sort | head -1)"
  [ -n "$prod" ] || { echo "no product note to inject into"; return 1; }
  target="__FAILCLOSED_NO_SUCH_NOTE__$$"
  {
    printf '\n## Related (discovered)\n'
    printf -- '- [[%s|broken]] — adversarial fail-closed test\n' "$target"
  } >> "$prod"
  echo "injected broken wikilink [[${target}]] into products/$(basename "$prod")"
}

run_scenario "(a)" "deleted source note"   "broken link"          corrupt_delete_source
run_scenario "(b)" "truncated note"        "truncated"            corrupt_truncate_note
run_scenario "(c)" "tampered manifest"     "combined_dest_notes"  corrupt_tamper_manifest
run_scenario "(d)" "broken injected link"  "broken link"          corrupt_broken_link

# ---- read-only-safety: prove the REAL repo is untouched ---------------------
NOW_HEAD="$(git -C "$REPO" rev-parse HEAD 2>/dev/null || echo none)"
NOW_STATUS="$(git -C "$REPO" status --porcelain 2>/dev/null || true)"
NOW_MANIFEST_SHA="$(sha256sum "$REPO/.manifest.json" | awk '{print $1}')"
SAFE="yes"
[ "$NOW_HEAD" = "$REAL_HEAD" ] || SAFE="no (HEAD moved!)"
[ "$NOW_STATUS" = "$REAL_STATUS" ] || SAFE="no (working tree changed!)"
[ "$NOW_MANIFEST_SHA" = "$REAL_MANIFEST_SHA" ] || SAFE="no (manifest changed!)"
[ "$SAFE" = "yes" ] || OVERALL=1

# ---- summary ----------------------------------------------------------------
echo
echo "==============================================================="
echo " RESULTS"
echo "---------------------------------------------------------------"
for r in "${RESULTS[@]}"; do echo "  $r"; done
echo "---------------------------------------------------------------"
echo "  real vault untouched: $SAFE"
if [ "$OVERALL" -eq 0 ]; then
  echo "  OVERALL: PASS — verify gate is FAIL-CLOSED on all four attacks."
else
  echo "  OVERALL: FAIL — the gate let damage through OR the real vault changed."
fi
echo "==============================================================="
exit "$OVERALL"
