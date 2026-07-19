# IP-004 Implementation Report

Status: `IMPLEMENTED LOCALLY — CONTEXT REFERENCE VALIDATED`
Branch: `codex/ip-000-baseline-safety`
Date: 2026-07-19

## Outcome

Added the first bounded context package, `TeamCapacityContext`, to the existing
read-only `team-workload-overview` result. It is built deterministically from
the IP-003 structured result; it performs no extra database query and makes no
write.

The VS Code Copilot workload prompt now explicitly consumes this context. It
must describe the capacity period as current, state evidence/freshness/
assumptions/warnings and execution ID, and recommend verification when source
state is not fresh.

## Context contract

- `context_type`: `team_capacity`; version `1.0`.
- Scope: requested team and fixed `effective_period: current`.
- Summary: member count, available/overloaded counts, average and maximum load.
- Members: stable ID, display name, current load, active-project count, and a
  deterministic availability classification.
- Supporting fields: evidence, freshness, assumptions, warnings, alternatives,
  rule version, truncation state, and execution metadata.

Availability classification deliberately reuses workload thresholds:

- `< 80%`: available
- `80%` to `< 100%`: allocated
- `>= 100%`: overloaded

## Bounds and limitations

The context retains at most 20 members, sorts them deterministically by current
load then stable ID, and reports omitted-member count. It represents only active
assignments at execution time. It does not claim next-week capacity, future
plans, unrecorded work, staffing feasibility, or authority to assign a person.

## Modules changed

- `src/pm_agent/use_cases/service.py`: structured context field on the result.
- `src/pm_agent/use_cases/team_capacity_context.py`: pure bounded context
  builder.
- `src/pm_agent/use_cases/team_workload.py`: attaches the context to the
  existing reference result.
- `.github/prompts/dm-workload.prompt.md`: grounded Copilot explanation rules.
- `src/tests/test_unified_use_case_contract.py`: context schema,
  classification, sorting, and truncation coverage.

## Validation

- Focused context and regression tests: `25 passed`.
- Full runtime test suite: `54 passed`.
- Repository tool tests: `18 passed, 19 subtests passed`.
- Static compilation, portable-only audit, repository-boundary check,
  synthetic-sample check, and `git diff --check`: passed.

## Rollback

Remove the context builder and context field/population, then restore the prior
prompt text. No schema, execution trace, tool transport, business calculation,
or data rollback is required.

## Recommended next pack

Independently review and commit IP-004. Do not start IP-005 until this bounded
current-state context behavior is accepted; IP-005 must separately define
period-aware canonical staffing facts.
