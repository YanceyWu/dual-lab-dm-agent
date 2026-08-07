# Copilot Chat Repo-Scoped Interaction Memory Design

Date: 2026-08-07
Status: Approved for planning, not implementation

## 1. Purpose

The current Delivery Manager product already has authoritative deterministic
business facts, controlled write paths, and a Copilot-facing natural-language
entry. The remaining usability gap is not missing business capability; it is
that the main user entry is GitHub Copilot Chat, but the chat does not yet
become noticeably easier and more personalized as a Delivery Manager keeps using
it inside one repository or project.

This design adds a bounded **interaction-memory capability** for Copilot Chat.
Its purpose is to help the assistant:

1. understand the user's recurring question style and preferred answer shape;
2. carry forward the right local context without making the user repeat it;
3. remind the user about unfinished follow-up items at the right time; and
4. improve the assistant's local response strategy over time.

This design does **not** change the authoritative business-fact path. Capacity,
health, attention, weekly brief, staffing, connector state, and other business
results remain owned by the existing `pm` query / propose / preview / confirm /
persist contracts.

## 2. User decisions captured in this design

This design reflects the following explicitly approved user choices:

- the main entry is **GitHub Copilot Chat**;
- memory is meant to retain **user preference**, **repeated local context**, and
  **follow-up items**, not long-lived business facts;
- preference memory may be captured automatically;
- follow-up memory is written only at meaningful confirmation points;
- the highest-priority improvements are:
  - better understanding of the user's asking pattern; and
  - stronger follow-up and next-step reminders;
- all memory is scoped to the **current repository/project only**;
- the system should work mostly in the background, but the user must have a
  clear way to inspect, clear, disable, or reset local memory;
- the term **working prompt / dialogue strategy** is preferred over raw
  "prompt" terminology.

## 3. Problem statement

Today the DM product already routes Copilot requests to approved structured
commands. That gives correctness and safety, but repeated use still has friction:

- the user must restate local preferences such as answer shape, comparison
  framing, or preferred level of proactivity;
- repeated repo-local context is not automatically reused;
- unfinished follow-up items can disappear between chats unless they already
  exist as explicit product-side Actions or Decisions;
- Copilot instructions can be rich, but they are mostly static and do not learn
  from repeated local usage patterns.

The product therefore needs a bounded personalization layer that improves the
chat experience without becoming a second source of truth, a second agent
runtime, or an uncontrolled prompt-editing system.

## 4. Scope

### 4.1 In scope

- a repo-scoped interaction-memory capability for Copilot Chat;
- memory objects for:
  - user preferences;
  - recurring local context;
  - explicit follow-up items;
  - reusable dialogue-strategy profiles with learned priority;
- a memory selection step before response generation;
- a post-response learning step that updates memory from local interaction
  signals;
- an inspect / clear / disable control surface for the local repo/project;
- synthetic validation and explicit diagnostics when the memory layer is
  unavailable or degraded.

### 4.2 Out of scope

- no new business use case;
- no new direct write path for staffing, attention, weekly brief, health, or
  connector operations;
- no storage of raw business facts, raw connector payloads, or copied query
  results as memory authority;
- no cross-repository or global personal memory in the first design;
- no arbitrary user-authored prompt text, arbitrary rules, SQL, expressions, or
  free-form strategy scripting;
- no second agent, background autonomous planner, or independent reasoning
  runtime;
- no dependence on historic chat backfill for production readiness.

## 5. Design principles

1. **Single-agent continuity**: the capability augments the existing Copilot
   interaction instead of creating a second assistant workflow.
2. **Repo-scoped only**: memory must not bleed across unrelated repositories or
   projects.
3. **Facts stay deterministic**: interaction memory may shape context and
   explanation style, but it must not invent or replace authoritative business
   facts.
4. **No silent personalization**: when the memory layer is unavailable,
   degraded, disabled, or empty, the runtime must surface that state rather than
   pretending personalization happened.
5. **Controlled writing**: preference capture may be automatic, but follow-up
   persistence still needs an explicit checkpoint.
6. **No arbitrary prompt editing**: learned behavior comes from fixed strategy
   catalog entries with bounded weights, not from open-ended prompt text
   mutation.
