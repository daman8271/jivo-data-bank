#!/usr/bin/env python3
"""Deterministically validate the Phase 0 intelligence foundation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any
from urllib.parse import urlparse

from jsonschema import Draft202012Validator, FormatChecker

ORCHESTRATION_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_FILES = {
    "authority-registry.v1.schema.json",
    "capability-card.v1.schema.json",
    "evidence-packet.v1.schema.json",
    "ingestion-receipt.v1.schema.json",
    "metrics-registry.v1.schema.json",
    "sources-registry.v1.schema.json",
    "specialists-registry.v1.schema.json",
}
REGISTRY_SCHEMAS = {
    "registry/sources.json": "sources-registry.v1.schema.json",
    "registry/authority.json": "authority-registry.v1.schema.json",
    "registry/metrics.json": "metrics-registry.v1.schema.json",
    "registry/specialists.json": "specialists-registry.v1.schema.json",
}
PLACEHOLDERS = re.compile(r"\b(?:TBD|FIXME|TODO)\b", re.IGNORECASE)
EVIDENCE_REF = re.compile(r"^sha256:[a-f0-9]{64}(?:#[A-Za-z0-9][A-Za-z0-9._:-]{0,127})?$")
SECRET_VALUE_PATTERNS = (
    ("GitHub token", re.compile(r"(?<![A-Za-z0-9_])(?:ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})(?![A-Za-z0-9_])")),
    ("AWS access key", re.compile(r"(?<![A-Z0-9])AKIA[A-Z0-9]{16}(?![A-Z0-9])")),
    ("Slack token", re.compile(r"(?<![A-Za-z0-9-])xox[a-z]-[A-Za-z0-9-]{10,}(?![A-Za-z0-9-])", re.IGNORECASE)),
    ("OpenAI-style key", re.compile(r"(?<![A-Za-z0-9-])sk-[A-Za-z0-9_-]{20,}(?![A-Za-z0-9_-])")),
    ("JWT", re.compile(r"(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}(?![A-Za-z0-9_-])")),
    ("Bearer credential", re.compile(r"\bBearer\s+(?!(?:authentication|token)\b)[A-Za-z0-9._~+/-]{12,}", re.IGNORECASE)),
    ("credential-bearing URL", re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://[^\s/:@]+:[^\s/@]+@[^\s/]+")),
    ("PEM private key", re.compile(r"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----")),
)
SECRET_COMPONENTS = {
    "authorization", "cookie", "credential", "credentials", "jwt", "password",
    "secret", "token",
}
SECRET_KEY_PAIRS = {
    ("access", "token"), ("api", "key"), ("auth", "header"),
    ("authorization", "header"), ("client", "secret"), ("private", "key"),
    ("refresh", "token"), ("bearer", "token"),
}
METRIC_CORE = (
    "metric_id", "label", "lifecycle", "owner_role", "decision_purpose", "grain",
    "formula", "unit", "time_basis", "authority_ids", "freshness_sla", "additivity",
    "reconciliation", "proxy", "display_qualifier", "allowed_dimensions",
)


def _load(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def validate_document(document: Any, schema_name: str, root: Path | None = None) -> None:
    """Validate one document and raise jsonschema.ValidationError on failure."""
    base = Path(root) if root else ORCHESTRATION_ROOT
    schema = _load(base / "contracts" / schema_name)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(document)


def _duplicates(values: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)


def _secret_like_key(key: str) -> bool:
    # Split snake/kebab/space and camelCase names into semantic components. This
    # catches credential-bearing composed names without flagging innocent words
    # such as "tokenizer", "secretariat", or "monkey".
    expanded = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", key)
    parts = [part.lower() for part in re.split(r"[^A-Za-z0-9]+", expanded) if part]
    if any(part in SECRET_COMPONENTS for part in parts):
        return True
    return any(tuple(parts[index:index + 2]) in SECRET_KEY_PAIRS for index in range(len(parts) - 1))


def _secret_value_label(value: Any) -> str | None:
    if isinstance(value, str):
        for label, pattern in SECRET_VALUE_PATTERNS:
            if pattern.search(value):
                return label
    return None


def _contains_secret_value(value: Any) -> bool:
    if _secret_value_label(value) is not None:
        return True
    if isinstance(value, dict):
        return any(_contains_secret_value(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_secret_value(item) for item in value)
    return False


def _scan(value: Any, location: str, failures: list[str], *, scan_keys: bool = True) -> None:
    if isinstance(value, dict):
        for key in sorted(value):
            child_location = f"{location}.{key}"
            if scan_keys and _secret_like_key(key):
                failures.append(f"{child_location}: secret-like key is forbidden")
            if scan_keys and PLACEHOLDERS.search(key):
                failures.append(f"{child_location}: placeholder is forbidden")
            _scan(value[key], child_location, failures, scan_keys=scan_keys)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _scan(item, f"{location}[{index}]", failures, scan_keys=scan_keys)
    elif isinstance(value, str):
        if PLACEHOLDERS.search(value):
            failures.append(f"{location}: placeholder is forbidden")
        label = _secret_value_label(value)
        if label is not None:
            # Report only location and class; never echo secret material.
            failures.append(f"{location}: secret-like value is forbidden ({label})")


def _document_kind(relative: str, document: Any) -> str | None:
    """Classify governed JSON without trusting a partial discriminator."""
    parts = relative.split("/")
    if len(parts) == 2 and parts[0] == "contracts" and parts[1].endswith(".schema.json"):
        return "schema"
    if relative in REGISTRY_SCHEMAS:
        return "registry"
    discriminator = None
    if isinstance(document, dict):
        if "receipt_schema" in document:
            discriminator = document.get("receipt_schema")
        elif "schema" in document:
            discriminator = document.get("schema")
    if not isinstance(discriminator, str):
        return None
    kind = {
        "jivo.ingestion-receipt/v1": "receipt",
        "jivo.evidence-packet/v1": "evidence",
        "jivo.capability-card/v1": "capability",
    }.get(discriminator)
    if relative.startswith("fixtures/valid/"):
        return kind if kind in {"receipt", "evidence"} else None
    return kind


def _schema_errors(document: Any, schema: Any, label: str) -> list[str]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = []
    for error in sorted(validator.iter_errors(document), key=lambda item: list(item.absolute_path)):
        path = ".".join(str(part) for part in error.absolute_path) or "$"
        message = (
            f"value rejected by {error.validator} constraint (details redacted)"
            if _contains_secret_value(error.instance) else error.message
        )
        errors.append(f"{label}:{path}: schema violation: {message}")
    return errors


def _receipt_invariants(receipt: dict[str, Any], label: str) -> list[str]:
    failures: list[str] = []
    if receipt.get("extract_mode") == "incremental":
        if not isinstance(receipt.get("cursor_start"), str) or not receipt["cursor_start"].strip() \
                or not isinstance(receipt.get("cursor_end"), str) or not receipt["cursor_end"].strip():
            failures.append(f"{label}: incremental receipt requires non-empty cursor_start and cursor_end")
    totals = receipt.get("control_totals")
    if isinstance(totals, dict):
        for key in ("source_record_count", "unique_record_count"):
            value = totals.get(key)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                failures.append(f"{label}: receipt requires nonnegative integer {key}")
    if receipt.get("status") == "landed":
        if not isinstance(totals, dict):
            failures.append(f"{label}: landed receipt requires control_totals")
        else:
            if not isinstance(totals.get("completeness_check"), str) or not totals["completeness_check"].strip():
                failures.append(f"{label}: landed receipt requires non-empty completeness_check")
            source_count = totals.get("source_record_count")
            unique_count = totals.get("unique_record_count")
            if isinstance(source_count, int) and not isinstance(source_count, bool) and source_count >= 0:
                if source_count != receipt.get("rows"):
                    failures.append(f"{label}: source_record_count must equal receipt rows")
                if isinstance(unique_count, int) and not isinstance(unique_count, bool) and unique_count > source_count:
                    failures.append(f"{label}: unique_record_count cannot exceed source_record_count")
    for key in ("rows", "bytes"):
        value = receipt.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            failures.append(f"{label}: receipt {key} must be a nonnegative integer")
    if receipt.get("status") == "failed" and receipt.get("cursor_end") is not None:
        failures.append(f"{label}: failed receipt cannot claim cursor_end")
    return failures


def _normalized_receipt_ref(value: Any) -> bool:
    """Return whether value is an immutable, normalized repo-relative JSON path."""
    if not isinstance(value, str) or not value or "\\" in value or "//" in value:
        return False
    if Path(value).is_absolute() or urlparse(value).scheme or "?" in value or "#" in value:
        return False
    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts) or not value.endswith(".json"):
        return False
    # Bare `latest` components are mutable; versioned names merely containing
    # that word are not needlessly prohibited.
    return not any(part.lower() in ("latest", "latest.json") for part in parts)


def _metric_is_monetary(unit: Any) -> bool:
    return isinstance(unit, str) and bool(
        re.search(r"\b(?:currency|amount|INR)\b", unit, re.IGNORECASE)
    )


def _metric_literal_currency(unit: Any) -> str | None:
    if not isinstance(unit, str):
        return None
    match = re.search(r"\b(INR|USD|EUR|GBP|AED|JPY|CNY)\b", unit, re.IGNORECASE)
    return match.group(1).upper() if match else None


def validate_repository(root: Path | str | None = None) -> dict[str, Any]:
    base = Path(root).resolve() if root else ORCHESTRATION_ROOT
    failures: list[str] = []
    warnings: list[str] = []

    paths = sorted(base.rglob("*.json"), key=lambda path: path.relative_to(base).as_posix())
    documents: dict[str, Any] = {}
    for path in paths:
        relative = path.relative_to(base).as_posix()
        try:
            documents[relative] = _load(path)
        except (OSError, json.JSONDecodeError) as exc:
            failures.append(f"{relative}: cannot load JSON: {exc}")

    required = [
        "registry/sources.json", "registry/authority.json", "registry/metrics.json",
        "registry/specialists.json", "fixtures/valid/evidence-packet.json",
        "fixtures/valid/ingestion-receipt.json",
    ] + [f"contracts/{name}" for name in sorted(SCHEMA_FILES)]
    for relative in required:
        if relative not in documents:
            failures.append(f"{relative}: required JSON file is missing")

    schemas: dict[str, Any] = {}
    for name in sorted(SCHEMA_FILES):
        schema = documents.get(f"contracts/{name}")
        if schema is not None:
            schemas[name] = schema
            try:
                Draft202012Validator.check_schema(schema)
            except Exception as exc:
                failures.append(f"contracts/{name}: invalid Draft 2020-12 schema: {exc}")

    document_kinds: dict[str, str] = {}
    for relative, document in sorted(documents.items()):
        kind = _document_kind(relative, document)
        if kind is None:
            discriminator = None
            if isinstance(document, dict):
                discriminator = document.get("receipt_schema", document.get("schema"))
            if discriminator is None:
                failures.append(f"{relative}: unclassified JSON document (missing supported schema discriminator)")
            else:
                failures.append(f"{relative}: unsupported schema discriminator")
        else:
            document_kinds[relative] = kind
            if kind == "schema" and relative.removeprefix("contracts/") not in SCHEMA_FILES:
                try:
                    Draft202012Validator.check_schema(document)
                except Exception as exc:
                    failures.append(f"{relative}: invalid Draft 2020-12 schema: {exc}")

    # Contract property names intentionally describe forbidden runtime fields,
    # but schema string values can still leak credentials and must be scanned.
    for relative, document in sorted(documents.items()):
        _scan(document, relative, failures, scan_keys=not relative.startswith("contracts/"))

    for relative, schema_name in REGISTRY_SCHEMAS.items():
        if relative in documents and schema_name in schemas:
            failures.extend(_schema_errors(documents[relative], schemas[schema_name], relative))

    sources_doc = documents.get("registry/sources.json", {})
    authority_doc = documents.get("registry/authority.json", {})
    metrics_doc = documents.get("registry/metrics.json", {})
    specialists_doc = documents.get("registry/specialists.json", {})
    sources = sources_doc.get("sources", []) if isinstance(sources_doc, dict) else []
    authorities = authority_doc.get("authorities", []) if isinstance(authority_doc, dict) else []
    metrics = metrics_doc.get("metrics", []) if isinstance(metrics_doc, dict) else []
    specialists = specialists_doc.get("specialists", []) if isinstance(specialists_doc, dict) else []

    # Capability cards can also be emitted as standalone governed documents.
    capability_schema = schemas.get("capability-card.v1.schema.json")
    standalone_cards = {
        relative: document for relative, document in documents.items()
        if document_kinds.get(relative) == "capability" and isinstance(document, dict)
    }
    if capability_schema is not None:
        for relative, card in sorted(standalone_cards.items()):
            failures.extend(_schema_errors(card, capability_schema, relative))

    if len(sources) != 7:
        failures.append(f"expected exactly 7 source families, found {len(sources)}")
    if len(specialists) != 7:
        failures.append(f"expected exactly 7 specialists, found {len(specialists)}")
    if len(metrics) != 20:
        failures.append(f"expected exactly 20 metrics, found {len(metrics)}")

    id_groups = [
        ("source_id", [item.get("source_id") for item in sources if isinstance(item, dict)]),
        ("authority_id", [item.get("authority_id") for item in authorities if isinstance(item, dict)]),
        ("metric_id", [item.get("metric_id") for item in metrics if isinstance(item, dict)]),
        ("specialist id", [item.get("id") for item in specialists if isinstance(item, dict)]),
    ]
    for label, ids in id_groups:
        usable = [item for item in ids if isinstance(item, str) and item]
        for duplicate in _duplicates(usable):
            failures.append(f"duplicate {label}: {duplicate}")
        if len(usable) != len(ids):
            failures.append(f"blank or invalid {label}")

    source_by_id = {item.get("source_id"): item for item in sources if isinstance(item, dict)}
    source_ids = set(source_by_id)
    authority_by_id = {item.get("authority_id"): item for item in authorities if isinstance(item, dict)}
    authority_ids = set(authority_by_id)
    metric_by_id = {item.get("metric_id"): item for item in metrics if isinstance(item, dict)}
    metric_ids = set(metric_by_id)

    for source in sources:
        if isinstance(source, dict):
            for duplicate in _duplicates([item for item in source.get("datasets", []) if isinstance(item, str)]):
                failures.append(f"source {source.get('source_id')} has duplicate dataset_id: {duplicate}")

    for authority in authorities:
        if not isinstance(authority, dict):
            failures.append("authority registry contains a non-object")
            continue
        for source_id in authority.get("source_ids", []):
            if source_id not in source_ids:
                failures.append(f"authority {authority.get('authority_id')} references unknown source_id: {source_id}")

    owns: list[str] = []
    for specialist in specialists:
        specialist_id = specialist.get("id", "<unknown>") if isinstance(specialist, dict) else "<unknown>"
        if capability_schema is not None:
            failures.extend(_schema_errors(specialist, capability_schema, f"specialist {specialist_id}"))
        if not isinstance(specialist, dict):
            continue
        owns.extend(specialist.get("owns", []))
        for source_id in specialist.get("source_ids", []):
            if source_id not in source_ids:
                failures.append(f"specialist {specialist_id} references unknown source_id: {source_id}")
        if specialist.get("readiness") == "enabled":
            if specialist.get("writes") is not False:
                failures.append(f"enabled specialist {specialist_id} must have writes false")
            if not specialist.get("source_ids"):
                failures.append(f"enabled specialist {specialist_id} must have source IDs")
            for source_id in specialist.get("source_ids", []):
                if source_by_id.get(source_id, {}).get("readiness") != "ready":
                    failures.append(f"enabled specialist {specialist_id} source is not ready: {source_id}")
    for duplicate in _duplicates(owns):
        failures.append(f"overlapping specialist owns string: {duplicate}")

    for metric in metrics:
        if not isinstance(metric, dict):
            failures.append("metrics registry contains a non-object")
            continue
        metric_id = metric.get("metric_id", "<unknown>")
        missing = [field for field in METRIC_CORE if field not in metric]
        if missing:
            failures.append(f"metric {metric_id} missing core metadata: {', '.join(missing)}")
        for authority_id in metric.get("authority_ids", []):
            if authority_id not in authority_ids:
                failures.append(f"metric {metric_id} references unknown authority_id: {authority_id}")
        if metric.get("proxy") is True and not str(metric.get("display_qualifier", "")).strip():
            failures.append(f"proxy metric {metric_id} requires explicit display qualifier")

    evidence_schema = schemas.get("evidence-packet.v1.schema.json")
    receipt_schema = schemas.get("ingestion-receipt.v1.schema.json")
    receipts = {
        relative: document for relative, document in documents.items()
        if document_kinds.get(relative) == "receipt" and isinstance(document, dict)
    }
    evidences = {
        relative: document for relative, document in documents.items()
        if document_kinds.get(relative) == "evidence" and isinstance(document, dict)
    }

    # Receipt run IDs identify ingestion executions globally. Dataset IDs remain
    # source-scoped, and evidence packets may legitimately re-use receipt runs.
    receipt_run_paths: dict[str, list[str]] = {}
    for relative, receipt in sorted(receipts.items()):
        if isinstance(receipt.get("run_id"), str):
            receipt_run_paths.setdefault(receipt["run_id"], []).append(relative)
        if receipt_schema is not None:
            failures.extend(_schema_errors(receipt, receipt_schema, relative))
        source_id = receipt.get("source_id")
        if source_id not in source_ids:
            failures.append(f"{relative}: receipt references unknown source_id: {source_id}")
        elif receipt.get("dataset_id") not in source_by_id[source_id].get("datasets", []):
            failures.append(f"{relative}: receipt references unknown dataset_id for {source_id}: {receipt.get('dataset_id')}")
        failures.extend(_receipt_invariants(receipt, relative))
    for run_id, receipt_paths in sorted(receipt_run_paths.items()):
        if len(receipt_paths) > 1:
            failures.append(f"duplicate ingestion receipt run_id: {run_id} ({', '.join(receipt_paths)})")

    for relative, evidence in sorted(evidences.items()):
        if evidence_schema is not None:
            failures.extend(_schema_errors(evidence, evidence_schema, relative))
        runs = [run for run in evidence.get("source_runs", []) if isinstance(run, dict)]
        run_ids: list[str] = []
        for run in runs:
            run_id = run.get("run_id")
            if isinstance(run_id, str):
                run_ids.append(run_id)
        for duplicate in _duplicates(run_ids):
            failures.append(f"{relative}: duplicate source-run run_id: {duplicate}")
        run_by_id = {run.get("run_id"): run for run in runs}
        for run in runs:
            source_id = run.get("source_id")
            if source_id not in source_ids:
                failures.append(f"{relative}: evidence references unknown source_id: {source_id}")
            elif run.get("dataset_id") not in source_by_id[source_id].get("datasets", []):
                failures.append(f"{relative}: evidence references unknown dataset_id for {source_id}: {run.get('dataset_id')}")
            ref = run.get("receipt_ref")
            if not _normalized_receipt_ref(ref):
                failures.append(
                    f"{relative}: receipt_ref is not a normalized immutable "
                    f"repository-relative JSON path: {ref}"
                )
            else:
                assert isinstance(ref, str)  # narrowed by _normalized_receipt_ref
                target = (base / ref).resolve()
                if not target.is_relative_to(base):
                    failures.append(f"{relative}: receipt_ref escapes repository root: {ref}")
                else:
                    target_relative = target.relative_to(base).as_posix()
                    target_doc = documents.get(target_relative)
                    if target_doc is None:
                        failures.append(f"{relative}: receipt_ref target does not exist: {ref}")
                    elif not isinstance(target_doc, dict) or target_doc.get("receipt_schema") != "jivo.ingestion-receipt/v1":
                        failures.append(f"{relative}: receipt_ref target is not an ingestion receipt: {ref}")
                    else:
                        for field in ("source_id", "dataset_id", "run_id"):
                            if target_doc.get(field) != run.get(field):
                                failures.append(f"{relative}: receipt_ref {field} mismatch: {ref}")
        for finding in evidence.get("findings", []):
            if not isinstance(finding, dict):
                continue
            metric_id = finding.get("metric_id")
            authority_id = finding.get("authority_id")
            for ref in finding.get("evidence_refs", []):
                if not isinstance(ref, str) or not EVIDENCE_REF.fullmatch(ref):
                    failures.append(
                        f"{relative}: finding evidence_ref must be content-addressed "
                        "sha256 with optional safe fragment"
                    )
            if metric_id is not None and metric_id not in metric_ids:
                failures.append(f"{relative}: evidence references unknown metric_id: {metric_id}")
            if authority_id not in authority_ids:
                failures.append(f"{relative}: evidence references unknown authority_id: {authority_id}")
            finding_runs = [run_by_id.get(run_id) for run_id in finding.get("source_run_ids", [])]
            for run_id, run in zip(finding.get("source_run_ids", []), finding_runs):
                if run is None:
                    failures.append(f"{relative}: evidence finding references unknown source run_id: {run_id}")
            if metric_id in metric_by_id and authority_id not in metric_by_id[metric_id].get("authority_ids", []):
                failures.append(f"{relative}: finding authority_id is not compatible with metric {metric_id}: {authority_id}")
            if authority_id in authority_by_id:
                finding_sources = {
                    run.get("source_id") for run in finding_runs
                    if isinstance(run, dict) and isinstance(run.get("source_id"), str)
                }
                authority_sources = set(authority_by_id[authority_id].get("source_ids", []))
                disallowed_sources = sorted(finding_sources - authority_sources)
                if disallowed_sources:
                    failures.append(
                        f"{relative}: finding authority {authority_id} does not allow "
                        f"source(s): {', '.join(disallowed_sources)}"
                    )
            if metric_id in metric_by_id:
                metric = metric_by_id[metric_id]
                for field in ("grain", "unit", "time_basis"):
                    if finding.get(field) != metric.get(field):
                        failures.append(f"{relative}: finding {field} does not match metric contract {metric_id}")
                currency = finding.get("currency")
                if _metric_is_monetary(metric.get("unit")):
                    if not isinstance(currency, str) or not currency.strip():
                        failures.append(f"{relative}: monetary metric {metric_id} requires non-null currency")
                    literal_currency = _metric_literal_currency(metric.get("unit"))
                    if literal_currency and isinstance(currency, str) and currency.upper() != literal_currency:
                        failures.append(f"{relative}: finding currency must match metric contract currency {literal_currency}")
                elif currency is not None:
                    failures.append(f"{relative}: non-monetary metric {metric_id} requires null currency")

    planned = sum(1 for source in sources if isinstance(source, dict) and source.get("readiness") != "ready")
    if planned:
        warnings.append(f"{planned} source family/families are explicitly not ready")

    failures = sorted(set(failures))
    warnings = sorted(set(warnings))
    return {
        "status": "PASS" if not failures else "FAIL",
        "counts": {
            "authorities": len(authorities),
            "evidence_packets": len(evidences),
            "ingestion_receipts": len(receipts),
            "json_files": len(documents),
            "metrics": len(metrics),
            "schemas": len(schemas),
            "sources": len(sources),
            "specialists": len(specialists),
            "valid_fixtures": sum(1 for name in documents if name.startswith("fixtures/valid/")),
        },
        "warnings": warnings,
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ORCHESTRATION_ROOT, help="orchestration foundation root")
    args = parser.parse_args()
    result = validate_repository(args.root)
    print(json.dumps(result, indent=2, sort_keys=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
