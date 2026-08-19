# Hermes Company Intelligence OS

**Status:** target operating architecture  
**Purpose:** let Daman ask one business question in natural language and receive a current, reconciled, evidence-backed answer spanning every JIVO department.

This architecture assumes that departmental software will be exposed through machine-friendly CLIs and that SAP Business One/HANA will provide the financial and inventory backbone. It deliberately keeps the main Hermes conversation small: domain knowledge and raw data stay behind specialist boundaries.

The companion data-platform design is [`../../DATA-PLATFORM-ARCHITECTURE.md`](../../DATA-PLATFORM-ARCHITECTURE.md). The finalized normative foundation rules and acceptance gates are in [`BUILD-RULES.md`](BUILD-RULES.md).

Validate the executable Phase 0 foundation from the repository root (the wrapper itself is safe from any current working directory):

```bash
./bin/validate_intelligence_foundation.sh
python3 -m pytest intelligence/hermes-orchestration/tests/test_foundation.py
```

These artifacts are the executable foundation and initial registry; they do not claim the target platform is fully deployed or Phase 0 is otherwise complete.

## 1. North star

```text
Daman asks one question
        │
        ▼
Executive Orchestrator — understands intent, plans the investigation
        │
        ├── Factory/WMS specialist
        ├── E-commerce specialist
        ├── SAP specialist
        ├── Import/export specialist
        ├── Accounting specialist
        ├── Billing/collections specialist
        └── future departmental specialists
        │
        ▼
Reconciliation and evidence verifier
        │
        ▼
One answer: finding → cause → financial/operational impact → action → owner → deadline
```

A successful answer is not merely plausible. Every consequential claim states:

- the metric and grain,
- source authority,
- source `as_of` time,
- freshness and quality state,
- evidence/provenance reference,
- confidence and unresolved contradictions.

## 2. Core architectural decisions

1. **One domain specialist per CLI or coherent business domain.** The specialist owns command discovery, authentication checks, source semantics, extraction, validation, and domain analysis.
2. **A thin main orchestrator.** It receives capability summaries and compact evidence packets, never complete command catalogs or bulk API output.
3. **CLIs are interfaces, not data stores.** Connector code and source-specific contracts stay with each CLI. Extracted evidence lands through the common data platform.
4. **JIVO Data Bank is the semantic and governance control plane.** It stores meaning, contracts, authority, metric/entity cards, exceptions, and compact provenance—not unlimited raw rows.
5. **SAP is the posting authority, not the only operational truth.** SAP governs posted documents and balances; departmental systems govern events they originate. Reconciliation connects them without erasing disagreement.
6. **Read and act are separate trust zones.** Insight agents are read-only. Any write, posting, cancellation, payment, PO, stock transfer, or message is handled by a separate action executor with explicit policy and approval.
7. **Fresh specialists are the default.** Use `delegate_task` for interactive investigations. Use isolated Hermes profiles/Kanban workers only for durable monitoring, scheduled ownership, or independent credentials.
8. **Batch-first, evidence-first.** Begin with reliable scheduled snapshots and governed metrics. Add streaming, graph databases, or heavy serving systems only after measured need.

## 3. System layers

### Layer A — source systems

- SAP Business One/HANA
- Factory/WMS/dispatch application
- E-commerce and marketplace application
- Import/export and logistics software
- Accounting, billing and collections software
- CRM, HR, procurement, quality, advertising and future systems
- Governed spreadsheets/files where no API exists

Each source has a named owner, authority scope, cadence, sensitivity, retention policy, and expected business controls.

### Layer B — CLI adapter layer

Every departmental CLI should support the same agent-facing lifecycle even if native commands differ:

```text
doctor/auth   prove reachability and permission
api/discover  enumerate datasets and capabilities
which         route a natural-language need to the right command
read/export   return deterministic paginated data
sync/archive  preserve a reproducible local snapshot
schema        expose keys, grain, units and timestamps
receipt       emit counts, hashes, source time and completeness controls
```

CLI requirements:

- `--agent` JSON mode with stable schemas and typed exit codes;
- explicit `--data-source live|local` and source/freshness metadata;
- deterministic pagination with cap detection;
- `--select`, filters and bounded output;
- file delivery for large results instead of stdout dumps;
- read-only by default; writes in a separate command group;
- secrets only from scoped credential stores/environment, never output;
- structured errors such as `AUTH_EXPIRED`, `SCHEMA_DRIFT`, `PARTIAL_PAGE`, `RATE_LIMITED`;
- version and schema fingerprint in every extraction receipt.

