#!/usr/bin/env python3
"""Build the current expected distributor inventory ledger from baselines and normalized movements."""
from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import re
from collections import defaultdict
from pathlib import Path

FIELDS = [
    "as_of_date", "distributor", "sap_sku_code", "product", "baseline_cutoff", "baseline_confidence",
    "opening_quantity", "billing_inward_proxy", "accounting_negative_diagnostic", "confirmed_outward",
    "expected_quantity", "status", "notes",
]


def number(value: str) -> float:
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def normalize_item(value: str) -> str:
    text = re.sub(r"[^A-Z0-9]+", " ", str(value or "").upper()).strip()
    aliases = {
        "CANOLA 1 1 L": "CANOLA 1 1L",
        "GROUNDNUT 200 ML": "GROUNDNUT 200ML",
        "EXTRA VIRGIN 200 ML": "EXTRA VIRGIN 200ML",
        "EXTRA VIRGIN 250 ML": "EXTRA VIRGIN 250ML",
    }
    return aliases.get(text, text)


def open_writer(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = path.open("wb")
    gz = gzip.GzipFile(filename="", fileobj=raw, mode="wb", compresslevel=9, mtime=0)
    text = io.TextIOWrapper(gz, encoding="utf-8", newline="")
    writer = csv.DictWriter(text, fieldnames=FIELDS)
    writer.writeheader()
    return raw, gz, text, writer


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baselines", required=True, type=Path)
    parser.add_argument("--sales", required=True, type=Path)
    parser.add_argument("--outward", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--as-of-date", required=True)
    args = parser.parse_args()

    baseline: dict[tuple[str, str], dict] = {}
    cutoffs: dict[str, str] = {}
    with gzip.open(args.baselines, "rt", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            key = (row["distributor"], row["sap_sku_code"])
            baseline[key] = row
            cutoffs[row["distributor"]] = row["effective_cutoff"]

    product_codes: dict[str, set[str]] = defaultdict(set)
    for row in baseline.values():
        product_codes[normalize_item(row.get("product", ""))].add(row["sap_sku_code"])
    unique_product_code = {product: next(iter(codes)) for product, codes in product_codes.items() if product and len(codes) == 1}

    inward = defaultdict(float)
    negative = defaultdict(float)
    movement_only_inward = defaultdict(float)
    movement_only_negative = defaultdict(float)
    with gzip.open(args.sales, "rt", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            distributor = row.get("cardname", "").strip().upper()
            code = row.get("itemcode", "").strip()
            date = row.get("docdate", "")
            quantity = number(row.get("quantity", ""))
            if not distributor or not code or not date or date > args.as_of_date:
                continue
            if "2026-07-01" <= date <= args.as_of_date:
                if row["movement_class"] == "billing_inward_proxy":
                    movement_only_inward[(distributor, code)] += quantity
                elif row["movement_class"] == "accounting_negative_not_physical":
                    movement_only_negative[(distributor, code)] += quantity
            cutoff = cutoffs.get(distributor)
            if cutoff is None or date <= cutoff:
                continue
            if row["movement_class"] == "billing_inward_proxy":
                inward[(distributor, code)] += quantity
            elif row["movement_class"] == "accounting_negative_not_physical":
                negative[(distributor, code)] += quantity

    outward = defaultdict(float)
    recovered_outward = defaultdict(float)
    recovered_outward_rows = defaultdict(int)
    movement_only_outward = defaultdict(float)
    with gzip.open(args.outward, "rt", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            movement_class = row["movement_class"]
            code = row.get("sap_sku_code", "").strip()
            recovered = False
            if movement_class != "confirmed_outward":
                flags = set(filter(None, row.get("quality_flags", "").split(";")))
                recoverable_flags = {"missing_sap_sku_code", "delivery_after_expiry"}
                if movement_class == "quarantine_candidate" and "missing_sap_sku_code" in flags and flags <= recoverable_flags:
                    code = unique_product_code.get(normalize_item(row.get("item", "")), "")
                    recovered = bool(code)
                if not recovered:
                    continue
            distributor = row.get("distributor", "").strip().upper()
            date = row.get("delivery_date", "")
            quantity = number(row.get("delivered_qty", ""))
            if not distributor or not code or not date or date > args.as_of_date:
                continue
            if "2026-07-01" <= date <= args.as_of_date:
                movement_only_outward[(distributor, code)] += quantity
            cutoff = cutoffs.get(distributor)
            if cutoff is None or date <= cutoff:
                continue
            if recovered:
                recovered_outward[distributor] += quantity
                recovered_outward_rows[distributor] += 1
            outward[(distributor, code)] += quantity

    keys = set(baseline) | set(inward) | set(outward)
    rows = []
    summary = defaultdict(lambda: {
        "baseline_cutoff": None,
        "baseline_confidence": None,
        "opening_quantity": 0.0,
        "billing_inward_proxy": 0.0,
        "accounting_negative_diagnostic": 0.0,
        "confirmed_outward": 0.0,
        "recovered_outward_from_item_mapping": 0.0,
        "recovered_outward_rows": 0,
        "expected_quantity": 0.0,
        "sku_rows": 0,
        "negative_expected_skus": 0,
    })
    for distributor, code in sorted(keys):
        if distributor not in cutoffs:
            continue
        base = baseline.get((distributor, code), {})
        opening = number(base.get("baseline_quantity", ""))
        billing = inward[(distributor, code)]
        returns = negative[(distributor, code)]
        delivered = outward[(distributor, code)]
        expected = opening + billing - delivered
        confidence = base.get("confidence") or next(
            (value["confidence"] for key, value in baseline.items() if key[0] == distributor), ""
        )
        status = "expected_negative" if expected < 0 else "expected_nonnegative"
        notes = "Accounting-negative rows are diagnostic and excluded from physical movement."
        if not base:
            notes += " SKU absent from baseline canonical scope; operational rule treats opening as zero."
        rows.append({
            "as_of_date": args.as_of_date,
            "distributor": distributor,
            "sap_sku_code": code,
            "product": base.get("product", ""),
            "baseline_cutoff": cutoffs[distributor],
            "baseline_confidence": confidence,
            "opening_quantity": opening,
            "billing_inward_proxy": billing,
            "accounting_negative_diagnostic": returns,
            "confirmed_outward": delivered,
            "expected_quantity": expected,
            "status": status,
            "notes": notes,
        })
        item = summary[distributor]
        item["baseline_cutoff"] = cutoffs[distributor]
        item["baseline_confidence"] = confidence
        item["opening_quantity"] += opening
        item["billing_inward_proxy"] += billing
        item["accounting_negative_diagnostic"] += returns
        item["confirmed_outward"] += delivered
        item["recovered_outward_from_item_mapping"] = recovered_outward[distributor]
        item["recovered_outward_rows"] = recovered_outward_rows[distributor]
        item["expected_quantity"] += expected
        item["sku_rows"] += 1
        if expected < 0:
            item["negative_expected_skus"] += 1

    raw, gz, text, writer = open_writer(args.out)
    try:
        writer.writerows(rows)
    finally:
        text.close()

    movement_only_distributors = [
        "KNOWTABLE ONLINE SERVICES PRIVATE LIMITED",
        "EVARA ENTERPRISES",
    ]
    movement_only = {}
    for distributor in movement_only_distributors:
        billing = sum(value for (dist, _), value in movement_only_inward.items() if dist == distributor)
        returns = sum(value for (dist, _), value in movement_only_negative.items() if dist == distributor)
        delivered = sum(value for (dist, _), value in movement_only_outward.items() if dist == distributor)
        movement_only[distributor] = {
            "period": "2026-07-01 through 2026-07-16",
            "billing_inward_proxy": billing,
            "accounting_negative_diagnostic": returns,
            "confirmed_outward": delivered,
            "net_movement_without_opening": billing - delivered,
            "absolute_inventory_available": False,
            "reason": "No dated July opening baseline."
        }

    document = {
        "schema_version": 1,
        "as_of_date": args.as_of_date,
        "equation": "expected = opening baseline + positive JIVO billing proxy - confirmed customer GRN/outward",
        "current_expected_inventory": dict(summary),
        "movement_only": movement_only,
        "confidence_rule": {
            "physical_verified": "Operational expected stock; physical re-count still required to certify closing.",
            "physical_verified_canonical_scope": "Canonical expected stock; alternate-pack exceptions remain separate.",
            "physical_statement_mapped": "Expected stock from a mapped statement baseline; negative reported openings are preserved.",
            "manual_tracker_unverified": "Provisional expected stock only."
        },
        "limitations": [
            "Customer/platform GRN date is not the physical distributor dispatch timestamp; in-transit timing remains inside residual stock until dispatch evidence exists.",
            "Positive JMPL sales are billing/inward proxies, not proof of distributor receipt.",
            "Accounting-negative sales rows are excluded because physical returns are confirmed zero.",
            "Knowtable and Evara need dated opening baselines before absolute inventory can be calculated."
        ]
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(document, indent=2) + "\n")


if __name__ == "__main__":
    main()
