# IP-003 Implementation Report

Status: `IMPLEMENTED LOCALLY — G2 VALIDATED LOCALLY`
Branch: `codex/ip-000-baseline-safety`
Date: 2026-07-19

## Outcome

The `team-workload-overview` reference result now returns bounded evidence,
freshness, assumptions, warnings, alternatives, and execution metadata. Each
executor invocation persists a safe execution trace, retrievable by execution
ID through the application executor.

## Verified source-state mapping

The workload result maps only the two registered local source-state records that
can contribute to the member/skill workload view:

- `import-resource-portal`
- `import-skills-matrix`

States map to `fresh`, `stale`, `partial`, `unavailable`, or `unknown`. A
missing registration or a source not yet synced is explicitly `unknown`; a
failed source is `unavailable`. The deterministic workload calculation itself
is unchanged.

## Modules changed

- `src/pm_agent/use_cases/service.py`: first-class freshness, assumptions, and
  alternatives result fields.
- `src/pm_agent/use_cases/team_workload.py`: reference evidence/freshness recipe
  and explicit assumptions/warnings.
- `src/pm_agent/use_cases/execution.py`: duration/outcome metadata, safe trace
  persistence, failure classification, and trace-summary retrieval.
- `src/pm_agent/database/bootstrap.py`: idempotent `execution_traces` table and
  index.
- `src/pm_agent/database/repository.py`: bounded safe-trace storage/retrieval.
- `src/tests/test_unified_use_case_contract.py`: trace, freshness-state, and
  redaction coverage.

## Trace safety and retention

The trace stores only execution metadata, status, count/filter-based evidence
summaries, source-state summaries, warning codes, and proposed-write count. It
does not store the result data, employee rows, skills, connector configuration,
endpoints, credentials, or raw source payloads.

Retention is capped at the 500 most recently finished traces. The table is
append-only from the business-data perspective; removing this feature leaves
workload business tables intact. Existing local backup/restore procedures cover
the SQLite database, while rollback code may leave the safe table inert until a
future coordinated schema cleanup.

## Validation

- Focused contract, trace, freshness, CLI, Dashboard, and bootstrap tests:
  `26 passed`.
- Full runtime test suite: `53 passed`.
- Repository tool tests: `18 passed, 19 subtests passed`.
- Static compilation, portable-only audit, repository-boundary check,
  synthetic-sample check, and `git diff --check`: passed.

## Remaining risks

- A workload source without a registered or completed local sync can only be
  reported as `unknown`; the result never guesses freshness.
- The IP-002 structured transport does not yet expose trace lookup as a command;
  retrieval is available from the application executor only, as scoped by IP-003.
- No other business use case has an evidence/freshness recipe yet.

## Recommended next pack

G2 is locally validated. Before starting IP-004, intentionally review and
commit the approved portable paths, then assess the bounded context-package and
Copilot-playbook scope against this final result envelope.
