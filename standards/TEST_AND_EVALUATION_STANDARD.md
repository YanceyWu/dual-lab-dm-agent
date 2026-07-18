# Test and Evaluation Standard

## Minimum layers

- Contract tests for use-case input and output schemas.
- Unit tests for deterministic filters, calculations, and scoring.
- Repository and connector tests with sanitized fixtures.
- Golden scenarios for management reasoning and evidence quality.
- Regression snapshots for existing interfaces during migration.
- Smoke tests for each supported runtime entry point.

## Observability

Record execution ID, use-case ID, selected context types, source freshness,
components invoked, model version, prompt version, rule version, warnings,
proposed writes, confirmation result, duration, and outcome.

Do not log credentials or unrestricted raw source content.

## Promotion gate

A migrated use case is promotable only when legacy behavior is preserved or an
approved behavior change is documented, focused tests pass, evidence is visible,
failure behavior is defined, and rollback is practical.

