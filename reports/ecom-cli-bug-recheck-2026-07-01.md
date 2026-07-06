# Ecom CLI/API Bug Recheck

Date: 2026-07-01
CLI: `jivo-ecom-pp-cli 1.0.0`
API health: reachable, auth valid

## Result

None of the previously confirmed bugs appear resolved in the currently installed/live CLI/API.

## Current checks

1. `subCategory` still silently behaves differently from `sub_category`
   - `sub_category=JIVO POMACE`: `total_units=32567.0`
   - `subCategory=JIVO POMACE`: `total_units=54419.3`
   - Status: OPEN

2. `dashboard state-sales` still lacks category/sub-category/brand CLI flags
   - Command with `--category` exits with `unknown flag: --category`
   - Status: OPEN

3. Invalid metric still silently defaults
   - `--metric banana` exits `0` and returns `metric=units`
   - Status: OPEN

4. Invalid mode still silently defaults
   - `--mode unknown` exits `0` and returns `mode=single`
   - Status: OPEN

5. Platform case handling still inconsistent
   - `top-skus --platform amazon` works
   - `top-skus --platform AMAZON` fails validation
   - Status: OPEN

6. `category-platform-breakdown` still returns empty/Uncategorized
   - `total_ltrs=0`, `platforms_len=0`, `name=Uncategorized`
   - Status: OPEN

7. `category-sku-breakdown --platform amazon` still returns empty/Uncategorized
   - `total_ltrs=0`, `skus_len=0`, `name=Uncategorized`
   - Status: OPEN

8. `state-sales-detail` still does not reconcile with summary
   - Detail returns `total_units=0`, `rows=0`
   - Status: OPEN

9. City aliases still split
   - City sample includes both `Bangalore` and `Bengaluru`
   - Status: OPEN

10. Unsupported platform commands are still exposed and fail at API layer
   - `platform ads blinkit` still calls backend and gets: `Amazon Ads Dashboard is available only for Amazon.`
   - Status: OPEN

11. Metric/source semantics still confusing
   - `state-sales --metric litres` still returns field `total_units` while `metric=litres`
   - Status: OPEN

## Files

Raw TSV recheck saved at:
`/root/pa-clients/jivo-data-bank/reports/ecom-cli-bug-recheck-2026-07-01.tsv`
