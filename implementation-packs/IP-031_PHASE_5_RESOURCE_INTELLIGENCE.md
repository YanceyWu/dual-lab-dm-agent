# IP-031 — Phase 5 Resource Intelligence

Status: `BATCH C IMPLEMENTED AND REVIEWED — OWNER ACCEPTANCE REQUIRED`
Design: `architecture/12_PHASE_5_RESOURCE_INTELLIGENCE_DESIGN.md`
Implementation branch: `codex/phase-5-resource-intelligence`
Baseline: `37d9ee704459591296acdb8024e1cb96eb9598e6`

## Accepted prerequisite

Register Phase 5 and implement only the workforce/project/plan/monthly-
allocation clean-import prerequisite. Effective capacity and every Resource
Intelligence consumer remain separately gated.

The owner accepted this prerequisite on 2026-08-01 at local commit
`624ba356ff838a89baa39138e99aa73128957339`.

## Authorized capacity-core outcome

Add only dedicated additive capacity schema, versioned synthetic commitment
package preview/confirmation and audit, deterministic effective-capacity and
overload derivation, immutable member/month readers, coverage/freshness/conflict
states, replay safety, and clean-bootstrap/integrity/rollback tests. Heatmap,
Staffing, Project Health, Skill Dependency, Attention, connectors, and public
capacity editing remain separately gated.

## Capacity-core ownership and public contracts

- Owning capability: `pm_agent.resource_intelligence`; it does not extend the
  generic database repository or the workforce/planning importer.
- Schema owner: `resource_intelligence.schema`; bootstrap only composes its
  additive DDL.
- Persistence owner: `resource_intelligence.repository`; it owns capacity
  session/run/attempt audit, immutable publications, coverage, observations,
  and derivations as one aggregate.
- Service contract: `preview_import(payload, db_path=...)` followed by explicit
  `confirm_import(session_id, db_path=...)`.
- Immutable reader contract:
  `get_effective_capacity(member_id, year, month, plan_version_id,
  db_path=...)`; absence is `unknown`, never zero or healthy.
- Workforce/planning dependency contract:
  `workforce_planning_import.read_model.dependency_snapshot(...)`; Resource
  Intelligence does not read that capability's coverage or audit tables.
- Local command: `python scripts/import_resource_capacity.py --file PACKAGE
  --dry-run`, then repeat with `--confirm` to persist.

The package schema is `resource-capacity-import-v1`. Its authoritative manifest
requires every covered member/month multiplied by exactly `leave`, `bau`, and
`non_project`. Each known observation carries its fixed authoritative source,
source reference, observed time, rule version, and monotonic source observation
version. Explicit `0.0` is known zero; an absent logical key is invalid.

## Capacity derivation and publication rules

- Base capacity is `1.0` only for an active member with complete full-month
  workforce and allocation evidence; otherwise the result is `unknown`.
- Effective capacity is `max(0, 1 - leave - bau - non_project)` and available
  capacity is `max(0, effective capacity - planned project allocation)`.
- Overload is clear at zero, amber above zero through `0.10`, and red above
  `0.10`. Observations older than 720 hours at assessment time publish `stale`.
- `unknown`, `stale`, and `conflicting` never expose effective/available
  capacity or an overload classification.
- A complete higher-version package supersedes the current publication in one
  transaction. Identical replay is idempotent; same-package conflicting replay,
  incomplete replacement scope, and non-increasing observation versions cannot
  replace the last complete current publication.
- Session, preview run, confirmation attempt, publication, derivation,
  integrity, coverage, and rollback-compatibility evidence are auditable.

## Verified gap

The existing Distribution Excel utility loads the same four concept families,
but it is a mutable local utility rather than a production clean-import
contract. It performs destructive clearing and multiple commits, has no
package/schema version, authoritative coverage manifest, explicit
preview/confirmation boundary, atomic publication, session/run/attempt audit,
conflicting-replay guard, integrity report, or software-rollback proof.

## Capability ownership and contracts

- Owning capability: `pm_agent.workforce_planning_import`.
- Schema owner: `workforce_planning_import.schema`; bootstrap may only compose
  its additive DDL.
- Persistence owner: `workforce_planning_import.repository`; it alone publishes
  the bounded package atomically into the existing `employees`, `projects`,
  `plan_versions`, and `monthly_allocations` contracts and owns import audit and
  coverage storage.
- Service owner and public Python contract:
  `preview_import(payload, db_path=...)` and
  `confirm_import(session_id, db_path=...)`.
- Local non-interactive contract:
  `python scripts/import_workforce_planning.py --file PACKAGE --dry-run` then
  the same command with `--confirm` for explicit persistence.
- Package contract: `workforce-planning-import-v1`, synthetic marker and stable
  anonymous IDs, effective-dated members, projects, plan versions, monthly
  allocation observations, authoritative member/project/plan identities,
  member-month workforce coverage, and exact allocation logical keys.

## Allowed dependencies

- SQLite and the database-path platform contract;
- existing canonical `employees`, `projects`, `plan_versions`, and
  `monthly_allocations` table contracts;
- bootstrap schema composition only; and
- existing read contracts solely for compatibility/rollback verification.

The capability must not depend on Resource Intelligence capacity internals,
Staffing operations, Project Health storage, connector payloads, presentation
adapters, live data, or a generic repository write helper.

