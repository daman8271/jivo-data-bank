# JIVO Data Bank

> **Private repository.** This vault contains JIVO's proprietary internal e-commerce
> data (sales, inventory, POs, targets, margins) fused with competitor price
> intelligence. It is **not for public distribution.** Do not make this repo public
> and do not export its contents outside the company.

A single Obsidian "data bank" that fuses **JIVO's internal app data** (what the
business sells, at what volume, against what target) with **competitor-price
intelligence** (what the live shelf shows on each platform) — so that **each
product is one node carrying both lenses.** Open it in Obsidian, start at
[`Home.md`](Home.md), and use the graph view to traverse the connections.

---

## 1. What this is

JIVO (edible oils) runs two completely separate data systems:

1. **The JIVO app** (`ecom.jivo.in`) — the company's internal e-com control tower:
   sell-through, primary/secondary volumes, inventory, purchase orders, monthly
   targets, margins, across a Wellness → JM Primary → Primary → Secondary value
   chain, segmented **Premium / Commodity / Other**.
2. **The ecom price scraper** — a daily crawl of competitor/live prices for each
   JIVO product, per platform, per pincode (the price the shopper actually sees).

Neither system knows about the other — they share no common SKU id. This data bank
is the **fusion layer** that joins them. Raw extraction is worthless without the
connections; the connections **are** the deliverable. Every matched product becomes
a single Markdown note that shows, side by side:

- **Identity** — JIVO SAP code(s), the ecom canonical listing(s), category, tier, pack sizes.
- **Competitor-price lens** — per platform: JIVO reference/floor price vs the latest
  live competitor price, the diff %, and the violation verdict (below / match / above).
- **JIVO lens** — 2026 sell-through (Secondary + Primary litres) for the product's tier.
- **Connections** — wikilinks back to the underlying JIVO source note(s), the ecom
  source note(s), and the category / tier / platform hubs.

### Numbers (as of this snapshot)

| Metric | Value |
|---|---|
| Fused product nodes | **153** |
| Hubs | **30** (10 platform · 3 tier · 17 category) |
| Lossless source notes carried verbatim | **36,891** (JIVO 34,750 · ecom 2,141) |
| Wikilinks across the vault | **~486,000** (485,973 measured) |
| JIVO app rows behind it | ~1.31M (lossless extract) |
| Vault size on disk | ~560 MB of notes (~630 MB incl. scratch) |
| Zero-loss proof | `zero_loss_ok: true` (see [`.manifest.json`](.manifest.json)) |
| Snapshot date | 2026-06-27 (SKU bridge + pricematch latest) |

---

## 2. How it was built

```
  JIVO app (ecom.jivo.in)                 Ecom price scraper
  ──────────────────────                  ──────────────────
  lossless extract → jivo-intel vault     daily crawl → ecom-intel vault
  (34,750 notes, ~1.31M rows)             (2,141 notes, 8 platforms)
            │                                       │
            └───────────────┬───────────────────────┘
                            ▼
                 SKU BRIDGE (the "Rosetta Stone")
        price-match sheet maps  sku → canonical_sku → platform listing
        112 core (priced) + 58 new_confirmed = 170/178 JIVO SKUs bridged
                            ▼
                 LOSSLESS MERGE  (combined_migrate.py)
        both vaults copied verbatim into one tree; sha256 byte-for-byte verified
                            ▼
              PRODUCT / HUB / TIER BACKBONE  (combined_backbone.py)
        153 fused product nodes + 30 hubs + Home.md, and a deterministic
        "## Related" wikilink layer APPENDED to every source note that
        references a known SKU / canonical / product / platform / category
                            ▼
              SEMANTIC LINK FAN-OUT  (combined_inject_links.py)
        agent-discovered cross-vault links from .links/domain-*.json injected
        as "## Related (discovered)"  →  ~486k total links
                            ▼
                 5-AGENT ADVERSARIAL REVIEW + fixes
```

**Why the bridge matters.** The app keys products by SAP code (`sku-FG0000032`); the
scraper keys them by product-name slug (`canola-oil-cold-pressed-1l`). They share no
ASIN, no SKU, nothing. The **price-match sheet** already maps
`sku → canonical_sku → platform/listing` for the master SKUs, so it is used as the
bridge. 170 of 178 JIVO SKUs are bridged; the remaining 8 are bulk pack-size gaps
(15L / 3kg / 100ml not sold online — the product itself *is* matched in its retail
sizes), plus 1 owner-confirmed call. Spelling/pack twins (e.g. `200 GM` vs `200G`,
`1L + 1L` vs `1+1L`, `CHIASEEDS` vs `CHIA SEEDS`) collapse to one node.

**Lossless by construction.** Both source vaults are copied **verbatim**; the fusion
only **appends** a `## Related` link layer to the bottom of notes. Zero data loss is
proven per-file: each source file's original bytes are an exact byte-prefix of its
copy here (`n_altered = n_truncated = 0`, nothing missing, nothing extra). The honest
signal is `original_prefix_preserved_all` in [`.manifest.json`](.manifest.json) — not
`bytes_match`, because the copies are intentionally *larger* than their sources by the
appended link layer (~1.97 MB total).

---

## 3. Structure

