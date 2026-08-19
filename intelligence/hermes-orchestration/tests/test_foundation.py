import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest
from jsonschema import ValidationError

HERE = Path(__file__).resolve()
ORCH = HERE.parents[1]
SPEC = importlib.util.spec_from_file_location("validate_foundation", ORCH / "tools" / "validate_foundation.py")
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


def load(name):
    return json.loads((ORCH / "fixtures" / "valid" / name).read_text())


def temp_foundation(tmp_path):
    destination = tmp_path / "intelligence" / "hermes-orchestration"
    shutil.copytree(ORCH, destination, ignore=shutil.ignore_patterns("__pycache__"))
    return destination


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def assert_failure(result, text):
    assert result["status"] == "FAIL"
    assert any(text in item for item in result["failures"]), result


def test_repository_validation_success():
    result = validator.validate_repository(ORCH)
    assert result["status"] == "PASS", result
    assert result["counts"]["metrics"] == 20
    assert result["counts"]["sources"] == 7
    assert result["counts"]["specialists"] == 7
    assert result["counts"]["schemas"] == 7
    assert result["failures"] == []


def test_unknown_source_in_fixture(tmp_path):
    root = temp_foundation(tmp_path)
    path = root / "fixtures" / "valid" / "ingestion-receipt.json"
    value = json.loads(path.read_text())
    value["source_id"] = "unknown-source"
    write_json(path, value)
    assert_failure(validator.validate_repository(root), "unknown source_id")


def test_recursive_secret_key(tmp_path):
    root = temp_foundation(tmp_path)
    path = root / "fixtures" / "valid" / "ingestion-receipt.json"
    value = json.loads(path.read_text())
    value["parameters_redacted"] = {"nested": {"api_key": "sanitized-but-forbidden-key"}}
    write_json(path, value)
    assert_failure(validator.validate_repository(root), "secret-like key")


def test_more_than_ten_findings_rejected():
    value = load("evidence-packet.json")
    value["findings"] = [copy.deepcopy(value["findings"][0]) for _ in range(11)]
    with pytest.raises(ValidationError):
        validator.validate_document(value, "evidence-packet.v1.schema.json")


def test_invalid_hash_rejected():
    value = load("ingestion-receipt.json")
    value["sha256"] = "not-a-sha"
    with pytest.raises(ValidationError):
        validator.validate_document(value, "ingestion-receipt.v1.schema.json")


def test_incremental_receipt_requires_cursors(tmp_path):
    root = temp_foundation(tmp_path)
    path = root / "fixtures" / "valid" / "ingestion-receipt.json"
    value = json.loads(path.read_text())
    value["cursor_start"] = None
    write_json(path, value)
    assert_failure(validator.validate_repository(root), "incremental receipt requires")


def test_failed_receipt_cannot_claim_cursor_end(tmp_path):
    root = temp_foundation(tmp_path)
    path = root / "fixtures" / "valid" / "ingestion-receipt.json"
    value = json.loads(path.read_text())
    value["status"] = "failed"
    write_json(path, value)
    assert_failure(validator.validate_repository(root), "failed receipt cannot claim cursor_end")


def test_proxy_metric_requires_qualifier(tmp_path):
    root = temp_foundation(tmp_path)
    path = root / "registry" / "metrics.json"
    value = json.loads(path.read_text())
    metric = next(metric for metric in value["metrics"] if metric["proxy"])
    metric["display_qualifier"] = ""
    write_json(path, value)
    assert_failure(validator.validate_repository(root), "proxy metric")


def test_duplicate_ids_rejected(tmp_path):
    root = temp_foundation(tmp_path)
    path = root / "registry" / "sources.json"
    value = json.loads(path.read_text())
    value["sources"].append(copy.deepcopy(value["sources"][0]))
    write_json(path, value)
    assert_failure(validator.validate_repository(root), "duplicate source_id")


