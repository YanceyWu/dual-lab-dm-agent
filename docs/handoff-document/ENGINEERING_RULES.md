# Engineering Rules

## 1. Product value before implementation

Every product change must identify:

- the Delivery Manager problem;
- the user starting point and end result;
- the information required;
- the judgment, decision, or action supported;
- the acceptance scenario;
- the target maturity level.

Use these maturity levels consistently:

- **L0** — design, documentation, or placeholder only;
- **L1** — code exists but is not in a real user flow;
- **L2** — locally useful, but the user manually joins information, judgment,
  or follow-up;
- **L3** — one end-to-end business judgment or decision is supported;
- **L4** — proactive discovery, evidence explanation, DM confirmation,
  execution, and follow-up closure are supported.

A running page, successful API response, or passing unit test does not by
itself establish L3 or L4.

## 2. Reuse before addition

Before creating a page, API, service, Agent behavior, job, table, or library:

1. inspect the existing call path and data model;
2. identify assets that already solve part of the problem;
3. explain why connection or a small correction is insufficient;
4. state the maintenance cost of the proposed addition;
5. obtain the required design approval.

Do not create parallel implementations of the same business concept. When
duplication already exists, select an authority and migrate incrementally;
do not perform a broad cleanup solely for architectural neatness.

## 3. Module and dependency rules

- Each business capability has one owner, one public application contract, and
  focused tests.
- Presentation calls application use cases. It does not own business rules.
- Application services orchestrate use cases and transactions. They do not
  expose storage details as domain contracts.
- Domain services own business rules and canonical concepts.
- Connectors translate source-specific data into canonical contracts and retain
  provenance.
- Persistence implements capability-owned repositories and schemas.
- Cross-capability access uses public contracts. Direct reads of another
  capability's private tables are prohibited.
- Initialization and migration composition files do not own business logic.
- A module that already owns multiple distinct responsibilities must be split
  at a behavior-preserving boundary before absorbing another responsibility.

Prefer a modular monolith. A new deployable service requires a demonstrated
need for independent lifecycle, state, permissions, reliability, or scale.

## 4. Data and database rules

For every important field or dataset, define:

- business meaning and owner;
- source fact or derived output;
- stable identity and time semantics;
- provenance and freshness;
- missing, stale, partial, and conflicting behavior;
- import, export, and regeneration path;
- retention and audit expectations.

Production readiness assumes a supported empty-database bootstrap and
versioned full re-import. A persisted capability must define:

- bootstrap ownership;
- versioned import contract;
- preview and validation;
- idempotent replay;
- audit and integrity reporting;
- derivation or regeneration behavior;
- software rollback;
- export of user-maintained source facts when continuity or migration requires
  it.

Do not add a table for a temporary workflow or cache without proving ownership,
lifecycle, query need, clean re-import behavior, and deletion strategy.

## 5. Deterministic and AI responsibilities

Deterministic code owns:

- identifiers and joins;
- calculations and thresholds;
- validation and authorization;
- data freshness and conflict detection;
- persistence and audit;
- reproducible option impacts.

The model owns:

- intent interpretation;
- comparison and explanation;
- summarization grounded in evidence;
- questions for missing information;
- explicit communication of uncertainty.

The model must not invent availability, project state, risk status, assignment,
contract facts, or write confirmation. An AI feature requires an evidence
contract, output contract, failure behavior, scenarios, and tests.

## 6. Write safety

Product writes use this sequence:

1. propose the intended change;
2. preview the exact effects and validation warnings;
3. obtain explicit confirmation from the authorized user;
4. persist atomically;
5. record an audit result;
6. make replay, retry, and stale-preview behavior explicit.

Read-only analysis is the default. A conversational statement is not implicit
write approval.

## 7. Interfaces and contracts

Copilot, dashboard, CLI, HTTP, and automation should converge on the same
application use cases. Do not duplicate business logic per interface.

Public contracts must be structured, versioned when externally consumed,
backward-compatible within the stated support window, and explicit about
evidence, warnings, uncertainty, and errors.

## 8. Testing and acceptance

Tests should cover the changed contract at the lowest useful level and the
user-reachable flow at the highest necessary level.

Required evidence depends on the change and may include:

- domain and service tests;
- API or CLI contract tests;
- schema/bootstrap/import/export tests;
- idempotency, concurrency, stale-preview, rollback, and failure tests;
- UI or Agent route verification;
- clean re-import and package rehearsal;
- a synthetic end-to-end acceptance scenario.

Do not claim product completion from test count. L3 acceptance needs a clear
business question, representative input, supported reasoning or comparison,
an actionable output, and TPO-confirmed acceptance evidence.

## 9. Maintainability

- Prefer clear code and explicit data contracts over speculative abstraction.
- Record the reason for a non-obvious rule close to its authoritative design or
  test.
- Avoid hidden global state, implicit environment assumptions, and
  order-dependent setup.
- Keep configuration, local data, credentials, generated artifacts, and source
  code separate.
- New dependencies require a current need, ownership, license/security review,
  and removal consideration.
- Accepted transitional debt must have an owner, impact, and review trigger.

## 10. Documentation and traceability

Maintain the trace where it exists:

`business scenario -> capability -> workflow -> story and acceptance criteria
-> UI/API/service/domain/data -> test evidence -> release result`

Do not duplicate current state across many files. `PROGRESS.md` owns the current
gate and exact next action. Architecture decisions own lasting design choices.
Implementation packs own bounded change scope. Release evidence owns the exact
artifact result.

## Mapping to existing repository assets

These rules consolidate the existing root `AGENTS.md`, Architecture North
Star, architecture decisions, module-growth guardrails, clean re-import policy,
controlled-write conventions, Current Product Audit, and DM Scenario Capability
Map. More specific approved decisions may add constraints but must not silently
weaken these rules.
