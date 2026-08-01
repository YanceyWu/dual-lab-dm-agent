# IP-032 Implementation Report — Phase 6 Weekly Brief v2

Status: `PHASE 6 PROMOTED LOCALLY`
Date: 2026-08-01
Branch: `codex/phase-6-weekly-brief-design`
Approved baseline: `33fc6f100b36f6e54eec73e531590c186f4b0441`
Implementation head before Batch D: `3df79a1`

## Delivered scope

- B1 public read-contract prerequisites: canonical active Project manifest,
  Attention current/history, Action current/completion, and Execution
  achievement event-time contracts, each owned by its capability and consumed
  through public readers only.
- B2 snapshot and comparison core: one additive capability-owned table, hashed
  one-time preview/confirm, expiry, actor-scoped idempotency, stale and
  concurrent rejection, scope/input/baseline/statement/evidence/result
  fingerprints, immutable confirmed history, eligibility checks, and an
  integrity report that re-derives persisted rows.
- B3 nine-section deterministic composition: fixed section contract, typed
  facts/signals/recommendations with reference chains, fail-closed
  availability, exact baseline selection, and no route registration.
- Batch C shared-interface integration: opt-in `weekly-dm-brief-v2` use case
  (contract version 2.0), dedicated `pm weekly-brief` CLI, dedicated Dashboard
  `/api/weekly-brief/operations` preview/confirm endpoint, the controlled
  capture facade, and the Copilot contract with an explicit exact-preview
  approval workflow.
- Batch D regression, full validation, installed-package rehearsal, and
  independent read-only review; the owner then promoted the candidate as the
  local Phase 6 development baseline on 2026-08-01.

## Module ownership and public contracts

- `pm_agent.weekly_brief` owns the snapshot schema, repository, preview/confirm
  service, comparison, composer, and capture facade.
- `pm_agent.use_cases.weekly_brief_v2` owns the read-only v2 projection;
  `pm_agent.cli.commands.weekly_brief` owns the dedicated CLI; the Dashboard
  endpoint is the only other controlled-operation surface.
- `pm_agent.project_identity`, `attention`, `action`, and
  `database.execution_review` own the public readers consumed by the composer.
- `database/bootstrap.py` only composes the dedicated
  `WEEKLY_BRIEF_SNAPSHOT_DDL` constant; no rule, query, or transaction was
  added there.
- Legacy `weekly-dm-brief`, `WeeklyReportService`, `pm report`, and the generic
  v1 ToolTransport surface are unchanged.

## Local commits

- `cce14e4` — IP-032 Batch B1 read contracts; `8cb5f69` — B1 acceptance record.
- `da093ba` — Weekly Brief v2 snapshot core.
- `ce726f6` — Weekly Brief v2 nine-section composition; `b9c9141` — B3
  acceptance record.
- `3df79a1` — Batch C shared-interface integration; `dc0547c` — Batch C
  acceptance record.
- `c0504a6` — Batch D validation record; the promotion record is the current
  local HEAD.

All commits are local and unpushed.

## Validation evidence

- Combined focused regression: 78 synthetic tests passed covering the Weekly
  Brief v2 composer, snapshot, shared-interface, and prerequisite suites plus
  weekly report, unified discovery/transport, Attention Center, layered
  Project Health, execution review, Resource capacity, and Delivery Manager
  agent routing.
- `make validate`: 332 runtime tests and 21 repository-tool tests (19
  subtests) passed, together with Ruff, compilation, diff hygiene, wheel/sdist
  build, and 8 release validation checks.
- `make rehearse-release`: installed the built wheel into an isolated
  location; bootstrapped an empty database; upgraded an isolated populated
  copy; verified additive Weekly Brief capture preview/confirm, identical
  replay, stale/concurrent rejection, and expiry; proved prior-runtime
  rollback preserves operations/snapshots and legacy weekly behavior; and
  checked integrity without modifying the source sample database.
- All evidence is stable anonymous synthetic data. No connector, network,
  credential, company record, internal identifier, real data, or active
  operational database was accessed.

## Compatibility, integrity, and rollback

- The Weekly Brief table is additive and capability-owned; the prior runtime
  ignores it and legacy weekly behavior continues unchanged.
- A query performs no snapshot write. Identical confirmation replay is
  idempotent; changed scope/input/baseline or drifted evidence rejects preview
  or confirmation as stale and persists no confirmed baseline.
- Only confirmed structurally complete snapshots with matching scope,
  comparison-rule, and contract versions are eligible baselines. Failed or
  unconfirmed operations never replace the latest eligible baseline.
- Confirmed snapshot content is immutable; only operation status fields
  transition under the controlled lifecycle. Rollback removes v2 code and
  advertising while retaining all additive rows.
- The first v2 query on a clean database explicitly has no baseline; history
  begins only after a separate confirmed capture.

## Remaining risks and deferred work

1. Decisions Required remains `not_available` until a separately approved
   governance contract exists.
2. The execution reader does not publish collection-complete coverage, so
   achievements are bounded to explicitly evidenced Milestones with known
   event dates; collection-wide completeness is not claimed.
3. Resource concerns require an exact optional plan version; omission is
   `not_available`, never spare capacity.
4. Snapshot retention, deletion, publication, and export are outside Phase 6;
   no automatic cleanup is added.
5. Live connector semantics, company fields, source authority, and
   operational coverage remain `UNKNOWN` until separately authorized and
   sanitized.

## Explicitly unimplemented

No Skill Dependency, new Attention producer, `pending_decision_attention`
change, Decision governance, Action/Project/Staffing write, publication,
email, connector/live-data integration, active database action, push, merge,
tag, release, or deployment was performed.

## Promotion recommendation

The owner promoted the validated and independently reviewed IP-032 candidate
as the local Phase 6 development baseline on 2026-08-01. Promotion authorizes
no external action and no Phase 7 implementation; the next approved gate is a
separately approved Phase 7 Forecast v1 design and named authorization.

## Independent review

Each accepted batch received independent read-only review and repeated
validation. Batch C review found and corrected three defects before
acceptance: the Copilot contract did not register `weekly-dm-brief-v2` (the
agent routing test failed), the typed intelligence projection mislabeled
subject kinds and dropped known section states, and the Dashboard operations
endpoint omitted its interface-contract header; a focused shared-interface
suite was added. Batch D review covered contracts, privacy, clean import,
schema, rollback, traceability, freshness, and legacy compatibility and found
no remaining P0-P2 actionable finding.