@pytest.mark.parametrize("registry,key,expected", [
    ("sources.json", "sources", "exactly 7 source"),
    ("specialists.json", "specialists", "exactly 7 specialists"),
    ("metrics.json", "metrics", "exactly 20 metrics"),
])
def test_exact_registry_counts(tmp_path, registry, key, expected):
    root = temp_foundation(tmp_path)
    path = root / "registry" / registry
    value = json.loads(path.read_text())
    value[key].pop()
    write_json(path, value)
    assert_failure(validator.validate_repository(root), expected)


def test_duplicate_dataset_id_per_source_rejected(tmp_path):
    root = temp_foundation(tmp_path)
    path = root / "registry" / "sources.json"
    value = json.loads(path.read_text())
    value["sources"][0]["datasets"].append(value["sources"][0]["datasets"][0])
    write_json(path, value)
    assert_failure(validator.validate_repository(root), "duplicate dataset_id")


def test_duplicate_source_run_id_rejected(tmp_path):
    root = temp_foundation(tmp_path)
    path = root / "fixtures" / "valid" / "evidence-packet.json"
    value = json.loads(path.read_text())
    value["source_runs"].append(copy.deepcopy(value["source_runs"][0]))
    write_json(path, value)
    assert_failure(validator.validate_repository(root), "duplicate source-run run_id")


@pytest.mark.parametrize("mutation,expected", [
    (lambda doc: doc.update({"unexpected": True}), "Additional properties"),
    (lambda doc: doc["sources"][0].pop("owner_role"), "owner_role"),
])
def test_source_registry_schema_rejects_unknown_or_missing_metadata(tmp_path, mutation, expected):
    root = temp_foundation(tmp_path)
    path = root / "registry" / "sources.json"
    value = json.loads(path.read_text())
    mutation(value)
    write_json(path, value)
    assert_failure(validator.validate_repository(root), expected)


@pytest.mark.parametrize("registry", ["authority.json", "metrics.json"])
def test_registry_envelopes_reject_unknown_fields(tmp_path, registry):
    root = temp_foundation(tmp_path)
    path = root / "registry" / registry
    value = json.loads(path.read_text())
    value["unknown_governed_field"] = "no"
    write_json(path, value)
    assert_failure(validator.validate_repository(root), "Additional properties")


def test_placeholder_rejected(tmp_path):
    root = temp_foundation(tmp_path)
    path = root / "registry" / "authority.json"
    value = json.loads(path.read_text())
    value["authorities"][0]["process"] = "TODO later"
    write_json(path, value)
    assert_failure(validator.validate_repository(root), "placeholder is forbidden")


@pytest.mark.parametrize("key", [
    "db_password", "session_cookie", "access_token", "client_secret", "auth_header",
    "private_key", "api_key", "refresh_token", "bearer_token", "oauthAccessToken",
    "service-client-secret",
])
def test_composed_secret_keys_rejected(tmp_path, key):
    root = temp_foundation(tmp_path)
    path = root / "fixtures" / "valid" / "ingestion-receipt.json"
    value = json.loads(path.read_text())
    value["parameters_redacted"] = {"nested": {key: "redacted"}}
    write_json(path, value)
    assert_failure(validator.validate_repository(root), "secret-like key")


def test_innocent_secret_substrings_are_not_rejected(tmp_path):
    root = temp_foundation(tmp_path)
    path = root / "fixtures" / "valid" / "ingestion-receipt.json"
    value = json.loads(path.read_text())
    value["parameters_redacted"] = {
        "tokenizer_version": "v1", "secretariat_scope": "public", "monkey_species": "rhesus"
    }
    write_json(path, value)
    assert validator.validate_repository(root)["status"] == "PASS"


