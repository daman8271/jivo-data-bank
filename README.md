# JIVO Data Bank

> **🔒 Private — proprietary.** This vault fuses JIVO's internal e-commerce data (sales,
> inventory, POs, targets, margins) with competitor price intelligence. **Do not make this repo
> public** and do not export its contents outside the company.

A single Obsidian "data bank" where **each product is one node carrying three lenses**: what JIVO's
own systems know about it (volume, tier, value chain), what the live shelf charges for it on every
platform (the competitor price the shopper actually sees), **and how it moves through the factory**
(gate, QC, goods-receipt, barcode traceability, dispatch — the Jivo Mart manufacturing/supply lens).
Three systems that share no common id, joined into one connected graph. **The connections are the
deliverable — not the raw rows.**

---

## Start here — reading order for a new agent

Read these four files **in order** (~10 minutes) and you have the whole foundation: what this is,
how it's laid out, how to read it, and what it means. Then you can navigate and analyse confidently.

1. **`README.md`** ← you are here — what this is, the at-a-glance numbers, the rules.
2. **[`ARCHITECTURE.md`](ARCHITECTURE.md)** — how the data is laid out: the three source vaults, the
   generated fusion layer, the deterministic build pipeline, and the git-history time machine.
3. **[`VAULT-GUIDE.md`](VAULT-GUIDE.md)** — how to **read & navigate**: the anatomy of a fused
   product node, the hubs, traversal recipes, and the one caveat you must not miss.
4. **[`DATA-MODEL.md`](DATA-MODEL.md)** — what the data **means**: JIVO's business, the SKU bridge,
   the price-match vocabulary, and the honest coverage gaps.

**Also in this repo:** **[`RUNBOOK.md`](RUNBOOK.md)** (how to refresh it) · **[`Home.md`](Home.md)**
(the in-Obsidian map of content — open the vault and start there).

---

## What this is, in one picture

```
JIVO e-com app (ecom.jivo.in)     Ecom price scraper           Factory app (ji.jivo.in / Jivo Mart)
lossless → jivo/ (34,955)         daily crawl → ecom/ (2,878)   daily refresh → factory/ (49,462)
  │ SAP code (sku-FG0000032)        │ name-slug (canola-…-1l)     │ SAP item code (FG0000032)
  └───────────────────┬─────────────┴────────────────┬───────────┘
                      ▼                                ▼
            SKU BRIDGE (price-match sheet)     SAP-CODE BRIDGE (FG####)
       sku → canonical_sku → platform listing    factory item_code → product node
                      └────────────────┬────────────────┘
                                       ▼
                   FUSION LAYER  (generated, deterministic)
  products/ (151) + hubs/ (30) + Home.md + identity/ (JIDs)  — one node per product, THREE lenses
```

The three source vaults are copied in **verbatim** (proven byte-lossless); the fusion only **appends**
a connection layer (and the per-product **Factory lens** + stable **JID** identity layer). Everything
in `products/`, `hubs/`, `Home.md`, and `identity/` is regenerated on every refresh — **never
hand-edit it.**

---

## At a glance (current data-bank build)

| Metric | Value |
|---|---|
| Fused product nodes | **151** (111 core-priced + 40 new-confirmed; each has identity · price lens · JIVO lens · **factory lens** where bridged) |
| Hubs | **30** — 10 platform · 3 tier · 17 category |
| Lossless source notes carried verbatim | **87,295** across **3 pillars** (JIVO 34,955 · ecom 2,878 · **factory 49,462**) |
| Wikilinks across the vault | **~486,000+** |
| Rows behind it | **~1.31M** JIVO app + **~48k** factory records (gate/QC/barcode/dispatch) |
| Markdown on disk | **~1.4 GB** excluding `.git` (includes the generated `today/` snapshot); fused source trees are ~843 MB |
| Zero-loss proof | **`zero_loss_ok: true`** — see [`.manifest.json`](.manifest.json) |
| SKU bridge (ecom) | **151 product nodes** after pack/spelling twins collapse; **9** JIVO SKU gaps honestly surfaced |
| Factory bridge (SAP `FG####`) | **136** product nodes gain a Factory lens; 420 SAP items in `factory/` |

> **A snapshot, not a live mirror.** Every figure here is "as of `<the commit's date>`". The build
> is a deterministic full REPLACE committed once per refresh, so **git history is a time machine** —
> any past day's prices and volumes live in that day's commit. Date-stamp anything you report.

