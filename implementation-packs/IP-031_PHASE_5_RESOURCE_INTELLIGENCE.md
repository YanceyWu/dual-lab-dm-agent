# IP-031 — Phase 5 Resource Intelligence

Status: `IMPORT PREREQUISITE IMPLEMENTED AND REVIEWED — OWNER ACCEPTANCE REQUIRED`
Design: `architecture/12_PHASE_5_RESOURCE_INTELLIGENCE_DESIGN.md`
Implementation branch: `codex/phase-5-resource-intelligence`
Baseline: `37d9ee704459591296acdb8024e1cb96eb9598e6`

## Authorized outcome

Register Phase 5 and implement only the workforce/project/plan/monthly-
allocation clean-import prerequisite. Effective capacity and every Resource
Intelligence consumer remain separately gated.

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
`src/tests/test_workforce_planning_import.py`.

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

## Explicitly excluded

No effective-capacity derivation; leave, BAU, or non-project calculation;
heatmap; Staffing assessment/confirmation change; Project Health capacity
publication; Skill Dependency; Attention; legacy replacement; connector or real
data; active operational database; next Phase 5 gate; push, merge, tag, release,
or deployment.

## Current gate

The clean-import prerequisite is implemented, validated, and independently
reviewed. Commit it locally and stop for owner acceptance or revision. No
effective-capacity work is authorized.
