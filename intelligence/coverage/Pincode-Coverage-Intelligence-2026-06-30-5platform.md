# Pincode Coverage Intelligence — ALL 5 PLATFORMS (current)

> **Latest full census — 2026-06-30.** Supersedes the 3-platform 2026-06-29 snapshot.
> Physically scraped per-pincode coverage across all **1,885 pincodes** of the 25 priority
> cities, on all **5 pincode-wise platforms** (Amazon Fresh + Now on separate accounts,
> never merged). Source: ecom-intel `data/coverage/ledger.csv`. Analysed by a 5-agent fleet.

## Headline
- **1,173 / 1,885 pincodes (62%)** reachable by ≥1 platform — up from **234 (12%)** on the old anchor model.
- **1,071 / 1,885 (57%)** have Jivo on sale.
- **Blinkit's 416-pincode delivers-but-no-Jivo gap** is the #1 distribution opportunity; Amazon Fresh has a smaller 92-pincode version.

## Per platform (each a distinct surface — never summed)
| Platform | Serviceable | Jivo on sale | Deliver-no-Jivo gap | SKUs | Price range |
|---|--:|--:|--:|--:|---|
| **Amazon Fresh** | 973 | 881 | 92 | 39 | ₹159–2957 |
| **Blinkit** | 902 | 486 | 416 | 9 | ₹154–2308 |
| **Zepto** | 693 | 693 | 0 | 23 | ₹49–7920 |
| **Flipkart Minutes** | 340 | 340 | 0 | 16 | ₹22–2271 |
| **Amazon Now** | 132 | 132 | 0 | 25 | ₹159–2957 |
| **Combined (any)** | **1,173** | **1,071** | — | — | — |

## Per-platform deep-dive (5-agent fleet)
**Amazon Fresh**
- **Widest reach of any platform we track:** 973 serviceable pincodes across the 25-city universe, with Jivo already priced in **881** of them (91% of where Fresh delivers).
- **The opportunity gap is small but real — 92 pincodes deliver Fresh but carry no Jivo.** Biggest pockets to close: **Nagpur (27), Thiruvananthapuram (19), Chandigarh (12), Kochi (12), Bhubaneswar (9)** — a targeted listing push here converts existing delivery reach into shelf presence.
- **Metro strongholds:** Bengaluru (95), Delhi (91), Mumbai (85), Chennai (80) and Kolkata (73) anchor coverage — the big-city demand centres are fully lit up.

**Blinkit**
- **Widest quick-commerce footprint we track:** 902 of 1,885 pincodes are serviceable (~48% of the 25-city universe), and Blinkit reaches **all 25 cities** — there is no city where it doesn't operate.
- **The real gap is conversion, not reach:** Blinkit *delivers* in 902 pincodes but Jivo is on sale in only **486** of them. That's a **416-pincode "delivers-but-no-Jivo" gap** — listings/availability work, not network expansion, is the lever.
- **Gap concentrates in the South & West:** the biggest deliver-but-no-Jivo gaps are **Chennai (49), Kochi (46), Ahmedabad (41), Coimbatore (39), Hyderabad (36)** — priority cities for a distribution/listing push.

**Zepto**
- **Reach: 693 of 1,885 pincodes serviceable (≈37% of the 25-city universe), all carrying Jivo.** This run is the daily Jivo-priced subset, so serviceable and Jivo-priced coincide — gap = 0 by construction; "delivers-but-no-Jivo" is invisible here and needs a full census to surface.
- **Demand concentrates in the metros:** Mumbai (82), Bengaluru (79) and Delhi (70) alone account for ~34% of all Jivo-priced pincodes, with Chennai (61), Kolkata (48) and Hyderabad (40) rounding out the top six.
- **Three cities are dark — Visakhapatnam, Bhubaneswar and Thiruvananthapuram have zero serviceable pincodes**, signalling Zepto either doesn't operate there or carries no Jivo; a whitespace for distribution.

**Flipkart Minutes**
- **Reach: 340 of 1,885 pincodes serviceable (~18%)** across the 25-city universe — a focused, metro-led footprint rather than national.
- **Zero coverage gap: all 340 serviceable pincodes carry Jivo on sale.** Wherever Flipkart Minutes delivers, Jivo is listed and priced — no "delivers-but-no-Jivo" leakage to recover (gap = 0).
- **Strongest in Chennai (49) and Delhi (47)**, then Ahmedabad (27), Jaipur (24), Mumbai (23), Lucknow (22) — a broad metro spread, not just the usual two.

**Amazon Now**
- **Narrowest footprint of any platform: 132 serviceable pincodes across just 6 of 25 cities.** 1,753 of 1,885 pincodes (93%) return "not serviceable" — Amazon Now is a metro-only express lane, not a national network.
- **Bengaluru + Chennai are the whole story: 116 of 132 serviceable pincodes (88%).** Bengaluru alone carries 84. Mumbai (10) and Delhi (4) are thin; Pune and Ahmedabad are single-pincode toeholds.
- **Zero presence in 19 cities** — including Hyderabad, Kolkata, Jaipur, Surat, Kochi and all of Tier-2 (Coimbatore, Indore, Nagpur, Nashik, Vijayawada, Visakhapatnam…). Amazon Now simply does not operate there yet.

## Method
JIVO's own scraper set each of the 1,885 pincodes' location, resolved each platform's store, and
logged `price_captured / serviceable_no_jivo / not_serviceable` — 0 blocked. QC platforms 29 Jun,
Amazon (Fresh acct 259 + Now acct 520, strictly separate) 30 Jun. Live dashboard:
`darkstore-dashboard.vercel.app`. Raw: `coverage-ledger-2026-06-30-5platform.csv` (9,425 rows).
