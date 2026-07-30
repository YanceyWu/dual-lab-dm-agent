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

## Module growth guardrails

- Do not add a new business capability by extending an unrelated existing
  module. Identify the owning bounded capability, its public contract, and its
  focused test entry point before editing runtime code.
- `database/bootstrap.py` is an initialization and migration-composition
  boundary, not a home for capability rules, queries, transactions, or public
  service behavior. The existing embedded Phase 3 DDL is transitional schema
  debt: do not add tables to it. The next authorized Phase 3 schema change must
  first extract that family into a dedicated schema module without changing
  behavior.
- A module that owns both a derivation pipeline and a controlled write/import
  flow must not absorb a third responsibility. For Phase 3, further changes to
  `database/execution.py` require first splitting derivation and Milestone
  operation code at a behavior-preserving, separately reviewable boundary.
- New use-case, connector, presentation, and persistence concerns remain in
  their respective layers. A dependency may point inward to a capability
  contract, never sideways into another capability's storage internals.
- An implementation pack and `PROGRESS.md` entry must name the module owner,
  allowed dependencies, validation evidence, and any intentional transitional
  debt. Do not use an arbitrary line-count limit as a substitute for cohesion.
- After every implementation batch, perform an independent read-only review
  before requesting acceptance or advancing a gate. Record findings, correct
  all accepted defects, and repeat the review; passing tests alone do not
  replace this step.

## Deliverable rules

- External instructions state architecture intent, contracts, constraints,
  acceptance criteria, and local discovery steps.
- Do not invent internal file names or prescribe repository-specific edits.
- Every implementation pack must be independently reviewable and reversible.
- Use `UNKNOWN` instead of guessing about the company repository.

## Progress continuity

- Read `PROGRESS.md` before starting repository work in every new session.
- Update `PROGRESS.md` after every material code, architecture, test, security,
  data-model, or migration change.
- Record what changed, validation evidence, decisions, unresolved risks, and the
  exact next recommended action.
- Keep the current-state summary accurate; append concise entries to the change
  log instead of relying on chat history.
- Never put confidential values or company-derived details in the progress log.
- Before ending a development turn, verify that `PROGRESS.md` reflects the actual
  working tree and whether changes were committed or pushed.