### Layer C — evidence and canonical data platform

The platform has five logical zones:

```text
RAW evidence → BRONZE parsed → SILVER source-clean → CORE canonical → GOLD governed metrics
```

- **Raw:** exact immutable source response/file plus hash and receipt.
- **Bronze:** typed source rows with raw pointer and run ID.
- **Silver:** deduplicated source-native history; conflicts and rejects remain visible.
- **Core:** conformed products, partners, locations, documents, inventory movements and temporal identity mappings.
- **Gold:** governed business marts and leadership metrics.

The full target is object storage + Parquet/Iceberg + PostgreSQL control plane. Deployment must be staged:

- **Now:** CLI snapshots, receipts, Parquet and DuckDB; preserve existing pipelines.
- **At 4–6 mature CLIs or when Git/runtime becomes painful:** S3/MinIO raw evidence and PostgreSQL run/identity/quality control plane.
- **At multi-year/high-concurrency scale:** Iceberg/Trino; optional ClickHouse only when measured latency requires it.

Do not deploy infrastructure merely because it appears in the target diagram.

### Layer D — semantic and entity services

Hermes specialists should query stable services rather than inventing SQL against raw tables:

```text
list_metrics()
describe_metric(metric_id)
query_metric(metric_id, dimensions, filters, time_range, as_of)
explain_result(result_id)
resolve_entity(source, external_id, at_time)
get_entity_context(entity_id)
trace_document_chain(document_id)
list_exceptions(domain, severity, owner)
```

Every metric contract declares grain, formula, unit, authority, time basis, freshness SLA, allowed dimensions, additivity and reconciliation rule.

Canonical identity separates:

- product concept,
- exact sellable unit/pack,
- company-scoped SAP item,
- marketplace listing,
- legal entity,
- customer/distributor/vendor,
- physical location and warehouse.

### Layer E — Hermes agent mesh

#### Executive Orchestrator

Responsibilities:

- classify the question and decision horizon;
- select only required specialists;
- build a dependency DAG;
- run independent specialists in parallel;
- enforce common cutoffs and metric definitions;
- request verification when sources conflict;
- synthesize impact, priority, owner and deadline;
- ask Daman only for decisions or unavailable evidence.

The orchestrator does not directly operate a domain CLI when a specialist exists, except for a bounded verification call.

#### Domain specialists

Initial registry:

- `factory-specialist` — WMS, dispatch, barcode, QC, GRPO, intercompany.
- `ecom-specialist` — platform sales, availability, targets, pricing, ads, city/SKU performance.
- `sap-specialist` — posted documents, inventory movement/balance, PO/GRPO, document chains and master data.
- `distributor-specialist` — dated SOH, inward, outward, in-transit, expected stock and physical reconciliation.
- `import-export-specialist` — shipment, customs, container, landed cost and ETA.
- `accounting-specialist` — GL, receivables/payables, bank, tax and period close.
- `billing-collections-specialist` — invoices, credit notes, ageing, collection and deduction disputes.

Later domains should be added only after defining their contract and source authority.

Each specialist consists of:

```text
small routing card + on-demand skill + CLI wrapper + domain contracts + tests + output schema
```

A specialist is not an always-running LLM. It is a bounded role instantiated only when needed. Durable profiles are reserved for scheduled or long-running ownership.

#### Reconciliation specialist

A separate verifier handles questions that cross authorities, for example:

- factory scans vs SAP inventory transfer,
- SAP billing vs distributor receipt,
- distributor outward vs platform GRN,
- billing vs GL revenue,
- import landed cost vs inventory valuation,
- platform sales vs receivables and deductions.

It does not choose a winner by intuition. It applies the versioned source-authority matrix and preserves the residual as an exception.

#### Executive critic

For material decisions, a final critic checks:

- unsupported causal claims,
- mixed dates or grains,
- double counting/fan-out joins,
- proxy presented as actual,
- stale or partial sources,
- missing financial impact,
- unsafe action recommendations.

Use this gate for high-value procurement, inventory, cash, pricing, compliance or personnel decisions—not for every simple lookup.

### Layer F — insight and exception engine

Do not wait for Daman to ask every question. Deterministic monitors should generate compact exceptions such as:

- stockout risk on premium SKUs,
- excess/aged inventory,
- inventory movement not posted to SAP,
- dispatch or GRPO beyond SLA,
- PO shortage against validated demand,
- receivable or deduction ageing,
- margin/price leakage,
- cash or tax-control exceptions,
- missing documents and broken reconciliation.

LLMs explain and prioritize exceptions; scripts/SQL detect them. This prevents expensive agents from repeatedly scanning all raw data.

### Layer G — action execution

Use a three-stage autonomy ladder:

1. **Observe:** read, reconcile and explain automatically.
2. **Recommend:** draft actions, owners and payloads automatically.
3. **Execute:** perform approved actions through a separate executor.

Action classes:

- **Auto-safe:** refresh a cache, retry a failed read, open an internal exception card.
- **Approval-required:** send external messages, create transfers/PO drafts, change prices, post documents.
- **Dual-approval:** payments, journal entries, cancellations, credit notes, master-data changes, destructive operations.
- **Forbidden to autonomous agents:** secret export, bypassing controls, silent historical rewrites.

Every action records requester, approver, policy, exact payload hash, source evidence, execution result and rollback/compensating path.

## 4. Context-isolation contract

### Capability card

The main agent knows only this small record for each specialist:

```yaml
id: factory-specialist
owns: [wms, dispatch, barcode, qc, grpo, intercompany]
cli: jivo-factory-pp-cli
freshness_sla: 24h
skill: jivo-factory-analysis
output_schema: evidence-packet/v1
writes: false
```

Detailed CLI schemas load only inside the selected specialist.

### Evidence packet

Every specialist returns a bounded packet:

```json
{
  "schema": "jivo.evidence-packet/v1",
  "domain": "factory",
  "question": "...",
  "source_runs": [],
  "as_of": {},
  "quality": {"status": "pass|warn|fail", "exceptions": []},
  "findings": [
    {
      "claim": "...",
      "metric_id": "...",
      "value": null,
      "grain": "...",
      "unit": "...",
      "currency": null,
      "time_basis": "...",
      "authority_id": "...",
      "confidence": "high|medium|low",
      "evidence_refs": []
    }
  ],
  "contradictions": [],
  "recommended_actions": [],
  "data_needed": []
}
```

Limits:

- no raw API pages in the packet;
- maximum findings unless the orchestrator requests expansion;
- large evidence written to an artifact and referenced by hash/path;
- no credentials, cookies, headers or personal data beyond necessity;
- return null/unknown rather than inventing a value.

### Cross-domain query protocol

Example: “Why is Blinkit availability low despite enough production?”

1. Orchestrator fixes SKU scope, geography, period and desired decision.
2. E-commerce specialist measures availability and lost-sales exposure.
3. SAP specialist measures posted stock, commitments and transfers.
4. Factory specialist measures physical custody and dispatch exceptions.
5. Distributor specialist measures expected/physical SOH and outward/in-transit state.
6. Reconciliation specialist aligns SKU/UOM/date and builds the quantity bridge.
7. Critic verifies causality and confidence.
8. Orchestrator returns root cause and a ranked action plan.

Only compact packets reach the final synthesis context.

## 5. Source-of-truth policy

Authority is field-, process- and time-specific:

- SAP: legal postings, document status and financial/inventory ledger.
- Physical signed count: stock at the stated location and moment.
- Factory application: scan, box, pallet, gate and dispatch events it originates.
- Department application: its workflow events and operational state.
- Platform API/scrape: observation at the stated platform, surface, location and time.
- Governed spreadsheet: only the process/date explicitly assigned to it.
- Derived model: an estimate with formula/version, never relabeled as physical or posted actual.

When authorities disagree, store both values, the policy applied, the residual and the owner. Any unresolved inventory variance means incomplete reconciliation or a missing variable/source.

## 6. Security and governance

- One least-privilege service identity per CLI/domain.
- SAP access through approved read-only Service Layer endpoints, views or reporting replica; no agent-generated ad hoc production SQL.
- Secrets in a secret manager/profile environment, never Git, skills, prompts or evidence packets.
- Separate credentials and network paths for read and write operations.
- Column/row classification for financial, employee, customer and credential data.
- Full audit trail for source reads of sensitive domains and all writes.
- Private repositories and encrypted storage; no public Vercel data payloads.
- If a Vercel dashboard is added, it is an authenticated presentation layer over a private governed API, not the data store.
- Restore tests for raw evidence, control-plane state and a known publication.