7. **Sanitized storage only**: interaction memory and audit records store safe
   normalized summaries and stable references only; they do not persist raw chat
   transcript, credentials, endpoints, copied business facts, or sensitive free
   text.
8. **Background by default, inspectable on demand**: the user should not need to
   manage the system constantly, but they must be able to see and clear what the
   assistant retained.

## 6. Architecture summary

The capability inserts one bounded layer around the existing Copilot-to-`pm`
flow:

```text
GitHub Copilot Chat
  -> Interaction Memory Selector
  -> Working Prompt / Dialogue Strategy Composer
  -> Existing approved Copilot routing
  -> Existing pm tool transport / use-case execution
  -> Result explanation
  -> Interaction Learning Evaluator
  -> Repo-scoped interaction-memory store
```

The existing authoritative path remains intact. The new capability only changes
how the assistant prepares context and how it records approved local interaction
signals.

## 7. Capability boundary and public contract

### 7.1 Owning capability

The new bounded capability is **Copilot Interaction Memory**.

It owns:

- local interaction-memory persistence;
- memory selection for one chat turn;
- dialogue-strategy profile ranking;
- controlled local follow-up capture;
- local inspect / clear / disable state.

It does not own:

- business-fact queries;
- source imports or connector syncs;
- existing Actions, Decisions, Attention state, or staffing proposals;
- the authoritative result contracts of existing use cases.

### 7.2 Public contract

The capability should expose a small, explicit local contract:

- `memory status` — whether the capability is enabled, disabled, empty,
  unavailable, or degraded for this repo/project;
- `memory summary` — counts and latest entries by memory kind and state;
- `memory inspect` — bounded read projection of retained items;
- `memory clear preview` / `memory clear confirm` — controlled removal or reset;
- `memory disable` / `memory enable` — explicit local behavior toggle;
- `memory diagnostics` — integrity and freshness-style health of the interaction
  store itself.

This is a local product capability, not an external integration surface.

### 7.3 Execution placement

The capability must run in the existing Copilot-facing interaction adapter, not
inside the deterministic business use-case executor.

- the **Interaction Memory Selector** and **Working Prompt / Dialogue Strategy
  Composer** run immediately before the existing approved Copilot routing step;
- the **Interaction Learning Evaluator** runs immediately after response
  assembly and only observes:
  - selected memory identifiers;
  - selected strategy identifiers;
  - normalized interaction outcome signals;
  - explicit user confirmations relevant to follow-up persistence;
- the existing `pm` tool transport and `UseCaseExecutor` stay authoritative and
  unchanged.

The interaction-memory layer may shape context selection, answer structure, and
relevant reminder surfacing. It may not choose a different authoritative
business use case than the baseline routing would choose from the same user
intent.

### 7.4 Interaction event reference

Every write-capable operation in this capability must attach one normalized
`InteractionEventRef` containing:

- `repo_scope_id`;
- `conversation_id`;
- `turn_id`;
- `operation_kind`;
- `event_key`.

`event_key` is the idempotency authority for this capability and must be
deterministically derived from the stable repo scope plus host-provided
conversation and turn identity. If the host cannot provide stable conversation
and turn identity, the capability may still read memory, but it must reject new
memory writes with an explicit `interaction_event_id_unavailable` diagnostic.

Write-capable slices may not proceed past planning unless the host-identity
contract is proven: stable `project_id` (or repository-root fallback),
`conversation_id`, and `turn_id` must all be available to the interaction
adapter. If that contract is unavailable, the capability is restricted to
read-only empty/inspect/disable behavior until a separately approved identity
bridge exists.

### 7.5 Repo/project scope resolution

The first version uses one deterministic scope-resolution rule:

1. if the Copilot host provides a stable local `project_id`, use that as the
   primary `repo_scope_id`;
2. otherwise use a stable fingerprint of the current repository root path;
3. branch name is not part of the first-version scope key;
4. separate local clones without a shared `project_id` are separate scopes;
5. multi-root ambiguity is unsupported in v1 and must return
   `interaction_memory_scope_unknown`.

This keeps scope bounded to the current repository/project while remaining
deterministic across repeated local use.

