# IP-028 — Phase 2 Delivery Attention Center

Status: `BATCH C1 IMPLEMENTED — REVIEW REQUIRED`
Approved: 2026-07-28
Implementation branch: `codex/phase-2-attention-center`
Design: `architecture/07_PHASE_2_DELIVERY_ATTENTION_CENTER_DESIGN.md`

## Goal

Implement the approved deterministic foundation for a local Delivery Attention
Center: durable current Attention items, safe reconciliation and lifecycle
operations, deduplicated history, and evidence-backed rule evaluation.

## Batch B scope

- Add only the approved additive Attention storage: rule catalog, one-time
  Attention operations, reconciliations, current signals, and append-only
  history.
- Implement deterministic candidate evaluation for project health, overdue
  action, source freshness, and active-assignment resource overload strictly
  above 100% load.
- Store project-health RAG label mappings, source precedence, and state
  precedence as versioned rule parameters with a local DM default and optional
  stable-anonymous-project overrides; do not hard-code project-specific RAG
  semantics into evaluation.
- Register `pending_decision_attention` as disabled; it must emit no active
  signal, recommendation, or lifecycle record.
- Implement canonical identity, semantic observation hashing, deduplication,
  safe clear/partial/failed behavior, and lifecycle transition validation.
- Implement hashed one-time preview/confirm operations for reconciliation,
  acknowledgement, snooze, and resolve; keep query paths read-only.
- Add focused synthetic unit, repository, migration, integrity, rollback, and
  concurrency tests.

## Batch B non-goals

- No Center CLI, Dashboard, Copilot, or ToolTransport interface work.
- No modification of existing `management-attention` behavior or its Phase 1
  compatibility contract.
- No connector calls, source sync, real data, automatic action creation,
  project-status write, staffing change, or decision-log interpretation.
- No activation of pending-decision detection.
- No Phase 2 promotion, release, tag, merge, or push.

## Batch B acceptance criteria

1. Approved Attention tables and indexes are additive, migration-safe, and
   synthetic upgrade/rollback tests preserve existing tables, views, and data.
2. The four active rules create stable canonical identities and valid normalized
   evidence/freshness references; repeated unchanged reconciliation creates no
   duplicate current row or history event.
   Project-health RAG mappings and precedence are validated versioned
   configuration, and missing, invalid, or unmapped inputs never clear an
   active item.
3. A disabled pending-decision rule creates no Attention item under any
   synthetic decision-log input.
4. Preview tokens are hashed, expire, can be claimed once only, and stale or
   concurrent confirmation cannot partially mutate Attention state.
5. Successful clear, partial source state, failed evaluation, acknowledgement,
   snooze, and resolve follow the approved lifecycle semantics and are
   append-only auditable.
6. Existing Management Attention, trace payload boundary, repository boundary,
   and synthetic-data checks remain unchanged.
7. Focused tests and `make validate` pass. Run `make rehearse-release` before
   Batch D because Batch B introduces schema and migration behavior.

## Stop gate

After Batch B validation or review corrections, update `PROGRESS.md`, commit
the bounded result, and stop for explicit review. Do not start Batch C
interface integration until that review is approved.

The owner accepted the Batch B result and Batch C design review findings on
2026-07-28. Batch C1 below was the only authorized next implementation and is
now stopped at its validated local result for review.

## Batch C1 scope

- Add the separate read-only `delivery-attention-center` query through the
  shared executor and `UseCaseResult 1.0`.
- Return current Attention items, pre-limit zero-filled summary counts,
  explicit reconciliation coverage, validated facts/signals/advisory
  recommendations, evidence/freshness, and optional bounded event metadata.
- Add the exact JSON-only Attention CLI preview/confirm commands and the
  dedicated `POST /api/attention/operations` Dashboard API contract defined by
  the approved design.
- Add Copilot routing that never reconciles implicitly and requires explicit
  user authorization for preview and separate explicit confirmation.
- Reject duplicate acknowledgement, unchanged snooze, repeated resolve, and
  other lifecycle no-ops before creating an operation or history event.
- Preserve `management-attention` business projections and prove that its
  query creates no Attention current/history/operation/reconciliation write.
- Use only synthetic records and stable anonymous IDs.

## Batch C1 non-goals

- No visual Dashboard Center page.
- No RAG configuration mutation interface; Batch C1 may only read the
  currently persisted versioned configuration through rule evaluation.
- No activation of `pending_decision_attention`.
- No connector call, source sync, real record, automatic action/project/
  staffing/decision write, notification, push, or Phase 2 promotion.
- No change to the shared `UseCaseResult 1.0` models or existing
  `management-attention` contract.

## Batch C1 acceptance criteria

1. An empty or filtered Center result states whether a confirmed
   reconciliation covers the complete query scope; uncovered empty results
   never imply healthy or clear.
2. Query parameter member and cross-field validation, deterministic ordering,
   pre-limit summaries, resolved-only-on-request behavior, bounded newest-first
   history metadata, and result-local reference integrity follow the approved
   design exactly.
3. Every returned item has a stable fact, signal, and advisory recommendation.
   Health/action/resource recommendations block on unusable retained evidence;
   source-freshness advice remains available for its normalized limitation;
   clear/resolved recommendations are not applicable.
4. ToolTransport remains query-only. Direct executor, structured CLI, and
   generic Dashboard query serialize the same Center result.
5. Reconcile, acknowledge, snooze, and resolve are exposed only through the
   Attention-specific preview/confirm service. Tokens remain hashed at rest,
   one-time, expiring, and returned only by preview.
6. CLI and Dashboard API preserve stable service failures and reject
   caller-supplied Dashboard actor, unsupported fields/actions, lifecycle
   no-ops, and invalid confirmation without domain mutation.
7. Existing Management Attention and unrelated query/write boundaries retain
   their contracts and create no Attention side effect.
8. Focused synthetic tests and `make validate` pass. Update `PROGRESS.md`,
   create a local commit, and stop for Batch C1 review.

## Batch C2 gate

DM-operable project-health RAG configuration is a separately reviewed
Attention write capability. Batch C2 must define validated versioned
default/project-override configuration preview/confirm without executable
expressions, direct SQL, display names, or real identifiers. It requires
explicit authorization after Batch C1 review and must complete before Phase 2
may claim DM-operable RAG configuration or enter promotion review.

## Batch C1 result

Batch C1 is implemented and locally validated. Focused combined coverage
passed 69 tests, and `make validate` passed 174 runtime tests, 21
repository-tool tests with 19 subtests, Ruff, compilation, boundary/synthetic
checks, package build/inspection, and eight release validation checks.
`pending_decision_attention` remains disabled. The result is stopped for
explicit Batch C1 review; Batch C2 and Phase 2 promotion are not authorized.
