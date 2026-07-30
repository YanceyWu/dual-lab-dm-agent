# Module Growth and Context Guardrails

Status: `ACTIVE ARCHITECTURE CONSTRAINT`
Date: 2026-07-30

## Purpose

Keep the modular monolith understandable as Delivery Intelligence gains
capabilities. The goal is not to minimize file count or impose a line-count
threshold. The goal is that a future change can be reasoned about from one
capability boundary and a small number of stable contracts.

## Required ownership model

| Concern | Owns | Must not own |
| --- | --- | --- |
| Bootstrap | schema installation order and safe migration composition | capability queries, derivation rules, import workflow, public interfaces |
| Capability repository | deterministic persistence and retrieval for one canonical concept family | connector transport, CLI/Dashboard/Copilot projection |
| Capability service | deterministic derivation or one controlled operation workflow | schema installation, unrelated capability storage |
| Use case | stable application contract and orchestration | raw SQLite details or connector payload normalization |
| Connector | source acquisition and bounded normalization | canonical business decisions or presentation behavior |
| Presentation adapter | CLI, Dashboard Tool Transport, or Copilot projection | domain calculation and persistence |

## Mandatory change rule

Before adding a feature, the implementation pack or review note must state:

1. the owning capability module;
2. the allowed input contracts and output contract;
3. the focused synthetic test entry point; and
4. whether the change creates, removes, or pays down transitional debt.

If a proposed edit would make an existing module own another independent
responsibility, split at the existing behavior boundary first. A split is
behavior-preserving unless separately authorized as a functional change.

## Current transitional debt and freeze points

- `pm_agent.database.bootstrap` still contains the embedded Phase 3 canonical
  DDL. It remains valid for the already-reviewed B2 schema, but receives no
  additional Phase 3 tables. The next authorized Phase 3 schema change first
  extracts the whole family to a dedicated schema module and leaves bootstrap
  as a composition entry point.
- `pm_agent.database.execution` currently owns two B2 responsibilities:
  canonical derivation and controlled Milestone import. It receives no third
  responsibility. The next authorized change to either responsibility first
  separates them into capability-local modules while retaining a small facade
  for callers.
- Phase 3 C1/C2/D and Phase 4 are not authorized by this document. It only
  controls where a future authorized change may be placed.

## Review checklist

- Does the change have one capability owner and an inward dependency path?
- Can its focused tests run without loading unrelated interface or connector
  behavior?
- Does it preserve the existing public contract and additive migration path?
- Did it avoid adding unrelated code to bootstrap, a shared registry, or a
  cross-capability service?
- Are remaining intentional exceptions named in `PROGRESS.md` with a concrete
  paydown trigger?