## 7. Reliability and operating model

### Freshness

Every answer displays per-source `as_of`; never hide mixed-date inputs behind one date. “Latest” means latest successful, quality-approved publication.

### Quality gates

- Authentication/reachability
- Pagination/completeness
- Schema drift
- Duplicate/business-key integrity
- Unit and currency validity
- Identity coverage
- Source control totals
- Cross-source reconciliation
- Metric grain/fan-out safety

Hard failures block publication. Soft failures publish only with an explicit warning.

### Scheduling

- Source ingestion: deterministic scripts/cron, not LLM loops.
- Data transformations and checks: dependency-aware jobs.
- Exception summaries: scheduled specialist skill or script.
- Long multi-domain investigations: Hermes Kanban DAG with durable handoffs.
- Interactive questions: temporary `delegate_task` specialists.

### Observability

A control-tower view should show:

- source health and last successful run,
- data age and completeness,
- schema changes,
- failed reconciliations,
- quarantined rows,
- agent calls/cost/latency,
- action approvals and outcomes,
- unanswered questions caused by missing data.

## 8. What belongs in JIVO Data Bank

Keep:

- business glossary and source catalog;
- specialist capability cards;
- source-authority policies;
- extraction/data contracts and links to owning code;
- entity and metric definitions;
- curated company/product/customer/vendor cards;
- current quality summaries and exception queues;
- compact evidence/provenance manifests;
- architecture, runbooks and decision records;
- bounded executive reports.

Do not keep indefinitely:

- every raw API response;
- one Markdown file per SAP line, scan or transaction;
- full production database exports;
- credentials or personal data copied for convenience;
- generated daily trees whose only purpose is historical storage.

The Data Bank becomes the company’s **meaning and evidence index**. Bulk immutable history lives in the data platform.

## 9. Recommended rollout

### Phase 0 — foundation

- Confirm the specialist registry and domain boundaries.
- Define `evidence-packet/v1` and `ingestion-receipt/v1`.
- Create source/authority registry and first 20 leadership metrics.
- Record current CLI health, freshness and data ownership.

**Acceptance:** every current source and leadership metric has an owner, grain and authority.

### Phase 1 — standardize the three existing domains

- Factory, e-commerce and distributor/JIVO specialists.
- Wrap each CLI with common health, extraction and receipt behavior.
- Store large outputs as Parquet/artifacts; return compact packets.
- Implement reconciliation specialist for inventory flow.

**Acceptance:** a cross-domain inventory question is reproducible and does not load bulk CLI schemas into the main context.

### Phase 2 — SAP backbone

- Establish secure read-only SAP access.
- Build approved document, inventory, partner and accounting extracts.
- Create canonical document chain and temporal crosswalks.
- Reconcile SAP to existing factory and distributor movements.

**Acceptance:** priority inventory and billing processes bridge from physical event to SAP posting with quantified residuals.

### Phase 3 — finance and commercial domains

- Add accounting, billing/collections and import/export specialists.
- Define cash, margin, landed-cost, receivable and period-close metrics.
- Build executive exception packs.

**Acceptance:** operational recommendations include verified financial impact.

### Phase 4 — proactive control tower

- Daily deterministic exception generation.
- Telegram executive briefing and private Vercel control center.
- Kanban routing for unresolved exceptions.
- Trend outcomes: whether recommended actions actually improved the metric.

**Acceptance:** every critical exception has owner, SLA, evidence, status and measured outcome.

### Phase 5 — controlled execution

- Add draft-only actions first.
- Add approval workflows and audit log.
- Permit narrowly scoped automated actions only after repeated safe operation.

**Acceptance:** no write occurs outside policy; every write is attributable, reviewable and compensatable.

## 10. Immediate next build order

1. Finalize the specialist/capability registry.
2. Implement and test the evidence-packet schema.
3. Convert Factory CLI into the reference specialist.
4. Convert E-commerce CLI into the second specialist.
5. Implement inventory reconciliation fan-in across factory, SAP/ecom and distributor sources.
6. Secure SAP Service Layer/reporting access and onboard it read-only.
7. Add source freshness and quality control tower.
8. Only then onboard accounting, billing, import/export and additional CLIs using the same template.

The first milestone is not “connect every department.” It is proving that two or three specialists can answer one important cross-company question with exact provenance, low context use and a verified reconciliation. Once that template works, new domains become repeatable onboarding rather than architectural reinvention.
