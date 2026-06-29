---
type: intelligence
report_kind: platform-price
platform: blinkit
as_of: 2026-06-28
generated: 2026-06-29
source: jivo-data-bank fused vault (read-only extract of generated product nodes + Blinkit hub)
tags:
  - type/intelligence
  - report/price
  - platform/blinkit
---

# Blinkit — Price Intelligence

Up: [[Home]] · Platform hub: [[Platform - blinkit]]

> **Thesis:** Blinkit is JIVO's **best-behaved priced platform** — **every one of the 9 tracked
> SKUs sits at or below the JIVO reference price (9/9 🟢 BELOW, zero over-pricing)**, priced
> tight to the floor. The over-pricing problem lives elsewhere — **BigBasket and Flipkart
> marketplace** run *above* reference on the same SKUs.

*Snapshot as of **2026-06-28** (price-match regime `SVD`). Data bank is a time machine — any
prior day lives in that day's commit. **Not hand-data: these rows come from the daily ecom-intel
scraper + price-match engine; this note only reads and synthesises them.***

---

## At a glance

| Metric | Value |
|---|---|
| SKUs priced on Blinkit | **9** |
| At/below reference (🟢) | **9 of 9** |
| Above reference (🔴) | **0** |
| Avg gap below reference | **−10.7 %** |
| Deepest discount | **MUSTARD 1L (−18.2 %)** |
| 2026 Secondary volume (tier-level) | **394,762 L** |
| 2026 Primary volume (tier-level) | **466,081 L** |

---

## The 9 Blinkit SKUs (ref/floor vs live shelf)

| SKU | Tier | Ref/Floor ₹ | Live ₹ | Diff | Status |
|---|---|---:|---:|---:|---|
| [[MUSTARD 1L]] | Commodity | 209 | 171 | −18.2 % | 🟢 BELOW |
| [[EXTRA LIGHT 1L]] | Premium | 599 | 499 | −16.7 % | 🟢 BELOW |
| [[MUSTARD 5L]] | Commodity | 999 | 868 | −13.1 % | 🟢 BELOW |
| [[JIVO POMACE 1L]] | Premium | 429 | 379 | −11.7 % | 🟢 BELOW |
| [[SUNFLOWER 1L]] | Commodity | 219 | 195 | −11.0 % | 🟢 BELOW |
| [[JIVO POMACE 5L]] | Premium | 2119 | 1917 | −9.5 % | 🟢 BELOW |
| [[CANOLA 1L]] | Premium | 259 | 239 | −7.7 % | 🟢 BELOW |
| [[CANOLA 5L]] | Premium | 1249 | 1193 | −4.5 % | 🟢 BELOW |
| [[EXTRA LIGHT 2L]] | Premium | 1189 | 1139 | −4.2 % | 🟢 BELOW |

---

## The cross-platform contrast (same SKUs, other shelves)

Across these 9 SKUs, the **over-priced (🔴 ABOVE-reference) flags** cluster on the **marketplace /
slotted** platforms, never on Blinkit:

| Platform | 🔴 ABOVE flags | Read |
|---|---:|---|
| [[Platform - blinkit\|blinkit]] | **0** | cleanest — all 9 at/under floor |
| amazon (+ fresh / now) | 0 | compliant (BELOW / MATCH) |
| [[Platform - bigbasket\|bigbasket]] | **5** | worst over-pricer |
| [[Platform - flipkart\|flipkart]] | 3 (+4 OOS) | over-priced or absent |
| [[Platform - zepto\|zepto]] | 3 | mixed |

**Worked example — [[CANOLA 1L]] (2026-06-28):** Blinkit **₹239 (−7.7 %)** vs **BigBasket ₹329
(+27 %) 🔴** vs **Flipkart ₹332 (+28 %) 🔴**. Quick-commerce (Blinkit / Amazon-now /
Flipkart-minutes) tracks the floor; the marketplace listings drift well above it.

---

## Volume lens (Blinkit, 2026 — TIER-LEVEL)

| Tier | Secondary (L) | Primary (L) |
|---|---:|---:|
| [[Tier - Premium\|Premium]] | 236,755 | 297,793 |
| [[Tier - Commodity\|Commodity]] | 158,007 | 168,288 |
| **All Blinkit** | **394,762** | **466,081** |

> ⚠️ Tier-level, shared across every product in the tier — **not** per-SKU (JIVO sell-through rows
> key on platform `item_id` with no canonical join back to a product). See [[DATA-MODEL]] § Gaps.

---

## Files in this folder

- **`JIVO-Blinkit-Price-Intelligence.xlsx`** — 4-sheet workbook (Summary · Price-Match · Blinkit vs
  All Platforms · Volume Lens).
- **`data/blinkit-price-match.json`** — the raw extract (9 Blinkit rows + 67 cross-platform rows +
  volume lens) this note and the workbook are built from.

## How this was generated

Read-only extraction over `products/*.md` (Competitor-price lens tables) and
`hubs/Platform - blinkit.md` (volume lens). No source node was edited. `intelligence/` is excluded
from the daily rebuild rsync, so this hand-authored report persists across refreshes.
