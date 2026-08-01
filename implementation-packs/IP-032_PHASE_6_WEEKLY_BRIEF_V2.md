# IP-032 — Phase 6 Weekly Brief v2

Status: `BATCH C OWNER-ACCEPTED — BATCH D AUTHORIZATION REQUIRED`
Design: `architecture/13_PHASE_6_WEEKLY_BRIEF_V2_DESIGN.md`
Implementation branch: `codex/phase-6-weekly-brief-design`
Baseline: `33fc6f100b36f6e54eec73e531590c186f4b0441`

## Authorized outcome

The owner approved the Phase 6 design and then authorized only Batch B1 public
read-contract prerequisites. Register IP-032 and add the minimum owner-local
read contracts needed by a later Weekly Brief v2 composer. B2 snapshot/schema,
B3 composition, C interface integration, D promotion, and every external action
remain separately gated.

The owner accepted the validated, independently reviewed Batch B1 candidate at
`cce14e42c26c605bc76e895de8d611540eae06f8`. The owner subsequently explicitly
authorized only Batch B2 snapshot/comparison core. The owner accepted B2 at
`da093ba1b1f5dabc44053a2eb7edb4d237197768` and then authorized only B3
nine-section composition. C, D, and every external action remain separately
gated.

Batch B3 is implemented in `pm_agent.weekly_brief.composer` without route
registration. It composes the nine sections solely from promoted public
read contracts and supplies the B2 lookup/recompose seam. The owner accepted
the validated B3 result at `ce726f6c9e7bd334a5af3847141d0b66258a47b3`.

The owner authorized Batch C shared-interface integration on 2026-08-01 after
the corrected, validated candidate review and accepted the implementation at
local commit `3df79a1`. Batch C adds the opt-in `weekly-dm-brief-v2` use-case
routing, dedicated `pm weekly-brief` CLI, dedicated Dashboard
`/api/weekly-brief/operations` preview/confirm endpoint, the Copilot contract,
and the focused shared-interface tests. Batch D promotion and every external
action remain separately gated.

## Batch B2 capability ownership and boundary

- `pm_agent.weekly_brief` owns the additive snapshot-operation/confirmed-history
  table, its repository, and the non-routed preview/confirm service.
- `pm_agent.database.bootstrap` composes only the dedicated schema constant; it
  contains no Weekly Brief rules, queries, or transactions.
- The B2 service accepts an injected B3-supplied public query lookup and
  recomposer. It must not read Attention, Project Health, Resource, Action,
  Decision, execution, or legacy-report storage internals.
- The public controlled-operation contract is `weekly-brief-snapshot-preview`
  and `weekly-brief-snapshot-confirm`; no generic query transport, use-case,
  CLI, Dashboard, or Copilot route is registered in B2.

Batch B2 implements only hashed one-time preview/confirm, immutable confirmed
history, scope/input/baseline/statement/evidence/result fingerprints, expiry,
idempotent confirmed replay, stale/concurrent rejection, and integrity checks.
It must prove clean bootstrap and prior-runtime additive rollback preservation.
It must not implement the v2 composer or nine sections; B2 may compare only
already-normalized manifest records and must not assemble them from capabilities,
select a baseline for a query, replace `weekly-dm-brief`, create a producer,
change Staffing/confirmation, or activate a connector.

## Batch B1 capability ownership

- Canonical Project identity/read boundary:
  `pm_agent.project_identity.read_model.active_project_manifest(...)` owns the
  complete local active-project manifest and exact-subset validation.
- Attention read boundary:
  `pm_agent.attention.read_model.current_attention(...)` owns current persisted
  Attention, reconciliation coverage, optional bounded history, and explicit
  project-association state. It may read Attention-owned storage; consumers may
  not.
- Action read boundary:
  `pm_agent.action.read_model.list_action_records(...)` owns normalized current
  Action and explicit completion facts. It never derives a Project association
  from title, source, owner, prose, or assignments.
- Execution read boundary:
  `pm_agent.database.execution_review.list_latest_execution_facts(...)` remains
  the focused Phase 3 reader and additively publishes the fact-derivation time
  plus an evidence-bound achieved Milestone event date and its `date` precision.
  `database.execution.py` is unchanged.
- Existing Project Health, Resource Intelligence, and source-state readers are
  reused as verified; no duplicate adapter, table, calculation, or freshness
  rule is introduced.

The Weekly Brief capability itself is not implemented in B1. No new user-facing
use case calls another use case, and no consumer reads another capability's
private table.

## Public contract behavior

### Active Project manifest

- Input is global scope or 1–200 unique stable project IDs.
- Only canonical `projects.status = active` identities are eligible.
- Exact scope fails closed with `PROJECT_NOT_FOUND` for any absent/non-active
  ID.
- Output excludes project names and reports coverage as `complete`, `absent`,
  or `unavailable`; an empty catalog is never presented as a proved healthy
  portfolio. Global scope is limited to 200 active projects and fails closed
  without truncation when that bound is exceeded.
