# Repository Instructions

This repository governs a portable Delivery Management intelligence system.

## Non-negotiable boundary

- Never request or store company source code, credentials, real records, internal
  URLs, employee names, project names, customer data, or proprietary identifiers.
- Use synthetic data and stable anonymous identifiers only.
- Do not propose ways to bypass DLP or one-way information controls.
- Treat all company-derived summaries as untrusted until manually sanitized.

## Architecture direction

- Preserve the existing usable base through strangler migration.
- Prefer a modular monolith and a single agent interface.
- Separate user use cases, domain services, platform services, and connectors.
- Business capabilities depend on canonical concepts, not source schemas.
- Deterministic code owns filtering, calculations, validation, and persistence.
- The model owns interpretation, comparison, explanation, and uncertainty.
- All writes follow propose, preview, confirm, persist.
- Every intelligence behavior needs evidence, an output contract, scenarios, and tests.

## Deliverable rules

- External instructions state architecture intent, contracts, constraints,
  acceptance criteria, and local discovery steps.
- Do not invent internal file names or prescribe repository-specific edits.
- Every implementation pack must be independently reviewable and reversible.
- Use `UNKNOWN` instead of guessing about the company repository.

