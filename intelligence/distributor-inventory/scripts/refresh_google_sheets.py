#!/usr/bin/env python3
"""Probe/fetch registered Google Sheet tabs without storing login HTML as data.

This script never commits, resets, cleans, or pushes Git. Use --probe-only to test
access. Successful CSV snapshots are immutable; an existing different hash aborts.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
REGISTRY = BASE / "source-registry.json"


def is_html(data: bytes, content_type: str) -> bool:
    prefix = data[:512].lstrip().lower()
    return "text/html" in content_type.lower() or prefix.startswith(b"<!doctype html") or prefix.startswith(b"<html")


def gzip_deterministic(data: bytes, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", compresslevel=9, mtime=0) as gz:
        gz.write(data)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot-date", default=datetime.now(timezone.utc).date().isoformat())
    parser.add_argument("--probe-only", action="store_true")
    args = parser.parse_args()
    registry = json.loads(REGISTRY.read_text())
    attempt = {
        "schema_version": 1,
        "attempted_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "snapshot_date": args.snapshot_date,
        "probe_only": args.probe_only,
        "sources": [],
    }
    required_failure = False
    master_raw: Path | None = None
    for source in registry["sources"]:
        if not source.get("document_id") or not source.get("gid"):
            continue
        url = (
            f"https://docs.google.com/spreadsheets/d/{source['document_id']}"
            f"/gviz/tq?tqx=out:csv&gid={source['gid']}"
        )
        result = {"source_id": source["source_id"], "status": None, "valid_csv": False}
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "JIVO-Data-Bank/1.0"})
            with urllib.request.urlopen(request, timeout=90) as response:
                data = response.read()
                status = response.status
                content_type = response.headers.get("Content-Type", "")
            result.update({"status": status, "content_type": content_type, "bytes": len(data)})
            if status != 200 or is_html(data, content_type):
                raise ValueError("response is not a valid CSV export")
            text = data.decode("utf-8-sig")
            reader = csv.reader(io.StringIO(text))
            header = next(reader)
            row_count = sum(1 for _ in reader)
            if source.get("expected_columns") and len(header) != source["expected_columns"]:
                raise ValueError(f"expected {source['expected_columns']} columns, got {len(header)}")
            if source.get("minimum_rows") and row_count < source["minimum_rows"]:
                raise ValueError(f"row count {row_count} below minimum {source['minimum_rows']}")
            result.update({
                "valid_csv": True,
                "sha256_uncompressed": hashlib.sha256(data).hexdigest(),
                "rows": row_count,
                "columns": len(header),
            })
            if not args.probe_only:
                path = BASE / "raw" / args.snapshot_date / f"{source['source_id']}.csv.gz"
                if path.exists():
                    with gzip.open(path, "rb") as fh:
                        existing = fh.read()
                    if existing != data:
                        raise ValueError(f"immutable snapshot collision at {path}")
                else:
                    gzip_deterministic(data, path)
                result["raw_path"] = str(path.relative_to(BASE))
                if source["source_id"] == "google-master-po-gid-739390425":
                    master_raw = path
        except urllib.error.HTTPError as exc:
            result.update({"status": exc.code, "error": "access denied or unavailable; response body not stored"})
            if source.get("required_for_current_build"):
                required_failure = True
        except Exception as exc:
            result["error"] = str(exc)
            if source.get("required_for_current_build"):
                required_failure = True
        attempt["sources"].append(result)

    if not args.probe_only:
        quality = BASE / "quality"
        quality.mkdir(parents=True, exist_ok=True)
        attempt_path = quality / f"refresh-attempt-{args.snapshot_date}.json"
        attempt_path.write_text(json.dumps(attempt, indent=2) + "\n")
        if master_raw is not None and not required_failure:
            fact_path = BASE / "normalized" / f"fact-distributor-po-line-{args.snapshot_date}.csv.gz"
            subprocess.run([
                sys.executable, str(BASE / "scripts" / "build_snapshot.py"),
                "--raw-csv", str(master_raw),
                "--out", str(fact_path),
                "--profile", str(BASE / "quality" / f"master-po-profile-{args.snapshot_date}.json"),
                "--receipt", str(BASE / "raw" / args.snapshot_date / "master-po-receipt.json"),
                "--snapshot-date", args.snapshot_date,
                "--source-id", "google-master-po-gid-739390425",
                "--retrieved-at-utc", attempt["attempted_at_utc"],
            ], check=True)
            subprocess.run([
                sys.executable, str(BASE / "scripts" / "build_confirmed_outward_summary.py"),
                "--fact", str(fact_path),
                "--out", str(BASE / "derived" / f"confirmed-outward-summary-{args.snapshot_date}.json"),
                "--snapshot-date", args.snapshot_date,
            ], check=True)
    print(json.dumps(attempt, indent=2))
    if required_failure:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