## 8. Memory object model

The system stores only normalized interaction-memory objects. The first version
contains four kinds.

Common sanitization contract for all four kinds:

- all stored text must be a bounded normalized summary, not copied raw chat;
- stored values must use stable local identifiers or normalized category values
  rather than free-form sensitive details;
- audit deltas must record normalized prior/new state, never whole message
  bodies;
- if a candidate memory item cannot be safely normalized, it is rejected rather
  than stored.

### 8.1 Preference Memory

Represents stable chat behavior preferences for the current repo/project.

Examples:

- preferred answer structure;
- preferred level of proactivity;
- preferred reminder style;
- repeated comparison framing;
- preferred Chinese/English presentation behavior.

Required metadata:

- stable local identifier;
- repo/project scope identifier;
- preference category;
- normalized value;
- confidence;
- source interaction reference;
- created / updated / last-used time;
- active / disabled / cleared state.

### 8.2 Context Memory

Represents recurring repo-local context that improves understanding but is not
an authoritative business fact.

Examples:

- recurring focus on Copilot Chat as the main entry;
- repeated need to separate controlled actions from source-data refresh;
- repeated local terminology preferences;
- repeated repo-local framing constraints.

Required metadata:

- stable local identifier;
- repo/project scope identifier;
- context topic;
- normalized summary;
- confidence;
- recency score inputs;
- source interaction reference;
- created / updated / last-used time;
- active / expired / disabled / cleared state.

### 8.3 Follow-Up Memory

Represents a locally retained reminder or unfinished conversational thread.

Examples:

- "write the implementation plan after the design is approved";
- "return to inspect the memory-control UX";
- "remind the user about an unresolved design gate in the next relevant chat".

Required metadata:

- stable local identifier;
- repo/project scope identifier;
- follow-up summary;
- follow-up kind from a fixed enum such as `design_gate`, `planning_gate`,
  `assistant_commitment`, `user_requested_reminder`, or
  `controlled_action_reminder`;
- trigger context;
- status (`open`, `snoozed`, `done`, `cleared`, `expired`);
- confirmation provenance;
- optional authoritative reference identifier only when the item points to an
  already-existing local Action, Decision, operation, or proposal record;
- created / updated / due / last-surfaced time;
- source interaction reference.

Normalization constraints:

- the summary must be bounded, safe normalized text rather than copied raw chat
  transcript;
- the item must not persist raw business facts, copied payloads, or parallel
  owner/date/status records for operational objects;
- when an authoritative product object already exists, follow-up memory stores
  only a local reminder summary plus a stable reference to that object.

### 8.4 Dialogue Strategy Profile

Represents a bounded reusable working-strategy pattern, not arbitrary prompt
text.

Examples:

- "lead with conclusion, then give evidence";
- "before answering, surface one unfinished local follow-up if it is directly
  relevant";
- "auto-apply current repo/project context before asking for clarification";
- "prefer concise Chinese management answers unless detail is requested".

Required metadata:

- stable local identifier;
- repo/project scope identifier;
- strategy key from a fixed catalog;
- learned priority / weight;
- success and suppression counters;
- last-applied and last-promoted time;
- enablement state;
- rule or catalog version.

Boundary from Preference Memory:

- **Preference Memory** stores what the user prefers;
- **Dialogue Strategy Profile** stores which code-owned response strategy is
  worth applying because it has proven effective in this repo/project;
- a strategy profile never stores arbitrary user-specific text and never
  replaces preference records.

### 8.5 State model

To keep planning and storage explicit, the first version uses these state enums:

- **Capability state**: `enabled`, `disabled`, `empty`, `unavailable`,
  `integrity_invalid`, `scope_unknown`;
- **Preference Memory**: `active`, `disabled`, `cleared`;
- **Context Memory**: `active`, `expired`, `disabled`, `cleared`;
- **Follow-Up Memory**: `open`, `snoozed`, `done`, `cleared`, `expired`;
- **Dialogue Strategy Profile**: `active`, `suppressed`, `retired`, `cleared`.

## 9. Read path

For each Copilot Chat turn:

