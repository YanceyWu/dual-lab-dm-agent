# Copilot Chat Interaction Memory Implementation Plan

Date: 2026-08-07
Status: Planning only; no slice is implementation-authorized by this document
Design: `docs/superpowers/specs/2026-08-07-copilot-chat-memory-design.md`
Planning branch: `copilot-chat-memory-plan`

## Goal

Implement the approved **repo-scoped Copilot Chat interaction-memory**
capability in a small ordered sequence so the assistant becomes more useful in
this repository without changing the authoritative `pm` business-fact path.

This plan covers the **overall Slice A-D implementation order**. It does not
authorize runtime coding by itself. Each slice still requires its own explicit
review gate before work begins.

## Planning assumptions

- GitHub Copilot Chat remains the main user entry.
- The capability remains repo/project-scoped only in v1.
- The capability stores only normalized interaction memory:
  - preference memory;
  - context memory;
  - follow-up memory;
  - dialogue-strategy profiles.
- Deterministic business facts, validation, persistence, and controlled writes
  remain in the existing `pm` path.
- No slice may introduce arbitrary prompt text mutation, free-form rules, a
  second agent runtime, or a second source of truth.

## Mandatory pre-slice gate

Before any write-capable implementation slice proceeds, the repository must
prove that the Copilot-facing interaction adapter can obtain a stable:

- `project_id` or repository-root fallback;
- `conversation_id`;
- `turn_id`.

If that identity contract cannot be proven, the plan must stop at a read-only /
empty-state foundation and return for a separate design decision instead of
guessing event identity.

## Ordered slice plan

### Slice A — Contract and storage foundation

#### Scope

- establish the `interaction_memory` capability boundary and public contract;
- add empty-store bootstrap support for the local persistence layer;
- implement deterministic repo/project scope resolution;
- implement capability state reporting:
  - `enabled`;
  - `disabled`;
  - `empty`;
  - `unavailable`;
  - `integrity_invalid`;
  - `scope_unknown`;
- add the `InteractionEventRef` contract and the host-identity proof gate;
- add audit and integrity-report skeletons without enabling learning writes yet;
- prove that the baseline Copilot behavior remains unchanged when the memory
  capability is empty or disabled.

#### Owner boundary

- owning capability/module family: `pm_agent.interaction_memory`;
- allowed dependencies:
  - Copilot-facing interaction adapter boundary;
  - local database/bootstrap boundary;
  - existing diagnostics / structured-result patterns;
  - existing project/workspace context inputs.

Forbidden in Slice A:

- no automatic memory learning;
- no follow-up persistence;
- no strategy composition affecting live responses;
- no new public business use case;
- no cross-repository memory.

#### Acceptance criteria

- a clean local bootstrap creates an empty interaction-memory store;
- empty-store and disabled-store diagnostics are explicit and testable;
- repo/project scope resolution is deterministic and fails closed on ambiguity;
- host-identity availability is either proven or blocks later write slices;
- no existing `pm` query path changes behavior because Slice A exists.

#### Validation

- focused synthetic bootstrap and integrity tests;
- scope-resolution tests covering project-backed, repo-root-fallback, and
  ambiguous multi-root cases;
- capability-state contract tests;
- proof that baseline interaction behavior is unchanged in empty/disabled mode;
- `make validate`;
- independent read-only review before any later slice begins.

#### Stop gate

Do not begin Slice B unless Slice A is reviewed and accepted, and the
host-identity prerequisite is resolved explicitly.

### Slice B — Read path and strategy composition

#### Scope

- implement memory selection for one chat turn;
- implement the fixed dialogue-strategy catalog;
- compose a bounded working prompt / dialogue strategy package from:
  - repository instructions;
  - current user turn;
  - selected memory;
  - selected strategy profiles;
- make the adapter-to-routing interface explicit so memory can shape context and
  answer structure without changing authoritative routing semantics;
- support explicit degraded diagnostics when the selector/composer cannot apply.

#### Owner boundary

- owning capability/module family: `pm_agent.interaction_memory`;
- allowed dependencies:
  - Slice A interaction-memory contract/state;
  - Copilot-facing interaction adapter;
  - existing routing boundary, used as a downstream authority only.

Forbidden in Slice B:

- no automatic capture of new memory;
- no follow-up writes;
- no strategy promotion/demotion learning;
- no direct mutation of business result contracts.

#### Acceptance criteria

- relevant memory is selected only within the current repo/project scope;
- the strategy catalog stays code-owned and versioned;
- memory may influence context packaging and answer structure only;
- the downstream business use case selected for the same intent remains
  behavior-preserving;
- explicit degraded states are surfaced instead of silently guessing.

#### Validation

- selector ranking tests;
- strategy-catalog applicability/suppression tests;
- contract tests proving routing meaning is unchanged;
- degraded-state tests for unavailable, disabled, and scope-unknown behavior;
- `make validate`;
- independent read-only review.

#### Stop gate

