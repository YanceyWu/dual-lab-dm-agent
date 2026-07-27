# DM Agent Evolution Progress

Last updated: 2026-07-27
Current branch: `codex/delivery-intelligence-evolution-plan`
Current cleanup commit: `c068beb`
Package version: `0.2.0rc1`
Current implementation pack: `NONE — PHASE 1 DESIGN NOT YET APPROVED`
Gate status: `PHASE 0 DEVELOPMENT BASELINE ACCEPTED — PHASE 1 DESIGN OPEN`
Git state: independent planning branch created from exact validated commit
`a272890`; planning, roadmap, ADR, deferred-UAT, index, and progress changes are
committed locally on this branch and remain unpushed; do not merge or push to
`main`

## Read this first

This file is the current-state source of truth. Historical intermediate states
belong in Git history and must not be interpreted as current instructions.

## Current product

- Each Delivery Manager installs and runs the product locally.
- VS Code Copilot's `Delivery Manager` custom agent is the reasoning interface.
- Deterministic Python owns facts, filtering, calculations, validation,
  freshness, evidence, execution traces, and persistence.
- SQLite and locally configured connectors provide operational context.
- The architecture is a modular monolith with one structured agent interface;
  no embedded LLM or multi-agent runtime is planned.
- Read-only management use cases cover workload, project health, management
  attention, contract continuity, weekly brief, actions, connector status,
  connector sync results, and project snapshots.
- Staffing supports deterministic assessment and
  propose/preview/confirm/persist writes. Role is reference context rather than
  a hard eligibility constraint. HIREF number plus its project/date interval
  represents usable charge-code coverage.
- Dashboard writes use preview, explicit confirmation, one-time tokens,
  idempotency, and audit records.
- Database bootstrap owns idempotent migrations, integrity constraints,
  concurrency protection, hashed confirmation tokens, and dependent-view
  preservation.
- The recorded post-candidate evolution sequence is Phase 0 baseline proof,
  Intelligence contract, Attention, execution signals, Project Health,
  Resource Intelligence, Weekly Brief, Forecast, Simulation, and integrated
  release validation.
- The owner approved this sequence and its standard delivery gates on
  2026-07-27. The approval does not authorize Phase 1 implementation or any
  release, environment, connector, or real-data action.
- The owner accepted exact commit `a272890` as the development evolution
  baseline and deferred the `0.2.0rc1` tag, isolated operational-copy rehearsal,
  and real-environment UAT until the integrated candidate is ready. This is not
  operational or production approval.
- Each phase requires current-state inspection, bounded design approval, small
  implementation batches, focused tests, full regression, and explicit
  promotion before the next phase begins.

## Current validation evidence

The pre-cleanup `c2c0b16` candidate passed:

- 115 isolated runtime tests;
- 21 repository-tool tests, including 19 repository-boundary subtests;
- pinned validation-tool verification;
- portable Ruff and static compilation;
- repository-boundary and synthetic-sample checks;
- wheel/sdist build and packaged Dashboard asset checks;
- synthetic wheel installation, isolated database migration, integrity checks,
  dependent-view preservation, aggregate-count preservation, and rollback;
- GitHub Actions on Python 3.10 and 3.12.

The uncommitted documentation/context cleanup also passed `make validate` and
`make rehearse-release`: 115 runtime tests, 21 repository-tool tests, Ruff,
compilation, boundary and synthetic checks, package build/inspection, temporary
wheel installation, isolated synthetic database upgrade, and rollback.

The exact pushed candidate HEAD
`a272890a7b51856c033df69b5148bc8c2fa928da` passed GitHub Actions workflow
`Validate release candidate` in run `30189452632` on 2026-07-26. Both
`validate (3.10)` and `validate (3.12)` completed successfully, including
unified validation and installed-product upgrade/rollback rehearsal.

After the development-baseline decision and UAT deferral were recorded, the
independent planning branch passed `make validate`: repository boundary,
synthetic samples, 115 runtime tests, 21 repository-tool tests with 19 subtests,
Ruff, compilation, diff check, package build/inspection, and eight release
validation checks.

## Portability and data boundary

- The currently tracked runtime, tests, generic configuration examples,
  synthetic samples, tools, and documentation form the portable candidate.
- Repository checks exclude operational databases, exports, credentials,
  authentication caches, logs, backups, local environments, company
  configuration, internal documentation, and real records.
- Work-computer endpoints, credentials, database paths, source identifiers, and
  real records remain local and ignored.
- No company-derived content may be copied back without manual sanitization and
  policy approval.

## Open gates and risks

1. Historical IP-000 through IP-023 and IP-025 packs/reports were deliberately
   removed from the candidate checkout; Git history remains the archive.
2. Annotated tag `v0.2.0-rc.1` remains absent. Tagging and the current
   real-environment UAT flow are deliberately deferred rather than passed.
3. `docs/REAL_ENVIRONMENT_UAT_RUNBOOK.md` is retained as safety reference but
   must be revised and approved against the integrated candidate before use.
4. No branch may be merged or pushed to `main` under the current authorization.
5. Phase 1 implementation is not authorized and no new implementation pack is
   registered. The bounded Phase 1 output-contract design remains the next
   approval gate.

