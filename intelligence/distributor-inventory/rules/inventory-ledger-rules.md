# Distributor inventory ledger rules

## Purpose

This domain turns user-supplied physical stock snapshots, JIVO-to-distributor inward, and distributor-to-platform fulfilment into an auditable distributor stock ledger. It does not force balances to zero and does not merge distinct event dates.

## Canonical grain

`distributor × SAP SKU × effective date`

Each distributor currently has one warehouse. Keep the warehouse as reference metadata rather than a second inventory identity.

## Three separate stock states

1. **Distributor warehouse SOH**
   - `opening physical SOH + confirmed distributor receipts − confirmed distributor dispatch`
2. **In transit**
   - `confirmed distributor dispatch − customer/platform accepted GRN`
3. **Platform received**
   - confirmed customer/platform GRN quantity

Do not collapse these three states. MASTER PO supports the third state and can proxy the second deduction only when physical dispatch timing is unavailable.

## Source precedence

- **Current/latest outward:** authenticated JIVO Ecom live API.
- **Google MASTER PO:** distributor-sent customer-GRN reference and reconciliation snapshot.
- **Physical SOH:** dated distributor stock statement.
- **Manual `DIS. STOCK REPORT`:** Paramjot/team's expected-balance control tracker.
- **Raw spreadsheet formulas:** preserve as source logic, but do not use exported Google formulas as an independent calculation engine.

When the live API and Google snapshot differ, retain both, use live for current decisions, and log the bridge. Never append a new cumulative snapshot as a second movement.

## Confirmed outward rule for MASTER PO

Post `delivered_qty` as confirmed distributor-to-platform outward/GRN proxy only when all are true:

1. `delivered_qty > 0`
2. valid `delivery_date` exists
3. `po_status = COMPLETED`
4. `delivered_qty <= order_qty`
5. `delivery_date >= po_date`
6. distributor is mapped
7. platform SKU maps to a canonical SAP SKU

Use `delivery_date` as the movement date. Use `delivered_qty` once. `FILLED QTY`, `FILLED LTRS`, and `Total Delivered Liters` are derivatives and must not create a second movement.

## Quarantine rather than silently correct

- positive delivery without delivery date
- positive delivery on pending, cancelled, expired, or other non-completed PO
- delivered quantity greater than ordered quantity
- delivery before PO date
- expiry before PO date
- missing distributor or SAP SKU mapping
- downward revision to cumulative delivered quantity
- duplicate source rows
- invalid or ambiguous dates

A delivery after PO expiry is a warning, not automatic rejection: a late but accepted delivery can be valid.

## Not a stock movement

- PO/order quantity by itself
- PO creation or status transition by itself
- pending, cancelled, expired, or unfulfilled quantity
- missed quantity/litres
- zero or blank delivered quantity
- rates, amounts, margins, and commissions
- platform demand not yet delivered

For partial POs, deduct only confirmed delivered quantity. Never deduct the unfulfilled balance.

## Inward rule

JIVO-to-distributor inward comes from positive SAP invoice/sales rows aligned strictly after the opening cutoff through the closing cutoff. Signed `Sales Return`/credit rows are accounting evidence, not assumed physical movement. Current business confirmation is that physical returns, damage, and expiry are zero; therefore exclude those signed rows from the operational stock bridge unless physical movement evidence is later supplied.

## Physical snapshot rule

- Every stock snapshot needs distributor identity and effective cutoff.
- Preserve blank quantities as unknown unless the statement is explicitly complete and blanks/absent SKUs are confirmed as zero.
- Validate embedded SAP code against the live SAP item description. Code-description conflicts stay quarantined.
- Preserve packaging/carton exceptions separately from canonical SAP-SKU scope.

## Cutoff rule

If opening stock is the close of day `D0`, include movements from `D0 + 1` through closing cutoff `D1`, inclusive. Do not deduct a GRN dated on or before the opening close again.

## Reconciliation classifications

- `physically_reconciled`: two aligned physical snapshots and complete confirmed movements
- `provisional`: two snapshots but dispatch timing, blanks, or mappings remain unresolved
- `opening_only`: physical opening exists but no physical closing
- `expected_balance_only`: movements exist but physical opening/closing is incomplete
- `not_ready`: identity or cutoff is unknown

Residual differences without evidence are `unexplained variance`, not automatically shortage, theft, sale, or damage.

## Current Google MASTER PO snapshot quality gates

The 2026-07-17 snapshot contains 47,438 rows and 55 source columns. Known warnings include duplicate rows, missing SAP mappings, delivery-before-PO dates, and delivered-greater-than-ordered lines. The normalized fact labels rows as:

- `confirmed_outward`
- `quarantine_candidate`
- `no_confirmed_movement`

Only `confirmed_outward` is eligible for automatic stock deduction.
