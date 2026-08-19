# Phase 0 Company Intelligence OS build rules

**Status:** normative Phase 0 contract. **Scope:** the executable foundation and initial registry, not completion of the target platform.

The words **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

## Identity, registration, and provenance

1. Every source, dataset, run, authority rule, metric, specialist, schema, and evidence packet MUST have a stable ID. Breaking contract changes MUST receive a new version; IDs MUST NOT be silently repurposed.
2. A source and dataset MUST be registered, with lifecycle and accountable roles, before extraction or use. Unknown references MUST fail validation.
3. Phase 0 specialists and connectors MUST be read-only. `writes` MUST be `false`; insight generation MUST NOT post, mutate, message, approve, or execute business actions.
4. Every extraction MUST emit an immutable receipt identifying the exact source, dataset, run, cursor/snapshot, timestamps, extractor version, object URI, SHA-256, schema fingerprint, parameters (redacted), control totals, row/byte counts, and status. A retry or correction MUST append a new run/receipt; receipts MUST NOT be edited in place.
5. Claims MUST point to exact evidence references and source run IDs. Mutable URLs, filenames without hashes, and “latest” without an as-of time are not sufficient provenance.
6. Bulk raw payloads, row-level production history, binaries, secrets, tokens, cookies, headers, credentials, or personal data beyond necessity MUST NOT enter Git or evidence packets. Git MAY hold compact contracts, receipts, fixtures, summaries, and content-addressed pointers.

## Meaning and authority

7. Authority MUST be scoped by business process, field/fact, and effective time. “System X is authoritative” without that scope MUST NOT be used. Conflicts MUST remain visible and be reconciled by a versioned rule.
8. Every metric/finding MUST state its grain, unit of measure, currency where monetary, and time basis/as-of. Incompatible grain, units, currencies, or periods MUST NOT be silently combined.
9. Proxies, estimates, observations, samples, and expected quantities MUST be explicitly labeled. A proxy MUST NOT be presented as posted actual; an observation MUST NOT be presented as universal; expected stock MUST NOT be presented as physical stock.
10. Missing or unknown values MUST be represented as null/unknown. They MUST NOT be fabricated as zero. A real zero requires evidence at the declared grain and completeness boundary.
11. Posted financial and inventory facts MUST use the scoped posting authority. Operational systems MAY govern events they originate. Physical counts and expected/book quantities MUST remain distinct.

## Lifecycle, validation, and correction

12. Lifecycle MUST be explicit: `planned` → `draft` → `validated` → `governed` (or `blocked`). Promotion MUST pass registration, provenance, quality, reconciliation, ownership, and compatibility gates. Planned SAP-dependent metrics MUST remain draft until SAP evidence is ready.
13. Validation MUST be deterministic and fail closed: schemas reject unknown governed fields; IDs/references are unique and resolvable; secret-like keys and placeholders are rejected; incomplete incremental or landed receipts fail. A failed gate MUST prevent publication/promotion.
14. Corrections MUST append a new version/run with a link or reason; historical evidence and prior definitions MUST remain reproducible. In-place rewriting of receipts or source evidence is forbidden.
15. Contract/schema evolution MUST preserve compatibility or use a new version. Producers and consumers MUST have fixtures and tests for valid and invalid behavior before promotion.

## Evidence and action boundaries

16. Evidence packets MUST be compact: no more than 10 findings, no raw pages/payloads, nonempty evidence references, source run IDs, authority, as-of, quality, and confidence per finding.
17. Recommended actions MUST remain separate from execution. Approval-required and dual-approval actions MUST pass through a separate executor and policy/audit trail. Autonomous agents MUST NOT bypass controls or export secrets.
18. All additions MUST include deterministic repository validation and negative tests. Tests MUST NOT call production networks, mutate source data, or require credentials.

## Definition of Done — new dataset

A dataset is done for its current lifecycle only when:

- its stable source/dataset IDs and owner/steward roles are registered before ingestion;
- grain, schema/version, keys, time basis, units/currency, incremental strategy, sensitivity, retention, freshness, and authority scope are documented;
- a sanitized valid receipt fixture proves exact provenance, hash, completeness controls, and cursor behavior;
- quality/reconciliation controls and fail-closed behavior are defined and tested;
- no secrets or bulk raw payloads are in Git;
- downstream metric/reference compatibility tests pass; and
- lifecycle promotion has explicit accountable approval. A draft registration is not a governed dataset.

## Definition of Done — Phase 0 gate

Phase 0 foundation passes only when all seven schemas (three runtime contracts and four registry contracts), all registries, sanitized fixtures, the validator, wrapper, and tests are present; exactly seven source families, seven specialists, and 20 initial metrics are registered; enabled specialists are read-only and reference ready sources; every reference resolves; schemas and custom invariants fail closed; secret/placeholder scans pass; both commands below exit zero; and the result is reported as **foundation/initial registry**, not as a fully deployed or fully governed intelligence platform.

```bash
./bin/validate_intelligence_foundation.sh
python3 -m pytest intelligence/hermes-orchestration/tests/test_foundation.py
```
