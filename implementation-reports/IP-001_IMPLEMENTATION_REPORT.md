# IP-001 Implementation Report

Status: `IMPLEMENTED LOCALLY — G1 VALIDATION COMPLETE`
Branch: `codex/ip-000-baseline-safety`
Date: 2026-07-19

## Outcome

Introduced a versioned, application-level use-case execution contract and
migrated exactly one low-risk, read-only reference use case:
`team-workload-overview`.

The existing CLI workload overview retains its Rich-rendered output. A new
Dashboard JSON endpoint returns the same renderer-neutral contract. Both call
the same registered implementation; neither interface owns workload routing or
business rules.

## Modules changed

- `src/pm_agent/use_cases/service.py`: versioned request/result envelopes and
  common execution metadata.
- `src/pm_agent/use_cases/execution.py`: explicit use-case registration and
  execution boundary.
- `src/pm_agent/use_cases/team_workload.py`: adapter around the existing
  workload overview service.
- `src/pm_agent/use_cases/__init__.py`: reference-use-case registration.
- `src/pm_agent/cli/commands/operations.py`: CLI overview route through the
  shared executor; member detail is intentionally unmigrated.
- `src/pm_agent/dashboard/server.py`: read-only JSON endpoint at
  `/api/use-cases/team-workload-overview`.
- `src/tests/test_unified_use_case_contract.py`: contract, failure, CLI, and
  Dashboard coverage.

## Reused components

- Existing `TeamWorkloadService.overview` calculation and repository reads.
- Existing CLI renderer and Dashboard Flask application.
- Existing temporary-database and network-denial pytest fixture.

## Deviations and remaining risks

- This slice does not persist an execution history; the execution ID is
  returned only in the result envelope. Durable trace retrieval belongs to a
  later evidence/trace pack.
- Freshness, assumptions, and alternatives are not yet first-class fields in
  the IP-001 envelope. The reference use case declares local SQLite evidence
  and no proposed writes only.
- No other use cases or write paths were migrated.

## Validation

- Focused runtime and interface tests: `17 passed`.
- Full runtime test suite: `46 passed`.
- Repository tool tests: `18 passed, 19 subtests passed`.
- Static compilation of `pm_agent`: passed.
- Portable-only source audit, repository-boundary check, and synthetic-sample
  check: passed.
- `git diff --check`: passed.

## Rollback

Remove the executor registration and Dashboard route, then restore the CLI
overview call to `TeamWorkloadService.overview`. This does not require a schema
migration or data rollback.

## Recommended next pack

Independently review this G1 slice, then author and implement IP-002 and
IP-003 before migrating another business use case or any write path.
