# Architecture North Star

## Product definition

A local Delivery Management intelligence system that consolidates operational
data, maintains a unified management view, and supports recurring delivery
decisions through deterministic analysis and AI-assisted reasoning.

## Primary users

Delivery Managers responsible for approximately 40 people, multiple projects,
resource allocation, delivery health, and contract continuity.

## Core outcomes

- One trusted management view across source systems.
- Fast answers to recurring management questions.
- Evidence-backed resource and delivery recommendations.
- Safe, explicit manager control over all writes.
- Incremental capability expansion without multiplying source coupling.

## Core flow

```text
Enterprise sources and exported files
              |
              v
Connectors -> Raw records + provenance
              |
              v
Canonical Delivery Model
              |
              v
Domain services and deterministic analysis
              |
              v
Decision use cases + grounded AI reasoning
              |
              v
Manager decision and confirmed persistence
```

## Architectural stance

The product is not primarily a chatbot. The agent is one interface to a Delivery
Management Decision Support System. CLI, HTTP, dashboard, and agent interfaces
must converge on the same application use cases.

## Near-term V1 scope

- Management attention review.
- Project health review.
- Staffing recommendation and new-demand impact.
- Action follow-up.
- Weekly Delivery Manager brief.
- Contract renewal risk review.

## Non-goals

- Multi-agent orchestration without a concrete independent-state requirement.
- A full rewrite of the current working system.
- Letting the model invent availability, assignment, or contract facts.
- Automatic personnel evaluation.
- Silent writes to assignments, decisions, or project state.

