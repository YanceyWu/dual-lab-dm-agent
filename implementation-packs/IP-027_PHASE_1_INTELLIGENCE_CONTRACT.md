# IP-027 — Phase 1 Intelligence Contract

## Business goal

Add a typed, backward-compatible vocabulary for facts, signals, and
recommendations to the existing shared use-case result so deterministic
observations, rule outcomes, and supported actions remain distinguishable.

## Batch B1 scope

- Add typed fact, signal, recommendation, and shared subject-reference models.
- Add `facts`, `signals`, and `recommendations` to `UseCaseResult` with empty
  list defaults while retaining contract version `1.0`.
- Validate bounded, non-empty, same-type-unique intelligence IDs and all
  fact/signal/recommendation references after handler execution.
- Require derived facts to identify a rule version.
- Require non-known facts to carry a null value.
- Require proposal-mode recommendations to require confirmation.
- Fail closed with `status = "failed"` and warning code
  `RESULT_CONTRACT_INVALID` without exposing validation details or payloads.
- Add focused synthetic unit tests for valid and empty outputs, missing-data
  states, duplicate IDs, missing references, and invalid recommendations.

## Batch B2 scope

- Add typed descriptor capability metadata for facts, signals, and
  recommendations, defaulting each capability to false.
- Reject non-boolean capability values and invalid descriptor capability
  objects before registration or serialization.
- Include the capability object in list and describe transport projections.
- Keep all nine production descriptors at false until a later batch implements
  real intelligence output.
- Verify direct transport, structured CLI, generic Dashboard query, and bounded
  trace-summary behavior.
- Preserve descriptor and result contract version `1.0`, existing interface
  headers, status mapping, payload fields, and empty intelligence arrays.

## Explicit non-goals through Batch B2

- No Management Attention mapping or production recommendation behavior.
- No CLI or Dashboard business calculation, Copilot instruction, connector, or
  real-data behavior changes.
- No database schema, migration, or intelligence-payload persistence.
- No Phase 2 work.

## Acceptance scenarios

1. Existing handlers return the three new fields as empty arrays without
   changing their existing data, evidence, freshness, warning, context, write,
   or execution-metadata meanings.
2. A fully referenced synthetic fact/signal/recommendation chain succeeds.
3. Unknown, unavailable, and conflicting facts require null values and remain
   valid when correctly referenced.
4. Duplicate intelligence IDs and missing fact, signal, evidence, or freshness
   references fail closed with only `RESULT_CONTRACT_INVALID`.
5. Derived facts without rule versions and proposal-mode recommendations
   without confirmation fail closed.
6. Focused tests and `make validate` pass with no database schema change.
7. List and describe expose accurate all-false capabilities for every current
   production use case.
8. Capability values accept only strict booleans, and focused tests lock the
   exact set of nine production use-case descriptors.
9. Structured CLI and generic Dashboard query results expose the same empty
   intelligence arrays as direct execution.
10. Trace retrieval remains a bounded summary with empty intelligence arrays and
   `trace_summary = true`.

## Rollback

Revert the bounded IP-027 Batch commits through reviewed inverse commits.
Because the changes are additive and introduce no persistence or schema change,
rollback requires no data migration.