def test_enabled_specialist_cannot_write_or_use_nonready_source(tmp_path):
    root = temp_foundation(tmp_path)
    path = root / "registry" / "specialists.json"
    value = json.loads(path.read_text())
    specialist = value["specialists"][0]
    specialist["writes"] = True
    specialist["source_ids"] = ["sap-b1"]
    write_json(path, value)
    result = validator.validate_repository(root)
    assert_failure(result, "must have writes false")
    assert any("source is not ready" in failure for failure in result["failures"])


def test_every_discriminated_json_document_is_validated(tmp_path):
    root = temp_foundation(tmp_path)
    value = json.loads((root / "fixtures" / "valid" / "ingestion-receipt.json").read_text())
    value["sha256"] = "bad"
    write_json(root / "arbitrary-receipt-name.json", value)
    assert_failure(validator.validate_repository(root), "arbitrary-receipt-name.json:sha256")


@pytest.mark.parametrize("mode,expected", [
    ("missing", "target does not exist"),
    ("mismatch", "receipt_ref run_id mismatch"),
])
def test_receipt_reference_resolution_fails_closed(tmp_path, mode, expected):
    root = temp_foundation(tmp_path)
    path = root / "fixtures" / "valid" / "evidence-packet.json"
    value = json.loads(path.read_text())
    if mode == "missing":
        value["source_runs"][0]["receipt_ref"] = "fixtures/valid/missing.json"
    else:
        value["source_runs"][0]["run_id"] = "01JIVOEXAMPLE000000000099"
    write_json(path, value)
    assert_failure(validator.validate_repository(root), expected)


def test_finding_authority_must_match_metric_and_sources(tmp_path):
    root = temp_foundation(tmp_path)
    path = root / "fixtures" / "valid" / "evidence-packet.json"
    value = json.loads(path.read_text())
    value["findings"][0]["authority_id"] = "auth-ecom-availability-v1"
    write_json(path, value)
    result = validator.validate_repository(root)
    assert_failure(result, "not compatible with metric")
    assert any("does not allow source" in failure for failure in result["failures"])


@pytest.mark.parametrize("change,expected", [
    ({"cursor_start": ""}, "non-empty cursor_start"),
    ({"control_totals": {"completeness_check": "", "source_record_count": 20, "unique_record_count": 20}}, "non-empty completeness_check"),
    ({"control_totals": {"completeness_check": "ok", "source_record_count": "20", "unique_record_count": 20}}, "nonnegative integer source_record_count"),
    ({"control_totals": {"completeness_check": "ok", "source_record_count": 19, "unique_record_count": 19}}, "must equal receipt rows"),
    ({"control_totals": {"completeness_check": "ok", "source_record_count": 20, "unique_record_count": 21}}, "cannot exceed source_record_count"),
])
def test_landed_receipt_completeness_invariants(tmp_path, change, expected):
    root = temp_foundation(tmp_path)
    path = root / "fixtures" / "valid" / "ingestion-receipt.json"
    value = json.loads(path.read_text())
    value.update(change)
    write_json(path, value)
    assert_failure(validator.validate_repository(root), expected)


@pytest.mark.parametrize("field", ["unit", "currency", "time_basis"])
def test_findings_require_self_describing_measure_fields(field):
    value = load("evidence-packet.json")
    value["findings"][0].pop(field)
    with pytest.raises(ValidationError):
        validator.validate_document(value, "evidence-packet.v1.schema.json")


