#!/usr/bin/env python3
"""Normalize a live JIVO Ecom SAP-sales JSON extract into the inventory movement schema."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import re
from datetime import datetime
from pathlib import Path


def snake(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_") or "unnamed"


def iso_date(value) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()


def number(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-json", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--snapshot-date", required=True)
    args = parser.parse_args()
    with gzip.open(args.raw_json, "rt", encoding="utf-8") if args.raw_json.suffix == ".gz" else args.raw_json.open() as handle:
        document = json.load(handle)
    rows = document["data"]
    source_headers = document.get("columns") or list(rows[0])
    normalized_headers = [snake(header) for header in source_headers]
    output_headers = ["snapshot_date", "source_row_number", "source_row_sha256", "movement_class", "quality_flags"] + normalized_headers
    args.out.parent.mkdir(parents=True, exist_ok=True)
    counts = {}
    with args.out.open("wb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", compresslevel=9, mtime=0) as gz, io.TextIOWrapper(gz, encoding="utf-8", newline="") as text:
        writer = csv.DictWriter(text, fieldnames=output_headers)
        writer.writeheader()
        for index, source in enumerate(rows, 2):
            normalized = {snake(header): source.get(header) for header in source_headers}
            normalized["docdate"] = iso_date(normalized.get("docdate"))
            quantity = number(normalized.get("quantity"))
            movement_type = str(normalized.get("type") or "").strip().upper()
            flags = []
            if not normalized["docdate"]:
                flags.append("missing_doc_date")
            if not normalized.get("cardname"):
                flags.append("missing_distributor")
            if not normalized.get("itemcode"):
                flags.append("missing_sap_sku_code")
            if quantity is None:
                flags.append("invalid_quantity")
            if movement_type == "SALES" and quantity is not None and quantity > 0 and not flags:
                movement_class = "billing_inward_proxy"
            elif movement_type == "SALES RETURN":
                movement_class = "accounting_negative_not_physical"
            elif quantity == 0:
                movement_class = "no_movement"
            else:
                movement_class = "quarantine_candidate"
            counts[movement_class] = counts.get(movement_class, 0) + 1
            digest = hashlib.sha256(json.dumps(source, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
            writer.writerow({
                "snapshot_date": args.snapshot_date,
                "source_row_number": index,
                "source_row_sha256": digest,
                "movement_class": movement_class,
                "quality_flags": ";".join(flags),
                **normalized,
            })
    profile = {
        "schema_version": 1,
        "snapshot_date": args.snapshot_date,
        "source": document.get("source"),
        "from_date": document.get("from_date"),
        "to_date": document.get("to_date"),
        "raw_rows": len(rows),
        "movement_classes": counts,
        "precedence": "Authoritative current JIVO-to-distributor billing/inward source for this snapshot."
    }
    args.profile.parent.mkdir(parents=True, exist_ok=True)
    args.profile.write_text(json.dumps(profile, indent=2) + "\n")


if __name__ == "__main__":
    main()
