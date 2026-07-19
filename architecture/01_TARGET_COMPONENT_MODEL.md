# Target Component Model

## Layers

### Interfaces

Copilot Agent, CLI, HTTP, and dashboard interfaces translate user interaction
into a shared request. They do not own business routing, context assembly, or
deterministic rules. Copilot is the primary natural-language reasoning interface;
the other interfaces remain usable without a model.

### Agent tool gateway

A thin transport adapter exposes versioned use-case contracts to Copilot and
other automation clients. Initial transport may be structured CLI; future HTTP
or MCP transports call the same executor. Transport changes must not change
business contracts.

### Application and use cases

User-visible decision workflows such as Staffing Recommendation, Project Health,
Management Attention, and Weekly Brief. A use case may compose domain services,
but must not depend on another user-facing use case.

### Semantic planner and context builder

The planner selects use cases and required canonical context. The context builder
retrieves only the evidence needed for the management question. Routing logic is
separate from management reasoning.

### Domain services

Deterministic management logic including Capacity, Staffing, Contract, Project
Health, Action, Decision, Release, and Snapshot services.

### Canonical delivery model

Stable concepts shared across sources: Person, Skill, Contract, Project, Demand,
Assignment, Capacity, Milestone, Release, WorkItem, Risk, Dependency, Action,
Decision, Snapshot, and SourceRecord.

### Repositories and platform services

Persistence access, source registry, run history, freshness, configuration,
backup, tracing, and authorization.

### Connectors

Source-specific acquisition and basic mapping for JIRA, Confluence, SharePoint,
CSV, spreadsheet, JSON, browser export, and manual input.

## Dependency rule

```text
Interface -> Agent Tool Gateway -> Shared Use-Case Runtime
                                            |
                           +----------------+----------------+
                           v                                 v
                 Application Use Case                Context Builder
                           |                                 |
                           v                                 v
                    Domain Service                Canonical Repository
                           |                                 |
                           +----------------+----------------+
                                            v
                                    Connector / Storage
```

Dependencies point inward toward stable business concepts. A business use case
must not know source URLs, authentication, raw schemas, or connector details.

## Component classification

- `UC`: user-visible business use case.
- `DS`: reusable deterministic domain service.
- `PS`: platform or operational service.
- `CN`: enterprise or file connector.
- `IF`: human or agent interface.
- `RT`: shared execution, context, confirmation, or tracing runtime.

Every existing “capability” must be classified before it is migrated.