def test_daily_rebuild_shell_syntax_and_clean_exclusions(tmp_path):
    repo = ORCH.parents[1]
    script = repo / "bin" / "daily_rebuild.sh"
    subprocess.run(["bash", "-n", str(script)], check=True)
    text = script.read_text()
    for protected in ("AGENTS.md", "DATA-PLATFORM-ARCHITECTURE.md", "intelligence", "bin", "reports"):
        assert protected in text

    combined = tmp_path / "combined"
    sync_repo = tmp_path / "sync-repo"
    combined.mkdir()
    sync_repo.mkdir()
    (sync_repo / ".jdb-test-fixture").touch()
    for relative in (
        "AGENTS.md", "DATA-PLATFORM-ARCHITECTURE.md", "intelligence/card.json",
        "bin/wrapper.sh", "reports/local/report.txt",
    ):
        target = sync_repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("protected\n")
    (sync_repo / "unprotected.txt").write_text("delete me\n")
    subprocess.run(
        ["bash", str(script), "--test-sync-protection"], check=True,
        env={**os.environ, "JDB_TEST_HOOKS": "1", "JDB_REPO": str(sync_repo), "JDB_COMBINED": str(combined)},
    )
    assert not (sync_repo / "unprotected.txt").exists()
    assert all((sync_repo / relative).exists() for relative in (
        "AGENTS.md", "DATA-PLATFORM-ARCHITECTURE.md", "intelligence/card.json",
        "bin/wrapper.sh", "reports/local/report.txt",
    ))

    rollback_repo = tmp_path / "rollback-repo"
    rollback_repo.mkdir()
    (rollback_repo / ".jdb-test-fixture").touch()
    subprocess.run(["git", "init", "-q"], cwd=rollback_repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=rollback_repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=rollback_repo, check=True)
    for relative in ("DATA-PLATFORM-ARCHITECTURE.md", "bin/wrapper.sh", "generated.txt"):
        target = rollback_repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("baseline\n")
    subprocess.run(["git", "add", "."], cwd=rollback_repo, check=True)
    subprocess.run(["git", "commit", "-qm", "baseline"], cwd=rollback_repo, check=True)
    (rollback_repo / "DATA-PLATFORM-ARCHITECTURE.md").write_text("approved local architecture\n")
    (rollback_repo / "bin/wrapper.sh").write_text("approved local wrapper\n")
    (rollback_repo / "generated.txt").write_text("bad generated state\n")
    for relative in ("AGENTS.md", "intelligence/card.json", "reports/local/report.txt"):
        target = rollback_repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("protected local\n")
    (rollback_repo / "unrelated.tmp").write_text("clean me\n")
    subprocess.run(
        ["bash", str(script), "--test-rollback-protection"], check=True,
        env={**os.environ, "JDB_TEST_HOOKS": "1", "JDB_REPO": str(rollback_repo), "JDB_COMBINED": str(combined)},
    )
    assert (rollback_repo / "DATA-PLATFORM-ARCHITECTURE.md").read_text() == "approved local architecture\n"
    assert (rollback_repo / "bin/wrapper.sh").read_text() == "approved local wrapper\n"
    assert (rollback_repo / "generated.txt").read_text() == "baseline\n"
    assert not (rollback_repo / "unrelated.tmp").exists()
    assert all((rollback_repo / relative).exists() for relative in (
        "AGENTS.md", "intelligence/card.json", "reports/local/report.txt",
    ))


def test_duplicate_receipt_run_id_rejected_but_evidence_reuse_allowed(tmp_path):
    root = temp_foundation(tmp_path)
    receipt = json.loads((root / "fixtures/valid/ingestion-receipt.json").read_text())
    write_json(root / "fixtures/valid/duplicate-receipt.json", receipt)
    assert_failure(validator.validate_repository(root), "duplicate ingestion receipt run_id")

    (root / "fixtures/valid/duplicate-receipt.json").unlink()
    evidence = json.loads((root / "fixtures/valid/evidence-packet.json").read_text())
    evidence["packet_id"] = "fixture:dispatch:second"
    # Re-use of one ingestion run by independent evidence packets is legitimate.
    write_json(root / "fixtures/valid/second-evidence.json", evidence)
    assert validator.validate_repository(root)["status"] == "PASS"


