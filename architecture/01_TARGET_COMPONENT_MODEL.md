# Target Component Model

## Layers

### Interfaces

CLI, HTTP, agent chat, and future dashboards translate user interaction into a
shared request. They do not own business routing, context assembly, or rules.

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
Interface -> Application Use Case -> Domain Service -> Repository
                              |               |
                              v               v
                     Context Builder     Canonical Model
                              |
                              v
                         Connector Hub
```

Dependencies point inward toward stable business concepts. A business use case
must not know source URLs, authentication, raw schemas, or connector details.

## Component classification

- `UC`: user-visible business use case.
- `DS`: reusable deterministic domain service.
- `PS`: platform or operational service.
- `CN`: enterprise or file connector.

Every existing “capability” must be classified before it is migrated.

