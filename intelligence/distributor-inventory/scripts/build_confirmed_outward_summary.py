#!/usr/bin/env python3
"""Build a decision-safe by-distributor summary from confirmed-outward fact rows."""
from __future__ import annotations

import argparse
import csv
import gzip
import json
from collections import defaultdict
from pathlib import Path


def number(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def empty_record() -> dict:
    return {
        "rows": 0,
        "po_numbers": set(),
        "delivered_line_units": 0.0,
        "delivered_litres": 0.0,
        "min_delivery_date": None,
        "max_delivery_date": None,
        "quarantine_rows": 0,
        "no_confirmed_movement_rows": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fact", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--snapshot-date", required=True)
    args = parser.parse_args()
    grouped = defaultdict(empty_record)
    with gzip.open(args.fact, "rt", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            distributor = row["distributor"] or "__MISSING__"
            record = grouped[distributor]
            movement_class = row["movement_class"]
            if movement_class == "confirmed_outward":
                record["rows"] += 1
                record["po_numbers"].add(row["po_number"])
                record["delivered_line_units"] += number(row["delivered_qty"])
                record["delivered_litres"] += number(row["total_delivered_litres"])
                date = row["delivery_date"]
                if date:
                    if record["min_delivery_date"] is None or date < record["min_delivery_date"]:
                        record["min_delivery_date"] = date
                    if record["max_delivery_date"] is None or date > record["max_delivery_date"]:
                        record["max_delivery_date"] = date
            elif movement_class == "quarantine_candidate":
                record["quarantine_rows"] += 1
            else:
                record["no_confirmed_movement_rows"] += 1
    result = {}
    for distributor, record in sorted(grouped.items()):
        serializable = {key: value for key, value in record.items() if key != "po_numbers"}
        serializable["distinct_pos"] = len(record["po_numbers"])
        result[distributor] = serializable
    document = {
        "schema_version": 1,
        "snapshot_date": args.snapshot_date,
        "rule": "Only movement_class=confirmed_outward. Delivered line units are mixed SKU units and must not be treated as a portfolio-wide homogeneous quantity or as litres.",
        "by_distributor": result,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(document, indent=2) + "\n")


if __name__ == "__main__":
    main()
