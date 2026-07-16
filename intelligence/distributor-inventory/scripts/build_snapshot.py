#!/usr/bin/env python3
"""Build a lossless, normalized distributor-outward snapshot from MASTER PO CSV.

The raw CSV remains immutable. The normalized fact keeps one output row per raw row,
adds lineage/quality flags, and never silently deduplicates or converts PO demand into
inventory movement.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

SOURCE_ID = "google-master-po-gid-739390425"
SNAPSHOT_DATE = "2026-07-17"

HEADER_MAP = {
    " ": "po_number",
    "PO Date": "po_date",
    "PO Expiry Date": "po_expiry_date",
    "Delivery Date": "delivery_date",
    "Vendor Name": "vendor_name_raw",
    "Status": "status_raw",
    "Remarks": "remarks",
    "SKU Code": "platform_sku_code",
    "SKU Name": "platform_sku_name",
    "Order Qty": "order_qty",
    "Delivered Qty": "delivered_qty",
    "Basic Rate": "basic_rate",
    "landing Rate": "landing_rate",
    "Location": "location",
    "Format": "platform",
    "Lead Time": "lead_time",
    "Days To Expiry": "days_to_expiry",
    "Po Window": "po_window",
    "PO Status": "po_status",
    "Item Status": "item_status",
    "Vendor_New": "distributor",
    "ITEM": "item",
    "SAP SKU NAME": "sap_sku_name",
    "SAP SKU Code": "sap_sku_code",
    "Category": "category",
    "Sub Category": "sub_category",
    "Case Pack": "case_pack",
    "Per Liter": "per_litre",
    "Total Order Liters": "total_order_litres",
    "Total Delivered Liters": "total_delivered_litres",
    "Total Order Amt (INCLUSIVE)": "total_order_amount_inclusive",
    "Total Deliver Amt (INCLUSIVE)": "total_delivered_amount_inclusive",
    "PO Month": "po_month",
    "Delivery Month": "delivery_month",
    "PO YEAR": "po_year",
    "DEL YEAR": "delivery_year",
    "Item Head": "item_head",
    "City": "city",
    "State": "state",
    "Distributor Margin": "distributor_margin",
    "Realise": "realise",
    "Distributor Commision Per Unit": "distributor_commission_per_unit",
    "Total Distributor Commission": "total_distributor_commission",
    "Brand": "brand",
    "Category Head": "category_head",
    "Unit of Measure": "unit_of_measure",
    "Open/Close": "open_close",
    "TOTAL ORDER AMT (EXCLUSIVE)": "total_order_amount_exclusive",
    "TOTAL DELIVERED AMT EXCLUSIVE": "total_delivered_amount_exclusive",
    "TOTAL ORDER AMT (WITHOUT MARGIN)": "total_order_amount_without_margin",
    "TOTAL DELIVERED AMT (WITHOUT MARGIN)": "total_delivered_amount_without_margin",
    "MISSED QTY": "missed_qty",
    "FILLED QTY": "filled_qty",
    "MISSED LTRS": "missed_litres",
    "FILLED LTRS": "filled_litres",
}
DATE_FIELDS = {"po_date", "po_expiry_date", "delivery_date"}
NUM_FIELDS = {
    "order_qty", "delivered_qty", "basic_rate", "landing_rate", "lead_time",
    "days_to_expiry", "po_window", "case_pack", "per_litre",
    "total_order_litres", "total_delivered_litres",
    "total_order_amount_inclusive", "total_delivered_amount_inclusive",
    "distributor_margin", "realise", "distributor_commission_per_unit",
    "total_distributor_commission", "total_order_amount_exclusive",
    "total_delivered_amount_exclusive", "total_order_amount_without_margin",
    "total_delivered_amount_without_margin", "missed_qty", "filled_qty",
    "missed_litres", "filled_litres",
}
LINEAGE_FIELDS = [
    "snapshot_date", "source_id", "source_row_number", "source_row_sha256",
    "source_duplicate_ordinal", "movement_class", "quality_flags",
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_date(value: str) -> tuple[str, bool]:
    s = (value or "").strip()
    if not s:
        return "", True
    candidates = [s[:10]]
    for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        for candidate in candidates:
            try:
                return datetime.strptime(candidate, fmt).date().isoformat(), True
            except ValueError:
                pass
    return s, False


def parse_number(value: str) -> tuple[str, float | None, bool]:
    s = (value or "").strip().replace(",", "")
    if not s:
        return "", None, True
    try:
        n = float(s)
    except ValueError:
        return s, None, False
    if n.is_integer():
        return str(int(n)), n, True
    return format(n, ".15g"), n, True


def canonical_row(raw: dict[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for original, normalized in HEADER_MAP.items():
        value = raw.get(original, "")
        if normalized in DATE_FIELDS:
            out[normalized] = parse_date(value)[0]
        elif normalized in NUM_FIELDS:
            out[normalized] = parse_number(value)[0]
        else:
            out[normalized] = (value or "").strip()
    return out


def movement_class_and_flags(row: dict[str, str]) -> tuple[str, list[str]]:
    flags: list[str] = []
    _, order, order_ok = parse_number(row["order_qty"])
    _, delivered, delivered_ok = parse_number(row["delivered_qty"])
    po_date, po_ok = parse_date(row["po_date"])
    delivery_date, delivery_ok = parse_date(row["delivery_date"])
    expiry_date, expiry_ok = parse_date(row["po_expiry_date"])

    if not order_ok:
        flags.append("invalid_order_qty")
    if not delivered_ok:
        flags.append("invalid_delivered_qty")
    if row["po_date"] and not po_ok:
        flags.append("invalid_po_date")
    if row["delivery_date"] and not delivery_ok:
        flags.append("invalid_delivery_date")
    if row["po_expiry_date"] and not expiry_ok:
        flags.append("invalid_expiry_date")
    if delivered is not None and delivered < 0:
        flags.append("negative_delivered_qty")
    if order is not None and order < 0:
        flags.append("negative_order_qty")
    if delivered is not None and order is not None and delivered > order:
        flags.append("delivered_gt_order")
    if delivered is not None and delivered > 0 and not delivery_date:
        flags.append("positive_delivery_missing_date")
    if po_date and delivery_date and delivery_date < po_date:
        flags.append("delivery_before_po")
    if po_date and expiry_date and expiry_date < po_date:
        flags.append("expiry_before_po")
    if delivery_date and expiry_date and delivery_date > expiry_date:
        flags.append("delivery_after_expiry")
    if not row["sap_sku_code"]:
        flags.append("missing_sap_sku_code")
    if not row["distributor"]:
        flags.append("missing_distributor")
    if delivered is not None and delivered > 0 and row["po_status"].upper() != "COMPLETED":
        flags.append("positive_delivery_noncompleted_po")

    if not delivered or delivered <= 0:
        movement_class = "no_confirmed_movement"
    else:
        blocking = {
            "invalid_delivered_qty", "negative_delivered_qty", "delivered_gt_order",
            "positive_delivery_missing_date", "invalid_delivery_date", "delivery_before_po",
            "missing_sap_sku_code", "missing_distributor", "positive_delivery_noncompleted_po",
        }
        movement_class = "confirmed_outward" if not blocking.intersection(flags) else "quarantine_candidate"
    return movement_class, flags


def open_source_text(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, mode="rt", encoding="utf-8-sig", newline="")
    return path.open(mode="r", encoding="utf-8-sig", newline="")


def build(
    raw_csv: Path,
    out_csv_gz: Path,
    profile_path: Path,
    receipt_path: Path,
    snapshot_date: str = SNAPSHOT_DATE,
    source_id: str = SOURCE_ID,
    retrieved_at_utc: str = "2026-07-16T19:13:51Z",
) -> None:
    raw_bytes = raw_csv.read_bytes()
    counters = Counter()
    dist = Counter()
    platforms = Counter()
    po_statuses = Counter()
    item_statuses = Counter()
    movement_classes = Counter()
    flag_counts = Counter()
    pos = Counter()
    po_set: set[str] = set()
    raw_hash_occurrence = Counter()
    date_min: dict[str, str | None] = {k: None for k in DATE_FIELDS}
    date_max: dict[str, str | None] = {k: None for k in DATE_FIELDS}

    out_csv_gz.parent.mkdir(parents=True, exist_ok=True)
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)

    with open_source_text(raw_csv) as src, out_csv_gz.open("wb") as compressed_file:
        with gzip.GzipFile(filename="", fileobj=compressed_file, mode="wb", compresslevel=9, mtime=0) as gz_file, io.TextIOWrapper(
            gz_file, encoding="utf-8", newline=""
        ) as dst:
            reader = csv.DictReader(src)
            source_headers = reader.fieldnames
            if source_headers is None or source_headers != list(HEADER_MAP):
                raise SystemExit(f"unexpected MASTER PO header: {source_headers}")
            writer = csv.DictWriter(dst, fieldnames=LINEAGE_FIELDS + list(HEADER_MAP.values()))
            writer.writeheader()
            for source_row, raw in enumerate(reader, 2):
                counters["rows"] += 1
                raw_cells = [raw.get(h, "") for h in source_headers]
                row_hash = sha256_bytes(json.dumps(raw_cells, ensure_ascii=False, separators=(",", ":")).encode())
                raw_hash_occurrence[row_hash] += 1
                duplicate_ordinal = raw_hash_occurrence[row_hash]
                row = canonical_row(raw)
                movement_class, flags = movement_class_and_flags(row)
                if duplicate_ordinal > 1:
                    counters["duplicate_excess_rows"] += 1
                    flags.append("duplicate_source_row")
                    if movement_class == "confirmed_outward":
                        movement_class = "quarantine_candidate"
                movement_classes[movement_class] += 1
                flag_counts.update(flags)
                po_set.add(row["po_number"])
                pos[(row["po_number"], row["platform_sku_code"])] += 1
                dist[row["distributor"]] += 1
                platforms[row["platform"]] += 1
                po_statuses[row["po_status"]] += 1
                item_statuses[row["item_status"]] += 1
                for field in DATE_FIELDS:
                    value, valid = parse_date(row[field])
                    if valid and value:
                        current_min = date_min[field]
                        current_max = date_max[field]
                        date_min[field] = value if current_min is None or value < current_min else current_min
                        date_max[field] = value if current_max is None or value > current_max else current_max
                writer.writerow({
                    "snapshot_date": snapshot_date,
                    "source_id": source_id,
                    "source_row_number": source_row,
                    "source_row_sha256": row_hash,
                    "source_duplicate_ordinal": duplicate_ordinal,
                    "movement_class": movement_class,
                    "quality_flags": ";".join(flags),
                    **row,
                })

    normalized_bytes = out_csv_gz.read_bytes()
    profile = {
        "schema_version": 1,
        "snapshot_date": snapshot_date,
        "source_id": source_id,
        "raw": {
            "path": str(raw_csv),
            "bytes": len(raw_bytes),
            "sha256": sha256_bytes(raw_bytes),
            "rows": counters["rows"],
            "columns": len(HEADER_MAP),
        },
        "normalized": {
            "path": str(out_csv_gz),
            "bytes": len(normalized_bytes),
            "sha256": sha256_bytes(normalized_bytes),
            "rows": counters["rows"],
            "columns": len(LINEAGE_FIELDS) + len(HEADER_MAP),
        },
        "counts": {
            "rows": counters["rows"],
            "distinct_pos": len([x for x in po_set if x]),
            "distinct_po_sku_keys": len(pos),
            "duplicate_po_sku_excess_rows": sum(n - 1 for n in pos.values() if n > 1),
            "duplicate_exact_excess_rows": counters["duplicate_excess_rows"],
            "movement_classes": dict(movement_classes),
            "quality_flags": dict(flag_counts.most_common()),
        },
        "date_ranges": {field: {"min": date_min[field], "max": date_max[field]} for field in sorted(DATE_FIELDS)},
        "distributors": dict(dist.most_common()),
        "platforms": dict(platforms.most_common()),
        "po_statuses": dict(po_statuses.most_common()),
        "item_statuses": dict(item_statuses.most_common()),
        "interpretation": {
            "movement_measure": "delivered_qty",
            "movement_date": "delivery_date",
            "movement_role": "confirmed distributor-to-platform outward/customer GRN proxy",
            "not_a_movement": ["order_qty", "missed_qty", "filled_qty as a second posting", "status change alone"],
            "latest_source_precedence": "authenticated JIVO Ecom live API",
        },
    }
    profile_path.write_text(json.dumps(profile, indent=2, ensure_ascii=False) + "\n")
    receipt = {
        "schema_version": 1,
        "source_id": source_id,
        "document_id": "10-P_ZBVGaIKz87PTByk8rMb_c1J0VT0mfZo_84qwjQU",
        "gid": "739390425",
        "tab_name": "MASTER PO",
        "retrieved_at_utc": retrieved_at_utc,
        "snapshot_date_ist": snapshot_date,
        "http_status": 200,
        "content_type": "text/csv",
        "raw_path": str(raw_csv),
        "raw_bytes": len(raw_bytes),
        "raw_sha256": sha256_bytes(raw_bytes),
        "row_count": counters["rows"],
        "column_count": len(HEADER_MAP),
        "header": list(HEADER_MAP),
        "validation": "pass",
    }
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--raw-csv", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--profile", required=True, type=Path)
    p.add_argument("--receipt", required=True, type=Path)
    p.add_argument("--snapshot-date", default=SNAPSHOT_DATE)
    p.add_argument("--source-id", default=SOURCE_ID)
    p.add_argument("--retrieved-at-utc", default="2026-07-16T19:13:51Z")
    args = p.parse_args()
    build(
        args.raw_csv,
        args.out,
        args.profile,
        args.receipt,
        snapshot_date=args.snapshot_date,
        source_id=args.source_id,
        retrieved_at_utc=args.retrieved_at_utc,
    )


if __name__ == "__main__":
    main()
