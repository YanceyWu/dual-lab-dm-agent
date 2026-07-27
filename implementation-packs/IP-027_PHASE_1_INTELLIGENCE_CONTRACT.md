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

## Explicit non-goals

- No descriptor intelligence capability metadata or list/describe changes.
- No Management Attention mapping or production recommendation behavior.
- No CLI, Dashboard, Copilot, connector, or real-data behavior changes.
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

## Rollback

Revert the bounded IP-027 Batch B1 commit through a reviewed inverse commit.
Because the change is additive and introduces no persistence or schema change,
rollback requires no data migration.
