# Current distributor inventory status

**Latest common data cutoff:** close 16 July 2026

## Operational equation

`Expected inventory = dated opening/physical baseline + positive JIVO billing proxy − confirmed customer/platform GRN`

Accounting-negative SAP rows are retained as diagnostics but excluded from physical movement because physical returns are confirmed as zero. Ordered, unfulfilled, cancelled, or expired PO quantity is not movement.

## Absolute expected inventory available

- **Antize Foods:** 44,622 canonical units expected at close 16 July
  - Physical close 15 July: 42,322
  - Positive JIVO billing on 16 July: 2,300
  - Confirmed outward on 16 July: 0
  - Confidence: operational expectation from dated physical baseline
- **Baba Lokenath:** 28,907 canonical units at close 16 July
  - Physical close 16 July: 28,907
  - Four alternate-pack/carton rows totaling 166 units remain outside canonical scope
  - Confidence: dated physical baseline, canonical scope
- **Chirag Enterprises:** 11,589 units expected at close 16 July
  - 30 June mapped statement baseline: 7,663
  - Positive JIVO billing 1–16 July: 16,606
  - Confirmed outward 1–16 July: 12,680
  - Two outward rows totaling 35 units were safely recovered from unique canonical item-name mapping because their source SAP code was blank
  - Confidence: expected stock from mapped statement baseline; eight SKU balances are negative and require control review
- **SustainQuest:** 33,543 units provisionally expected at close 16 July
  - Manual July opening assumption: 50,571
  - Positive JIVO billing 1–16 July: 48,392
  - Confirmed outward 1–16 July: 65,420
  - Confidence: provisional only because the opening is not a dated physical snapshot

## Movement-only distributors

Absolute inventory is not calculated without inventing an opening balance.

- **Knowtable, 1–16 July:** billing 68,364; outward 73,793; net movement −5,429
- **Evara, 1–16 July:** billing 31,739; outward 35,393; net movement −3,654

A dated opening SOH for either distributor can be inserted later without rebuilding the movement history.

## Source decisions

- Authenticated JIVO Ecom live SAP data is authoritative for current inward.
- MASTER PO/customer GRN is the current outward reference; repeated cumulative rows are upserted and duplicates are not deducted twice.
- DISTRIBUTORS CLAIMS `JMPL SALES V2` is a preserved reference and cross-check. Its sales values can differ from the live extract and therefore do not override live current data.
- DISTRIBUTORS CLAIMS `PO DATA`, FIFO allocations, and FIFO layers stop at 30 May 2026 and are historical claims/costing sources.
- GP `PRICE DATA` informs marketplace price and listing-stock decisions but never physical distributor inventory.
- Undated stock tabs in DISTRIBUTORS CLAIMS are historical context. Stale formula month filters and broken cached formula results prevent their use as current baselines.

## What this tracker can and cannot prove

The tracker can maintain expected canonical stock by distributor and SKU from each accepted cutoff onward. It can preserve every source row, mapping decision, anomaly, and adjustment.

It cannot prove physical dispatch timing or in-transit stock from customer GRN alone. Physical recounts remain the certification step, and dated openings are still required for Knowtable and Evara before their absolute SOH can be reported.
