# Phase 1 — Intelligence Output Contract Design

Status: `PROMOTED — IMPLEMENTATION COMPLETE`
Last updated: 2026-07-28
Baseline: `a272890a7b51856c033df69b5148bc8c2fa928da`
Approved planning commit: `3d406334f714ccad40daa9e8441499e5b7ebdaab`
Implementation branch: `codex/phase-1-intelligence-contract`

## Purpose

Add a small, backward-compatible intelligence vocabulary to the existing shared
use-case result so deterministic facts, signals, and recommendations are
distinguishable.

This phase is contract work, not a redesign of the runtime. It reuses the
current Pydantic request/result models, executor, structured CLI, generic
Dashboard endpoint, Copilot operating agent, evidence and freshness records,
and bounded execution traces.

The owner approved this design on 2026-07-27. Implementation is authorized only
through the bounded batches defined here, starting with Batch B1 on a dedicated
independent branch.

The owner promoted the completed Phase 1 implementation on 2026-07-28 after
Batch D validation and synthetic release rehearsal. See
`implementation-reports/IP-027_IMPLEMENTATION_REPORT.md`.

## Decision supported

The contract must let an interface or model answer three different questions
without treating them as interchangeable:

1. What was observed or deterministically calculated?
2. What condition did a deterministic rule detect?
3. What action, if any, does the system deterministically recommend?

The model may explain these objects and their uncertainty. It must not create
authoritative facts, signals, severity, freshness, or write authorization.

## Verified current architecture

```text
Copilot operating instructions
            |
            v
pm tool list / describe / query
            |
            v
ToolTransport
            |
            v
UseCaseExecutor
            |
            v
Registered read-only use-case handler
            |
            v
UseCaseResult
  data, evidence, freshness, assumptions, warnings,
  alternatives, context, proposed_writes, execution_metadata
            |
            +------------------+
            |                  |
            v                  v
   JSON CLI projection   Generic Dashboard projection
            |
            v
Bounded execution-trace summary
```

Verified responsibilities:

- `UseCaseRequest` and `UseCaseResult` are Pydantic models in the shared service
  contract.
- `UseCaseExecutor` owns registration, request validation, safe failure
  classification, execution metadata, and bounded trace persistence.
- Nine read-only use cases are registered through the same executor.
- `pm tool query` serializes `UseCaseResult.model_dump()` directly.
- the generic Dashboard query route serializes the same result directly and
  marks it as `use-case-result-v1`;
- the Copilot agent is instructed to treat structured JSON, evidence,
  freshness, assumptions, and warnings as authoritative;
- `execution_traces` stores only bounded evidence/freshness/warning summaries,
  not the business payload;
- existing use cases already return evidence, freshness, rule versions, and
  context, but fact, signal, and recommendation meaning is embedded in
  use-case-specific `data` or `context`.

## Current gap

The existing envelope is usable but leaves interpretation ambiguous:

- `data` mixes observed records, calculated summaries, and detected conditions;
- Management Attention items combine fact, severity, reason, and embedded
  evidence in one use-case-specific structure;
- there is no common reference chain from recommendation to signal to fact to
  evidence;
- clients cannot discover whether a use case emits facts, signals, or
  recommendations;
- empty or missing recommendation behavior is not explicit;
- the executor validates requests but not cross-references inside intelligence
  output.

## Approved-direction constraints

- Preserve the `UseCaseRequest` shape.
- Preserve the existing `UseCaseResult` fields and their meanings.
- Keep `contract_version = "1.0"` because the change is additive and every new
  field has an empty default.
- Preserve every existing `data` and `context` projection during Phase 1.
- Keep CLI and Dashboard as thin serializers.
- Do not add a database table or migration.
- Do not persist intelligence payloads in `execution_traces`.
- Do not add recommendation business behavior merely to populate a field.
- Do not change write authorization or the propose/preview/confirm/persist
  workflow.

## Proposed additive result contract

Add these top-level fields to `UseCaseResult`, each defaulting to an empty list:

```text
facts[]
signals[]
recommendations[]
```

