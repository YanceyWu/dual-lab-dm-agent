# Copilot-Driven Local DM Architecture

## Status

This document is the detailed target architecture for evolving the existing
local PM toolkit into a reusable Delivery Manager intelligence product. It
refines, but does not replace, the architecture north star and existing ADRs.

The implementation strategy is incremental. The existing local database,
connectors, commands, dashboard, deterministic rules, and working use cases are
assets to preserve.

Portable source-independent slices may be implemented and tested in this product
lab using synthetic data, then transferred through GitHub for internal adapter
integration and real-environment validation. Real databases, exports,
credentials, identifiers, and company-specific integration details never enter
the product lab.

## Product boundary

The product is installed and operated locally by each Delivery Manager.

GitHub Copilot Agent is the natural-language interaction and reasoning layer.
The Python runtime is the authoritative local tool and data layer. The runtime
must not embed another agent framework merely to reproduce capabilities that the
Copilot host already provides.

```text
Copilot Agent
  interprets the question, selects a DM use case, compares computed options,
  explains evidence and uncertainty
                         |
                         v
Stable Agent Tool Protocol
  versioned request/result, evidence, freshness, warnings, proposed writes
                         |
                         v
Application Use Cases and Context Packages
  staffing, health, attention, weekly brief, contract review
                         |
                         v
Deterministic Domain Services
  validation, eligibility, capacity, scoring, health signals, transactions
                         |
                         v
Canonical Repository Facade
  stable DM concepts adapted over existing tables
                         |
                         v
Local SQLite, Source Registry, Sync History, and Connectors
```

## Architectural outcomes

The architecture is successful when:

1. Copilot can answer a management question through a stable use-case tool
   without inspecting SQL, raw exports, or UI-formatted command output.
2. CLI, dashboard, and Copilot reuse the same application use-case execution
   path.
3. Deterministic code owns facts, validation, filtering, calculations,
   persistence, and authorization.
4. Copilot owns interpretation, comparison, explanation, clarification, and
   uncertainty framing.
5. Every recommendation exposes evidence and source freshness.
6. Every write is proposed, previewed, explicitly confirmed, transactionally
   persisted, and auditable.
7. A new use case does not require business logic changes in every interface.
8. A new connector does not require changes to unrelated use cases.
9. Each DM receives the same product core but keeps configuration, credentials,
   exports, and operational data local.

## Current-to-target mapping

### Preserve and wrap

| Existing asset | Target role | Evolution approach |
| --- | --- | --- |
| Use-case service classes | Application use cases | Route through a shared executor; do not rewrite together |
| Service request/response models | Contract seed | Version and extend with evidence, warnings, writes, and metadata |
| Service registry | Runtime registry seed | Make registration executable and independent of interfaces |
| Scoring and validation rules | Deterministic domain logic | Correct boundary cases, add time and contract constraints, version rules |
| Repository functions | Persistence implementation | Introduce domain-oriented facades before physically splitting modules |
| Existing SQLite tables | Local persistence | Adapt behind canonical contracts; migrate only when a use case requires it |
| Data-source and sync-run tables | Provenance and freshness foundation | Reuse in every context package and connector result |
| Connector modules and sync jobs | Connector implementation | Add a shared acquisition/mapping/result contract incrementally |
| CLI | Human and automation interface | Preserve formatted output; add a stable structured-output transport |
| Dashboard | Local visual interface | Migrate endpoint by endpoint to shared use cases |
| Repository AGENTS.md | Global agent policy | Keep concise; move recurring workflows into bounded playbooks or skills |
| Existing UAT and sample data | Regression evidence | Convert high-value paths into repeatable automated and golden scenarios |

### Contain as legacy

The following patterns may remain temporarily but must not receive new business
logic:

- interface handlers that query SQLite directly;
- source-shaped dictionaries returned as public use-case results;
- use-case-specific context assembly embedded in report or dashboard code;
- independent write commits inside one manager decision;
- prompt instructions that compensate for missing deterministic rules;
- registry metadata that is not connected to executable behavior.

## Component responsibilities

### 1. Copilot Agent interface

Copilot Agent may:

- interpret natural-language management requests;
- identify the intended use case;
- request missing decision-critical parameters;
- invoke read-only or proposal tools;
- compare deterministic candidate options;
- explain evidence, assumptions, trade-offs, and risks;
- format a PM-ready answer.

Copilot Agent must not:

- calculate authoritative availability from prose;
- infer contract coverage without a tool result;
- treat missing or stale source data as current;
- query or modify the database directly in normal PM operating mode;
- convert a recommendation into a persisted assignment without confirmation;
- silently reinterpret a failed tool result as an empty business fact.

