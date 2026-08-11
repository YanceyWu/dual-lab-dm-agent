# Repository Development Instructions

This file is the proposed development-repository `AGENTS.md` for handoff to the
engineering team. When adopted, it belongs at the repository root.

## Scope: development only

This file governs human developers, coding agents, reviewers, and repository
automation.

It is not the Delivery Manager product Agent. The maintained DM Agent and the
Agent generated into a release package are product assets for DM users. They
must be reviewed, tested, and released separately.

- Do not bundle this development file as the DM Agent.
- Do not put branch, pull-request, module, or test rules into the DM Agent.
- Do not use the DM Agent to authorize repository changes.
- A change that affects both development governance and DM behavior requires
  two explicit scopes and two separate acceptance checks.

## Product mission

This repository implements a Delivery Intelligence product for Delivery
Managers. Its purpose is to help a DM assemble evidence, identify uncertainty
and conflicts, make a delivery or resource decision, and follow the result.

The product is not a generic chatbot and is not a collection of unrelated
pages, services, agents, and database tables.

The current priority is to connect, simplify, and complete valuable existing
capabilities into an approved DM Golden Path. Do not continue feature expansion
without an explicit TPO decision.

## Authority and reading order

Before changing the repository, read:

1. this `AGENTS.md`;
2. `PROGRESS.md` for the current branch, gate, evidence, and next action;
3. the TPO-approved scenario, user story, or bounded implementation pack;
4. `docs/handoff-document/ENGINEERING_RULES.md`;
5. `docs/handoff-document/DEVELOPMENT_WORKFLOW.md`;
6. `docs/handoff-document/ARCHITECTURE_GOVERNANCE.md`;
7. relevant architecture decisions, code, schema, and tests.

Current code and reproducible behavior are the implementation evidence.
Documentation is intent or history unless it has been revalidated. Tests prove
the tested contract; they do not by themselves prove DM usefulness.

If the requested work conflicts with this file or has no clear product owner,
acceptance criteria, or approval boundary, stop and ask for a decision.

## Required behavior before implementation

For every change:

1. State the DM problem or engineering problem being solved.
2. Identify the affected user workflow and desired outcome.
3. Inspect the actual UI, API, application service, domain logic, persistence,
   Agent/tool route, and tests involved.
4. Identify existing assets that can be reused.
5. Define the smallest bounded change and explicit non-goals.
6. Name the owning module, public contract, data authority, and focused test
   entry point.
7. Obtain TPO approval for product behavior and technical-lead approval for a
   material architecture, public-contract, dependency, or schema change.

Do not infer authorization from a roadmap, old design, passing test, existing
table, or partially implemented feature.

## Engineering constraints

- Preserve the usable system through incremental, reversible change. No broad
  rewrite is authorized by default.
- Prefer reuse and connection over a new page, Agent, service, module, table,
  framework, or abstraction.
- Keep a modular monolith and one DM product Agent unless an approved need
  demonstrates otherwise.
- Keep presentation, application use cases, domain logic, platform services,
  connectors, and persistence responsibilities separate.
- Depend on public capability contracts, never another capability's storage
  internals.
- Deterministic code owns validation, filtering, calculations, authorization,
  and persistence. The model interprets, compares, explains, and communicates
  uncertainty.
- All state-changing product operations follow propose, preview, explicit
  confirm, persist, and audit.
- Missing, stale, partial, or conflicting evidence must remain visible. Never
  convert unknown information into zero, healthy, or complete.
- Keep source facts separate from derived outputs. Derived outputs must be
  reproducible from supported inputs.
- Use synthetic data and stable anonymous identifiers in the repository. Do not
  store credentials, real records, internal URLs, employee names, project
  names, customer data, or proprietary identifiers.

Detailed rules are in `docs/handoff-document/ENGINEERING_RULES.md` and
`docs/handoff-document/ARCHITECTURE_GOVERNANCE.md`.

## Change and approval boundary

A defect correction or connection of existing capability may proceed only when
its behavior, affected modules, compatibility expectations, and acceptance
tests are clear.

A new capability, new persistence, new public contract, new dependency, major
refactor, or change to DM product behavior requires a reviewed design before
implementation.

The following always require separate explicit authorization:

- real connector or real-data access;
- destructive data operations or irreversible migration;
- release-package or DM Agent behavior changes;
- push, merge, tag, deployment, publication, or production UAT;
- advancement into the next product slice.

## Validation and review

Every implementation batch must include:

- focused tests for the changed contract and failure cases;
- relevant regression validation;
- clean re-import and release rehearsal when schema, import, packaging, or
  operational contracts change;
- an independent read-only review of the completed diff;
- correction and re-review of accepted findings;
- evidence that the production-reachable user path exists, when product
  usability is claimed.

A documentation-only change may use focused reference checks and diff review
when it changes no runtime behavior, schema, data contract, generated artifact,
Agent behavior, configuration, or operational command.

## Continuity and completion

Update `PROGRESS.md` after every material code, architecture, test, security,
data-model, migration, packaging, or product-behavior change. Record:

- what changed and why;
- validation and review evidence;
- decisions and unresolved risks;
- the exact next approved action;
- branch, commit, and push state.

Completion reporting must state, in this order:

1. what changed and why;
2. what is usable and how it is reached;
3. impact on existing modules, data, and compatibility;
4. intentionally excluded scope and the next gate;
5. test, acceptance, and review evidence;
6. commit and push status.

Then stop. Do not automatically start the next slice.

## Mapping to existing repository assets

This handoff version consolidates rules currently distributed across the root
`AGENTS.md`, `PROGRESS.md`, `docs/DEVELOPER_ONBOARDING_INDEX.md`, the Current
Product Audit, the DM Scenario Capability Map, Architecture North Star,
architecture decisions, and implementation-pack conventions. Those files
remain evidence and history; this file is intended to become the short
operational entry point for future development.
