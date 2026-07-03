# JIVO Availability by Pincode — Amazon Now · Flipkart Minutes · Zepto · Swiggy Instamart (2026-07-03)

> **Question answered:** on how many pincodes is Jivo available, per platform, across the
> top-25-city universe? Latest measured status per pincode as of **2026-07-03** (IST).
> **No extrapolation** — every number below is a physically scraped check.

## Universe

- There is **no "top 25 pincodes" list** in the pipeline. The measured universe is the
  **top 25 tier-1 cities → 1,885 distinct pincodes** (India Post directory; see
  `universe25.py` in ecom-intel `tools/pincodes/`).
- Swiggy Instamart runs on its **own anchor universe** (363 representative pincodes across
  30+ cities, off-box collector) — its numbers are **not** directly comparable to the
  1,885-pin platforms.

## Headline — pincodes where Jivo is on sale

| Platform | Pins checked | **Jivo available** | Serviceable, no Jivo | Not serviceable | Data as of |
|---|--:|--:|--:|--:|---|
| Amazon Now | 1,885 | **132** | 0 | 1,753 | 2026-06-30 |
| Flipkart Minutes | 1,885 | **276** | 0 | 1,609 | 2026-07-03 |
| Zepto | 1,885 | **645** | 0 | 1,240 | 2026-07-03 |
| Swiggy Instamart | 363 (anchors) | **90** | 273 | 0 | 2026-07-03 |
| *(context)* Blinkit | 1,885 | 454 | 413 | 1,018 | 2026-07-03 |
| *(context)* Amazon Fresh | 1,885 | 881 | 92 | 912 | 2026-06-30 |

**Unions (distinct pincodes with Jivo on ≥1 platform):**
- Amazon Now + Flipkart Minutes + Zepto: **708**
- All four asked platforms (adding Swiggy Instamart's 90 pins; 43 overlap): **755**

## Per-city — Jivo-available pincodes (1,885-pin universe)

| City | Total pins | Amazon Now | Flipkart Minutes | Zepto | Blinkit | Amazon Fresh |
|---|--:|--:|--:|--:|--:|--:|
| Pune | 145 | 1 | 9 | 29 | 42 | 53 |
| Kochi | 143 | 0 | 0 | 33 | 0 | 46 |
| Thiruvananthapuram | 133 | 0 | 0 | 0 | 0 | 37 |
| Bengaluru | 117 | 84 | 9 | 78 | 82 | 91 |
| Coimbatore | 107 | 0 | 19 | 30 | 0 | 0 |
| Delhi | 97 | 4 | 47 | 63 | 75 | 91 |
| Mumbai | 89 | 10 | 17 | 81 | 79 | 85 |
| Jaipur | 84 | 0 | 20 | 20 | 0 | 20 |
| Chennai | 83 | 32 | 42 | 53 | 6 | 79 |
| Ahmedabad | 81 | 1 | 17 | 25 | 0 | 45 |
| Surat | 79 | 0 | 2 | 11 | 2 | 18 |
| Nashik | 77 | 0 | 9 | 6 | 12 | 0 |
| Kolkata | 74 | 0 | 11 | 44 | 51 | 73 |
| Bhubaneswar | 69 | 0 | 0 | 0 | 0 | 15 |
| Mysuru | 68 | 0 | 5 | 29 | 31 | 27 |
| Nagpur | 63 | 0 | 0 | 21 | 15 | 0 |
| Vadodara | 61 | 0 | 0 | 4 | 4 | 25 |
| Hyderabad | 60 | 0 | 16 | 35 | 0 | 55 |
| Vijayawada | 59 | 0 | 3 | 5 | 0 | 17 |
| Lucknow | 43 | 0 | 16 | 27 | 0 | 31 |
| Visakhapatnam | 41 | 0 | 3 | 0 | 0 | 28 |
| Indore | 30 | 0 | 0 | 12 | 10 | 15 |
| Gurugram | 29 | 0 | 13 | 18 | 21 | 18 |
| Noida | 28 | 0 | 3 | 3 | 3 | 12 |
| Chandigarh | 25 | 0 | 15 | 18 | 21 | 0 |

Machine-readable copy: [`2026-07-03-availability-by-city.csv`](2026-07-03-availability-by-city.csv).

### Swiggy Instamart per-city (its own anchor universe, pins with Jivo)

Delhi 24 · Mumbai 11 · Jaipur 10 · Pune 10 · Gurgaon 8 · Noida 5 · Mysuru 4 · Ghaziabad 4 ·
Chandigarh 2 · Surat 2 · Chennai 2 · Ludhiana, Bengaluru, Ahmedabad, Bhopal, Hyderabad,
Patna, Vadodara, Visakhapatnam 1 each. *(Includes cities outside the 25-city universe.)*

## Reads

- **Zepto is the widest quick-commerce footprint** of the asked platforms almost everywhere
  (Mumbai 81, Bengaluru 78, Delhi 63).
- **Amazon Now is a Bengaluru+Chennai story**: 116 of its 132 Jivo pins are in those two cities.
- **Flipkart Minutes is strongest in Delhi (47) and Chennai (42)**; zero presence in
  Kochi/Thiruvananthapuram/Bhubaneswar/Nagpur/Vadodara/Indore.
- **Swiggy Instamart skews North/West** (Delhi 24, Mumbai 11, Jaipur/Pune 10) and has only
  1 Jivo pin in Bengaluru — the inverse of Amazon Now.

## Method & caveats

- Source of truth: ecom-intel `data/coverage/ledger.csv` (17,570 rows), taking the **latest
  dated status per (platform, pincode)**. Daily copies of that ledger are synced into this
  folder (`coverage-ledger-YYYY-MM-DD-5platform.csv`).
- Swiggy source: `Jivo-SwiggyInstamart-Live-Report-2026-07-03.xlsx` → "Coverage & Gaps" sheet
  (363 anchor pins, 90 with Jivo, 273 serviceable-without-Jivo).
- **Supersedes the Swiggy line in** `2026-07-01-25city-coverage-summary.md` ("Swiggy Instamart
  not running") — the off-box collector has been dropping daily since 2026-07-01.
- Numbers here are slightly **lower than the 2026-07-01 census** (e.g. Zepto 645 vs 693,
  Flipkart Minutes 276 vs 340, Blinkit 454 vs 486): the census was a one-time full pass;
  since then the daily re-checks flipped some pins to not-serviceable. This note reflects
  the **freshest** per-pin status, not the census high-water mark.
- Amazon Now / Amazon Fresh were last re-checked 2026-06-30 (their daily set runs on the
  serviceable footprint; the account-global location constraint serializes them).
