# Roadmap

## Wave 0 — Safety net

- Capture current behavior snapshots and smoke tests.
- Establish execution IDs, use-case IDs, warnings, and source freshness.
- Maintain an internal current-architecture baseline.

## Wave 1 — Shared execution contract

- Implement IP-001 with one low-risk, read-only use case.
- Reuse the same implementation from at least two interfaces.
- Validate behavior preservation and rollback.

## Wave 2 — Boundary classification

- Classify existing capabilities as UC, DS, PS, or CN.
- Remove user-use-case dependencies on other user use cases.
- Introduce canonical contracts around existing tables without bulk migration.

## Wave 3 — Staffing reference slice

- Model demand, assignment, capacity, skill, and contract constraints.
- Keep eligibility, allocation math, and scoring deterministic.
- Use model reasoning only to compare computed options and explain uncertainty.
- Add synthetic golden staffing scenarios and evidence contracts.

## Wave 4 — High-value use cases

- Project Health.
- Management Attention.
- Weekly DM Brief.
- Contract Renewal Risk.
- Release Readiness.

## Wave 5 — Connector decoupling

- Standardize acquisition, provenance, freshness, and mapping contracts.
- Move source-specific behavior out of use cases and domain services.
- Add connector fixtures, retries, partial-failure behavior, and observability.
