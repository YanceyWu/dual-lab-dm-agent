# Architecture Governance

## Purpose

Architecture exists to make Delivery Manager workflows reliable and the system
safe to change. It is not a reason to rewrite working code or introduce new
layers for hypothetical future needs.

The default evolution strategy is incremental: preserve usable assets, place a
clear contract around them, connect them into an approved workflow, and replace
legacy paths only when evidence supports the change.

## Architectural direction

The system is a local Delivery Intelligence product with:

- a modular monolith runtime;
- one Delivery Manager product Agent as a reasoning interface;
- shared application use cases reached by Agent, dashboard, CLI, HTTP, or
  automation;
- canonical delivery concepts between source systems and business logic;
- deterministic validation, calculation, authorization, and persistence;
- model-assisted interpretation, comparison, explanation, and uncertainty;
- manager-controlled writes;
- evidence and provenance for intelligence outputs.

No Greenfield rebuild is implied by this target.

## Logical responsibilities

| Responsibility | Owns | Must not own |
|---|---|---|
| Presentation | UI/API/CLI/Agent input and output adaptation | Business rules or direct database logic |
| Application use cases | Workflow orchestration, authorization boundary, transaction intent, output contract | Source-specific parsing or another capability's storage |
| Domain capability | Canonical business concepts, rules, decisions, and invariants | Interface-specific formatting |
| Platform services | Shared technical concerns such as time, audit, configuration, and model/tool transport | Delivery business policy |
| Connectors/onboarding | Source translation, validation, provenance, and import receipt | Canonical business judgment |
| Persistence | Capability-owned schema and repositories | Cross-capability orchestration |

The physical repository may evolve without being reorganized into generic
`frontend`, `backend`, or `database` folders. Responsibility and dependency
direction matter more than cosmetic structure.

## Capability ownership

Every business capability must have:

- a named business purpose and owning module;
- a public application or domain contract;
- authoritative data and lifecycle;
- known upstream and downstream dependencies;
- a focused test entry point;
- a supported import, derivation, and release path where applicable;
- a retirement or compatibility strategy.

A dependency may point inward to another capability's public contract. It must
not reach sideways into that capability's private tables or internal helpers.

When ownership is unclear, resolve ownership before adding behavior.

## Canonical data and source boundaries

Source-specific Jira, Confluence, Excel, and other imported fields belong at
the connector or onboarding boundary. New business rules operate on canonical
concepts rather than source schemas.

Keep these data classes distinct:

- user-maintained source facts;
- imported raw evidence and provenance;
- normalized canonical facts;
- deterministic derived outputs;
- model explanations;
- user-confirmed decisions and actions;
- audit and execution traces.

An export intended for continuity or migration must make clear which classes
are included. User-maintained facts should remain portable; derived outputs
should normally be regenerated and must not silently become new source facts.

Missing, stale, partial, and conflicting data are first-class states. They must
survive through application and presentation contracts.

## Database governance

The database is not the architecture. A table is justified only by a stable
capability-owned concept, lifecycle, access pattern, and supported data path.

Schema changes require:

- capability ownership and canonical meaning;
- versioned bootstrap or migration composition;
- empty-database clean import behavior;
- preview/validation and idempotent replay where data enters the system;
- integrity and audit expectations;
- compatibility and software rollback;
- export or regeneration treatment;
- focused schema and workflow tests.

Do not place capability queries, transactions, or rules in a bootstrap module.
Do not create a table to bypass an unclear domain contract.

## Agent and interface governance

The development `AGENTS.md` and the DM product Agent are different artifacts:

- development `AGENTS.md` governs repository changes;
- the maintained DM Agent governs user interaction with product use cases;
- the generated release Agent is verified as part of the exact release
  artifact.

The DM Agent does not own authoritative calculations or persistence. It routes
intent to approved use cases and explains structured results. Interfaces should
not implement competing versions of the same business rule.

Any DM Agent behavior change requires product acceptance in addition to code
review. Any generated Agent or bundle-instruction change requires artifact-level
release verification.

## When a design decision is required

Create or update a reviewed architecture decision when a change:

- adds or moves capability ownership;
- introduces a public contract or breaks compatibility;
- adds persistent data or changes data authority;
- changes dependency direction or crosses capability boundaries;
- adds a framework, service, connector type, model host, or deployable unit;
- changes security, privacy, authorization, or write semantics;
- changes clean re-import, export, rollback, or release architecture;
- replaces an earlier architectural decision.

The decision record should state context, selected option, alternatives,
consequences, compatibility, migration or strangler path, validation, owner,
status, and any decision it supersedes.

A local defect fix that preserves contracts and ownership does not need a new
architecture document. Record its impact and tests in the change handoff.

## Refactoring rules

Refactor when it is necessary to make an approved product change safe, remove a
confirmed ownership violation, or reduce a demonstrated handoff risk.

Do not refactor only because:

- another folder layout appears cleaner;
- a new framework is fashionable;
- future scale is imagined but not measured;
- existing code is unfamiliar;
- tests pass after a large rewrite.

Prefer a behavior-preserving boundary extraction followed by a separately
reviewed product change. Transitional debt is acceptable when its owner,
impact, constraint, and removal trigger are documented.

## Architecture review questions

Before approval, answer:

1. Which real DM workflow or engineering risk requires this change?
2. Which existing capability and contract owns it?
3. Can current assets be connected or corrected instead?
4. Does the dependency direction remain clear?
5. What is the authoritative data and how are uncertainty and provenance kept?
6. Does the change preserve deterministic versus model responsibility?
7. How does it participate in clean re-import, export, audit, and rollback?
8. What compatibility and release effects exist?
9. Which tests and user acceptance scenario prove the result?
10. Can a new developer understand and safely modify it without the original
    author?

## Mapping to existing repository assets

This document maps the Architecture North Star, existing architecture
decisions, modular-monolith and single-Agent stance, strangler migration,
canonical model, deterministic/model split, controlled writes, clean re-import,
module-growth guardrails, release separation, and the Current Product Audit's
handover risks into one concise governance reference.

Existing architecture documents remain the detailed decision history. They do
not automatically authorize new implementation, and any conflict must be
resolved through an explicit current decision.
