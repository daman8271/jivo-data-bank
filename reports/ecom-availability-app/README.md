# JIVO Ecom Availability App

Static web app. **Serviceability sourced from each platform's latest FULL per-pincode coverage run** (not last-ever-seen anchor data).

Source of truth:
- `/opt/ecom-intel/data/coverage/ledger.csv` — serviceability per pincode/platform
- `/opt/ecom-intel/data/<platform>/history.csv` — per-SKU rows (Blinkit/Zepto/Flipkart-Minutes)

Coverage runs used:
- Blinkit / Zepto / Flipkart-Minutes: 2026-06-29 (full 1,885-pincode probe)
- Amazon Fresh / Amazon Now: 2026-06-30 (amzcov) — serviceability + representative price + Jivo SKU count (per-SKU rows not retained by the coverage runner)

Data summary: 1,173 serving pincodes · 5 platforms · 15 states · 44 SKUs · 18,406 rows.

Backup of the prior (stale, last-seen <=28 Jun) build is in `_backup-pre-coverage-fix-20260630/`.