def test_dataset_ids_are_source_scoped_not_globally_unique(tmp_path):
    root = temp_foundation(tmp_path)
    path = root / "registry/sources.json"
    value = json.loads(path.read_text())
    shared_dataset_id = value["sources"][0]["datasets"][0]
    assert shared_dataset_id not in value["sources"][1]["datasets"]
    value["sources"][1]["datasets"].append(shared_dataset_id)
    write_json(path, value)
    # Dataset IDs intentionally need uniqueness only inside their source family.
    assert validator.validate_repository(root)["status"] == "PASS"


@pytest.mark.parametrize("location", ["envelope", "entry"])
def test_specialists_registry_schema_is_closed(tmp_path, location):
    root = temp_foundation(tmp_path)
    path = root / "registry/specialists.json"
    value = json.loads(path.read_text())
    target = value if location == "envelope" else value["specialists"][0]
    target["unknown_governed_field"] = True
    write_json(path, value)
    assert_failure(validator.validate_repository(root), "Additional properties")


def test_standalone_discriminated_capability_card_is_validated(tmp_path):
    root = temp_foundation(tmp_path)
    registry = json.loads((root / "registry/specialists.json").read_text())
    card = copy.deepcopy(registry["specialists"][0])
    card["writes"] = True
    write_json(root / "standalone-card.json", card)
    assert_failure(validator.validate_repository(root), "standalone-card.json:writes")


@pytest.mark.parametrize("ref", [
    "/tmp/receipt.json", "https://example.invalid/receipt.json", "../receipt.json",
    "fixtures/./receipt.json", "fixtures//receipt.json", "latest.json",
    "fixtures/latest/receipt.json", "fixtures/receipt.txt",
])
def test_receipt_ref_must_be_normalized_repo_relative_json(tmp_path, ref):
    root = temp_foundation(tmp_path)
    path = root / "fixtures/valid/evidence-packet.json"
    value = json.loads(path.read_text())
    value["source_runs"][0]["receipt_ref"] = ref
    write_json(path, value)
    assert_failure(validator.validate_repository(root), "normalized immutable repository-relative JSON path")
    with pytest.raises(ValidationError):
        validator.validate_document(value, "evidence-packet.v1.schema.json", root)


def test_finding_authority_must_allow_every_source_run(tmp_path):
    root = temp_foundation(tmp_path)
    sources = json.loads((root / "registry/sources.json").read_text())["sources"]
    ecom = next(source for source in sources if source["source_id"] == "jivo-ecom-api")
    receipt = json.loads((root / "fixtures/valid/ingestion-receipt.json").read_text())
    receipt.update(source_id="jivo-ecom-api", dataset_id=ecom["datasets"][0], run_id="01JIVOEXAMPLE000000000002")
    write_json(root / "fixtures/valid/ecom-receipt.json", receipt)
    path = root / "fixtures/valid/evidence-packet.json"
    evidence = json.loads(path.read_text())
    evidence["source_runs"].append({
        "source_id": "jivo-ecom-api", "dataset_id": ecom["datasets"][0],
        "run_id": receipt["run_id"], "receipt_ref": "fixtures/valid/ecom-receipt.json",
    })
    evidence["findings"][0]["source_run_ids"].append(receipt["run_id"])
    write_json(path, evidence)
    assert_failure(validator.validate_repository(root), "does not allow source(s): jivo-ecom-api")


@pytest.mark.parametrize("field", ["grain", "unit", "time_basis"])
def test_finding_measure_contract_must_exactly_match_metric(tmp_path, field):
    root = temp_foundation(tmp_path)
    path = root / "fixtures/valid/evidence-packet.json"
    evidence = json.loads(path.read_text())
    evidence["findings"][0][field] += " changed"
    write_json(path, evidence)
    assert_failure(validator.validate_repository(root), f"finding {field} does not match metric contract")