The existing fields remain unchanged and continue to be returned:

```text
contract_version
status
data
evidence[]
freshness[]
assumptions[]
warnings[]
alternatives[]
context
proposed_writes[]
execution_metadata
```

### Shared subject reference

Every intelligence object uses the same subject reference:

| Field | Type | Rule |
| --- | --- | --- |
| `kind` | string | Stable canonical kind such as `project`, `action`, or `source`. |
| `id` | string | Stable local identifier; never invented by the model. |

Display names remain in existing `data` or `context`. They are not required for
reference integrity.

### Fact

| Field | Type | Required behavior |
| --- | --- | --- |
| `fact_id` | string | Unique within one result. |
| `fact_type` | string | Stable machine-readable fact code. |
| `fact_kind` | enum | `observed` or `derived`. |
| `subject` | subject | Canonical subject reference. |
| `value` | JSON value or null | Null unless `value_state` is `known`. |
| `value_state` | enum | `known`, `unknown`, `unavailable`, or `conflicting`. |
| `observed_at` | timestamp or null | Source observation time when known. |
| `freshness_refs` | string list | References `source_id` values in top-level `freshness`. |
| `evidence_refs` | string list | References `evidence_id` values in top-level `evidence`. |
| `rule_version` | string or null | Required for a derived fact. |

Facts do not contain recommendations or prose conclusions. A known numeric zero
is different from an unknown or unavailable value.

### Signal

| Field | Type | Required behavior |
| --- | --- | --- |
| `signal_id` | string | Unique within one result. |
| `signal_type` | string | Stable machine-readable rule outcome. |
| `subject` | subject | Canonical subject reference. |
| `state` | enum | `active`, `clear`, `unknown`, or `unavailable`. |
| `severity` | enum | `critical`, `high`, `medium`, `low`, `info`, or `unknown`. |
| `reason_codes` | string list | Deterministic reason codes, not model prose. |
| `fact_refs` | string list | References top-level `fact_id` values. |
| `evidence_refs` | string list | References top-level `evidence_id` values. |
| `rule_version` | string | Deterministic rule version. |

Generic signal state is not the future Attention lifecycle. Acknowledgement,
snooze, ownership, and resolution belong to Phase 2 and must not be encoded
prematurely in this field.

### Recommendation

| Field | Type | Required behavior |
| --- | --- | --- |
| `recommendation_id` | string | Unique within one result. |
| `recommendation_type` | string | Stable machine-readable action code. |
| `subject` | subject | Canonical subject reference. |
| `state` | enum | `available`, `blocked`, or `not_applicable`. |
| `rationale_codes` | string list | Deterministic rationale codes. |
| `signal_refs` | string list | References top-level `signal_id` values. |
| `evidence_refs` | string list | References top-level `evidence_id` values. |
| `write_mode` | enum | `advisory` or `proposal_required`. |
| `confirmation_required` | boolean | Must be true for `proposal_required`. |

Phase 1 allows an empty recommendation list. A model must not fill the absence
with an invented recommendation. Later phases add recommendations only when a
bounded use case defines deterministic action behavior.

## Result validation

The shared runtime must validate intelligence output after a handler returns and
before the result is traced or serialized.

Required deterministic checks:

- IDs are non-empty, bounded, and unique within their object type;
- every fact evidence/freshness reference resolves;
- every signal fact/evidence reference resolves;
- every recommendation signal/evidence reference resolves;
- a derived fact has a rule version;
- a non-known fact value is null;
- `proposal_required` implies `confirmation_required = true`;
- empty arrays are valid;
- malformed handler output fails closed as `status = "failed"` with safe warning
  code `RESULT_CONTRACT_INVALID`;
- validation details or payload values are not exposed through the warning.

The validator does not determine business facts or severity. It validates only
shape and reference integrity.

## Discovery contract

Extend use-case descriptor output additively with:

```text
intelligence_capabilities:
  facts: true | false
  signals: true | false
  recommendations: true | false
```

This metadata describes implemented output, not aspirational capability. A use
case with all values false still returns the three empty arrays through the
global envelope.