## Exact next actions

1. Complete Phase 1 Batch A architecture review of the existing request/result
   contract, executor, projections, schema, and tests.
2. Prepare the bounded Phase 1 intelligence-output contract design, scenarios,
   migration/compatibility position, acceptance criteria, and non-goals.
3. Obtain explicit Phase 1 design approval before registering an implementation
   pack or changing runtime/schema.

## Decisions in force

- Do not merge or rebase this independent branch into `main`.
- Do not push any current work to `main`; use independent `codex/` branches.
- Do not create, move, or push a release tag without explicit owner approval.
- Treat the current UAT runbook as deferred reference until it is revised and
  approved for the integrated Delivery Intelligence candidate.
- Do not run migration first against an active operational database.
- Connector probing or sync requires an explicit request and approved local
  configuration.
- OAuth refresh is automatic and invisible except for safe status metadata.
- Missing or non-fresh facts remain visible; the model must not infer zero,
  healthy, available, or safe.
- All writes follow propose, preview, confirm, persist.
- New Delivery Intelligence capabilities follow
  `architecture/05_DELIVERY_INTELLIGENCE_EVOLUTION_PLAN.md`; one phase and one
  bounded outcome are active at a time.
- Do not register or implement Phase 1 until its bounded design approval gate
  passes.

## Recent change log

### 2026-07-27 — Delivery Intelligence phase planning

- Added the durable Phase 0 through Phase 9 Delivery Intelligence evolution
  plan, standard design/implementation/regression gates, definitions of ready
  and done, and cross-session continuation rules.
- Owner approved the phase sequence and standard delivery gates. This approval
  did not authorize Phase 1 implementation, a release tag, a merge, connector
  access, migration of an active database, or real-data operations.
- Added ADR-011 for phase-gated vertical-slice delivery and updated roadmap and
  repository navigation.
- Kept IP-024 and IP-026 as the only active implementation packs. No Phase 1
  implementation pack, runtime change, database migration, tag, merge,
  connector access, or real-data operation was performed.
- `make validate` passed for this uncommitted planning batch: repository
  boundary, synthetic samples, 115 runtime tests, 21 repository-tool tests with
  19 subtests, Ruff, compilation, diff check, and package build/inspection.
- Re-ran `make validate` after recording owner approval and remote CI evidence;
  the exact `a272890` working tree plus planning changes passed the same checks
  and built the `0.2.0rc1` wheel and source distribution.
- Confirmed the exact remote candidate HEAD `a272890` passed GitHub Actions run
  `30189452632`; Python 3.10 and 3.12 validation jobs, including install,
  upgrade, and rollback rehearsal, completed successfully.
- Confirmed by read-only remote-ref lookup that reserved tag `v0.2.0-rc.1`
  remains absent. No tag was created or pushed.
- Owner accepted `a272890` as the development evolution baseline and deferred
  the release tag, isolated operational-copy rehearsal, and real-environment
  UAT until the integrated candidate.
- Created independent branch `codex/delivery-intelligence-evolution-plan`.
  Updated the roadmap, evolution plan, ADRs, implementation-pack index, and UAT
  runbook status for the deferred gate. No runtime, schema, connector,
  real-data, tag, or `main` operation was performed.
- `make validate` passed after the deferral decision was fully recorded: 115
  runtime tests, 21 repository-tool tests with 19 subtests, Ruff, compilation,
  boundary and synthetic checks, diff check, package build, and eight release
  validation checks.

### 2026-07-26 — IP-024 isolated migration rehearsal

- Repaired migration handling for dependent SQLite views and added rollback,
  integrity, concurrency, and legacy-dirty-data regression coverage.
- Synthetic isolated migration and rollback passed. Real operational data was
  not accessed.

### 2026-07-26 — IP-026 release engineering

- Added pinned unified validation, package/release identity, temporary
  wheel-install rehearsal, database upgrade/rollback rehearsal, and read-only
  GitHub Actions.
- Base commit `c2c0b16` is pushed and green on Python 3.10 and 3.12.
- No tag, publication, deployment, active-database migration, real record
  access, or merge into `main` was performed.

### 2026-07-26 — Repository context cleanup

- Removed obsolete runtime-baseline, portability-audit, release-readiness,
  reconstruction-prompt, nested Agent, legacy migration-wrapper, and unsafe
  direct project-profile writer files.
- Replaced repository onboarding, roadmap, portability status, and progress
  context with current candidate instructions.
- Owner selected the minimal candidate context: removed completed IP-000 through
  IP-023 and IP-025 packs/reports, retained only IP-024 and IP-026, and replaced
  the queue with a current candidate index. Removed material remains available
  from Git history.
- Validation passed: 115 runtime tests, 21 repository-tool tests, Ruff,
  compilation, boundary and synthetic checks, package build/inspection,
  temporary wheel installation, isolated synthetic database upgrade, and
  rollback.
- Context cleanup was committed as `c068beb` and pushed to
  `origin/codex/ip-000-baseline-safety`; no PR, tag, main-branch merge,
  publication, or deployment was performed.
