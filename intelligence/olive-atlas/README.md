# Olive Atlas — per-pincode olive-oil availability & competitor study (2026-07-04)

JIVO olive-oil availability vs the full competitor olive universe, measured **per pincode**
across the **top 25 Indian cities (1,885 pincodes)**, one platform at a time. Same framework as
the Blinkit "Olive Ledger". Scraped 2026-07-03/04; geocode-corrected universe; every headline
independently hostile-audited (two implementations agreed to 0.0pp).

## Live reports (public)
- Zepto — Ledger: https://jivo-olive-zepto-report.vercel.app · Coverage Register (missing pincodes by name): https://jivo-zepto-coverage-register.vercel.app
- Swiggy Instamart — Ledger: https://jivo-olive-instamart-report.vercel.app · Coverage Register: https://jivo-instamart-coverage-register.vercel.app
- Flipkart Minutes — Ledger: https://jivo-olive-fkm-report.vercel.app · Coverage Register: https://jivo-fkm-coverage-register.vercel.app  *(deploying)*
- Amazon Now — collecting; report to follow.

## Headline findings (in-stock, edible olive only; resolved-this-run denominator)
| Platform | Serviceable pins | Jivo presence | Any-competitor | Whitespace (rivals sell, Jivo absent) | Top rival |
|---|---|---|---|---|---|
| **Swiggy Instamart** | 979 | **94.5%** | 96.5% | 20 pins | Borges 96% |
| **Zepto** | 719 | **76.8%** | 89.3% | 162 pins | Figaro 89% |
| **Flipkart Minutes** | 611 | **14.1%** | 100% | 525 pins | Figaro 96% |
| Amazon Now | *collecting* | — | — | — | — |

**The story:** two opposite platforms. On **Instamart** JIVO is nearly everywhere it can be sold
(94.5%, essentially tied with Borges) — a distribution win. On **Flipkart Minutes** competitors have
blanketed the olive shelf and JIVO is almost absent (14%): of 525 whitespace pincodes, **92 list JIVO
but out-of-stock (restock lead)** and **433 never carry it (get-listed lead)**. **Zepto** sits in
between — JIVO present but trailing Figaro/Tata/Borges, and weak on extra-virgin (Jivo 38% vs 86%).

## How to query this data
- Per platform, `intelligence/olive-atlas/<platform>/`:
  - `data.json` — national + per-state/city blocks: `national.{serviceable, jivo_universe_pct,
    any_competitor_pct, jivo_absent_rivals_present, by_grade}`, `brand_rank_national[]`, `states[]`.
  - `coverage.json` — `cities[]` each with `total_pins, serviceable_count, jivo_count,
    missing[{pincode,locality}], serviceable_no_jivo[{pincode,locality}]` → **exact missing pincodes by name**.
- Grades tracked: pomace, extra_light, extra_virgin, pure_classic. Rivals: Figaro, Borges, Del Monte,
  Tata Simply Better, Oleev, Bertolli, Leonardo, Disano, Colavita, Fragata, Olitalia, etc. (blends &
  non-olive excluded by taxonomy).
- Universe: top-25-city, 1,885 pincodes (9 geo-invalid excluded & disclosed). Single-probe floor.

## Source of record (on the VPS, not in this repo)
- Raw shards: `/root/olive-atlas/results/*_competitor_full25.json`
- Aggregated outputs: `/root/olive-atlas/out/<platform>/{merged,data,coverage}.json`
- Pipeline (deterministic, zero-LLM): `/root/olive-atlas/pipeline/{merge_shards,aggregate,build_coverage}.py` + `taxonomy.json`
- Site generators: `/root/olive-atlas/site/{build_ledger,build_register}.py`
