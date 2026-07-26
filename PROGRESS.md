# DM Agent Evolution Progress

Last updated: 2026-07-26
Current branch: `codex/ip-000-baseline-safety`
Current base commit: `c2c0b16`
Package version: `0.2.0rc1`
Current implementation pack: `IP-026 — Release Engineering`
Gate status: `CONTEXT CLEANUP VALIDATED — COMMIT/PUSH, TAG, AND REAL UAT PENDING`
Git state: base commit is pushed and GitHub Actions is green on Python 3.10 and
3.12; the validated context-cleanup working tree is not yet committed or
pushed; do not merge into `main`

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

## Current validation evidence

The pushed `c2c0b16` base passed:

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

1. This validated context-cleanup change remains uncommitted and unpushed.
2. Historical IP-000 through IP-023 and IP-025 packs/reports were deliberately
   removed from the candidate checkout; Git history remains the archive.
3. Annotated tag `v0.2.0-rc.1` is reserved but has not been created.
4. Real-environment database-copy migration rehearsal and UAT are pending.
5. The candidate remains an independent branch and must not be merged into
   `main`.

## Exact next actions

1. Review, commit, and push the validated cleanup only with owner authorization.
2. Wait for GitHub Actions on the exact pushed commit.
3. Create and push immutable tag `v0.2.0-rc.1` only with separate explicit owner
   authorization.
4. On the work computer, follow `docs/REAL_ENVIRONMENT_UAT_RUNBOOK.md`: back up,
   migrate an isolated operational-database copy, verify it, and then run
   controlled real-environment UAT.

## Decisions in force

- Do not merge or rebase this independent branch into `main`.
- Do not create, move, or push a release tag without explicit owner approval.
- Do not run migration first against an active operational database.
- Connector probing or sync requires an explicit request and approved local
  configuration.
- OAuth refresh is automatic and invisible except for safe status metadata.
- Missing or non-fresh facts remain visible; the model must not infer zero,
  healthy, available, or safe.
- All writes follow propose, preview, confirm, persist.

## Recent change log

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