```
jivo-data-bank/
├── Home.md            ← START HERE (map of content: tiers, platforms, categories, all 153 products)
├── products/          ← 153 fused product nodes (one per bridged product)
├── hubs/              ← 30 hubs:
│   ├── Platform - *.md  (10: amazon, swiggy, blinkit, zepto, flipkart,
│   │                         flipkart_grocery, jiomart, bigbasket, citymall, zomato)
│   ├── Tier - *.md      (3:  Premium, Commodity, Other)
│   └── Category - *.md  (17: CANOLA, OLIVE, MUSTARD, SEEDS, DRINKS, GHEE, …)
├── jivo/              ← verbatim copy of the JIVO app vault (34,750 notes)
├── ecom/              ← verbatim copy of the ecom price-intel vault (2,141 notes)
├── .manifest.json     ← zero-loss proof (counts, bytes, sha256, prefix-preservation)
├── bin/               ← the build + verify toolchain (see RUNBOOK.md)
├── README.md          ← this file
└── RUNBOOK.md         ← how to refresh the data bank
```

`jivo/` and `ecom/` are the **source** vaults (raw, lossless). `products/`, `hubs/`,
and `Home.md` are the **generated** fusion layer — they are fully rebuilt from the
sources on every refresh, so never hand-edit them.

---

## 4. How to use it in Obsidian

1. In Obsidian: **Open folder as vault** → select this `jivo-data-bank/` folder.
2. Open **`Home.md`** — it lists every tier, platform, category hub, and all 153 products.
3. Click into any product (e.g. `CANOLA 1L`) to see its dual lens; click the hub
   links to pivot by platform / tier / category.
4. Open the **graph view** to see the ~486k connections; filter by tag
   (`type/product`, `type/hub`, `tier/PREMIUM`, `platform/amazon`, …) to explore.

The `.obsidian/` config under `ecom/` is preserved so the dataview-style plugins
work; if Obsidian prompts to trust/enable community plugins, that is expected.

---

## 5. The daily refresh model (a time machine)

The data bank is rebuilt by a **deterministic, full REPLACE**: each refresh re-copies
the current source vaults, regenerates the entire product/hub/link backbone, runs the
zero-loss + link verification gates, and — **only if every gate passes** — commits the
new state. Because each refresh is one commit, **git history is a time machine**: the
data as of any past day is exactly that day's commit. Yesterday's prices and volumes
are never overwritten in place; they live in yesterday's commit.

Accuracy is enforced **fail-closed**: if the rebuild loses a single byte, drops a note,
breaks the product/hub link backbone, or regresses the node counts, the updater
**aborts without committing** and alerts. Stale-but-correct always beats fresh-but-wrong.

What refreshes when:

- **Ecom price source** — refreshes **daily** via the existing ecom-intel scrape crons.
- **JIVO app source** — needs a **periodic owner re-auth + pull**: the app's bearer
  token lives ~24h and there is no refresh token, and **the password is never stored**
  (cardinal rule). So the JIVO lens is only as fresh as the owner's last `auth login`
  + extract. Until then, the data bank re-fuses the most recent JIVO extract on disk.
- **Semantic link fan-out** (the agent-discovered `## Related (discovered)` layer) is
  **expensive** and runs **weekly / on-demand**, not daily. The daily rebuild cheaply
  re-applies the already-cached `.links/domain-*.json`; regenerating that cache is the
  separate weekly step.

See **[RUNBOOK.md](RUNBOOK.md)** for the exact commands.

---

## 6. Honest known gaps

This is a real dataset with real limits. Read these before drawing conclusions.

- **The JIVO lens is TIER-level, not per-product.** JIVO's sell-through rows key on a
  platform `item_id` with **no canonical join** back to a product, so each product
  note shows the **2026 sell-through of its whole tier** (Premium / Commodity),
  *shared across every product in that tier* — it is **not** that single product's
  volume. The competitor-price lens, by contrast, *is* per-product. (The `Other` tier
  is not tracked in target-history at all.)

- **Competitor-price coverage is partial.** All 153 products are mapped to at least one
  platform listing, but **live dated competitor prices currently exist for 121 of 153**
  products (32 await a live match). And only **5 of the 10 platforms are currently
  priced** — amazon, flipkart, bigbasket, zepto, blinkit. The other **5 platforms are
  unscraped / contribute 0 priced products**: swiggy, flipkart_grocery, jiomart,
  citymall, zomato.

- **The top of the value chain is not in the per-product data.** The Wellness → JM
  Primary stages of the value chain are described in the app model but are **not**
  present as data here; only the **Primary → Secondary** tier sell-through (from
  target-history) feeds the JIVO lens.

- **9 JIVO SKUs are unmatched.** 8 have no ecom listing (bulk pack-size gaps: 15L / 3kg
  / 100ml) and 1 needs owner review. No product node is minted for these; they are
  surfaced honestly under "Gaps / Unmatched" in `Home.md`, not silently dropped.

- **It is a snapshot.** This build reflects the SKU bridge and price-match data **as of
  2026-06-27**. Use the daily refresh (and git history) to move through time.

---

## 7. Provenance

- **Build toolchain:** [`bin/`](bin/) — `combined_migrate.py` (lossless copy + proof),
  `combined_backbone.py` (product/hub/link backbone + manifest), `combined_inject_links.py`
  (semantic link injection), `verify_databank.py` (fail-closed gates), `daily_rebuild.sh`.
- **Source vaults:** JIVO app vault (`daman8271/jivo-intel`) and ecom price-intel vault
  (`daman8271/ecom-intel`). This data bank is a derived, fused copy of both.
- **Zero-loss proof:** [`.manifest.json`](.manifest.json).