1. identify the current repo/project scope using the host workspace context;
2. classify the turn intent at a bounded level such as query, clarification,
   planning, controlled-action follow-up, or documentation/design discussion;
3. retrieve only relevant active memory objects for that scope;
4. rank them by:
   - kind relevance to the current turn;
   - recency;
   - confidence;
   - prior usage success;
   - explicit suppression state;
5. compose a bounded working prompt / dialogue strategy package from:
   - fixed repository instructions;
   - the current task or user message;
   - selected repo-scoped interaction memory;
   - applicable dialogue strategy profiles;
6. continue through the existing approved Copilot routing and deterministic
   `pm` execution path.

If no relevant memory exists, the system reports the memory layer as empty and
continues with the baseline interaction contract. Empty memory is a valid state,
not an error.

If scope resolution is ambiguous, the layer reports
`interaction_memory_scope_unknown`, performs no memory write, and proceeds
without personalization rather than guessing scope.

## 10. Write path

The capability writes memory only from local interaction events and only within
the current repo/project scope.

### 10.1 Automatic preference capture

The system may automatically create or strengthen a Preference Memory object
when:

- the same behavioral preference is expressed repeatedly;
- the preference is normalized into a supported category;
- confidence passes a fixed threshold; and
- the preference does not conflict with a later explicit override.

This write is local and auditable. It does not require a business-operation
preview/confirm flow because it does not mutate authoritative product facts.

### 10.2 Automatic context capture

The system may retain Context Memory when:

- the context is repeatedly reused;
- it is repo/project-local rather than global personal biography;
- it does not duplicate authoritative business data;
- it can be normalized into a bounded context category.

### 10.3 Follow-up capture

Follow-Up Memory must be written only at a meaningful confirmation point, such
as:

- the user explicitly asks to remember a next step;
- the assistant proposes a follow-up and the user accepts it;
- a bounded planning or design gate explicitly requires resumption later.

The write should record whether the item was:

- user-requested;
- assistant-suggested and approved; or
- system-required by a bounded workflow rule.

The allowed workflow-rule catalog is code-owned and bounded in v1. It may
include only local conversational continuity gates such as:

- `design_spec_review_required`;
- `implementation_plan_resume_required`;
- `explicit_user_review_pending`;
- `exact_preview_confirmation_pending`.

It may not infer new business work, create a domain Action/Decision, or turn a
recommendation into an operational task by itself.

Deterministic boundary versus existing domain memory:

- interaction follow-up memory is only for conversational continuity and local
  reminder behavior;
- it must not create or replace canonical Action or Decision rows;
- if an existing product workflow already exposes an Action, Decision, preview,
  or proposal object, interaction follow-up memory may reference that object but
  may not duplicate its operational fields as a second record of truth;
- if the user's intent is an operational action rather than a chat reminder, the
  assistant must stay on the authoritative product path.

### 10.4 Strategy learning

The system may adjust Dialogue Strategy Profile priority based on bounded local
signals such as:

- the user accepts the answer without needing repeated structure corrections;
- the assistant successfully surfaces a relevant unfinished follow-up;
- the assistant requires fewer repetitive clarification turns for the same local
  topic;
- a strategy repeatedly proves irrelevant and should be down-ranked.

The capability must not synthesize new arbitrary strategy text. It may only
promote, demote, suppress, or retire entries from a fixed strategy catalog.

## 11. Strategy catalog model

The first version should ship a fixed strategy catalog owned by code and version
controlled with the product. Examples:

- concise conclusion-first answer;
- evidence-after-conclusion answer;
- repo-context prefill;
- unresolved-follow-up reminder;
- clarification minimization pattern;
- controlled-action reminder pattern.

Each catalog entry has:

- a stable strategy key;
- applicability conditions;
- suppression conditions;
- maximum composition priority;
- incompatibility rules with other strategies;
- version metadata.

The catalog may influence context assembly, reminder surfacing, and answer
shape. It may not directly choose a different business use case or change the
deterministic meaning of an existing `pm` contract.

This preserves the repository rule that the product must not expose arbitrary
prompt/rule configuration as a user-facing feature.

## 12. Interaction-state control surface