def test_metric_currency_semantics(tmp_path):
    root = temp_foundation(tmp_path)
    evidence_path = root / "fixtures/valid/evidence-packet.json"
    evidence = json.loads(evidence_path.read_text())
    evidence["findings"][0]["currency"] = "INR"
    write_json(evidence_path, evidence)
    assert_failure(validator.validate_repository(root), "non-monetary metric")

    evidence["findings"][0]["unit"] = "INR"
    metrics_path = root / "registry/metrics.json"
    metrics = json.loads(metrics_path.read_text())
    metric = next(item for item in metrics["metrics"] if item["metric_id"] == "factory-dispatch-quantity")
    metric["unit"] = "INR"
    evidence["findings"][0]["currency"] = None
    write_json(metrics_path, metrics)
    write_json(evidence_path, evidence)
    assert_failure(validator.validate_repository(root), "requires non-null currency")

    evidence["findings"][0]["currency"] = "USD"
    write_json(evidence_path, evidence)
    assert_failure(validator.validate_repository(root), "must match metric contract currency INR")


def test_amount_semantic_metric_requires_currency(tmp_path):
    root = temp_foundation(tmp_path)
    metrics = json.loads((root / "registry/metrics.json").read_text())["metrics"]
    metric = next(item for item in metrics if item["metric_id"] == "ecom-sale-value")
    path = root / "fixtures/valid/evidence-packet.json"
    evidence = json.loads(path.read_text())
    finding = evidence["findings"][0]
    finding.update(
        metric_id=metric["metric_id"], authority_id=metric["authority_ids"][0],
        grain=metric["grain"], unit=metric["unit"], time_basis=metric["time_basis"],
        currency=None,
    )
    write_json(path, evidence)
    assert_failure(validator.validate_repository(root), "monetary metric ecom-sale-value requires non-null currency")


@pytest.mark.parametrize("field,value", [
    ("rows", 1.5), ("rows", True), ("rows", -1),
    ("bytes", 1.5), ("bytes", False), ("bytes", -1),
])
def test_receipt_rows_and_bytes_are_nonnegative_integers(tmp_path, field, value):
    root = temp_foundation(tmp_path)
    path = root / "fixtures/valid/ingestion-receipt.json"
    receipt = json.loads(path.read_text())
    receipt[field] = value
    write_json(path, receipt)
    assert_failure(validator.validate_repository(root), f"receipt {field} must be a nonnegative integer")


@pytest.mark.parametrize("field,value", [
    ("source_record_count", 1.5), ("source_record_count", True), ("source_record_count", -1),
    ("unique_record_count", 1.5), ("unique_record_count", False), ("unique_record_count", -1),
])
def test_receipt_control_counts_are_nonnegative_integers(tmp_path, field, value):
    root = temp_foundation(tmp_path)
    path = root / "fixtures/valid/ingestion-receipt.json"
    receipt = json.loads(path.read_text())
    receipt["control_totals"][field] = value
    write_json(path, receipt)
    assert_failure(validator.validate_repository(root), f"nonnegative integer {field}")


def test_receipt_control_totals_reject_unknown_governed_fields(tmp_path):
    root = temp_foundation(tmp_path)
    path = root / "fixtures/valid/ingestion-receipt.json"
    receipt = json.loads(path.read_text())
    receipt["control_totals"]["unexpected_governed_field"] = 1
    write_json(path, receipt)
    assert_failure(validator.validate_repository(root), "Additional properties")


@pytest.mark.parametrize("secret", [
    "ghp_" + "a" * 36,
    "github_pat_" + "a" * 30,
    "AKIA" + "A" * 16, "xoxb-" + "a" * 24,
    "sk-" + "a" * 32, "eyJ" + "a" * 8 + "." + "b" * 12 + "." + "c" * 12,
    "Bearer " + "a" * 26, "https://alice:" + "example-only" + "@example.invalid/path",
    "-----BEGIN RSA " + "PRIVATE KEY-----\nexample-only-body",
])
def test_recursive_secret_values_rejected_without_leaking(tmp_path, secret):
    root = temp_foundation(tmp_path)
    path = root / "fixtures/valid/ingestion-receipt.json"
    value = json.loads(path.read_text())
    value["parameters_redacted"] = {"nested": {"value": secret}}
    write_json(path, value)
    result = validator.validate_repository(root)
    assert_failure(result, "secret-like value")
    assert secret not in "\n".join(result["failures"])