Repository-wide instructions define identity and invariant safety rules. Bounded
use-case playbooks or agent skills define repeatable workflows. The stable tool
protocol remains independent of the prompt-file mechanism so the product can
survive Copilot feature changes.

### 2. Agent Tool Gateway

The gateway is a thin transport adapter, not a second business layer.

Initial transport may be a structured CLI command. Future transports may include
HTTP or MCP, but all must call the same executor and preserve the same schemas.

Required operations:

- list available use cases and versions;
- describe a use case input/output contract;
- execute a read-only use case;
- create a write proposal;
- preview a proposal;
- confirm or reject a proposal;
- retrieve an execution result by ID.

Transport-neutral request envelope:

```text
UseCaseRequest
  contract_version
  use_case_id
  operation: query | propose | preview | confirm | reject
  actor
  parameters
  requested_output
  confirmation_token, optional
  correlation_id, optional
```

Transport-neutral result envelope:

```text
UseCaseResult
  contract_version
  execution_id
  use_case_id
  status: success | partial | invalid | unavailable | failed
  data
  evidence[]
  freshness[]
  assumptions[]
  warnings[]
  alternatives[]
  proposed_writes[]
  confirmation
  execution_metadata
```

Interfaces may render this result differently, but must not change its business
meaning.

### 3. Shared Use-Case Runtime

The runtime owns:

- use-case registration and version discovery;
- input schema validation;
- permission and operation-mode checks;
- context-package construction;
- domain-service orchestration;
- transaction and confirmation coordination;
- result-envelope construction;
- execution tracing and error classification.

The runtime does not contain use-case-specific business rules. A use case may
compose domain services but must not invoke another user-facing use case.

### 4. Context Package Builder

Each use case declares a context recipe. The builder retrieves only the
canonical facts needed for the management question.

A context package contains:

- requested scope and effective period;
- canonical entities and derived facts;
- evidence references;
- source freshness and last-success state;
- missing-data and conflicting-data indicators;
- rule and calculation versions;
- size and truncation metadata.

Context selection is driven by the decision being supported, not by all sources
that happen to be connected.

The first context packages should be:

- TeamCapacityContext;
- StaffingDecisionContext;
- ProjectHealthContext;
- ContractContinuityContext;
- WeeklyBriefContext.

### 5. Application use cases

Every use case follows the Use Case Standard and is independently testable.

V1 business use cases:

| ID | Use case | Default mode | Primary decision |
| --- | --- | --- | --- |
| UC-TEAM-CAPACITY | Team Capacity Review | Query | Who has usable capacity in a period? |
| UC-NEW-DEMAND | Assess New Demand | Query | What is the impact of additional effort? |
| UC-STAFFING | Recommend Staffing | Propose | Which feasible options best satisfy demand? |
| UC-PROJECT-HEALTH | Project Health Review | Query | What is the current health and why? |
| UC-ATTENTION | Management Attention | Query | What most needs DM attention now? |
| UC-WEEKLY-BRIEF | Weekly DM Brief | Query | What changed, what matters, and what follows? |
| UC-CONTRACT-RISK | Contract Continuity Review | Query | Which staffing commitments face contract risk? |
| UC-ACTION | Action Follow-up | Query/Propose | What is overdue or missing ownership? |

Use cases return computed facts and evidence. Copilot transforms those results
into the final conversational response.

### 6. Deterministic domain services

Initial services:

- CapacityService;
- StaffingService;
- ContractService;
- ProjectHealthService;
- ActionService;
- DecisionService;
- SnapshotService;
- FreshnessService.

Domain services:

- accept canonical inputs;
- contain no interface rendering;
- contain no source URL or authentication knowledge;
- return typed domain results and rule violations;
- expose rule/calculation versions;
- remain usable without Copilot.

### 7. Canonical Repository Facade

The facade establishes a stable semantic API over current persistence.

Initial repository contracts:

- PersonRepository;
- ProjectRepository;
- AssignmentRepository;
- CapacityRepository;
- ContractRepository;
- DeliveryEvidenceRepository;
- ActionRepository;
- DecisionRepository;
- SourceStateRepository.

These are logical contracts. They may initially delegate to the existing large
repository module and existing tables. Physical module or schema extraction is
allowed only after a vertical slice proves the boundary.

### 8. Local data zones

#### Raw/source cache

Preserves source-shaped observations, sync batch, source reference, observed
time, parser version, and processing status.

#### Canonical domain

Provides stable local concepts: Person, Project, Demand, Assignment, Capacity,
Contract, WorkItem, Release, Risk, Dependency, Action, Decision, and Snapshot.

#### Derived/evidence

