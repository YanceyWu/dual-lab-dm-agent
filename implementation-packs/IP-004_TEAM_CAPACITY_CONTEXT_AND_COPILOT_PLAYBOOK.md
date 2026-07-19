# IP-004 — Team Capacity Context and Copilot Playbook

## Business goal

Let a Delivery Manager ask VS Code Copilot a capacity or availability question
and receive a concise, grounded response that clearly separates calculated
facts, evidence, freshness, assumptions, risks, and the recommended next action.

## Architecture intent

Create the first bounded Context Package, `TeamCapacityContext`, for the
existing read-only `team-workload-overview` use case. Deterministic local code
constructs the package from the structured result; Copilot interprets and
explains it but never calculates capacity or invents missing people, assignments,
or source state.

## Verified current foundation

- IP-001 provides the registered `team-workload-overview` execution path.
- IP-002 provides `pm tool list`, `describe`, and JSON `query` plus portable VS
  Code Copilot instructions and a workload prompt.
- IP-003 provides bounded evidence, source freshness, assumptions, warnings,
  alternatives, execution metadata, and safe trace summaries.
- The current workload calculation is based on active assignments only; it does
  not model an effective future period or planned capacity.

## Required outcome

Introduce one deterministic context builder and a versioned
`TeamCapacityContext` that contains only the facts needed to answer the current
workload/availability question. Update the VS Code Copilot playbook to consume
that context and return a fixed, evidence-led management response shape.

## Required context contract

```text
context_version: "1.0"
context_type: "team_capacity"
use_case_id: "team-workload-overview"
requested_scope:
  team, effective_period: "current", requested_output
capacity_summary:
  total_members, available_members, overloaded_members, average_load, maximum_load
members[]:
  anonymous/stable member ID, display name, current load, active-project count,
  availability classification
evidence[], freshness[], assumptions[], warnings[], alternatives[]
calculation:
  rule_version, calculation_basis: "active_assignments"
truncation:
  is_truncated, omitted_member_count, maximum_members
execution_metadata
```

The builder must set an explicit `unknown` or `partial` indicator whenever the
structured result has non-fresh source state. It must not add raw database rows,
connector configuration, credentials, endpoints, or unbounded historical data.

## Mandatory constraints

- Reuse the IP-001 executor and IP-003 result envelope; do not query SQLite
  from Copilot prompt text or a presentation layer.
- Keep `effective_period` fixed to `current` in this pack. Do not imply
  next-week or future-capacity accuracy before IP-005/IP-006 define periods.
- Use deterministic code for availability classification and size truncation.
- Do not migrate another business use case, connector, or write path.
- Copilot must treat unavailable, partial, stale, and unknown data as a reason
  to qualify the answer or ask for missing decision-critical information.

## Local repository discovery

Before implementation, identify and record:

- the exact workload result fields and execution statuses from IP-003;
- the deterministic workload thresholds already used by the existing service;
- the tool transport command/JSON behavior and its error status handling;
- the VS Code Copilot repository-instruction and prompt-file surfaces already
  present in `.github/`;
- the synthetic fixtures needed for happy, no-data, stale, unknown, partial,
  unavailable, and over-capacity scenarios.

Stop and report a conflict if a future-period answer would need inferred plans,
untracked source data, raw connector output, or a write operation.

## Reference migration scope

- Add a pure context builder for `team-workload-overview`.
- Add an optional structured `context` representation to its result or a
  dedicated read-only context operation, preserving existing data and renderers.
- Update the workload VS Code Copilot prompt to request the structured context
  and use its response shape.
- Add a portable playbook documenting the user question, tool call, context
  interpretation rules, response template, and failure handling.

## Copilot response playbook

For a question such as “Who can help with the current delivery workload?”:

1. Select `team-workload-overview`; ask for the exact team only if needed.
2. Invoke the structured local tool and use the generated context only.
3. State the capacity conclusion first, without inventing a future period.
4. List the relevant available/overloaded people and calculated loads.
5. State evidence, freshness, assumptions, and any warnings.
6. If source state is unknown, stale, partial, or unavailable, explain the
   limitation and recommend verification before making a commitment.
7. Do not make a staffing assignment or persist a decision.

## Acceptance criteria

1. The same structured workload result produces the same deterministic context
   for CLI, Dashboard, and Copilot use.
2. Context size is bounded and truncation is visible.
3. Current availability classifications match the existing deterministic
   workload thresholds.
4. Copilot playbook scenarios cover synthetic happy, no-data, stale, unknown,
   partial, unavailable, and overloaded conditions.
5. Every management answer can identify context evidence, freshness,
   assumptions, warnings, and execution ID.
6. The playbook does not calculate facts or use raw database/CLI output.
7. Existing CLI and Dashboard behavior remain semantically equivalent.

## Non-goals

- Future-period capacity, staffing recommendations, demand feasibility, or
  write proposals.
- Context packages for project health, contracts, actions, or weekly briefs.
- Model-host-specific orchestration, MCP, or a second LLM runtime.
- Changes to source ingestion, source freshness calculation, or database schema
  unless a strictly bounded context cache is independently justified.

## Test and validation requirements

- Unit tests for context construction, availability classification, and
  deterministic truncation.
- Contract tests for the context schema and source-state propagation.
- Synthetic playbook checks for all listed happy/failure scenarios.
- Regression tests for the structured tool, CLI workload renderer, and Dashboard
  endpoint.
- Full runtime tests, repository tool tests, static compilation, portable-only
  audit, repository-boundary check, synthetic-sample check, and diff check.

## Rollback requirements

Remove the context builder and prompt/playbook additions. The structured tool,
result envelope, local trace data, existing CLI renderer, Dashboard, database,
and business calculations must remain usable without a migration or data restore.

## Required final report

Report the verified context schema, deterministic classification rules, size
limit, actual Copilot playbook surface, scenario evidence, deviations, remaining
future-period limitations, rollback, and recommended next pack.
