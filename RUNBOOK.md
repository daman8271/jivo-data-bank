# RUNBOOK — refreshing the JIVO Data Bank

How to keep this data bank current and accurate. The golden rule: **accuracy at
all costs.** The updater is fail-closed — it would rather ship yesterday's correct
data than today's wrong data.

## TL;DR

```bash
/root/jivo-data-bank/bin/daily_rebuild.sh
```

That rebuilds the whole combined vault from the current source vaults, proves zero
data loss, verifies the product/hub/link backbone, and **commits only if every gate
passes**. It never pushes (the owner pushes — see bottom).

---

## What the updater does (and why)

`bin/daily_rebuild.sh` runs, in order:

1. **Clean mirror** — deletes the copied `jivo/` and `ecom/` subtrees so deletions
   in the source propagate (a true *replace*, not a merge).
2. **`combined_migrate.py`** — copies both source vaults in verbatim and proves the
   copy is byte-for-byte identical (sha256 per file + aggregate).
3. **`combined_inject_links.py`** — re-applies the cached semantic cross-vault links
   from `.links/domain-*.json` (cheap; skipped if the cache is absent).
4. **`combined_backbone.py`** — regenerates the 153 product nodes, 30 hubs, `Home.md`,
   the deterministic `## Related` link layer, and the zero-loss `.manifest.json`.
5. **`verify_databank.py`** (fail-closed gate) — must pass ALL of:
   - zero-loss proof (`zero_loss_ok`, no altered/truncated/missing/extra files),
   - structure (10 Platform + 3 Tier hubs, ≥1 Category hub, `Home.md` present),
   - no regression vs `bin/.baseline.json` (product / hub / source-note counts may
     grow but must not shrink),
   - link integrity (every wikilink in the generated layer resolves).
6. **rsync** the verified build into this repo (repo-only files — `bin/`, `README.md`,
   `RUNBOOK.md`, `.gitignore`, `.git/` — are protected from `--delete`).
7. **Re-verify** the synced repo and bump the baseline.
8. **Commit** only if there is a change. One run = one commit ⇒ git history is a
   time machine. **On any failure at any step it aborts WITHOUT committing and alerts.**

A run log is appended to `bin/daily_rebuild.log` (git-ignored).

---

## Data freshness — what updates when

| Source | Cadence | How |
|---|---|---|
| **Ecom price vault** (`/opt/ecom-intel/vault`) | **Daily, automatic** | existing ecom-intel scrape crons |
| **Factory vault** (`/root/jivo-factory-intel/vault`) | **Daily, automatic** | `factory_refresh.sh` @ 05:30 IST (rotating-auth → capture → render); self-sustaining auth, see `/root/jivo-factory-intel/REFRESH-RUNBOOK.md` |
| **JIVO app vault** (`/root/jivo-intel/vault`) | **Periodic, owner-driven** | needs a re-auth + re-pull (see below) |
| **Semantic link fan-out** (`.links/domain-*.json`) | **Weekly / on-demand** | expensive agent pass (see below) |

### JIVO app re-auth + pull (owner, periodic)

The JIVO app token lives ~24h, there is no refresh token, and **the password is never
stored** (cardinal rule). So the JIVO lens is only as fresh as the last extract. To
refresh it, the owner:

```bash
# refresh the ~24h bearer token (password via stdin / env, never persisted)
jivo-ecom-pp-cli auth login            # or: JIVO_ECOM_EMAIL=... JIVO_ECOM_PASSWORD=... ...
# then re-run the jivo-intel lossless extract that populates /root/jivo-intel/vault
```

Until that is done, `daily_rebuild.sh` simply re-fuses the most recent JIVO extract on
disk — correct, just not newer.

### Weekly semantic link regeneration (expensive)

The `## Related (discovered)` layer comes from `.links/domain-*.json`, produced by an
agent fan-out. **Regenerating that cache is the expensive weekly/on-demand step** — the
daily rebuild only cheaply *re-applies* whatever cache exists. Regenerate when source
content has drifted enough to warrant new semantic links, then run the daily rebuild.

---

## Scheduling (INSTALLED)

The daily pipeline is installed in crontab (IST), single-flight locked and idempotent:

```cron
# 05:30 — refresh the factory (Jivo Mart) source vault (rotating-auth → capture → render, full REPLACE)
30 5 * * *  /root/jivo-factory-intel/bin/factory_refresh.sh >> /root/jivo-factory-intel/daily.log 2>&1
# 06:00 — JIVO Data Bank: rebuild (jivo+ecom+factory) → fail-closed verify → commit → push → Telegram
0  6 * * *  /root/jivo-data-bank/bin/run_daily.sh >> /var/log/jivo-data-bank/cron.log 2>&1
```

`run_daily.sh` wraps `daily_rebuild.sh` (the fail-closed accuracy gate) + `push_both.sh` (auto-pushes
the verified commit — cron-push is owner-sanctioned) + `notify.sh` (Telegram heartbeat/alert). The
05:30 factory refresh runs **first** so the 06:00 rebuild fuses fresh factory data.

Environment overrides (all optional): `JDB_REPO`, `JDB_COMBINED`, `JDB_GEN_DIR`,
`JDB_JIVO_SRC`, `JDB_ECOM_SRC`, `JDB_FACTORY_SRC`, `JDB_SEMANTIC` (`auto`|`yes`|`no`), `JDB_PYTHON`.

> Note: `combined_migrate.py` / `combined_backbone.py` build into the hard-coded path
> `/opt/ecom-intel/combined-vault`, so `JDB_COMBINED` must match it unless those
> generators are parameterized.

---

## Manual verify (anytime)

```bash
python3 /root/jivo-data-bank/bin/verify_databank.py            # exit 0 = PASS, 1 = FAIL
```

## Pushing (owner only)

Claude is blocked from pushing the proprietary dataset (data-exfiltration classifier),
so **the owner runs the push** with `!`:

```bash
cd /root/jivo-data-bank && git push origin main
```
