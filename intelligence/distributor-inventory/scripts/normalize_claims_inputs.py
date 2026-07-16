#!/usr/bin/env python3
"""Normalize the two decision-relevant fact tabs from DISTRIBUTORS CLAIMS."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
from collections import Counter
from datetime import datetime
from pathlib import Path


def parse_date(value: str) -> tuple[str, bool]:
    text = str(value or "").strip()
    if not text:
        return "", True
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat(), True
        except ValueError:
            pass
    return text, False


def number(value: str) -> float | None:
    text = str(value or "").strip().replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def snake(value: str) -> str:
    import re
    text = re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")
    return text or "unnamed"


def open_writer(path: Path, fieldnames: list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = path.open("wb")
    gz = gzip.GzipFile(filename="", fileobj=raw, mode="wb", compresslevel=9, mtime=0)
    text = io.TextIOWrapper(gz, encoding="utf-8", newline="")
    writer = csv.DictWriter(text, fieldnames=fieldnames)
    writer.writeheader()
    return raw, gz, text, writer


def normalize_sales(source: Path, output: Path, snapshot_date: str) -> dict:
    counts = Counter()
    min_date = max_date = None
    with gzip.open(source, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        raw_headers = reader.fieldnames or []
        headers = [snake(header) for header in raw_headers]
        fields = ["snapshot_date", "source_row_number", "source_row_sha256", "movement_class", "quality_flags"] + headers
        raw, gz, text, writer = open_writer(output, fields)
        try:
            for line, row in enumerate(reader, 2):
                raw_values = [row.get(header, "") for header in raw_headers]
                digest = hashlib.sha256(json.dumps(raw_values, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
                normalized = {snake(header): row.get(header, "") for header in raw_headers}
                date_value, date_valid = parse_date(normalized.get("docdate", ""))
                normalized["docdate"] = date_value
                quantity = number(normalized.get("quantity", ""))
                flags = []
                if not date_valid:
                    flags.append("invalid_doc_date")
                if not normalized.get("cardname"):
                    flags.append("missing_distributor")
                if not normalized.get("itemcode"):
                    flags.append("missing_sap_sku_code")
                if quantity is None:
                    flags.append("invalid_quantity")
                if quantity is not None and quantity > 0 and not flags:
                    movement_class = "billing_inward_proxy"
                elif quantity is not None and quantity < 0:
                    movement_class = "accounting_negative_not_physical"
                elif quantity == 0:
                    movement_class = "no_movement"
                else:
                    movement_class = "quarantine_candidate"
                counts[movement_class] += 1
                counts["rows"] += 1
                for flag in flags:
                    counts[f"flag:{flag}"] += 1
                if date_valid and date_value:
                    min_date = date_value if min_date is None or date_value < min_date else min_date
                    max_date = date_value if max_date is None or date_value > max_date else max_date
                writer.writerow({
                    "snapshot_date": snapshot_date,
                    "source_row_number": line,
                    "source_row_sha256": digest,
                    "movement_class": movement_class,
                    "quality_flags": ";".join(flags),
                    **normalized,
                })
        finally:
            text.close()
    return {"source": str(source), "output": str(output), "counts": dict(counts), "date_range": {"min": min_date, "max": max_date}}


def normalize_po(source: Path, output: Path, snapshot_date: str) -> dict:
    counts = Counter()
    min_date = max_date = None
    with gzip.open(source, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        raw_headers = reader.fieldnames or []
        headers = [snake(header) for header in raw_headers]
        fields = ["snapshot_date", "source_row_number", "source_row_sha256", "movement_class", "quality_flags"] + headers
        raw, gz, text, writer = open_writer(output, fields)
        try:
            for line, row in enumerate(reader, 2):
                raw_values = [row.get(header, "") for header in raw_headers]
                digest = hashlib.sha256(json.dumps(raw_values, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
                normalized = {snake(header): row.get(header, "") for header in raw_headers}
                po_date, po_valid = parse_date(normalized.get("po_date", ""))
                delivery_date, delivery_valid = parse_date(normalized.get("delivery_date", ""))
                normalized["po_date"] = po_date
                normalized["delivery_date"] = delivery_date
                delivered = number(normalized.get("delivered_qty", ""))
                ordered = number(normalized.get("order_qty", ""))
                flags = []
                if not po_valid:
                    flags.append("invalid_po_date")
                if delivered is not None and delivered > 0 and (not delivery_valid or not delivery_date):
                    flags.append("positive_delivery_missing_date")
                if delivered is not None and ordered is not None and delivered > ordered:
                    flags.append("delivered_gt_order")
                if po_date and delivery_date and delivery_date < po_date:
                    flags.append("delivery_before_po")
                if not normalized.get("vendor_new"):
                    flags.append("missing_distributor")
                if not normalized.get("sap_sku_code"):
                    flags.append("missing_sap_sku_code")
                if delivered is not None and delivered > 0 and not flags:
                    movement_class = "historical_outward_reference"
                elif delivered is not None and delivered > 0:
                    movement_class = "quarantine_candidate"
                else:
                    movement_class = "no_confirmed_movement"
                counts[movement_class] += 1
                counts["rows"] += 1
                for flag in flags:
                    counts[f"flag:{flag}"] += 1
                if delivery_valid and delivery_date:
                    min_date = delivery_date if min_date is None or delivery_date < min_date else min_date
                    max_date = delivery_date if max_date is None or delivery_date > max_date else max_date
                writer.writerow({
                    "snapshot_date": snapshot_date,
                    "source_row_number": line,
                    "source_row_sha256": digest,
                    "movement_class": movement_class,
                    "quality_flags": ";".join(flags),
                    **normalized,
                })
        finally:
            text.close()
    return {"source": str(source), "output": str(output), "counts": dict(counts), "delivery_date_range": {"min": min_date, "max": max_date}, "latest_source_precedence": "Google MASTER PO / authenticated JIVO Ecom live API"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--claims-dir", required=True, type=Path)
    parser.add_argument("--normalized-dir", required=True, type=Path)
    parser.add_argument("--quality", required=True, type=Path)
    parser.add_argument("--snapshot-date", required=True)
    args = parser.parse_args()
    sales = normalize_sales(
        args.claims_dir / "jmpl-sales-v2.csv.gz",
        args.normalized_dir / f"fact-jmpl-sales-{args.snapshot_date}.csv.gz",
        args.snapshot_date,
    )
    po = normalize_po(
        args.claims_dir / "po-data.csv.gz",
        args.normalized_dir / f"fact-historical-claims-po-{args.snapshot_date}.csv.gz",
        args.snapshot_date,
    )
    args.quality.parent.mkdir(parents=True, exist_ok=True)
    args.quality.write_text(json.dumps({"schema_version": 1, "sales": sales, "claims_po": po}, indent=2) + "\n")


if __name__ == "__main__":
    main()
