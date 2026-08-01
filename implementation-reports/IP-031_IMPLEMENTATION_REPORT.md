# IP-031 Implementation Report — Resource Intelligence

Status: `BATCH D VALIDATED AND REVIEWED — PROMOTION DECISION REQUIRED`
Date: 2026-08-01
Branch: `codex/phase-5-resource-intelligence`
Approved baseline: `37d9ee704459591296acdb8024e1cb96eb9598e6`
Implementation head before Batch D: `e7e24b6049155f3a001dc80b95816ba59e8f8ed1`

## Delivered scope

- Added the bounded `workforce_planning_import` clean-import prerequisite for
  stable anonymous members, projects, plan versions, and monthly project
  allocations. Its versioned synthetic package supports deterministic preview,
  explicit confirmation, atomic first publication, audit, authoritative
  coverage, integrity reporting, replay protection, and software rollback.
- Added the dedicated `resource_intelligence` capacity core. Versioned
  synthetic leave, BAU, and non-project commitment observations derive one
  immutable member/month effective-capacity and overload fact with exact
  package, source, freshness, formula, plan-version, and publication evidence.
- Added the read-only `resource-capacity-heatmap` through the generic
  `UseCaseResult 1.0` transport. It projects persisted facts and signals only;
  it has no recommendation or write path.
- Added one minimum Staffing compatibility marker, installed disabled. When
  explicitly enabled after a complete capacity publication, existing Staffing
  assessment and transactional confirmation consume and revalidate the same
  canonical capacity fact before any domain write.
- Added public project/month allocation and capacity-coverage readers. The
  existing Project Health assessment can consume an exact year, month, and plan
  version and persists Resource state in its existing factor/result tables.
  Authoritative empty is known evidence but not green; incomplete, stale, and
  conflicting evidence fails closed.

## Module ownership and public contracts

- `pm_agent.workforce_planning_import` owns the dependency package, its audit
  and coverage schema, atomic publisher, and public dependency/allocation
  readers.
- `pm_agent.resource_intelligence` owns commitment import/audit, deterministic
  capacity derivation, immutable member/month readers, aggregate project/month
  coverage, and no consumer storage.
- `use_cases.resource_capacity_heatmap` owns only the generic read projection.
- Existing Staffing services/repository own proposal and confirmation; they
  depend on the public transactional capacity reader behind the dedicated
  disabled-default policy marker.
- Existing Project Health evaluation owns factor semantics and persistence; it
  depends only on the public capacity-coverage reader and ignores same-named
  execution-store facts.
- `database/bootstrap.py` only composes dedicated schemas. No import workflow,
  capacity calculation, Project Health rule, or query was added there.

## Local commits

- `624ba35` — workforce/planning clean-import prerequisite.
- `1b33d0c` — canonical effective-capacity core.
- `e0068b8` — capacity-core acceptance and Batch C gate record.
- `5773d6c` — read-only heatmap and capacity-aware Staffing consumption.
- `e7e24b6` — Project Health capacity-coverage publication.

All commits are local and unpushed.
The Batch D rehearsal/report commit is the current local HEAD; its exact hash is
reported in the handoff.

## Validation evidence

- Combined focused capacity/Staffing/Project Health and shared-contract
  regression: 169 synthetic tests passed.
- `make validate`: 297 runtime tests and 21 repository-tool tests with 19
  subtests passed, together with repository-boundary, synthetic-sample, Ruff,
  compilation, diff-hygiene, and wheel/sdist build checks.
- Enhanced `make rehearse-release`: installed the built wheel into an isolated
  location; bootstrapped an empty database; performed workforce/planning import
  and idempotent replay; performed capacity import, derivation, audit, and
  replay; verified the disabled Staffing marker and explicit synthetic
  capacity-aware assessment; evaluated installed Project Health capacity with
  the same derivation evidence and no Attention creation; upgraded an isolated
  populated copy; checked integrity; and proved software rollback without
  modifying the source sample database.
- All evidence is stable anonymous synthetic data. No connector, network,
  credential, company record, internal identifier, real data, or active
  operational database was accessed.

## Compatibility, integrity, and rollback

- Dependency and capacity schemas are additive and capability-owned. Existing
  canonical employee/project/plan/allocation contracts remain readable.
- Identical package replay creates no duplicate current publication; conflicting
  or incomplete replacement cannot overwrite the last complete capacity view.
  Explicit zero remains distinct from a missing manifest/record.
- Installation alone preserves legacy Staffing behavior because the marker is
  disabled. Once capacity-aware behavior is enabled, a missing marker or
  missing/non-current/non-known capacity fails closed rather than silently
  resuming the legacy `1.0` assumption.
- Existing `evaluate(project_id)` retains Project Health Resource
  `not_available`. Exact scoped evaluation uses the new public reader and
  existing assessment tables. Legacy `project-health-review`, layered read
  projection, Attention behavior, and other six health dimensions are
  unchanged.
- An older software build can ignore the additive import/capacity tables and
  newly persisted factor evidence. Rollback neither deletes capability data nor
  requires migration/backfill as the supported production path.

## Remaining risks and deferred work

1. The workforce/planning prerequisite intentionally supports one authoritative
   publication into an empty target; a future replacement contract requires
   separate design and authorization.
2. Project Health capacity evaluation requires an exact internal year/month/
   plan scope. No automatic evaluation trigger or new public mutation interface
   is included.
3. The Staffing marker has no public enablement command. Operational enablement,
   database migration, and real-environment UAT remain separately gated.
4. Skill demand/evidence is not versioned or authoritative; therefore
   `resource_skill_dependency` remains `not_available`.
5. Live connector semantics, company fields, source authority, and operational
   coverage remain `UNKNOWN` until separately authorized and sanitized.

## Explicitly unimplemented

No Skill Dependency, Attention producer, `pending_decision_attention` change,
automatic assignment, public capacity editor, legacy Project Health
replacement, connector/live-data integration, active database action, push,
merge, tag, release, deployment, or Phase 6 work was performed.

## Promotion recommendation

The local IP-031 candidate has satisfied its technical Batch D gate and is ready
for the owner's explicit promote, revise, or reject decision. This is not an
automatic promotion and authorizes no later phase or external action.

## Independent review

The initial Batch D review found one accepted evidence gap: the installed-wheel
rehearsal did not yet execute the Project Health capacity projection. The
rehearsal now evaluates that installed path, verifies the exact canonical
derivation rule and green Resource result, and proves it creates no Attention.

After correction, repeated whole-branch review checked every change from the
approved baseline, dedicated schema and dependency direction, package
validation, atomic publication, replay/conflict retention, formula/state
semantics, Staffing same-transaction confirmation, Project Health reader
isolation, installed behavior, rollback, privacy, report accuracy, and gate
wording. No remaining P0-P2 or actionable finding was identified.
The final continuity pass also corrected the implementation-pack index's stale
top-level Batch C gate so every authoritative status now names the Batch D
promotion decision consistently.
