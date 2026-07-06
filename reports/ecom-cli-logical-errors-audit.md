# Jivo Ecom App / CLI Logical Errors Audit

Date: 2026-07-01
CLI: `jivo-ecom-pp-cli 1.0.0`
Base URL: `https://ecom.jivo.in`

## Confirmed issues

### 1. `subCategory` silently ignored on state-sales API
- Correct params: `category=OLIVE&sub_category=JIVO POMACE&brand=JIVO`
  - Result: `total_units = 190,177 L`
- Incorrect camelCase param: `category=OLIVE&subCategory=JIVO POMACE&brand=JIVO`
  - Result: `total_units = 347,554.8 L`
- Problem: API does not reject unknown filter param and returns broader OLIVE data, causing inflated Pomace numbers.
- Fix: validate query params and reject unknown keys; support aliases intentionally or document one canonical key.

### 2. CLI has no category/sub-category/brand flags for `dashboard state-sales`
- `jivo-ecom-pp-cli dashboard state-sales --help` exposes only `--metric`, `--mode`, `--month`, `--platform`, `--year`.
- But raw API supports at least `category`, `sub_category`, and `brand`.
- Problem: users cannot safely reproduce filtered rankings through the CLI wrapper; they must call raw API.
- Fix: add `--category`, `--sub-category`, `--brand` flags and map to API keys `category`, `sub_category`, `brand`.

### 3. Invalid `metric` and `mode` are silently ignored/defaulted
- Command: `dashboard state-sales --year 2026 --month 6 --metric banana --agent`
  - Exit: `0`
  - Returned `metric: units`, not an error.
- Command: `dashboard state-sales --year 2026 --month 6 --mode unknown --agent`
  - Exit: `0`
  - Returned `mode: single`, not an error.
- Problem: typoed metric/mode produces plausible but wrong output.
- Fix: validate enum values before request. For metric, allow only known values like `units`, `value`, `litres`/`ltr`. For mode, allow only real modes.

### 4. Platform case handling is inconsistent across commands
- Raw API normalizes `platform=amazon` and `platform=AMAZON` for state-sales.
- CLI `dashboard category-litres --platform AMAZON` also works.
- CLI `dashboard top-skus --platform AMAZON` fails validation: `must be one of [amazon ...]`.
- Problem: same conceptual filter behaves differently by command.
- Fix: normalize platform input lower-case before CLI validation everywhere, or reject uppercase everywhere with the same message.

### 5. `dashboard category-platform-breakdown` returns 0/Uncategorized despite category data existing
- Command/API: `dashboard category-platform-breakdown --year 2026 --month 6`
  - Returned `total_ltrs: 0`, `name: Uncategorized`, `platforms: []`.
- Same month has category data:
  - `dashboard category-litres --year 2026 --month 6` returned `total_ltrs: 314,797.2` for premium categories.
  - `dashboard category-breakdown --year 2026 --month 6` returned premium + commodity category totals.
- Problem: endpoint appears wired to empty/default filters or wrong source.
- Fix: verify backend query source/default `head/category/sub_category` logic for category-platform-breakdown.

### 6. `dashboard category-sku-breakdown` returns empty/Uncategorized even for valid platform/month
- Command/API: `dashboard category-sku-breakdown --platform amazon --year 2026 --month 6`
  - Returned `total_ltrs: 0`, `skus: []`, `name: Uncategorized`.
- But `dashboard top-skus --platform amazon --year 2026 --month 6` returns SKU sales for Amazon.
- Problem: SKU breakdown endpoint is probably using the wrong default category/head/source or requires hidden params not exposed by CLI.
- Fix: align category-sku-breakdown defaults with top-skus/category-breakdown or require explicit category and validate.

### 7. `dashboard state-sales-detail` returns empty even when summary has data
- Command: `dashboard state-sales --year 2026 --month 6 --metric litres --platform amazon`
  - Raw API summary: `total_units = 1,997,882`, `states_len = 35`.
- Command: `dashboard state-sales-detail --year 2026 --month 6 --platform amazon`
  - Returned `total_units = 0`, `rows = []`, `cities = []`.
- Problem: detail endpoint cannot drill into summary result.
- Fix: share the same platform/month/year filtering logic between summary and detail endpoints.

### 8. State-sales city list contains duplicate normalized city names
- Example in June state-sales: both `Bangalore` and `Bengaluru` appear as separate cities.
- Problem: city rollups can split demand and rank city incorrectly.
- Fix: canonicalize city aliases before city aggregation (`Bangalore -> Bengaluru`, `Gurgaon -> Gurugram`, etc.).

### 9. Platform command surface exposes unsupported endpoints for many platforms
- Recon manifest `/root/pa-clients/jivo-intel/recon/2026-06-26/MANIFEST.tsv` has 86 non-zero command results.
- Common patterns:
  - 59 cases: Amazon-only endpoints exposed for non-Amazon platforms.
  - 8 cases: `region-doh` endpoint returns 404 but CLI exposes it.
  - 3 cases: not-enabled endpoints exposed.
- Problem: CLI advertises endpoints that backend immediately rejects, creating noisy UX and agent confusion.
- Fix: hide/disable platform commands by platform capability matrix, or show clear capability metadata in `agent-context`.

### 10. Source/metric semantics are confusing across dashboards
- `state-sales --metric litres` for Jun 2026 returns `total_units = 2,366,331.3` and `metric = litres`.
- `category-breakdown` for same month returns `source: primary`, premium total `314,797.2`, commodity total `319,316`.
- `category-litres` returns premium only (`total_ltrs = 314,797.2`).
- Problem: endpoints mix `units`, `litres`, `value`, and `source` in ways that can be mistaken as comparable totals.
- Fix: every dashboard response should include explicit `source`, `metric`, `unit`, and scope (`premium_only`, `all_heads`, `secondary`, etc.).

## Priority fixes
1. Reject unknown API params and invalid enum values.
2. Add missing `state-sales` filters: category, sub-category, brand.
3. Fix category-platform-breakdown/category-sku-breakdown empty defaults.
4. Fix state-sales-detail to reconcile with state-sales summary.
5. Add a platform capability matrix so unsupported CLI commands do not appear as valid.
6. Canonicalize city names before aggregation.
