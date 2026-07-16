# JIVO distributor inventory intelligence

This protected Data Bank domain stores the evidence and rules needed to track stock held by JIVO distributors without confusing PO demand, distributor dispatch, customer GRN, or physical stock.

## Current source status

Paramjot supplied three Google Sheet links on 2026-07-17. All are now publicly readable and ingested.

- **GP / PRICE DATA (`gid=1182473296`)**: 113 Amazon price/listing rows. It is a pricing and marketplace-stock signal, never distributor SOH or movement.
- **MASTER PO (`gid=739390425`)**: 47,438 data rows and 55 columns through 2026-07-16. Paramjot defined it as distributor-sent GRN / distributor-to-platform outward confirmation.
- **DISTRIBUTORS CLAIMS (`gid=1014515057`)**: the linked `SNAP__MASTER PO` tab is empty, but the 21-tab workbook contains current JIVO sales through 2026-07-16, historical distributor snapshots, PO claim-costing through 2026-05-30, rate/mapping masters, and FIFO allocations/layers through 2026-05-30. All non-empty tabs and formulas are preserved separately.

Current expected inventory is calculated from dated July baselines plus authoritative live SAP inward and MASTER PO/customer-GRN outward. Undated historical stock tabs from DISTRIBUTORS CLAIMS are not substituted for missing current openings.

## Directory map

- `CURRENT-STATUS.md` — latest common-cutoff results, coverage, confidence, and source decisions
- `source-registry.json` — the three supplied Google links plus live and physical source packs
- `raw/2026-07-16/` — preserved physical evidence and authenticated live SAP snapshot
- `raw/2026-07-17/` — immutable Google-sheet values, all DISTRIBUTORS CLAIMS tabs/formulas, and reference tabs
- `normalized/` — lineage-preserving outward, inward, claims, historical, and baseline facts
- `derived/` — current SKU ledger, summaries, reconciliations, and user-facing workbook
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
