#!/usr/bin/env python3
"""Fail-closed checks for the protected distributor-inventory intelligence domain."""
from __future__ import annotations

import csv
import gzip
import hashlib
import importlib.util
import json
import tempfile
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SNAPSHOT = "2026-07-17"
RAW = BASE / "raw" / SNAPSHOT / "master-po-gid-739390425.csv.gz"
FACT = BASE / "normalized" / f"fact-distributor-po-line-{SNAPSHOT}.csv.gz"
PROFILE = BASE / "quality" / f"master-po-profile-{SNAPSHOT}.json"
RECEIPT = BASE / "raw" / SNAPSHOT / "master-po-receipt.json"
REGISTRY = BASE / "source-registry.json"
REFERENCE_MANIFEST = BASE / "raw" / SNAPSHOT / "reference-tabs" / "reference-tabs-manifest.json"
DERIVED = BASE / "derived" / f"confirmed-outward-summary-{SNAPSHOT}.json"
FUTURE_DATA = BASE / "future-data-register.json"
LIVE_COMPARISON = BASE / "quality" / f"master-po-vs-live-{SNAPSHOT}.json"
WORKBOOK_STRUCTURE = BASE / "quality" / f"workbook-structure-{SNAPSHOT}.json"
EXPECTED_RAW_HEADER = [
    " ", "PO Date", "PO Expiry Date", "Delivery Date", "Vendor Name", "Status", "Remarks",
    "SKU Code", "SKU Name", "Order Qty", "Delivered Qty", "Basic Rate", "landing Rate", "Location",
    "Format", "Lead Time", "Days To Expiry", "Po Window", "PO Status", "Item Status", "Vendor_New",
    "ITEM", "SAP SKU NAME", "SAP SKU Code", "Category", "Sub Category", "Case Pack", "Per Liter",
    "Total Order Liters", "Total Delivered Liters", "Total Order Amt (INCLUSIVE)",
    "Total Deliver Amt (INCLUSIVE)", "PO Month", "Delivery Month", "PO YEAR", "DEL YEAR", "Item Head",
    "City", "State", "Distributor Margin", "Realise", "Distributor Commision Per Unit",
    "Total Distributor Commission", "Brand", "Category Head", "Unit of Measure", "Open/Close",
    "TOTAL ORDER AMT (EXCLUSIVE)", "TOTAL DELIVERED AMT EXCLUSIVE", "TOTAL ORDER AMT (WITHOUT MARGIN)",
    "TOTAL DELIVERED AMT (WITHOUT MARGIN)", "MISSED QTY", "FILLED QTY", "MISSED LTRS", "FILLED LTRS",
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_builder():
    path = BASE / "scripts" / "build_snapshot.py"
    spec = importlib.util.spec_from_file_location("build_snapshot", path)
    if spec is None or spec.loader is None:
        raise AssertionError("cannot import build_snapshot.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    errors: list[str] = []
    warnings: list[str] = []
    for path in [
        RAW, FACT, PROFILE, RECEIPT, REGISTRY, REFERENCE_MANIFEST,
        DERIVED, FUTURE_DATA, LIVE_COMPARISON, WORKBOOK_STRUCTURE,
    ]:
        if not path.is_file():
            errors.append(f"missing: {path.relative_to(BASE)}")
    if errors:
        raise SystemExit("FAIL\n" + "\n".join(errors))

    registry = json.loads(REGISTRY.read_text())
    source_ids = [s["source_id"] for s in registry["sources"]]
    if len(source_ids) != len(set(source_ids)) or len(source_ids) != 3:
        errors.append("source registry must contain three unique sources")
    for source in registry["sources"]:
        if source.get("last_http_status") == 401 and source.get("last_success"):
            errors.append(f"401 source incorrectly marked successful: {source['source_id']}")

    receipt = json.loads(RECEIPT.read_text())
    profile = json.loads(PROFILE.read_text())
    derived = json.loads(DERIVED.read_text())
    future_data = json.loads(FUTURE_DATA.read_text())
    live_comparison = json.loads(LIVE_COMPARISON.read_text())
    workbook_structure = json.loads(WORKBOOK_STRUCTURE.read_text())
    if derived.get("snapshot_date") != SNAPSHOT or not derived.get("by_distributor"):
        errors.append("derived confirmed-outward summary is invalid")
    if not future_data.get("datasets"):
        errors.append("future-data register is empty")
    if live_comparison.get("sheet_rows") != 47438:
        errors.append("live comparison does not match source row count")
    if len(workbook_structure.get("sheets", [])) != 22:
        errors.append("workbook structure does not contain 22 inspected tabs")
    if receipt["http_status"] != 200 or receipt["validation"] != "pass":
        errors.append("MASTER PO receipt is not a validated HTTP 200 source")
    if sha(RAW) != receipt["raw_sha256"] or sha(RAW) != profile["raw"]["sha256"]:
        errors.append("raw hash does not match receipt/profile")
    if sha(FACT) != profile["normalized"]["sha256"]:
        errors.append("normalized fact hash does not match profile")

    with gzip.open(RAW, "rt", encoding="utf-8-sig", newline="") as raw_f, gzip.open(
        FACT, "rt", encoding="utf-8", newline=""
    ) as fact_f:
        raw_reader = csv.reader(raw_f)
        fact_reader = csv.DictReader(fact_f)
        raw_header = next(raw_reader)
        if raw_header != EXPECTED_RAW_HEADER:
            errors.append("raw header/schema changed")
        expected_line = 2
        raw_count = fact_count = 0
        hash_occurrence = Counter()
        allowed_classes = {"confirmed_outward", "quarantine_candidate", "no_confirmed_movement"}
        for raw_cells, fact in zip(raw_reader, fact_reader):
            raw_count += 1
            fact_count += 1
            if int(fact["source_row_number"]) != expected_line:
                errors.append(f"lineage break at normalized row {fact_count}")
                break
            expected_hash = hashlib.sha256(
                json.dumps(raw_cells, ensure_ascii=False, separators=(",", ":")).encode()
            ).hexdigest()
            hash_occurrence[expected_hash] += 1
            if fact["source_row_sha256"] != expected_hash:
                errors.append(f"row hash mismatch at source row {expected_line}")
                break
            if int(fact["source_duplicate_ordinal"]) != hash_occurrence[expected_hash]:
                errors.append(f"duplicate ordinal mismatch at source row {expected_line}")
                break
            if fact["movement_class"] not in allowed_classes:
                errors.append(f"invalid movement class at source row {expected_line}")
                break
            expected_line += 1
        if next(raw_reader, None) is not None or next(fact_reader, None) is not None:
            errors.append("raw and normalized row counts differ")
    if raw_count != receipt["row_count"] or raw_count != profile["counts"]["rows"]:
        errors.append("row counts disagree across raw/receipt/profile")
    if raw_count < 47000:
        errors.append("unexpected row-count regression below 47,000")

    reference = json.loads(REFERENCE_MANIFEST.read_text())
    for tab in reference["tabs"].values():
        path = REFERENCE_MANIFEST.parent / tab["file"]
        if not path.is_file():
            errors.append(f"missing reference tab: {tab['file']}")
        else:
            try:
                with gzip.open(path, "rb") as fh:
                    fh.read(1024)
            except Exception as exc:
                errors.append(f"invalid gzip reference tab {tab['file']}: {exc}")

    builder = load_builder()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        fact2 = tmp_path / "fact.csv.gz"
        builder.build(RAW, fact2, tmp_path / "profile.json", tmp_path / "receipt.json")
        if sha(fact2) != sha(FACT):
            errors.append("determinism failure: same raw input produced a different normalized fact")

    known_warnings = profile["counts"]["quality_flags"]
    for key in ["delivered_gt_order", "delivery_before_po", "missing_sap_sku_code"]:
        if known_warnings.get(key, 0):
            warnings.append(f"{key}={known_warnings[key]}")

    if errors:
        raise SystemExit("FAIL\n" + "\n".join(errors))
    print(json.dumps({
        "status": "PASS",
        "raw_rows": raw_count,
        "normalized_rows": fact_count,
        "raw_sha256": sha(RAW),
        "fact_sha256": sha(FACT),
        "warnings": warnings,
    }, indent=2))


if __name__ == "__main__":
    main()