The descriptor contract version remains `1.0`.

## Phase 1 reference slice

Use `management-attention` as the single production reference slice because it
already owns deterministic ranking, severity, reason codes, evidence, freshness,
and a strict item limit.

Required mapping:

- preserve existing `data.items`, order, summary, context, warnings, and status;
- create facts only for returned attention items;
- create one signal for each returned attention item;
- use deterministic result-local IDs derived from attention type and subject ID;
- reference top-level evidence and freshness rather than embedding new copies;
- add bounded source-freshness evidence when required for reference integrity;
- advertise `facts = true`, `signals = true`, and
  `recommendations = false`;
- leave `recommendations` empty.

Initial fact types:

- `project_health_state`;
- `action_due_state`;
- `source_freshness_state`.

Initial signal types reuse the existing meaning:

- `project_health_attention`;
- `overdue_action_attention`;
- `source_freshness_attention`.

No new scoring, severity thresholds, lifecycle state, ownership, or action
recommendation is introduced in Phase 1.

## Interface behavior

### Structured CLI

`pm tool query` continues to serialize the full result. It gains the three
fields automatically and does not calculate or reshape them.

### Generic Dashboard

`POST /api/tool/query/<use-case-id>` continues to return the full shared result.
The existing interface header and HTTP status mapping remain unchanged.

### Legacy CLI and Dashboard

Existing formatted commands and legacy projections remain unchanged. Phase 1
adds no business logic to a legacy route.

### Copilot

After implementation, the operating instructions must require this priority:

1. facts establish what is known;
2. signals establish deterministic rule outcomes;
3. recommendations establish supported next actions;
4. evidence, freshness, assumptions, and warnings qualify all three;
5. empty recommendations remain empty.

Copilot may explain or compare the objects but may not create missing objects.

### Execution trace retrieval

Trace retrieval remains a bounded operational summary. A retrieved trace returns
empty facts, signals, and recommendations and sets
`execution_metadata.trace_summary = true`.

This avoids a database migration and prevents business payload persistence.
Full result replay is explicitly outside Phase 1.

## Database and migration position

No database change is required.

Reuse:

- existing operational tables as sources for the reference use case;
- existing `data_sources` and `sync_runs` freshness calculations;
- existing `execution_traces` bounded summaries.

The implementation must prove that bootstrap schema, table/view counts,
migrations, rollback, and trace retention behavior are unchanged.

## Deterministic and model boundary

Deterministic code owns:

- fact value and value state;
- observed time and freshness references;
- signal state, severity, reason codes, and rule version;
- recommendation availability and confirmation behavior;
- reference validation and serialization.

The model owns:

- interpreting the management question;
- selecting the use case;
- explaining facts and signals;
- comparing supported recommendations;
- making uncertainty and missing data understandable.

The model must not:

- turn `unknown` into zero or healthy;
- create an unreturned signal;
- raise or lower deterministic severity;
- invent a recommendation when the list is empty;
- convert an advisory recommendation into a write;
- infer evidence or freshness not returned by the runtime.

## Scenarios

### S1 — Active health and action signals

Synthetic input contains one red project and one overdue action. The result
preserves current attention ordering, emits known facts, emits active signals
with valid fact/evidence references, and emits no recommendation.

### S2 — Non-fresh source

A stale or unavailable synthetic source produces a fact whose value and
freshness reference expose that state, plus the existing deterministic
source-freshness signal. It is not converted into a healthy or empty fact.

### S3 — No attention required

The use case succeeds with its existing empty item result and returns empty
facts, signals, and recommendations.

### S4 — Bounded result

When more items exist than the requested limit, intelligence objects cover only
returned items. Existing summary and truncation behavior still expose omitted
count.

### S5 — Invalid reference

A synthetic handler returns a signal with an unknown fact reference. The
executor returns `failed` and `RESULT_CONTRACT_INVALID` without exposing the
invalid payload.

### S6 — Interface parity

Direct executor, structured CLI, and generic Dashboard results contain
equivalent facts, signals, and recommendations for the same synthetic request.

