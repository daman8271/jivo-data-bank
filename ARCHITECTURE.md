# ARCHITECTURE — how the JIVO Data Bank is laid out

How the data physically flows and where everything lives. Read **[`README.md`](README.md)** first
for the mental model; read **[`VAULT-GUIDE.md`](VAULT-GUIDE.md)** next for how to read the output,
and **[`RUNBOOK.md`](RUNBOOK.md)** for the operational commands.

---

## The core idea

> **Three** independent systems describe JIVO's products but **share no common key** — the JIVO
> e-com app keys by SAP code (`sku-FG0000032`), the price scraper keys by name-slug
> (`canola-…-1l`), and the **factory app** keys by SAP item code (`FG0000032`). This repo is the
> **fusion layer** that bridges them. It does so **without touching the source data**: all three
> vaults are copied in **verbatim**, and a connection layer is **appended** on top. Nothing is
> summarised, rewritten, or dropped — so the bank is lossless by construction and every claim is
> traceable back to a source note.

---

## Three source trees + one generated fusion

| Tree | What it is | Origin | Edit? |
|---|---|---|---|
| **`jivo/`** | The JIVO app vault — 34,750 notes (~1.31M rows): SKUs, POs, dashboards, taxonomy, vendors, months | verbatim copy of `/root/jivo-intel/vault` | **never** (source) |
| **`ecom/`** | The competitor-price vault — 2,293 notes: per-SKU price-match history, platforms, daily/weekly/monthly runs | verbatim copy of `/opt/ecom-intel/vault` | **never** (source) |
| **`factory/`** | The JIVO factory (Jivamart / `JIVO_MART`) vault — 47,549 notes: gate, vehicles, drivers, QC, GRPO, barcode traceability (boxes/pallets/scans), dispatch, SAP item master — one note per record, FK-linked | verbatim copy of `/root/jivo-factory-intel/vault` (refreshed daily, see [`RUNBOOK.md`](RUNBOOK.md)) | **never** (source) |
| **`products/` · `hubs/` · `Home.md`** | The fusion layer — 151 product nodes (each with a **Factory lens**) + 30 hubs + the map of content | **generated** by `bin/combined_backbone.py` + `bin/factory_pillar.py` + `bin/combined_identity.py` | **never** (regenerated every refresh) |

`jivo/`, `ecom/`, and `factory/` are the **source of truth**; the fusion layer is a pure function of
them. The fusion is rebuildable; the sources are not — they come from upstream extracts. **The
factory pillar bridges to product nodes by SAP item code (`FG####`)** — a third lens (manufacturing /
supply) beside the competitor-price (`ecom/`) and JIVO-volume (`jivo/`) lenses.

---

## The build pipeline

Orchestrated by `bin/daily_rebuild.sh` (single-flight `flock`), a deterministic **full REPLACE**:

```
 1. CLEAN MIRROR        delete copied jivo/ + ecom/ + factory/ so upstream deletions propagate (replace, not merge)
        │
 2. combined_migrate.py copy both source vaults in VERBATIM; sha256 per-file + aggregate proof
        │                 → jivo/  ecom/   (dest bytes EXCEED source by the appended layer — by design)
        ▼
 3. combined_inject_links.py   re-apply cached semantic cross-vault links from .links/domain-*.json
        │                        → "## Related (discovered)" appended to matching source notes  (cheap)
        ▼
 4. combined_backbone.py       regenerate products/ (153) + hubs/ (30) + Home.md + the deterministic
        │                        "## Related" link layer + .manifest.json (the zero-loss proof)
        ▼
 4b.factory_pillar.py          copy factory/ verbatim (sha256 proof merged into the manifest) + append a
        │                        "## Factory lens" to every product whose FG#### SAP code appears in factory data
        ▼
 4c.combined_identity.py       mint/stamp OUR stable internal product IDs (JID) + the JID↔SAP↔canonical
        │                        crosswalk (identity/REGISTRY.md) + the duplicate-identity conflict scan
        ▼
 5. verify_databank.py  FAIL-CLOSED GATE — must pass ALL of:
        │                 · zero-loss (no altered/truncated/missing/extra files)
        │                 · structure (10 Platform + 3 Tier hubs, ≥1 Category hub, Home.md present)
        │                 · no regression vs bin/.baseline.json (counts may grow, never shrink)
        │                 · link integrity (every generated wikilink resolves)
        ▼
 6. rsync --delete      sync the verified build into this repo (repo-only files are protected — see below)
        ▼
 7. re-verify + bump bin/.baseline.json
        ▼
 8. COMMIT only if something changed.   One run = one commit ⇒ git history is a time machine.
                                        Any failure at any step → ABORT without committing + alert.
```