## Validation and publication rules

- Preview validates exact fields, package and schema version, stable synthetic
  identity, effective dates, references, months, allocation range, duplicate
  logical keys, conflicting content, and manifest completeness.
- Explicit `0.0` allocation is a known observation and is persisted together
  with coverage; a missing manifest record is invalid and never becomes zero.
- Confirmation requires an empty dependency target, writes one full current
  publication in one transaction, then records integrity, authoritative
  coverage, and rollback-compatibility evidence.
- Validation, publication, derivation-independent integrity, or report failure
  publishes no partial current view. The failed attempt remains audited and is
  retryable.
- An identical package is idempotent. The same package ID with different
  content is a rejected conflicting replay and cannot replace the last complete
  publication.

## Focused test entry point and evidence

Focused capability tests:
`src/tests/test_workforce_planning_import.py` and
`src/tests/test_resource_capacity_import.py`.

Required evidence before local commit:

- focused synthetic capability tests;
- `make validate`;
- `make rehearse-release` because schema and installed behavior change;
- independent read-only diff, boundary, schema, atomicity, replay, rollback,
  and privacy review;
- correction, repeated focused/full/rehearsal validation, and repeated review.

Validation evidence is recorded in `PROGRESS.md`; passing tests alone do not
complete this pack.

## Rollback and compatibility

The new audit and coverage tables are additive. The published dependency facts
remain in the Phase 4-readable canonical tables, so the Phase 4 runtime can
ignore the additive import schema and continue read-only operation. No
effective-capacity or Staffing write switch is introduced, so rollback requires
no capacity policy marker and cannot resume a newly introduced write formula.
Installed-package rehearsal must preserve the pre-existing sample database and
prove clean bootstrap plus isolated rollback.

## Transitional debt

- The legacy Excel importer remains available for its current local/demo
  compatibility but is not the supported production clean-import path. This
  slice does not refactor or delete it.
- Effective employment intervals are carried in the bounded import contract and
  canonical member metadata plus authoritative member-month coverage because
  the promoted `employees` table has no dedicated interval columns. A later
  separately authorized capacity-core slice must consume a public reader over
  this contract, not read metadata or coverage storage directly.
- The first contract intentionally permits one clean publication into an empty
  target. Multi-version replacement is outside this prerequisite and must not
  be inferred from replay support.
- Capacity source inputs remain synthetic structured packages only. A future
  separately authorized connector/import adapter may implement the same public
  contract; this core neither selects nor calls a live source.
- The public capacity reader is deliberately a single member/month lookup. A
  heatmap/query aggregation is a later consumer gate, not hidden in this core.

## First-principles design guardrail

Use the minimum structure that protects current invariants. Every persisted
table, audit layer, field, and public contract must map to a present acceptance
criterion; hypothetical future flexibility is not sufficient justification.
When an invariant is removed, explicitly reconsider consolidation or deletion
instead of preserving accidental complexity. The accepted capacity tables are
not a template for later capabilities unless those capabilities independently
demonstrate the same atomicity, evidence, replay, and audit requirements.

## Batch C ownership and contracts

- C1 owner: `use_cases.resource_capacity_heatmap`, using only
  `resource_intelligence.read_model.list_effective_capacity`. Public ID:
  `resource-capacity-heatmap`; transport remains generic and read-only.
- C2 owner: `database.staffing_capacity`. Its sole table is the singleton
  `staffing_capacity_policy`; bootstrap composes its DDL and installs
  `capacity_required=0`. Missing policy state fails closed.
- C3 assessment owner: the existing Staffing use-case service. With the marker
  disabled it retains `staffing-feasibility-v2`; with the marker enabled it
  consumes canonical effective capacity under `staffing-effective-capacity-v1`.
- C3 transaction owner: the existing Staffing confirmation repository method.
  It depends on the public transactional effective-capacity reader and checks
  current allocation, exact derivation/publication/rule/plan evidence, and the
  effective limit before the first domain write.

No second capacity formula, heatmap storage, presentation adapter, generic
repository query, public marker command, or capacity editor is added.

Focused tests are `test_resource_capacity_heatmap.py` and
`test_staffing_capacity_consumption.py`, plus the existing capacity import,
Staffing pipeline, intelligence contract, discovery, and transport regressions.

## Batch C rollback contract

Installation alone leaves the marker disabled and is behavior-compatible with
the accepted capacity-core build. Once enabled, missing marker state or missing,
non-current, non-known, changed, or insufficient capacity blocks confirmation;
rollback must never silently resume the legacy `1.0` write assumption. The
installed-wheel rehearsal proves the disabled default and explicit synthetic
enablement only; no active operational database is changed.

## Explicitly excluded

No Project Health capacity publication; Skill Dependency; Attention; legacy
replacement; connector or real data; active operational database; Batch D;
push, merge, tag, release, or deployment.

## Current gate

The clean-import prerequisite and canonical effective-capacity core are
owner-accepted. Batch C is authorized only as three independently reviewable
boundaries: C1 read-only heatmap, C2 disabled Staffing compatibility marker,
and C3 capacity-aware Staffing assessment/confirmation behind that marker. The
candidate is repeatedly validated, independently reviewed, and committed
together with this gate record as current local HEAD. Stop for owner
acceptance. Project Health capacity publication and every later integration
remain gated.