The control surface must support the approved user expectation: mostly invisible
background behavior with explicit inspection and cleanup when needed.

The control surface should be exposed through the existing Copilot interaction
path for this repository. A separate dashboard or standalone UI is not required
for the first version.

Required capabilities:

- show whether interaction memory is enabled for the current repo/project;
- list retained items by kind, status, and latest usage;
- show why one item exists and where it came from at a safe normalized level;
- preview clear/reset operations before confirm;
- clear one item, one kind, or the entire local repo/project memory scope;
- disable or re-enable the capability without deleting all rows.

The control surface should remain bounded and operationally simple. It is not a
full user-authored knowledge-base editor.

Definitions:

- **clear**: remove one retained item or one memory kind from active use inside
  the current repo/project scope;
- **reset**: scope-wide clear of all retained interaction-memory items plus all
  learned strategy weights for the current repo/project, while keeping the
  capability installed and preserving only the minimum normalized audit trail
  required below.

Disabled-state semantics in the first version:

- `disabled` stops automatic memory selection, strategy composition, and
  learning writes during normal chat turns;
- `disabled` does **not** block `memory status`, `memory summary`,
  `memory inspect`, `memory enable`, or clear/reset preview/confirm operations;
- re-enable resumes normal reads/writes without requiring a restore step unless
  the user has already cleared the local scope.

Retention and expiry rules in the first version:

- Preference Memory does not auto-delete, but confidence may decay after long
  non-use and the item may be suppressed from normal selection;
- Context Memory becomes `expired` after a bounded inactivity window and is
  excluded from normal selection until refreshed or cleared;
- Follow-Up Memory must always move through an explicit lifecycle:
  `open` -> `snoozed` or `done` or `cleared` or `expired`;
- Dialogue Strategy Profiles revert to catalog-default priority when the
  catalog version changes or when long non-use retires the learned promotion.

Thresholds, inactivity windows, and decay rules remain code-owned and versioned
with this capability. They are not user-editable in v1.

## 13. Error handling and degraded behavior

### 13.1 Required failure visibility

If the interaction-memory layer is unavailable, corrupt, disabled, or otherwise
degraded, the system must return a bounded diagnostic state such as:

- `interaction_memory_disabled`;
- `interaction_memory_empty`;
- `interaction_memory_unavailable`;
- `interaction_memory_integrity_invalid`;
- `interaction_event_id_unavailable`;
- `interaction_memory_scope_unknown`.

The assistant may continue with baseline behavior, but the state must be
available to the interaction layer and must not be silently hidden.

### 13.2 Failure boundaries

- memory failure must not corrupt or block the existing authoritative `pm`
  query path unless the same lower-level storage fault makes all local product
  state unavailable;
- failed memory writes must not invent success;
- partially normalized memory candidates must be rejected rather than stored as
  ambiguous free text blobs;
- follow-up confirmation provenance must be explicit; unconfirmed follow-up
  writes are rejected;
- strategy catalog mismatch or version drift fails closed for the affected
  strategy entry.

## 14. Distinction from canonical product memory

The canonical delivery model already includes `Action` and `Decision` as
management follow-up and decision memory. This new capability is different.

`Action` / `Decision` memory:

- belongs to the product's delivery-management domain;
- may support authoritative operational workflows;
- is part of the deterministic business model.

Interaction memory:

- belongs only to Copilot Chat personalization inside one repo/project;
- shapes context reuse and reminder behavior;
- never becomes a domain-fact substitute.

The two may reference each other in later design, but this design keeps them
separate.

## 15. Clean re-import, bootstrap, audit, and rollback posture

This capability is persisted local assistant state, so it must still obey the
repository's clean re-import rule without becoming a production-data dependency.

### 15.1 Bootstrap

On an empty local database, bootstrap creates the interaction-memory schema and
starts with **zero retained memory**. The product remains usable immediately in
that empty state.

### 15.2 Import contract

There is no external-source import requirement for first release. The supported
production posture is:

- install product;
- bootstrap empty interaction-memory storage;
- let local chat usage accumulate memory naturally.

No migration, backfill, copied chat export, or historical replay is required
for correctness or readiness.

### 15.3 Validation and integrity