Do not begin Slice C unless Slice B proves that personalization does not widen
or reinterpret authoritative routing.

### Slice C — Controlled learning and follow-up persistence

#### Scope

- add automatic preference-memory capture with thresholding and deduplication;
- add automatic context-memory capture for bounded normalized categories only;
- add follow-up persistence only through:
  - explicit user request;
  - assistant-suggested and user-approved follow-up;
  - code-owned workflow-rule catalog entries already approved in the design;
- add dialogue-strategy priority learning using bounded outcome signals;
- enforce `InteractionEventRef`-based idempotency on every write;
- enforce sanitization and reject unsafely normalizable content.

#### Owner boundary

- owning capability/module family: `pm_agent.interaction_memory`;
- allowed dependencies:
  - Slice A identity/audit skeleton;
  - Slice B selector/composer outputs;
  - explicit confirmation signals from the interaction adapter.

Forbidden in Slice C:

- no creation of canonical Action or Decision rows;
- no copying raw query payloads or raw chat transcript into memory;
- no autonomous operational task creation;
- no arbitrary new strategy text generation.

#### Acceptance criteria

- repeated preferences strengthen one normalized record instead of duplicating;
- follow-up writes require explicit provenance and stay separate from domain
  Action/Decision memory;
- strategy learning can promote or demote fixed catalog entries only;
- repeated processing of the same interaction event is idempotent;
- unsafely normalizable content is rejected, not stored.

#### Validation

- preference threshold and deduplication tests;
- context-category and sanitization rejection tests;
- follow-up provenance and workflow-rule gate tests;
- Action/Decision separation tests;
- idempotency tests using repeated `InteractionEventRef.event_key`;
- audit-record tests proving tombstoned clear/reset behavior;
- `make validate`;
- independent read-only review.

#### Stop gate

Do not begin Slice D unless Slice C proves that learned memory stays bounded,
sanitized, and operationally separate from domain memory.

### Slice D — Control surface and operator hardening

#### Scope

- expose the memory control surface through the existing Copilot interaction
  path;
- implement:
  - `memory status`;
  - `memory summary`;
  - `memory inspect`;
  - `memory clear preview` / `memory clear confirm`;
  - `memory disable` / `memory enable`;
  - reset semantics for one repo/project scope;
- implement retention/expiry behavior:
  - context expiry;
  - follow-up lifecycle transitions;
  - strategy retirement/default reversion;
- add bounded local guidance so the user can inspect, clear, and disable memory
  without learning a second operating model.

#### Owner boundary

- owning capability/module family: `pm_agent.interaction_memory`;
- allowed dependencies:
  - Slice A-D persistence/state contracts;
  - existing Copilot command/interaction path;
  - local documentation surface.

Forbidden in Slice D:

- no dashboard-only control requirement;
- no repo-global admin console;
- no cross-project memory management;
- no hidden destructive clear without preview/confirm.

#### Acceptance criteria

- the user can inspect and clean local memory without editing stored rows
  directly;
- disabled mode stops automatic use while preserving safe inspect/re-enable
  operations;
- clear and reset affect only the current repo/project scope;
- audit and integrity behavior remains explicit after control-surface actions;
- the capability remains simpler than a user-authored knowledge base.

#### Validation

- control-surface contract tests;
- lifecycle/expiry tests by memory kind;
- clear/reset preview-confirm tests;
- disabled-state behavior tests;
- local guidance/documentation checks;
- `make validate`;
- independent read-only review.

#### Stop gate

Do not promote the capability beyond local review until the user confirms the
control surface feels simpler, not heavier, than the baseline Copilot workflow.

## Cross-slice guardrails

- never store raw business facts or raw chat transcript;
- never let interaction memory select a different authoritative business use
  case than the existing routing would select;
- never use memory to bypass `pm` controlled write paths;
- never introduce a second source of operational Action/Decision truth;
- keep all thresholds, decay rules, workflow-rule catalogs, and strategy
  catalogs code-owned in v1;
- keep every slice independently reviewable and reversible.

## Explicit non-goals

- no cross-repository or global personal memory;
- no historical chat import/backfill requirement;
- no arbitrary prompt/rule configuration surface;
- no new connector, sync, or import path;
- no release/UAT/real-data action;
- no automatic implementation beyond the accepted slice boundary.

## Rollback posture

Prefer software-only rollback for every slice:

- Slice A reverts the interaction-memory foundation without affecting business
  data;
- Slice B reverts selector/composer behavior and returns to baseline chat
  context assembly;
- Slice C reverts learning logic while preserving or clearing retained local
  memory according to explicit local control;
- Slice D reverts the control surface without requiring business-data repair.

The capability must remain optional from the product's point of view: the
product still works without historical interaction memory.

## Recommended first execution package

When implementation is authorized, start with a bounded **Slice A-only**
implementation package. That package should name:

- the owning module family;
- the exact public contract;
- the host-identity proof criteria;
- the bootstrap and integrity evidence;
- the focused synthetic tests;
- the stop gate preventing Slice B drift.