def test_secret_scan_allows_hashes_and_ordinary_text(tmp_path):
    root = temp_foundation(tmp_path)
    path = root / "fixtures/valid/ingestion-receipt.json"
    value = json.loads(path.read_text())
    value["parameters_redacted"] = {
        "notes": ["Bearer authentication is required", "sk-short-example", "a" * 64]
    }
    write_json(path, value)
    assert validator.validate_repository(root)["status"] == "PASS"


@pytest.mark.parametrize("ref", [
    "https://example.invalid/latest", "latest/evidence.json", "evidence/file.json",
    "sha256:" + "A" * 64, "sha256:" + "a" * 63,
    "sha256:" + "a" * 64 + "#unsafe fragment",
])
def test_finding_evidence_refs_require_content_address(tmp_path, ref):
    root = temp_foundation(tmp_path)
    path = root / "fixtures/valid/evidence-packet.json"
    value = json.loads(path.read_text())
    value["findings"][0]["evidence_refs"] = [ref]
    write_json(path, value)
    assert_failure(validator.validate_repository(root), "content-addressed sha256")
    with pytest.raises(ValidationError):
        validator.validate_document(value, "evidence-packet.v1.schema.json", root)


@pytest.mark.parametrize("document,expected", [
    ({"message": "ordinary JSON"}, "unclassified JSON document"),
    ({"schema": "jivo.evidence-packet/v2"}, "unsupported schema discriminator"),
    ({"receipt_schema": "jivo.ingestion-receipt/vO"}, "unsupported schema discriminator"),
])
def test_unknown_or_missing_discriminator_fails_closed(tmp_path, document, expected):
    root = temp_foundation(tmp_path)
    write_json(root / "other.json", document)
    assert_failure(validator.validate_repository(root), expected)


def test_valid_fixture_must_be_evidence_or_receipt(tmp_path):
    root = temp_foundation(tmp_path)
    card = json.loads((root / "registry/specialists.json").read_text())["specialists"][0]
    write_json(root / "fixtures/valid/capability.json", card)
    assert_failure(validator.validate_repository(root), "unsupported schema discriminator")

def test_unguarded_rebuild_test_hook_refuses_without_mutation(tmp_path):
    repo = ORCH.parents[1]
    script = repo / "bin" / "daily_rebuild.sh"
    fixture = tmp_path / "fixture"
    combined = tmp_path / "combined"
    fixture.mkdir()
    combined.mkdir()
    sentinel = fixture / "sentinel.txt"
    sentinel.write_text("unchanged\n")
    result = subprocess.run(
        ["bash", str(script), "--test-sync-protection"],
        env={**os.environ, "JDB_REPO": str(fixture), "JDB_COMBINED": str(combined)},
        capture_output=True, text=True,
    )
    assert result.returncode == 64
    assert sentinel.read_text() == "unchanged\n"


def test_contradiction_evidence_refs_are_content_addressed():
    packet = load("evidence-packet.json")
    packet["contradictions"] = [{
        "description": "Sanitized contradiction",
        "evidence_refs": [
            "sha256:" + "a" * 64,
            "https://example.invalid/latest",
        ],
        "status": "open",
    }]
    with pytest.raises(ValidationError):
        validator.validate_document(packet, "evidence-packet.v1.schema.json")


def test_contract_schema_string_values_are_secret_scanned(tmp_path):
    root = temp_foundation(tmp_path)
    path = root / "contracts" / "probe.schema.json"
    write_json(path, {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "string",
        "description": "ghp_" + "a" * 36,
    })
    assert_failure(validator.validate_repository(root), "secret-like value is forbidden")

