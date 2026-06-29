---
type: analysis-note
title: Quick-Commerce Dark-Store Intelligence (Blinkit · Zepto · Instamart)
status: snapshot
snapshot_date: 2026-06-28
tags:
  - analysis
  - intelligence/dark-stores
  - platform/blinkit
  - platform/zepto
  - platform/swiggy
---

# Quick-Commerce Dark-Store Intelligence

Up: [[Home]] · Live dashboard: **https://darkstore-dashboard.vercel.app** · Source: `intelligence/dark-stores/`

> Competitive-footprint intelligence for 12 tier-1 metros. **Two layers, kept separate:**
> (1) public per-city dark-store **counts** + who dominates, and (2) **proprietary** count of
> the dark stores that actually **carry JIVO**, from our own scraper. Snapshot: **2026-06-28**.

## 1. Public store map — dominance by city
Per-city dark-store counts from **quickcommercemap.com** (mapped from platform APIs,
reverse-geocoded; verified **2026-06-19**). National fleets: Blinkit 1,954 · Zepto 1,089 ·
Instamart 1,038. NCR = Delhi+Gurgaon+Noida+Faridabad+Ghaziabad (**includes** the Delhi row).

| City | [[Platform - blinkit\|Blinkit]] | [[Platform - zepto\|Zepto]] | [[Platform - swiggy\|Instamart]] | Dominant |
|---|--:|--:|--:|---|
| Delhi NCR | **338** | 221 | 136 | Blinkit (+117) |
| Bengaluru | **165** | 159 | 116 | Blinkit (+6) |
| Delhi | **170** | 98 | 63 | Blinkit (+72) |
| Hyderabad | 94 | **110** | 77 | Zepto (+16) |
| Chennai | 62 | **80** | 67 | Zepto (+13) |
| Mumbai | **83** | 80 | 44 | Blinkit (+3) |
| Pune | **84** | 54 | 46 | Blinkit (+30) |
| Kolkata | **58** | 34 | 29 | Blinkit (+24) |
| Ahmedabad | **44** | 20 | 17 | Blinkit (+24) |
| Jaipur | **38** | 19 | 16 | Blinkit (+19) |
| Surat | **14** | 13 | 8 | Blinkit (+1) |
| Chandigarh | **13** | 4 | 4 | Blinkit (+9) |

**Dominance:** Blinkit **10 / 12** cities · Zepto **2** (Hyderabad, Chennai) · Instamart **0**.

## 2. Dark stores carrying JIVO (PROPRIETARY)
Distinct dark stores **proven to stock JIVO**, from JIVO's own scraper
(`/opt/ecom-intel/platforms/{blinkit,zepto,swiggy-instamart}/result.json`) — counting distinct
`store_id` with ≥1 JIVO listing. A **verified floor** (467 anchor pincodes ≈ 1,196 pincodes, 19 cities).

| Platform | Stores carrying JIVO | JIVO SKUs | % of probed pincodes | Captured |
|---|--:|--:|--:|---|
| Blinkit | **152** | 9 | 37.5% | 2026-06-28 (on-VPS) |
| Zepto | **180** | 23 | 45.8% | 2026-06-28 (on-VPS) |
| Instamart | **78** | 29 | 41.6% | 2026-06-27 (off-box) |

**Per-city distinct stores carrying JIVO** (full data: `data/jivo-store-presence.json`):

| City | Blinkit | Zepto | Instamart |
|---|--:|--:|--:|
| Delhi | 42 | 31 | 12 |
| Mumbai | 17 | 16 | 13 |
| Kolkata | 27 | 20 | 5 |
| Pune | 18 | 14 | 2 |
| Chennai | 6 | 29 | 1 |
| Hyderabad | 0 ⚠ | 27 | 1 |
| Jaipur | 1 ⚠ | 8 | 10 |
| Ahmedabad | 0 ⚠ | 9 | 1 |
| Bengaluru | 5 | 5 | 1 |
| Gurgaon | 6 | 4 | 5 |
| Noida | 5 | 4 | 6 |
| Faridabad | 3 | 2 | 4 |
| Ghaziabad | 4 | 3 | 0 |
| Surat | 0 ⚠ | 1 | 2 |
| Chandigarh | 5 | 2 | 1 |

## 3. Honest limits
- **Sampled floor, not a census** — only 467 anchor pincodes probed.
- **⚠ Blinkit 0s in Hyderabad / Ahmedabad / Surat / Jaipur are scrape gaps** (175/467 anchors
  unresolved from datacenter-IP rate-limiting), not real absence — Zepto found JIVO there.
- **Instamart = off-box residential collector** (different pincode set/day); not head-to-head.
- **OOS listings still count as "carries"**; use distinct `store_id`, not pincode count.
- **Correction:** Instamart is *not* a price blind spot (29 SKUs / 78 stores via off-box) — the
  gap is it isn't fused into the [[price-match]] data bank yet.

## 4. Provenance & refresh
- Layer 1: quickcommercemap.com (public, re-maps ~monthly).
- Layer 2: JIVO scraper at `/opt/ecom-intel` (proprietary, daily).
- This note + dashboard are a **dated snapshot**; periodic auto-rebuild is the open follow-up.
- Deploy (owner, classifier blocks Claude): `vercel deploy /root/darkstore-dashboard --prod --yes --scope damans-projects-458c664b`.