- Workforce planning remains Resource evidence and never defines project
  existence or global scope.

### Attention current/history

- Reads persisted state only and never evaluates or reconciles Attention.
- Preserves existing severity order, lifecycle state, rule state, evaluation
  status, fact/signal/evidence/freshness payload, reconciliation coverage, and
  optional bounded history.
- Project-subject Attention has a known direct Project association. Action,
  member, source, Milestone, and Decision subjects remain association
  `unavailable` until an owning public contract explicitly publishes one.
- No operation, confirmation token/hash, actor credential, or raw exception is
  exposed.
- Only a successful covering reconciliation means complete coverage. Partial
  remains partial; failed or invalid coverage is unavailable with safe warning
  codes and can never make an empty result mean clear.
- The existing `delivery-attention-center` reuses the same scope-coverage rule;
  its public projection remains behavior-compatible.

### Action current/completion

- Reads recorded `open | done | cancelled` Actions with validated status filters.
- Computes follow-up reasons from recorded status, owner, due date, priority,
  and the date derived from an explicit UTC `through` boundary.
- A completion is `known` only when status is `done` and `completed_at` is
  parseable and falls in the `(completed_since, through]` window. Missing,
  invalid, or future completion evidence remains visible as `unavailable` and
  makes coverage partial; it is never filtered into an apparently complete
  empty result.
- Only stable `owner_id` and `owner_state` are published. The Action reader does
  not join Person storage or expand the display-name data surface.
- The existing schema has no Action-to-Project field, so every association is
  explicitly unavailable. No string or relationship inference is permitted.
- It performs no create, complete, assign, or confirm operation.

### Execution event time

- Existing execution facts remain latest/current rather than historical as-of
  facts.
- Milestone achievement facts add `fact_observed_at`, `event_occurred_at`,
  `event_time_state`, `event_time_basis`, and `event_time_precision`.
  `fact_observed_at` is explicitly the derivation time, not a source-subject
  observation. The event fields come from the same immutable derivation
  evidence as the returned fact, never a later mutable Milestone row.
- The achieved event currently has date precision because derivation evidence
  stores `actual_date`; it is not fabricated as a timestamp. Missing or invalid
  fact evidence publishes event time as unavailable with a safe warning.
- Non-Milestone facts report event time as unavailable.

## Allowed dependencies and prohibited coupling

Allowed dependencies are SQLite, the configured database-path contract, each
capability's own storage/read modules, the existing canonical Project and Action
tables, and the focused Execution review query.

B1 must not:

- add or modify schema, bootstrap composition, import, derivation, or migration;
- modify `database/bootstrap.py` or `database/execution.py`;
- read another capability's private repository from a Weekly Brief module;
- add a Weekly Brief composer, snapshot/history table, capture operation, use
  case parameter, CLI, Dashboard, or Copilot route;
- create an Attention producer or reconciliation, change Action/Staffing/
  Decision behavior, or call a connector; or
- use real records, operational databases, company identifiers, or source
  payloads.

## Focused tests and acceptance evidence

Focused entry point:

```text
src/tests/test_weekly_brief_prerequisites.py
```

Required combined regression:

```text
src/tests/test_attention_center.py
src/tests/test_delivery_execution_review.py
```

Acceptance requires:

- synthetic manifest scope, fail-closed ID, Action completion/association,
  Attention order/coverage/history/parity, and Milestone event-time tests;
- existing Attention Center and Execution Review regression;
- `make validate`;
- independent read-only review of capability ownership, public/private
  boundaries, query-only behavior, privacy, parity, compatibility, and gate
  scope;
- correction of every accepted finding, repeated focused/full validation, and
  repeated independent review; and
- an accurate `PROGRESS.md` plus local commit. Passing checks does not authorize
  B2.

`make rehearse-release` is not required for B1 because this slice changes no
schema, import, migration, packaging contract, or installed-data behavior. B2
must run it if separately authorized because B2 proposes additive schema.

## Compatibility and rollback

- All B1 readers are additive.
- Existing `delivery-attention-center` retains the same public result and now
  shares the owner-local reconciliation-coverage function.
- Execution Review adds event-time fields without removing or renaming any key.
- Legacy `weekly-dm-brief`, `WeeklyReportService`, `pm report`, project
  snapshots, Action writes, Project Health, Resource, Staffing, and connectors
  are unchanged.
- Rollback is a single B1 code revert. No data conversion, cleanup, or row
  deletion is required.

## Intentional limitations and next gate

- Action/Milestone/member/source Attention associations remain unavailable
  unless the owner publishes a direct canonical Project association.
- Action completion history is bounded by the existing current row and
  `completed_at`; no event ledger or backfill is added.
- Execution achievement time has date, not timestamp, precision.
- Project Health, Resource, and freshness retain their promoted availability
  and limitation semantics.
- No Decision Required governance exists.

The exact next gate is a separate owner decision to authorize, revise, or defer
named Batch B2. Only that explicit authorization may begin B2.