---

## Repo at a glance

```
jivo-data-bank/
├── README.md            ← this file
├── ARCHITECTURE.md      ← how the data is laid out + the build pipeline
├── VAULT-GUIDE.md       ← how to read & navigate the fused vault
├── DATA-MODEL.md        ← what the data means (business, bridge, price-match, gaps)
├── RUNBOOK.md           ← how to refresh the data bank (operations)
├── Home.md              ← START HERE in Obsidian (MOC: tiers · platforms · categories · 151 products)
├── products/            151 fused product nodes (one per bridged product)   [generated]
├── hubs/                30 hubs (Platform-* · Tier-* · Category-*)           [generated]
├── identity/            JID identity layer — REGISTRY.md + registry.json (stable internal IDs)  [generated]
├── jivo/                verbatim copy of the JIVO app vault (34,955 notes)   [source]
├── ecom/                verbatim copy of the ecom price-intel vault (2,878)  [source]
├── factory/             verbatim copy of the factory (Jivo Mart) vault (49,462, daily)  [source]
├── bin/                 build + verify toolchain (migrate · backbone · factory_pillar · identity · verify · rebuild)
├── .manifest.json       zero-loss proof (counts · bytes · sha256 · prefix-preservation)
└── .links/              cached agent-discovered cross-vault links (domain-*.json)
```

Full annotated map: **[`ARCHITECTURE.md`](ARCHITECTURE.md)**.

---

## The honest gaps (read before drawing conclusions)

This is a real dataset with real limits. The full discussion is in **[`DATA-MODEL.md`](DATA-MODEL.md)
§ Gaps**; the headlines:

- **The JIVO volume lens is TIER-level, not per-product.** JIVO sell-through rows key on a platform
  `item_id` with no canonical join back to a product, so each product note shows the **2026
  sell-through of its whole tier** (Premium / Commodity), *shared across every product in that
  tier* — **not** that one product's volume. The **competitor-price lens, by contrast, is
  per-product.** (The `Other` tier isn't in target-history at all.)
- **Competitor-price coverage is partial:** **120 of 151** products have live dated prices today,
  and only **5 of 10 platforms are priced** (amazon, flipkart, bigbasket, zepto, blinkit). The other
  five (swiggy, flipkart_grocery, jiomart, citymall, zomato) contribute 0 priced products so far.
- **The top of the value chain (Wellness → JM Primary) is not in the per-product data** — only the
  Primary → Secondary tier sell-through feeds the JIVO lens.
- **9 JIVO SKUs are unmatched** (8 bulk pack-size gaps, 1 owner-review) — surfaced under "Gaps" in
  `Home.md`, never silently dropped.

---

## Hard rules

- **Proprietary — never publish or export.** Private repo. Verified automation may push through
  owner-sanctioned cron (`run_daily.sh` / `push_all_repos.sh`); manual pushes still require the owner.
- **Never write secrets** (JIVO password / JWT) into any file. The app token lives ~24h and is
  re-minted from env only; the password is never stored (cardinal rule).
- **Accuracy at all costs — fail-closed.** The refresh would rather ship yesterday's correct data
  than today's wrong data; if a rebuild loses a byte, drops a note, or breaks the link backbone, it
  **aborts without committing** and alerts. See [`RUNBOOK.md`](RUNBOOK.md).
- **Never hand-edit `products/`, `hubs/`, `Home.md`, `identity/`, `jivo/`, `ecom/`, `factory/`** —
  they are regenerated every refresh. Change the builders in `bin/` and rebuild.

---

## Where this fits — the source repos

This is the **fusion** repo of the JIVO data bank programme — it joins **three source pillars**:

1. **ECOM-Intel** — the competitor-price scraper (`/opt/ecom-intel`, repo `daman8271/ecom-intel`) → `ecom/`.
2. **JIVO-Intel** — the app's internal data (`/root/jivo-intel`, repo `daman8271/jivo-intel`) → `jivo/`.
3. **JIVO-Factory** — the ji.jivo.in factory app, Jivo Mart (`/root/jivo-factory-intel`, CLI `jivo-factory-pp-cli`) → `factory/`.
4. **JIVO Data Bank** — *this* repo: the three, joined per product. **`bin/` + the price-match sheet
   (price↔volume) + the SAP item code FG#### (factory↔product) are the joins.**
