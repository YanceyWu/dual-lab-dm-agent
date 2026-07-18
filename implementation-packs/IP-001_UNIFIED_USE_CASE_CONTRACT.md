# IP-001 — Unified Use Case Execution Contract

## Business goal

Allow CLI, HTTP, and future agent interfaces to invoke the same Delivery Manager
use cases.

## Architecture intent

User interfaces must not own business routing, context assembly, or domain rules.

## Current problem indicators

- Multiple entry points contain hard-coded routing.
- A new capability may require changes across many architectural areas.
- Some features bypass shared capability abstractions.

These indicators must be verified against the local repository before changes.

## Required outcome

A single application-level execution contract is introduced and used by exactly
one low-risk, read-only reference use case.

## Required contract

`UseCaseRequest`:

- use_case_id;
- actor;
- parameters;
- requested_output;
- optional confirmation_token.

`UseCaseResult`:

- status;
- data;
- evidence;
- warnings;
- proposed_writes;
- execution_metadata.

## Mandatory constraints

- Preserve existing interface behavior.
- Reuse existing repositories, connectors, logging, and renderers.
- Do not migrate all functions in this change.
- Do not introduce multi-agent orchestration or a new framework.
- Do not redesign the database.
- Writes are out of scope.

## Local discovery before implementation

Identify current entry points, routing locations, capability interface, output
renderers, persistence dependencies, logging path, focused tests, and behavior
that other components rely on. Report conflicts before editing.

## Acceptance criteria

1. At least two existing entry points can invoke the same reference implementation.
2. Existing output remains semantically equivalent.
3. Registering another use case does not require business logic in each interface.
4. Execution is traceable by use-case ID and execution ID.
5. Focused automated tests are added and pass.
6. Internal architecture documentation is updated.

## Required final report

Actual modules changed, components reused, deviations, tests executed, validation
results, remaining risks, rollback approach, and recommended next pack.

