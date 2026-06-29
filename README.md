# JIVO Data Bank

> **🔒 Private — proprietary.** This vault fuses JIVO's internal e-commerce data (sales,
> inventory, POs, targets, margins) with competitor price intelligence. **Do not make this repo
> public** and do not export its contents outside the company.

A single Obsidian "data bank" where **each product is one node carrying two lenses**: what JIVO's
own systems know about it (volume, tier, value chain) **and** what the live shelf charges for it on
every platform (the competitor price the shopper actually sees). Two systems that share no common
SKU id, joined into one connected graph. **The connections are the deliverable — not the raw rows.**

---

## Start here — reading order for a new agent

Read these four files **in order** (~10 minutes) and you have the whole foundation: what this is,
how it's laid out, how to read it, and what it means. Then you can navigate and analyse confidently.

1. **`README.md`** ← you are here — what this is, the at-a-glance numbers, the rules.
2. **[`ARCHITECTURE.md`](ARCHITECTURE.md)** — how the data is laid out: the two source vaults, the
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
JIVO app (ecom.jivo.in)                         Ecom price scraper
lossless extract → jivo/  (34,750 notes)        daily crawl → ecom/  (2,141 notes)
        │  keyed by SAP code (sku-FG0000032)             │  keyed by name-slug (canola-…-1l)
        └───────────────────────┬─────────────────────────┘
                                 ▼
                     SKU BRIDGE  (the "Rosetta Stone")
              price-match sheet maps  sku → canonical_sku → platform listing
                                 ▼
                  FUSION LAYER  (generated, deterministic)
        products/ (153 nodes) + hubs/ (30) + Home.md   — one node per product, both lenses
```

The two source vaults are copied in **verbatim** (proven byte-lossless); the fusion only **appends**
a connection layer. Everything in `products/`, `hubs/`, and `Home.md` is regenerated on every
refresh — **never hand-edit it.**

---

## At a glance (as of the 2026-06-27 snapshot)

| Metric | Value |
|---|---|
| Fused product nodes | **153** |
| Hubs | **30** — 10 platform · 3 tier · 17 category |
| Lossless source notes carried verbatim | **36,891** (JIVO 34,750 · ecom 2,141) |
| Wikilinks across the vault | **~486,000** (485,973 measured) |
| JIVO app rows behind it | **~1.31M** (lossless extract) |
| Notes on disk | **~560 MB** (+~2 MB appended link layer) |
| Zero-loss proof | **`zero_loss_ok: true`** — see [`.manifest.json`](.manifest.json) |
| SKU bridge | **170 / 178** JIVO SKUs matched (9 honestly surfaced as gaps) |

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
├── Home.md              ← START HERE in Obsidian (MOC: tiers · platforms · categories · 153 products)
├── products/            153 fused product nodes (one per bridged product)   [generated]
├── hubs/                30 hubs (Platform-* · Tier-* · Category-*)           [generated]
├── jivo/                verbatim copy of the JIVO app vault (34,750 notes)   [source]
├── ecom/                verbatim copy of the ecom price-intel vault (2,141)  [source]
├── bin/                 build + verify toolchain (migrate · backbone · inject-links · verify · rebuild)
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
- **Competitor-price coverage is partial:** **121 of 153** products have live dated prices today,
  and only **5 of 10 platforms are priced** (amazon, flipkart, bigbasket, zepto, blinkit). The other
  five (swiggy, flipkart_grocery, jiomart, citymall, zomato) contribute 0 priced products so far.
- **The top of the value chain (Wellness → JM Primary) is not in the per-product data** — only the
  Primary → Secondary tier sell-through feeds the JIVO lens.
- **9 JIVO SKUs are unmatched** (8 bulk pack-size gaps, 1 owner-review) — surfaced under "Gaps" in
  `Home.md`, never silently dropped.

---

## Hard rules

- **Proprietary — never publish or export.** Private repo; Claude is blocked from pushing it
  (data-exfiltration classifier) — **the owner pushes** with `! cd /root/jivo-data-bank && git push origin main`.
- **Never write secrets** (JIVO password / JWT) into any file. The app token lives ~24h and is
  re-minted from env only; the password is never stored (cardinal rule).
- **Accuracy at all costs — fail-closed.** The refresh would rather ship yesterday's correct data
  than today's wrong data; if a rebuild loses a byte, drops a note, or breaks the link backbone, it
  **aborts without committing** and alerts. See [`RUNBOOK.md`](RUNBOOK.md).
- **Never hand-edit `products/`, `hubs/`, `Home.md`, `jivo/`, `ecom/`** — they are regenerated.
  Change the builders in `bin/` and rebuild.

---

## Where this fits — the three vaults

This is **vault #3 of 3** in the JIVO data bank programme — the **fusion** of the other two:

1. **ECOM-Intel** — the competitor-price scraper (`/opt/ecom-intel`, repo `daman8271/ecom-intel`) → `ecom/`.
2. **JIVO-Intel** — the app's internal data (`/root/jivo-intel`, repo `daman8271/jivo-intel`) → `jivo/`.
3. **JIVO-Factory** — the ji.jivo.in factory app, Jivamart (`/root/jivo-factory-intel`, CLI `jivo-factory-pp-cli`) → `factory/`.
4. **JIVO Data Bank** — *this* repo: the three, joined per product. **`bin/` + the price-match sheet
   (price↔volume) + the SAP item code FG#### (factory↔product) are the joins.**
