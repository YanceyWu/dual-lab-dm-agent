# IP-030 — Phase 4 Seven-Dimension Project Health

Status: `BATCH B IMPLEMENTED — OWNER REVIEW REQUIRED`
Design: `architecture/11_PHASE_4_SEVEN_DIMENSION_PROJECT_HEALTH_DESIGN.md`
Implementation branch: `codex/phase-4-project-health-design`
Baseline: `bdfee9c7c764ea5eff353b31e7a1d5873577192b`

## Goal

Implement the approved layered Project Health assessment without converting
missing evidence into health, replacing the legacy grade, or allowing arbitrary
configuration logic.

## Approved-scope candidate

This pack is effective only after owner approval of its design. It follows the
four batches in the design: A supported clean re-import plus catalog/read
projection, B controlled configuration and assessment, C separate read-only
review plus a later Attention decision, and D regression/promotion.

## Constraints

- Preserve `UseCaseResult 1.0`, legacy snapshots, current Management Attention,
  and Phase 2 Attention behavior.
- Reuse only promoted canonical facts; absent Quality, Resource, or Governance
  facts must remain `not_available`.
- Configuration uses propose/preview/confirm/persist; it cannot configure
  prompts, SQL, expressions, source paths, or factor definitions.
- No automatic business-object write, Forecast, Phase 5+ work,
  `pending_decision_attention` activation, live connector, or real data.
- Production adoption uses clean initialization plus full authorized re-import;
  this pack does not require current operational-record migration or backfill.
  Batch A must provide a versioned structured package, local non-interactive
  import path, preview/validation, import audit, idempotent replay, coverage
  report, and clean-bootstrap/full-import integrity tests. It still requires
  software rollback rehearsal.
- Each batch is independently reviewable/reversible and requires focused
  synthetic tests, full validation, and review before the next batch.

## Current gate

The owner accepted the corrected Batch A result and separately authorized
Batch B. The bounded implementation is complete and awaits owner review;
Batch C and later work remain separately gated.