### S7 — Trace summary

Retrieving a stored execution trace returns bounded evidence/freshness/warning
summary data and empty intelligence arrays. No business payload is persisted.

### S8 — Legacy compatibility

Existing `data`, `context`, legacy CLI text, legacy Dashboard projections,
status mapping, contract version, and interface header remain unchanged.

### S9 — No schema change

Database bootstrap and release rehearsal show no new table, column, view, or
migration and preserve the existing trace-retention behavior.

## Acceptance criteria

- `UseCaseResult` exposes typed additive facts, signals, and recommendations
  with empty defaults.
- Existing use cases remain valid without immediate migration.
- The executor rejects broken intelligence references safely.
- `management-attention` is the only Phase 1 production mapping.
- Existing management-attention `data` behavior is unchanged.
- list/describe accurately advertises implemented intelligence capability.
- CLI and generic Dashboard preserve the same full result.
- the Copilot operating contract prohibits invented recommendations.
- no database DDL or migration is added.
- focused contract and reference-slice tests pass.
- all existing tests pass.
- `make validate` passes.
- `make rehearse-release` confirms installed behavior and unchanged migration.
- portability and synthetic-data checks pass.

## Risks and controls

| Risk | Level | Control |
| --- | --- | --- |
| Duplicate meaning between `data` and intelligence fields | Medium | One deterministic mapper in the reference use case; parity tests preserve old data. |
| Client assumes an exact set of JSON keys | Medium | Additive fields, unchanged `1.0` version, CLI/Dashboard compatibility tests. |
| Reference IDs drift or break | Medium | Executor-level uniqueness and cross-reference validation. |
| Result size grows | Low | Reuse existing attention limit; map returned items only. |
| Empty recommendation is misread as permission for model invention | High | Descriptor capability plus explicit Copilot prohibition. |
| Trace retrieval appears to reproduce a full result | Medium | Preserve `trace_summary = true` and require empty intelligence arrays. |
| Phase 1 absorbs Attention lifecycle work | High | No acknowledgement, snooze, owner, resolution, persistence, or new scoring. |
| Operational identifiers leave the approved environment | High | Existing local-only and sanitization boundary remains unchanged. |

## Implementation batches after approval

### Batch B1 — Contract and validation

- add typed intelligence objects and empty result defaults;
- add shared shape/reference validation;
- add unit tests for valid, empty, missing, conflicting, and invalid references.

### Batch B2 — Discovery and transport

- add accurate descriptor capability metadata;
- verify list/describe, structured CLI, generic Dashboard, and trace-summary
  behavior.

### Batch C — Management Attention reference mapping

- map current returned attention items into facts and signals;
- add only the evidence required for reference integrity;
- preserve existing ordering, summaries, context, and data;
- update Copilot result-handling instructions.

### Batch D — Regression and promotion

- run focused contract and management-attention tests;
- run `make validate`;
- run `make rehearse-release`;
- review portable scope and confirm no schema change;
- update `PROGRESS.md` and the implementation report;
- obtain explicit Phase 1 promotion decision.

## Non-goals

- no new embedded model or agent;
- no multi-agent orchestration;
- no replacement of `UseCaseResult`;
- no contract-version bump;
- no database schema change;
- no full-result persistence;
- no migration of all nine use cases;
- no Project Health redesign;
- no Attention lifecycle or persistence;
- no Forecast, Simulation, or resource recommendation behavior;
- no new write operation;
- no tag, merge, deployment, connector call, or real-data UAT.

## Approval gate

Owner approval was recorded on 2026-07-27. It authorizes preparation of a
Phase 1 implementation pack and sequential execution of the bounded batches
above. Batch B1 must be implemented and validated before B2 begins.

Owner promotion was recorded on 2026-07-28 after all Phase 1 batches passed.
Phase 1 is complete as a local development baseline.

Promotion does not authorize Phase 2 implementation, release tagging, merging,
pushing, connector access, active database migration, or real-data operations.
The next action is a new Phase 2 design task.