The capability needs a local integrity report covering:

- counts by memory kind and state;
- invalid scope references;
- orphaned follow-up confirmation references;
- retired strategy entries still marked active;
- disabled versus active counts;
- stale-item counts by age bucket.

### 15.4 Audit

Every write must record:

- operation type (`auto_capture`, `confirmed_follow_up`, `strategy_promote`,
  `strategy_demote`, `clear`, `disable`, `enable`);
- source interaction reference using the full `InteractionEventRef`;
- prior and new safe normalized state;
- timestamp;
- local actor context.

Audit behavior for clear/reset:

- audit rows remain retained so the product can prove that a clear/reset
  happened;
- content-bearing prior/new state for cleared items must be replaced with a
  minimal tombstone marker rather than preserved in recoverable form;
- retained audit rows may keep only scope, item kind, operation type, actor
  context, and timestamps after the clear/reset operation.

### 15.5 Idempotency

Repeated processing of the same interaction event must not create duplicate
memory rows or duplicate audit events. Each write path therefore needs a stable
interaction-local idempotency key derived from `InteractionEventRef.event_key`
rather than from free text.

### 15.6 Rollback

Rollback must be software-safe:

- disabling the capability must stop automatic selection and new learning writes
  without requiring data deletion, while still allowing inspect/status/enable
  and clear/reset control operations;
- full clear must remove retained interaction memory for the current repo/project
  without affecting authoritative business data;
- database rollback from backup must restore the store like any other local
  capability, but the product must not require preserved historical interaction
  memory to remain usable.

## 16. Validation strategy

Implementation planning must include synthetic tests for:

- repo/project scope isolation;
- preference auto-capture thresholds and deduplication;
- follow-up capture requiring a valid confirmation path;
- strategy-profile ranking and suppression rules;
- degraded-state diagnostics;
- inspect / clear / disable behavior;
- empty-store startup behavior on a clean database;
- integrity-report correctness;
- idempotent processing of repeated interaction events;
- proof that business-fact queries remain deterministic and unchanged when
  interaction memory is empty, disabled, or unavailable.

## 17. Success signals

The first version should measure success through local interaction outcomes,
not new business features.

Primary signals:

- fewer repeated context-restatement turns for the same repo/project;
- more timely surfacing of unfinished follow-up items;
- fewer user corrections about answer structure and working style;
- fewer redundant clarification turns before the same routing decision.

Negative signals:

- repeated irrelevant reminders;
- stale context being reused after it stops being helpful;
- user need to constantly clear noisy memory;
- any sign that memory is being mistaken for authoritative business fact.

## 18. Reviewable implementation slices

This design is intentionally split into small later planning units.

### Slice A — Contract and storage foundation

- introduce the bounded interaction-memory capability contract;
- add empty-store bootstrap and integrity/audit skeleton;
- prove clean startup, empty-state diagnostics, and repo/project scoping.

### Slice B — Read path and strategy composition

- add memory selection and bounded strategy composition;
- keep the strategy catalog fixed and code-owned;
- prove no authoritative business result changes when memory is absent.

### Slice C — Controlled learning and follow-up persistence

- add automatic preference/context capture;
- add confirmed follow-up capture;
- add strategy priority learning with idempotency and diagnostics.

### Slice D — Control surface

- add inspect / clear / disable / enable flows;
- add integrity-report and bounded local operator guidance.

Each slice must remain independently reviewable, reversible, and stopped at its
own acceptance gate. Passing tests on one slice does not authorize the next.

## 19. Non-goals for the first implementation plan

The first implementation plan must explicitly avoid:

- cross-repo memory sharing;
- user-authored free-text prompt libraries;
- importing historical Copilot chat transcripts;
- storing raw query payloads as memory;
- autonomous task execution based on remembered preferences alone;
- replacing domain Actions, Decisions, Attention, or staffing workflows.

## 20. Recommended next step

The next step after this spec is a bounded implementation plan for **Slice A —
Contract and storage foundation**. The plan should define the owning module,
public contract, diagnostics, bootstrap behavior, audit skeleton, integrity
report, focused synthetic tests, the host-identity planning gate, and the stop
gate without starting later slices.
