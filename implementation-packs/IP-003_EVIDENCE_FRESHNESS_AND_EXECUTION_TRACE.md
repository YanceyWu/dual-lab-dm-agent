# IP-003 — Evidence, Freshness, and Execution Trace Envelope

## Business goal

Make the reference use-case result understandable and safe for a Delivery
Manager by showing what facts were used, their freshness, important gaps, and a
traceable execution outcome.

## Architecture intent

Evidence and trace information are product-core contracts assembled by the
application layer. Connectors provide source state; use cases expose only the
bounded evidence needed for their decision. The model explains these fields but
does not create authoritative facts from prose.

## Verified current problem indicators

- IP-001 returns an execution ID and a small local SQLite evidence item.
- The result contract has no first-class `freshness`, `assumptions`, or
  `alternatives` fields, and its execution ID is not durably retrievable.
- The existing data-source and sync-run concepts can provide source-state data,
  but their applicability to the workload reference must be verified without
  exposing connector configuration or raw records.

## Required outcome

Extend the shared result envelope and reference use case so it can return
bounded evidence, freshness, assumptions, warnings, alternatives, and durable
execution trace metadata. Support the existing reference use case only.

## Required contracts

Add versioned, JSON-serializable fields to `UseCaseResult`:

```text
evidence[]
  evidence_id, source_kind, entity_kind, record_count, applied_filters
freshness[]
  source_id, state: fresh | stale | unknown | unavailable | partial,
  observed_at, last_success_at, refresh_sla_hours, warning
assumptions[]
  code, statement, impact
alternatives[]
  code, summary, availability_reason
execution_metadata
  execution_id, use_case_id, operation, actor, correlation_id,
  started_at, finished_at, duration_ms, outcome, component_versions
```

Add a local execution-trace persistence contract with a bounded retention and
no raw business payload. It must store the execution metadata, status,
redacted/count-based evidence summary, freshness state, warning codes, and
proposed-write count. A lookup by execution ID returns this safe trace only.

## Mandatory constraints

- Do not log credentials, URLs, raw connector payloads, full employee records,
  or unrestricted result data.
- Do not treat no data as fresh or connector failure as an empty successful
  result.
- Do not migrate connector code, change business calculations, or add writes to
  the reference use case.
- Reuse existing local source/sync state where it is applicable; otherwise
  return explicit `unknown` freshness with a warning.
- All persistence must be local, migration-safe, tested, and reversible.

## Local repository discovery

Before implementation, inspect and record:

- the current data-source and sync-run schema, repositories, and migration
  approach;
- the executor's exception and status behavior;
- local logging and backup rules;
- the reference use case's actual repository reads and their source-state
  coverage;
- existing synthetic fixtures for fresh, stale, unavailable, and no-data cases.

Use `UNKNOWN` rather than guessing when a source cannot be mapped to a tracked
freshness state.

## Reference migration scope

- Add envelope fields and trace persistence for `team-workload-overview` only.
- Build a bounded workload evidence/freshness recipe from local canonical data
  and applicable source state.
- Add result-by-execution-ID retrieval to the application executor, not to a
  Copilot-specific layer.
- Expose the same trace-safe result through the IP-002 transport only after both
  packs have passed their independent validation.

## Acceptance criteria

1. A successful reference result exposes evidence, freshness, assumptions,
   warnings, alternatives, and complete execution metadata.
2. Trace lookup returns a durable, redacted summary by execution ID.
3. Fresh, stale, unknown, unavailable, and partial source conditions remain
   distinguishable in synthetic tests.
4. An unavailable dependency produces an explicit unavailable or partial result
   and an actionable warning, never a false empty success.
5. No raw business row, credential, endpoint, or connector payload is persisted
   in trace data.
6. Existing workload calculations and interface output remain semantically
   equivalent.
7. The trace schema migration has a tested rollback or verified restore path.

## Non-goals

- Full context-package construction (IP-004).
- Connector migration or retry-policy changes.
- Copilot prompt engineering beyond consuming the structured fields.
- Any staffing or other business use-case migration.

## Test and validation requirements

- Envelope schema and trace redaction contract tests.
- Synthetic happy, no-data, stale, unknown, partial, and unavailable scenarios.
- Trace persistence/retrieval and migration rollback tests.
- Existing CLI and Dashboard regression tests.
- Static compilation, full runtime tests, repository tool tests, portable-only
  audit, repository-boundary check, synthetic-sample check, and diff check.

## Rollback requirements

The schema migration must be reversible or covered by a verified backup/restore
path. Removing the trace adapter must leave workload business data intact and
must not prevent legacy CLI or Dashboard behavior.

## Required final report

Report the verified source-state mapping, exact redaction rules, trace retention
policy, migration/rollback evidence, tests, known unknown-freshness cases, and
the recommended next pack.
