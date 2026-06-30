# DATA-MODEL — what the data means

The semantic foundation: JIVO's business, the bridge that joins the two systems, the price-match
vocabulary, and the honest gaps. Read **[`VAULT-GUIDE.md`](VAULT-GUIDE.md)** for how to find these
things in the vault.

> Figures are **as of the 2026-06-27 snapshot**. Use git history to move through time, and
> date-stamp anything you report.

---

## 1. The business in a nutshell

JIVO sells **edible oils** (heritage **OLIVE** — extra-light / pomace / extra-virgin — plus canola,
sunflower, mustard, groundnut, rice-bran, sesame, soyabean, blended), **A2 desi ghee** (premium),
and a **beverages** line (energy drinks, tonic/soda/mojito, many sugar-free "SF" variants). Two
house brands: **JIVO** (flagship) and **SANO** (value, esp. sunflower).

- **The house unit is LITRES** (`per_unit_value` = litres per unit); leadership reasons in litres.
- **Three product tiers** drive every rollup — **PREMIUM** (olive + A2 ghee), **COMMODITY**
  (canola/sunflower/mustard…), **OTHER** (beverages/misc). In this vault: 64 Premium · 29 Commodity ·
  60 Other product nodes.
- **The North-Star is premium-mix (~52 % by litres)** — keeping the premium line pacing is "the one
  number".
- **JIVO sells through distributors, not direct;** the app tracks a **Wellness → JM Primary →
  Primary → Secondary** value chain. **Only the Primary → Secondary tier sell-through feeds this
  vault's JIVO lens** (the upstream Wellness/JM-Primary stages are described in the app model but are
  not present as per-product data here).

The deep, adversarially-verified business + data model lives in the **jivo-intel source repo**
(`daman8271/jivo-intel` → `datamap/00-MASTER-data-model.md`), not in this tree.

---

## 2. Why a bridge is needed (the three systems)

| | JIVO e-com app (`jivo/`) | Ecom price scraper (`ecom/`) | Factory app (`factory/`) |
|---|---|---|---|
| **Knows** | volume, inventory, POs, targets, margins | the live shelf price per platform/pincode | physical movement: gate, QC, goods-receipt, barcode traceability, dispatch, on-hand stock |
| **Keys products by** | SAP code — `sku-FG0000032` | name-slug — `canola-…-1l` (`canonical_sku`) | SAP item code — `FG0000032` (`item_code`) |
| **Grain** | tier × platform × month | product × platform × day | per physical record (box, dispatch, inspection, gate entry) |

They share **no ASIN, no common SKU id** at the surface — but the JIVO app and the factory app both
key on the **SAP code (`FG####`)**, so that is the natural join between them (the ecom scraper joins
via the price-match sheet, §3). Neither system alone can answer "is my best-selling, competitively-
priced product actually flowing through the plant?" This vault joins all three.

---

## 3. The SKU bridge (the "Rosetta Stone")

The **price-match sheet** already maps `sku → canonical_sku → platform/listing` for the master SKUs,
so it is reused as the bridge:

```
JIVO SAP code            canonical_sku (scraper)              one fused product node
sku-FG0000032     ──►    jivo-…-canola-…-1l, canola-oil-…-1l  ──►   products/CANOLA 1L.md
(pack/spelling twins — 200 GM vs 200G, 1+1L vs 1L+1L, CHIASEEDS vs CHIA SEEDS — collapse to ONE node)
```

- **170 of 178** JIVO SKUs are bridged: **112 core (priced)** + **58 new_confirmed**.
- A product node's `## Identity` shows its SAP code(s) and every `canonical_sku` that folded into it,
  plus its **bridge class** (`core (priced)` vs `new_confirmed`).
- **9 SKUs are unmatched** (surfaced in `Home.md` → Gaps, never dropped): **8** have no ecom listing
  (bulk pack-size gaps — 15L / 3kg / 100ml not sold online; the product *is* matched in its retail
  sizes), and **1** (cola juice) needs owner review.

---

## 4. The price-match vocabulary (the per-product lens)

Each product's **Competitor-price lens** summarises that product's price-match history (the full
per-day series is in `ecom/pricematch/pm-<NAME>.md`, columns:
`date, platform, status, regime, ref, live, live_min, live_max, diff, diff_pct, stores_below, in_stock`).

| Term | Meaning |
|---|---|
| **ref** (Ref/Floor) | JIVO's reference / floor price for the product on that platform |
| **live** | the latest live competitor/shelf price the scraper saw (`live_min`/`live_max` across stores) |
| **diff / diff %** | `live − ref` and `(live − ref) / ref` |
| **status / Violation** | **BELOW** / **MATCH** / **ABOVE** the reference; plus **OOS** (out of stock) and **NOT_LISTED** in the raw history |
| **regime** | the price-match engine's market-regime label: **`BAU`** / **`SVD`** / **`ART`** (defined in the ecom price-match engine; see `ecom/VAULT-SPEC.md`) |
| **stores_below / below_days** | how many stores are under ref, and the run-length of BELOW days |

A platform can expand into multiple **surfaces** — `amazon` / `amazon-fresh` / `amazon-now`,
`flipkart` / `flipkart-minutes` — each priced separately, because the q-commerce and marketplace
shelves of the same retailer charge differently.

---

## 5. The JIVO lens — and its hard limit

The **JIVO lens** on each product is its **whole tier's** 2026 sell-through in litres (Secondary +
Primary), per platform, from target-history.

