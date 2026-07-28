# IP-028 — Phase 2 Delivery Attention Center

Status: `BATCH B REVIEW CORRECTIONS IMPLEMENTED — REVIEW REQUIRED`
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