The semantic link fan-out (step 3's `.links/` cache) is produced by an **expensive weekly/on-demand
agent pass** (`bin/weekly_semantic.sh`); the daily rebuild only cheaply *re-applies* the cache.

---

## ⚠️ The rsync protect-list (why root docs must be registered)

Step 6 runs `rsync -a --delete` from the freshly-generated build into this repo. `--delete` removes
anything in the repo that isn't in the generated build — so **every repo-only file must be in the
`--exclude` list in `bin/daily_rebuild.sh`, or it gets deleted on the next rebuild.** The protected
set is:

```
.git/  .gitignore  README.md  RUNBOOK.md  ARCHITECTURE.md  VAULT-GUIDE.md  DATA-MODEL.md
bin/  .daily_rebuild.lock  daily_rebuild.log
```

**If you add a new top-level doc, add it to that exclude list too** — otherwise the rebuild will
silently wipe it.

---

## Lossless — proven, honestly

The copy is **larger** than the source by design (the appended `## Related` layer, ~1.97 MB total),
so a naïve `bytes_match` would *fail* even though nothing was lost. The honest proof in
[`.manifest.json`](.manifest.json) is **`original_prefix_preserved_all: true`** — each source file's
original bytes are an **exact byte-prefix** of its copy here (`n_altered = n_truncated = 0`, nothing
missing, nothing extra), verified per file via sha256. The verifier (`bin/verify_databank.py`) gates
on this every build and exits nonzero on any violation.

Current proof: JIVO 34,750 + ecom 2,293 + factory 47,549 = **84,593 dest notes** across **3 pillars**,
`zero_loss_ok: true`. (The factory copy is an EXACT byte match — no appended layer — since the
factory→product bridge lives on the generated product nodes, not the factory source notes.)

---

## Directory map (annotated)

```
jivo-data-bank/
├── README.md ARCHITECTURE.md VAULT-GUIDE.md DATA-MODEL.md RUNBOOK.md   repo-only docs (rsync-protected)
├── Home.md                  the generated MOC (entry point in Obsidian)            [generated]
│
├── products/                153 fused product nodes — Identity · Price lens · JIVO lens · Connections  [generated]
├── hubs/                    30 hubs:                                                                   [generated]
│   ├── Platform - *.md        10 (amazon, swiggy, blinkit, zepto, flipkart, flipkart_grocery,
│   │                              jiomart, bigbasket, citymall, zomato)
│   ├── Tier - *.md            3  (Premium · Commodity · Other)
│   └── Category - *.md        17 (CANOLA, OLIVE, MUSTARD, SEEDS, DRINKS, GHEE, …)
│
├── jivo/                    SOURCE — verbatim JIVO app vault (34,750 notes)        [never edit]
│   └── skus/ platforms/ taxonomy/ vendors/ pos/ locations/ months/ dashboards/ data/ + SESSION-MEMORY.md
├── ecom/                    SOURCE — verbatim ecom price vault (2,293 notes)       [never edit]
│   └── skus/ platforms/ pricematch/ locations/ daily/ weekly/ monthly/ analysis/ runs/ + VAULT-SPEC.md
├── factory/                 SOURCE — verbatim factory (Jivamart) vault (47,549 notes, refreshed daily)  [never edit]
│   └── vehicle-management__*/ gate-core__*/ barcode__*/ quality-control__*/ grpo__*/ … + _HOME.md _bridge.json
│
├── identity/                JID identity layer — REGISTRY.md + registry.json (stable internal product IDs)  [generated]
│
├── bin/                     the toolchain (build into /opt/ecom-intel/combined-vault, then rsync here)
│   ├── combined_migrate.py     lossless copy + sha256 proof
│   ├── combined_inject_links.py semantic link injection from .links/
│   ├── combined_backbone.py    products/ + hubs/ + Home.md + .manifest.json
│   ├── factory_pillar.py       copy factory/ + merge zero-loss proof + factory→product SAP lens
│   ├── combined_identity.py    mint stable internal product IDs (JID) + identity/REGISTRY.md
│   ├── verify_databank.py      fail-closed gates (zero-loss · structure · baseline · links)
│   ├── daily_rebuild.sh        the orchestrator (steps 1–8 above)
│   ├── weekly_semantic.sh      the expensive weekly link-cache regeneration
│   ├── run_daily.sh push_both.sh notify.sh install_cron.sh test_failclosed.sh
│   └── .baseline.json           last-good counts (regression guard)
│
├── .manifest.json           zero-loss proof (summary + per-vault sha256 + prefix-preservation)
├── .links/                  cached agent-discovered cross-vault links (domain-*.json)
└── .gitignore               (logs, locks, scratch are ignored)
```

> The generators in `bin/` build into the hard-coded staging path
> `/opt/ecom-intel/combined-vault`, then `daily_rebuild.sh` rsyncs the verified result into this
> repo. See [`RUNBOOK.md`](RUNBOOK.md) for env overrides and the suggested (not-installed) cron.
