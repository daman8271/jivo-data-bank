# VAULT-GUIDE — how to read & navigate the Data Bank

This is the manual for actually reading the vault to gather data and make sense of it. Read
**[`ARCHITECTURE.md`](ARCHITECTURE.md)** first for where the data comes from, and keep
**[`DATA-MODEL.md`](DATA-MODEL.md)** alongside for what the numbers mean.

---

## The design in one sentence

> **Each bridged product is one note (`products/<PRODUCT>.md`) carrying three lenses side by side —
> the per-product competitor price, the (tier-level) JIVO volume, and the factory (Jivamart
> manufacturing / supply) presence — and every related entity is a `[[wikilink]]`, so you navigate by
> following links the way you'd browse a graph.**

**Open `Home.md` first** (in Obsidian: *Open folder as vault* → this folder). It is the map of
content: every **tier**, **platform**, and **category** hub, all **153 products**, and the honest
**Gaps / Unmatched** list. From there, click into a product or pivot through a hub.

---

## Anatomy of a fused product node

Every `products/<NAME>.md` (e.g. `CANOLA 1L`) has the same four sections. Here is what each tells
you and how to read it.

**Frontmatter** — the product's attributes + tags for graph filtering:

```yaml
type: product
product: "CANOLA 1L"
sap_codes: [FG0000032]      # one or more JIVO SAP codes (pack/spelling twins collapse here)
category: "CANOLA"
tier: PREMIUM               # Premium / Commodity / Other
platforms: [amazon, flipkart, blinkit, bigbasket]
tags: [type/product, tier/PREMIUM, category/CANOLA, platform/amazon, …]
```

**`## Identity`** — the bridge made visible: the JIVO SAP code(s), the **`canonical_sku(s)`** the
price scraper uses (often several listings collapse to one product), category, tier, pack size(s),
per-unit litres, and the **bridge class** (`core (priced)` or `new_confirmed`).

**`## Competitor-price lens`** — **per-product, the precise part.** One row per platform *surface*
(a platform can expand into `amazon` / `amazon-fresh` / `amazon-now`, `flipkart` /
`flipkart-minutes`, etc.):

| Column | Meaning |
|---|---|
| **Ref/Floor ₹** | JIVO's reference / floor price for this product |
| **Live ₹** | the latest live competitor/shelf price observed by the scraper |
| **Diff %** | `(live − ref) / ref` |
| **Violation** | where live sits vs the reference — **BELOW** / **MATCH** / **ABOVE** |
| **Regime** | the price-match engine's market-regime label (`BAU` / `SVD` / `ART`) |
| **Latest** | the date of that observation (snapshot ≈ 2026-06-27) |

The full day-by-day history (160+ observations per SKU, with `live_min/live_max`, `stores_below`,
`in_stock`, and `OOS` / `NOT_LISTED` states) lives in the linked **`ecom/pricematch/pm-<NAME>.md`**
source note — follow the connection for the time series.

**`## JIVO lens`** — **TIER-level, the shared part (read the caveat below).** A per-platform table of
**2026 sell-through in litres** (Secondary and Primary) for the product's *whole tier*, from
target-history.

**`## Factory lens`** — **the Jivamart manufacturing/supply view (present on the 71 products whose SAP
`FG####` appears in factory data).** Lists where the product's SAP item code shows up in the
`ji.jivo.in` factory — the `[[oitm-FG…]]` item-master note, its `[[box-…]]` barcode cartons, sales
dispatches, etc. — and tags the product `bridge/FG####`. Follow the links into `factory/` for the raw
records. Absent on products that don't move through the Jivamart plant.

**`## Connections`** — wikilinks back to the underlying JIVO source note(s) in `jivo/`, the ecom
source note(s) in `ecom/`, the factory record(s) in `factory/`, and the category / tier / platform
hubs. This is your path from the fused summary down to the raw, lossless data.

---

## ⚠️ The one caveat you must not miss

> **The price lens is per-product; the JIVO volume lens is per-TIER.** JIVO's sell-through rows key
> on a platform `item_id` with no canonical join back to a product, so a product's "JIVO lens"
> numbers are its **entire tier's** 2026 volume, **identical for every product in that tier** — not
> that single product's sales. Never read the JIVO-lens litres as one product's volume. (The `Other`
> tier has no target-history at all.)

Concretely: every Premium product shows the same `1,682,444 L Secondary / 1,855,826 L Primary`
(2026) — that is the **Premium tier total**, not the product's.

---

## The hubs (pivots)

`hubs/` has 30 notes, each a `type: hub`, all linked from `Home.md`:

| Hub | Count | What it gives you |
|---|---|---|
| **`Tier - *`** | 3 | Premium / Commodity / Other — the tier's 2026 volume aggregate + every member product |
| **`Platform - *`** | 10 | every product present on that platform (amazon, the q-comm trio, the grocery long-tail) |
| **`Category - *`** | 17 | every product in a category (CANOLA, OLIVE, GHEE, DRINKS, SEEDS, …) |

A hub lists its **member products** (with category + pack) and, for tiers, the per-platform 2026
litres table. Use hubs to move from "one product" to "all products like it".

---

## Navigation recipes

| You want to know… | Path through the vault |
|---|---|
| One product, both lenses | `products/<NAME>` — Identity + Price lens (per-product) + JIVO lens (tier) |
| Where a product is over/under-priced vs JIVO ref | the product's **Competitor-price lens** → `Violation` column |
| The full price time-series for a product | product → Connections → `ecom/pricematch/pm-<NAME>` (the CSV history) |
| Everything in a tier / category / on a platform | the matching **hub** (`Tier - …` / `Category - …` / `Platform - …`) |
| A product's raw JIVO app data (POs, inventory, dashboards) | product → Connections → its `jivo/skus/sku-<SAP>` hub, then follow its links |
| A product's factory presence (boxes, dispatch, item master) | product → **Factory lens** → `[[oitm-FG…]]` / `[[box-…]]`, or search the tag `bridge/FG####` |
| Everything in the factory (gate, vehicles, QC, barcode, dispatch) | open `factory/_HOME.md` — the per-domain MOC hubs over all 47,549 factory notes |
| What's *not* covered | `Home.md` → **Gaps / Unmatched** (9 SKUs) + the price-coverage gaps in [DATA-MODEL](DATA-MODEL.md) |

---

## How to open & query it

- **Obsidian** — *Open folder as vault*; use the **graph view** for the ~486k connections and filter
  by tag (`type/product`, `tier/PREMIUM`, `platform/amazon`, …). If prompted to trust community
  plugins (the `ecom/.obsidian` config ships dataview-style plugins), that's expected.
- **Plain reading / grep** — it's all Markdown + CSV; `rg`/`grep` works directly, e.g.
  `rg -l "tier: PREMIUM" products/` or `rg "ABOVE" "products/CANOLA 1L.md"`.
- **Trace to source** — for the lossless underlying rows, follow a product's Connections into `jivo/`
  (app data) or `ecom/` (price history); those trees are verbatim copies of the upstream vaults.

---

## Caveats when reading

- **Date-stamp everything** — this is the 2026-06-27 snapshot; use git history to move through time.
- **Per-product vs per-tier** — see the caveat above. It's the single easiest mistake to make here.
- **Partial price coverage** — 121/153 products and only 5/10 platforms are priced; a blank price
  row means "not yet matched/scraped", not "free". Details in [DATA-MODEL](DATA-MODEL.md).
- **Don't hand-edit** `products/`, `hubs/`, `Home.md`, `identity/`, `jivo/`, `ecom/`, `factory/` —
  they're regenerated every refresh. Fix the builders in `bin/` instead.
