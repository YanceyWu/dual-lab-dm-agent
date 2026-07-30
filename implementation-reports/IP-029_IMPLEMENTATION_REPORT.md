# IP-029 Implementation Report

Status: `BATCH D REVIEW PASSED — PHASE 3 PROMOTION DECISION REQUIRED`
Date: 2026-07-30
Branch: `codex/phase-3-execution-signals`
Approved design commit: `7dc51d8c0f0d0a0f7d6f5b3f6b51ff199fc62ca5`
Implementation head before this report: `a327847a09f3328fe669f073eb9512b42a875518`

## Implemented

- Added staged, cursor-protected synthetic Issue History and Issue Link evidence
  publication. Complete, authoritative manifests are required before evidence
  replaces the published view.
- Added canonical work item, Sprint, Release commitment, Milestone, Dependency,
  source identity, observation, derivation-run, input, and fact storage.
  Milestones enter only through a structured preview/confirm import.
- Added deterministic execution derivation with completeness, freshness,
  authority, temporal scope, target-history, and dependency evidence retained.
- Added the read-only `delivery-execution-review` use case and generic CLI,
  Dashboard Tool Transport, and Copilot projections. `UseCaseResult 1.0` is
  unchanged.
- Added one automatic Attention producer only:
  `critical_milestone_overdue_attention`. It opens only for a fresh, complete,
  structured critical Milestone whose known adherence fact is `overdue`; a
  complete non-match resolves it with `rule_clear`.
- Automatic reconciliation waits for a complete History-and-Links evidence
  pair. Confirmed Milestone imports refresh affected active boards. Partial or
  failed input retains the last complete active signal. A post-publication
  reconciliation failure preserves the evidence cursor and is recorded as
  `PHASE3_RECONCILIATION_FAILED`.

## Local commits

- `6415d94` — B1 source-evidence foundation.
- `7ffd495`, `bb80b4d` — B1 review corrections.
- `ee68f90`, `c8fcd60` — B2 canonical foundation and corrections.
- `27ff364` — C1 read-only execution review.
- `a327847` — C2 automatic derived Attention.

Acceptance-record commits are retained in the local branch history. No Phase 3
commit is pushed.

## Validation evidence

- Combined focused Phase 3/Attention regression: 73 tests passed, covering
  source evidence, canonical derivation, Milestone import, execution review,
  discovery/transport, Attention lifecycle, and Management Attention
  compatibility.
- `make validate`: passed with 219 runtime tests, 21 repository-tool tests and
  19 subtests, Ruff, compilation, repository-boundary checks, synthetic-sample
  checks, diff hygiene, and wheel/sdist inspection.
- `make rehearse-release`: passed temporary wheel installation, isolated clean
  bootstrap, populated synthetic upgrade, integrity checks, and rollback.
- All evidence used by tests and rehearsal is synthetic. No network, live
  connector, operational database, credentials, company record, or internal
  identifier was accessed.

## Schema, migration, and compatibility review

- Phase 3 schema is additive: evidence staging/publication and canonical
  execution tables are created by idempotent bootstrap. The installed-package
  rehearsal proves clean bootstrap and populated upgrade/rollback.
- Published cursors advance only after complete staging and survive automatic
  C2 failure; partial/failed staging cannot replace the prior published view.
- Existing Attention lifecycle and scoped manual reconciliation are reused;
  `pending_decision_attention` remains disabled.
- Existing use-case contracts, Management Attention projection, query-only Tool
  Transport, and Phase 2 Attention behavior remain compatible. No Project
  Health aggregation, Forecast, configurable health conditions, or automatic
  business-object write is introduced.

## Remaining risks and deferred work

1. The portable runtime has no verified live connector semantics; unknown
   company fields and workflows remain `UNKNOWN` until separately authorized.
2. The Phase 3 DDL remains transitional debt in `database/bootstrap.py`.
   Future Phase 3 schema work must first extract it to a dedicated schema
   module without behavior change.
3. `database/execution.py` combines derivation and Milestone import; any
   further responsibility requires the approved behavior-preserving split.
4. Remote CI, push, tag, release, deployment, active-database migration,
   real-data UAT, Phase 4 Project Health, and Phase 7 Forecast remain outside
   this batch.

## Promotion recommendation

Batch D validation, package rehearsal, migration, compatibility, and portable
scope checks are complete. The local Phase 3 implementation is ready for an
explicit owner decision to promote, revise, or reject. This report does not
itself promote Phase 3 or authorize any subsequent phase or external action.

## Independent review

The post-implementation read-only review found no P0-P2 defect. It reconciled
this report with the local commit history, 73-test focused regression, full
219-test validation, installed-package rehearsal, portable boundary checks,
and the approved no-live-data/no-Phase-4 scope. Promotion remains an explicit
owner decision.