> **It is TIER-level, not per-product.** JIVO's sell-through rows key on a platform `item_id` with no
> canonical join back to a product, so the litres shown are shared identically across every product
> in the tier — **not** that one product's volume. The price lens (§4) *is* per-product; the volume
> lens is not. The `Other` tier isn't in target-history at all.

The platform archetypes that shape these numbers (from the app model): **A — Amazon** (deepest
integration, the only one with true margins/ads), **B — quick-commerce `zbs`** (Blinkit/Swiggy/Zepto,
the availability battleground), **C — marketplace/grocery long-tail** (BigBasket, Flipkart-Grocery,
JioMart, …, several empty or stale).

---

## 5b. The factory lens (manufacturing / supply)

The third lens, from the **ji.jivo.in factory app** for **Jivo Mart (`JIVO_MART`)** — captured **daily**
and copied verbatim into `factory/` (47,549 notes, one per physical record). Jivo Mart is JIVO's
**retail / dispatch arm**: it does **not** manufacture — it receives finished, barcoded cartons from
Jivo Oil via an intercompany transfer rail, holds them across ~31 warehouses, and runs scan-to-ship
dispatch. So the factory data is **rich** in fleet, gate, barcode traceability, dispatch, and on-hand
inventory, and **largely empty** in production/maintenance (those modules are built but unused on the
retail arm — they live on Jivo Oil).

**The bridge:** the factory keys every item on the **SAP item code (`FG####`)** — the *same* code space
as the product nodes' `sap_codes`. `factory_pillar.py` appends a **`## Factory lens`** to each product
whose `FG####` appears in factory data (**71 products** today), linking to the factory records
(`[[oitm-FG…]]`, `[[box-…]]`, dispatches, …) and tagging the product `bridge/FG####`. The factory
entity domains (each a folder of FK-linked notes):

| Domain | What | scale |
|---|---|---|
| Barcode / traceability | boxes, pallets, scan history, dispatch sessions, intercompany transfers | ~43k records |
| Vehicle / driver | vehicles, transporters, drivers (masters) | ~700 |
| Gate | sales-dispatch gate-out, visitor/person entries, raw-material gate-in | ~600 |
| Dispatch | dispatch plans, docking, bilty / transporter invoices | ~700 |
| QC / GRPO | arrival-slip inspections, material & service goods-receipts | ~30 |
| WMS / warehouse | on-hand stock, sales-order backlog, transfers, batch expiry | dashboards |
| SAP item master (`oitm`) | the `FG####` item dictionary — the bridge keys | 200 |

The full per-page app model (what every page does + the data behind it) lives in
`/root/jivo-factory-intel/app-model/` (13 sections, 174 pages). The CLI that captures it is
`jivo-factory-pp-cli` (`/root/printing-press/library/jivo-factory`).

---

## 6. Gaps & caveats (read before drawing conclusions)

- **JIVO volume is tier-level, not per-product** (§5) — the single most important caveat.
- **Partial price coverage:** live dated competitor prices exist for **121 of 153** products (32
  await a live match), and only **5 of 10 platforms are priced** — **amazon, flipkart, bigbasket,
  zepto, blinkit**. The other five — **swiggy, flipkart_grocery, jiomart, citymall, zomato** —
  contribute **0** priced products so far.
- **Top of the value chain absent:** only Primary → Secondary tier sell-through feeds the JIVO lens;
  Wellness → JM Primary is described in the app model but not present as data here.
- **9 unmatched SKUs** (§3) — surfaced, not dropped.
- **Factory = Jivo Mart only, and only the retail arm.** The `factory/` pillar is `JIVO_MART`-scoped
  (Jivo Oil & Beverages are out of scope). Production / maintenance / WMS-execution are empty for
  Jivo Mart **by design** — it's the dispatch arm, not a manufacturer. A few SAP-report endpoints hard-
  cap (e.g. `dispatch/reports/boxes` at 1000) but their underlying data is captured in full elsewhere.
- **Factory bridge depth:** only **71 of 151** products carry a Factory lens (those whose `FG####`
  shows up in Jivo Mart's box/dispatch data); the rest don't move through the Jivo Mart plant.
- **Join landmines** (carried from the source data model): never join on EAN (sci-notation text);
  `amazon_inventory.brand` is dirty (derive brand from the master); `fc_code` ≠ inventory `location`;
  raw PO `status` is dirty — use normalised statuses. Full list in the jivo-intel `datamap`.
- **It is a snapshot.** This build reflects the SKU bridge + price-match data **as of 2026-06-27**;
  `zero_loss_ok: true` in [`.manifest.json`](.manifest.json) proves the *capture* is lossless, not
  that the live world has stood still.

---

## 7. Provenance & deeper reading

- **In this repo:** `ecom/VAULT-SPEC.md` (price-vault structure + price-match definitions),
  `ecom/pricematch/` (per-SKU history), `jivo/` (the app vault, verbatim), [`.manifest.json`](.manifest.json)
  (zero-loss proof), [`ARCHITECTURE.md`](ARCHITECTURE.md) (how it's built).
- **In the source repos:** `daman8271/jivo-intel` → `datamap/00-MASTER-data-model.md` (the full
  business + data model, value chain, metric dictionary) and `docs/sku-bridge/` (the bridge
  artifacts); `daman8271/ecom-intel` (the price scraper that produces `ecom/`).
