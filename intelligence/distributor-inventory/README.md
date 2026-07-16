# JIVO distributor inventory intelligence

This protected Data Bank domain stores the evidence and rules needed to track stock held by JIVO distributors without confusing PO demand, distributor dispatch, customer GRN, or physical stock.

## Current source status

Paramjot supplied three Google Sheet links on 2026-07-17.

- **MASTER PO (`gid=739390425`)**: accessible and ingested. Paramjot previously defined it as distributor-sent GRN / distributor-to-platform outward confirmation. The target tab contains 47,438 data rows and 55 columns through 2026-07-16.
- **Sheet 1 (`gid=1182473296`)**: registered, but Google returned HTTP 401. No login HTML was stored as data.
- **Sheet 3 (`gid=1014515057`)**: registered, but Google returned HTTP 401. No login HTML was stored as data.

The inaccessible links remain in `source-registry.json` so they can be ingested without losing identity when viewer access is granted.

## Directory map

- `source-registry.json` — all three supplied links, GIDs, access state, and source role
- `raw/2026-07-17/` — immutable compressed source values and selected workbook reference tabs
- `normalized/` — one normalized row per raw MASTER PO row, including source lineage and quality flags
- `derived/` — decision-safe summaries generated only from rows that pass the confirmed-outward rules
- `quality/` — reproducible profile, anomalies, workbook structure, and live-API comparison
- `rules/` — inventory movement, cutoff, transit, mapping, and classification rules
- `future-data-register.json` — valuable future data types, their grain, decision use, and collection trigger
- `scripts/` — deterministic extraction and build utilities
- `checks/` — domain-specific verification; the repository's main verifier does not inspect this protected subtree

## What MASTER PO can prove

A positive, completed, dated `Delivered Qty` is evidence of distributor-to-platform/customer fulfilment and may be used as a confirmed outward/GRN proxy under the quality gates in `rules/inventory-ledger-rules.md`.

MASTER PO does **not** provide:

- physical opening or closing distributor SOH
- physical distributor dispatch timestamp
- returns/reversals as negative stock movements
- damage, expiry, or transfers
- immutable installment-level GRN history

Therefore it cannot, alone, prove warehouse SOH or in-transit stock.

## Latest-source rule

For current calculations, query authenticated JIVO Ecom live data first. This Google Sheet is a user-owned reference snapshot. Its PO+SKU keys overlap strongly with the live source, but the sheet includes duplicate rows and is mutable; current values can differ in status, date, quantity, and distributor mapping.

Use an upsert/latest-state model. Never append repeated cumulative rows as fresh outward movements.

## Rebuild

```bash
python3 intelligence/distributor-inventory/scripts/build_snapshot.py \
  --raw-csv intelligence/distributor-inventory/raw/2026-07-17/master-po-gid-739390425.csv.gz \
  --out intelligence/distributor-inventory/normalized/fact-distributor-po-line-2026-07-17.csv.gz \
  --profile intelligence/distributor-inventory/quality/master-po-profile-2026-07-17.json \
  --receipt intelligence/distributor-inventory/raw/2026-07-17/master-po-receipt.json

python3 intelligence/distributor-inventory/checks/check_ingestion.py
```

The build is lossless at the row level: duplicates are retained with occurrence ordinals rather than deleted.