Contains calculated health, staffing options, context snapshots, execution
evidence, and versioned decision proposals.

The zones may initially be logical rather than separate databases. New use cases
must consume canonical contracts rather than raw/source schemas.

### 9. Connector boundary

Connectors acquire and parse source data. They do not make management decisions.

Every connector result states:

- connector and source ID;
- sync/execution ID;
- observed and effective time;
- success, partial, unavailable, or failed status;
- rows or records observed and changed;
- raw evidence reference;
- mapping result and validation issues;
- freshness and retry metadata.

Connector failures must remain visible through context packages. A failure must
not become an empty risk list, empty project status, or zero capacity.

### 10. Proposal and transaction boundary

All writes use four states:

```text
Propose -> Preview -> Confirm or Reject -> Persist
```

A proposal contains:

- immutable proposal ID and expiry;
- actor and use-case ID;
- facts and rule versions used;
- intended writes and before/after preview;
- warnings and unresolved assumptions;
- confirmation requirements.

Confirmation must revalidate decision-critical facts that may have changed.
All writes belonging to one manager decision must commit or roll back together.

## Staffing reference architecture

Staffing is the first high-value write-capable reference slice because it proves
canonical data, deterministic analysis, Copilot reasoning, and safe persistence.

### Demand contract

```text
Demand
  project_id
  requested_effort_person_months
  start_period
  end_period or duration
  required_roles[]
  required_skills[]
  minimum_allocation
  maximum_people
  splittable
  priority
  mandatory_constraints[]
  preferences[]
```

### Deterministic flow

1. Validate demand units, period, and constraints.
2. Build a StaffingDecisionContext.
3. Calculate time-bucket capacity from the selected plan version.
4. Check current and planned assignments.
5. Check contract coverage for the full effective period.
6. Exclude hard-rule violations.
7. Score eligible candidates with a versioned rule set.
8. Construct feasible combinations that satisfy total effort.
9. Calculate impact on existing commitments.
10. Return alternatives, evidence, warnings, and unresolved assumptions.

Copilot may compare the alternatives and recommend manager actions. It may not
invent an unavailable person or change the calculated allocations.

## Multi-DM local distribution model

The distributed product has three boundaries.

### Versioned product core

- runtime and migrations;
- domain/use-case contracts;
- connectors and importers;
- Copilot instructions, agent profiles, or skills;
- sanitized sample data;
- tests and upgrade tooling.

This product core may be developed externally and transferred through GitHub
after automated and human data-boundary checks.

### DM-specific configuration

- enabled use cases;
- team and project mappings;
- scoring and policy overrides;
- source registry configuration;
- local display preferences.

### Local private state

- credentials and token caches;
- operational database;
- exports and source documents;
- backups;
- generated reports containing real data;
- local execution logs.

Local private state is never part of the distributable repository. Product-core
upgrades must preserve it through versioned, tested, reversible migrations.

## Extension rules

Adding a use case requires:

1. one use-case manifest and versioned schemas;
2. one implementation using existing domain services or a justified new service;
3. one context recipe;
4. one Copilot playbook or skill;
5. contract, deterministic, golden, and interface smoke tests.

It must not require business logic edits in CLI, dashboard, or Copilot gateway.

Adding a connector requires:

1. connector manifest and configuration schema;
2. acquisition and mapping implementation;
3. provenance/freshness integration;
4. sanitized fixtures and contract tests.

It must not require changes to unrelated use cases.

## Architecture fitness checks

The following checks are evaluated at every release:

- all migrated interfaces call the shared executor;
- no migrated use case reads source tables directly;
- every result exposes freshness or explicitly states that freshness is unknown;
- every recommendation identifies evidence and rule version;
- every write has a proposal and explicit confirmation record;
- no decision spans multiple independent commits;
- connector failure and no-data conditions remain distinguishable;
- one use case can be added without changing existing interface handlers;
- local private-state paths are excluded from distribution;
- migrations are tested from the previous supported version and are reversible or
  backed by a verified restore path.

## Explicit non-goals for the first evolution cycle

- no multi-agent system;
- no replacement of SQLite;
- no broad ORM or web-framework migration;
- no full repository-module split;
- no complete schema redesign;
- no autonomous writes;
- no embedding of a second LLM orchestration framework;
- no personnel-performance judgment.

## Decision triggers for future reconsideration

Reconsider the modular monolith only when independently measured needs require
separate lifecycle, permissions, scaling, or failure isolation.

Reconsider structured CLI as the primary Agent Tool transport only when multiple
hosts require a long-running protocol or when the Copilot environment provides a
stable transport with materially better security and operability. The use-case
contracts must remain unchanged when the transport changes.
