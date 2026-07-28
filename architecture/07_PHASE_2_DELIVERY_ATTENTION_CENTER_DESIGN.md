# Phase 2 — Delivery Attention Center Foundation Design

Status: `APPROVED — BATCH B REVIEW CORRECTIONS IMPLEMENTED, REVIEW REQUIRED`
Last updated: 2026-07-28
Baseline: `289837855a230a14256a5ed00f5c8e353b1c3d36`
Implementation branch: `codex/phase-2-attention-center`
Implementation pack: `IP-028 — DELIVERY ATTENTION CENTER`

## Decision supported

Give a Delivery Manager one local, explainable view of high-confidence delivery
conditions that need attention, while preserving the difference between:

1. the underlying deterministic rule outcome;
2. the manager's attention workflow state; and
3. an advisory next step.

The Center must deduplicate repeated detections, retain a bounded and
sanitized history, and never turn missing, stale, partial, or failed source
data into a clear or healthy condition.

The owner approved this Batch A design on 2026-07-28. It authorizes only the
bounded, sequential IP-028 implementation batches starting with Batch B on the
dedicated implementation branch. It does not authorize connector calls, source
sync, real-data access, push, merge, tag, release, or deployment.

## Verified current state

### Current call path and interface boundary

```text
Copilot operating instructions
        -> pm tool query / generic Dashboard query
        -> ToolTransport
        -> UseCaseExecutor
        -> management-attention handler
        -> UseCaseResult facts + signals
        -> bounded execution_traces summary
```

- `UseCaseExecutor` validates result-local fact, signal, recommendation,
  evidence, and freshness references before serializing or tracing a result.
  Its trace stores only summary evidence, freshness, warning codes, and a
  proposed-write count; it does not retain business payloads.
- The `management-attention` descriptor is read-only and is the only current
  production use case that advertises facts and signals. It advertises no
  recommendations.
- Structured CLI and the generic Dashboard serialize the shared
  `UseCaseResult` without business reshaping. Existing formatted interfaces
  remain outside this contract.

### Current Management Attention behavior

`management-attention` is an in-memory, request-time ranking. It reads only
local SQLite repositories and creates no business write.

| Current producer | Current deterministic condition | Existing subject | Existing priority behavior |
| --- | --- | --- | --- |
| Project health | Latest local board health is red or amber | `project` | red is critical; amber is high |
| Action follow-up | Open action is overdue | `action` | high-priority action is high; otherwise medium |
| Source freshness | Required source is not fresh | `source` | stale/unavailable is high; other non-fresh state is medium |

The handler sorts by severity, attention type, and subject ID, then limits the
returned result to 20 items. It maps each returned item into one derived fact
and one active signal using `management-attention-v1`. Its legacy
`data.items`, summary, context, warnings, ordering, truncation, and empty
recommendation list are a Phase 1 compatibility contract.

The handler currently has no stable Attention identity across executions, no
deduplication, no historical record, no acknowledgement/snooze/resolution
state, no rule catalog, and no write path. Its result-local IDs must not be
mistaken for persistent IDs.

### Verified local sources and persistence model

- `projects`, `jira_board_configs`, `jira_health_snapshots`, and
  `confluence_status_snapshots` provide latest local health observations.
- `action_items` and `v_overdue_actions` provide recorded open overdue actions.
- `data_sources` plus `sync_runs` provide local freshness state. No connector
  probing is required or permitted for this design.
- `employees`, active `assignments`, and `v_member_load` provide current-load
  facts. The existing Team Workload view classifies `current_load >= 1.0` as
  overloaded. `monthly_allocations` and plan versions exist, but their
  period/version selection is not the current Team Workload definition.
- `decision_log` has `type`, `outcome`, timestamps, optional project link, and
  context JSON. It has no explicit decision due date, owner, or canonical
  pending-decision lifecycle.
- Existing `execution_traces`, `dashboard_operations`, `staffing_proposals`,
  `project_snapshots`, and `action_tracker` are not Attention storage. In
  particular, execution traces are intentionally payload-free and retention
  bounded; they cannot provide Attention history.

No `attention_*` table, view, repository API, migration, use case, or focused
test exists at this baseline.

## Target design

### Scope and non-goals

Phase 2 introduces a separate `delivery-attention-center` capability. It
materializes high-confidence, local, deterministic conditions and exposes
current items plus history. It does not replace, mutate, or cause a write from
`management-attention`.

In scope after approval:

- durable rule catalog, current attention items, reconciliation audit, and
  append-only state history;
- deduplication and lifecycle for four active initial signal families, plus a
  registered-but-disabled pending-decision rule;
- advisory, bounded recommendations with no implicit business write;
- read-only Center query plus explicit confirmed reconciliation and lifecycle
  commands; and
- synthetic schema, migration, integrity, compatibility, and regression
  tests.

Out of scope:

- Jira issue-history acquisition, issue links, aging blockers, scope growth,
  forecasts, predictive scoring, or model-authored signals;
- automatic action creation, action completion, project-status mutation,
  staffing assignment, resource commitment, or connector sync;
- changing the Phase 1 `management-attention` response, descriptor capability,
  sort order, limit, or result-local identifiers;
- interpreting `decision_log` narrative/context JSON with a model;
- replacing `execution_traces` with full-result persistence; and
- any real source, credential, operational configuration, person name, project
  name, or other non-synthetic value in tests or documents.

### Canonical attention identity and contracts

An Attention item has two distinct states:

| Field | Meaning | Allowed values |
| --- | --- | --- |
| `rule_state` | Latest deterministic observation | `active`, `clear`, `unknown`, `unavailable` |
| `attention_state` | Local manager workflow | `open`, `acknowledged`, `snoozed`, `resolved` |

The canonical identity is a stable, local `attention_id` derived from
`rule_key + subject.kind + subject.id`. Rule version, severity, reason codes,
and evidence are attributes of that identity, not deduplication keys. A
backward-compatible rule-version change produces a `rule_changed` history event
rather than a duplicate current item. A semantic-breaking rule change requires
a new `rule_key`; it must not reuse a prior identity. IDs are bounded and
deterministic; display names remain an optional current projection, never part
of identity.

Each persisted current item and event carries only the normalized facts,
reason codes, evidence references, freshness references, source observation
times, rule version, and a hash of the normalized observation. It must not
store raw connector payloads, tokens, endpoints, errors, copied execution
results, or model explanation text.

The observation hash includes only semantic state: rule key/version, subject,
fact value/value state, signal state/severity/reason codes, and normalized
evidence/freshness states. It excludes execution IDs, display names, query
timestamps, and source observation timestamps, so an unchanged successful
refresh does not create a meaningless history event.

The new Center response remains a `UseCaseResult` 1.0. Its facts, signals, and
recommendations use the Phase 1 reference rules. Every persistent item exposes
its `attention_id`, lifecycle fields, first/last detection timestamps,
latest evaluation ID, and a bounded history projection in `data`/`context`.
Facts and signals retain result-local IDs and are validated by the shared
executor; `attention_id` is a separate stable field in the Center's data
projection.

### Center interface contracts

The Center query is the only Center operation exposed through the existing
read-only ToolTransport and shared executor. Its descriptor has
`supported_operations = ("query",)` and `read_only = true`.

| Query parameter | Default and bound | Behavior |
| --- | --- | --- |
| `attention_states` | `[open, acknowledged, snoozed]`; `resolved` only when requested | Filters local workflow state without changing it |
| `rule_key`, `subject_kind`, `subject_id` | optional bounded stable identifiers | Narrow current items by canonical identity attributes |
| `include_history` | `false` | Enables the per-item history projection |
| `limit` | 20; 1–50 | Bounds returned current items after deterministic sort |
| `history_limit` | 5; 0–20 | Bounds newest-first events per returned item; zero returns no events |

The response has `data.items`, deterministic summary counts by rule and both
states, and—only when requested—`recent_events` for each returned item. Each
item exposes its canonical `attention_id`, current rule/lifecycle state,
severity, fact/evidence/freshness references, first/last detection timestamps,
and latest reconciliation ID. Result-local facts, signals, and advisory
recommendations remain top-level `UseCaseResult` fields and retain shared
reference validation.

Reconciliation and lifecycle actions do not use ToolTransport. A dedicated
Attention CLI/Dashboard write boundary exposes only these actions:

| Action | Preview scope | Confirmed effect |
| --- | --- | --- |
| `reconcile` | bounded rule keys and optional subject filters | Re-evaluate local facts and atomically materialize transitions |
| `acknowledge` | one current `attention_id` | Change only lifecycle state to `acknowledged` |
| `snooze` | one current `attention_id` plus bounded future expiry | Change only lifecycle state to `snoozed` |
| `resolve` | one current `attention_id` | Allowed only after a complete clear evaluation; records no rule override |

Every preview returns an opaque `operation_id`, one-time confirmation token,
expiry, actor, bounded scope, and proposed transitions. Confirmation returns
the actual re-evaluated outcome. Tokens are never persisted in plaintext or
returned after preview.

### Initial rule catalog

Rule logic is deterministic code. A persisted rule catalog stores only enabled
status, approved parameter values, rule version, and timestamps; it never
stores executable expressions or model prompts. A parameter change requires a
new rule version and reconciliation preview.

Project-health RAG semantics are configuration, not fixed runtime constants.
The current project-health rule version stores a local DM default plus optional
per-project overrides keyed only by stable anonymous project ID. The validated
parameters define:

- source precedence across normalized Jira grade and Confluence RAG inputs;
- precedence across normalized `red`, `amber`, and `clear` states; and
- source-specific mappings from bounded external labels to those normalized
  states.

Project overrides merge onto the local DM default and may replace only those
bounded fields. Seed values preserve the existing Management Attention
precedence, but are initial configuration rather than hard-coded behavior.
Changing any mapping or precedence requires a new project-health rule version
and takes effect only through Attention reconciliation preview/confirm. An
unknown label is an incomplete observation and never clears an active item.
Malformed configuration fails before a reconciliation write. Batch B does not
add a configuration UI or API; that remains outside this storage and
reconciliation core.

| Rule key / signal type | Subject and source | Deterministic initial criterion | Advisory recommendation |
| --- | --- | --- | --- |
| `project_health_attention` | `project`; latest local health snapshots | Existing red/amber precedence from Management Attention | `review_project_health` |
| `overdue_action_attention` | `action`; `v_overdue_actions` | Existing open overdue action criterion and priority severity | `follow_up_action` |
| `source_freshness_attention` | `source`; data source/sync records | Existing required-source freshness mapping | `review_source_freshness` |
| `resource_overload_attention` | `member`; active assignments and `v_member_load` | Current load strictly exceeds `1.0` | `review_resource_load` |
| `pending_decision_attention` | `decision`; `decision_log` | Registered as `disabled`; emits no Phase 2 active signal | none in Phase 2 |

The current `decision_log` lacks a due date, owner, and a dedicated decision
request workflow. A `pending` outcome means that a recorded decision has no
recorded outcome yet; it does not reliably mean that a manager decision is
required. Therefore `pending_decision_attention` is present in the rule
catalog but disabled for Phase 2: it produces no active signal,
recommendation, or lifecycle record. Its future activation requires a separate
approved definition of eligible decision types, ownership/due semantics, age
threshold, evidence, and rule version. It must never infer those properties
from narrative or arbitrary context JSON.

Resource overload deliberately uses active assignment load only in Phase 2.
It does not claim effective capacity, leave, BAU, skills, or future plan
coverage; those belong to Phase 5. No signal is emitted from a zero or absent
allocation merely because it is unknown.

Recommendations are advisory, `write_mode = advisory`, and
`confirmation_required = false`; they never create an action or change a
project, decision, or allocation. For health, action, and resource rules, a
recommendation is `available` only when its signal is active and required
evidence/freshness is usable. For `source_freshness_attention`, the normalized
local `data_sources`/`sync_runs` metadata is itself sufficient evidence even
when the observed source is stale, failed, missing, or unknown; its advisory
`review_source_freshness` recommendation remains available to explain that
limitation without treating the source as fresh.

### Proposed storage and migration boundary

The following is a proposed additive schema for an approved implementation.
This Batch A does not create it.

| Table | Purpose | Key fields and constraints |
| --- | --- | --- |
| `attention_rules` | Approved local rule catalog and parameters | `rule_key`, `rule_version`, `enabled`, `parameters_json`, timestamps; one active version per key |
| `attention_operations` | Attention-specific one-time preview/confirm boundary | operation ID, action, actor, bounded scope JSON, token hash, proposed/claimed/success/failed/expired status, expiry and safe failure/result summaries |
| `attention_reconciliations` | Safe audit of a confirmed evaluation | `reconciliation_id`, status, actor, started/finished timestamps, rule-set version, safe warning codes, candidate and transition counts |
| `attention_signals` | One current row per canonical identity | `attention_id`, rule key/version, subject kind/id, rule/attention state, severity, first/last seen, last reconciliation, snooze/acknowledgement/resolution fields, normalized snapshot hashes/JSON; unique `(rule_key, subject_kind, subject_id)` |
| `attention_history` | Append-only detection and lifecycle history | event ID, attention ID, reconciliation ID, event type, prior/new state, severity, rule version, actor, safe normalized observation snapshot, event timestamp |

Foreign keys link current signals and history to their rule and reconciliation
records where practical; confirmed reconciliation and lifecycle history also
reference their Attention operation. `attention_operations` is intentionally
separate from the current sync-only `dashboard_operations` path, while using
the same hashed-token, expiry, atomic-claim, and audit principles. Indexes must
support active/open severity ranking, subject lookup, recent history,
operation expiry/claim, and idempotent reconciliation lookup. JSON is limited
to normalized, schema-validated local snapshots; filtering and state
transitions do not depend on JSON text.

Migration requirements for a later Batch B:

- use the established idempotent bootstrap/migration path and preserve existing
  tables, views, foreign keys, indexes, and dependent views;
- create no initial historical backfill from old execution traces or source
  records, because that would invent lifecycle history;
- start with an empty Center and create history only from confirmed future
  reconciliations or lifecycle changes;
- make a downgrade safe by leaving the additive tables unused by the prior
  version; do not drop data automatically; and
- prove synthetic bootstrap, legacy upgrade, rollback, integrity, view
  preservation, and package rehearsal before promotion.

### Data lifecycle and state transitions

```text
Local SQLite facts and freshness
        -> confirmed reconciliation preview
        -> deterministic rule evaluation
        -> canonical identity / deduplication
        -> current attention row + append-only event
        -> read-only Center query and advisory recommendation
```

1. A reconciliation or lifecycle preview writes only an expiring
   `attention_operations` proposal. It reads local repositories, returns
   candidate counts, rule versions, source freshness, and proposed
   create/update/clear/reopen or lifecycle transitions. It does not write
   Attention signals/history or call connectors.
2. Explicit confirmation atomically claims the one-time operation and, for
   reconciliation, re-evaluates the same bounded local scope inside the
   persistence transaction. This avoids persisting a stale preview. It
   atomically records the reconciliation, current-state changes, and history
   events before finishing the operation.
3. A newly qualifying identity creates `open` + `active` and a `detected`
   event. An unchanged identity updates `last_seen_at` and appends
   `observed_again` only when the normalized semantic observation hash,
   severity, freshness state, or rule version changes; this controls history
   volume.
4. A successful, complete evaluation that no longer qualifies changes
   `rule_state` to `clear`, records `cleared`, and resolves the current item
   with machine reason `rule_clear`. A manual resolve is allowed only after the
   latest complete evaluation is clear; otherwise it fails safely with
   `ATTENTION_STILL_ACTIVE`.
5. Acknowledgement and snooze are manager workflow writes, never rule outcomes.
   They require preview and confirmation, actor recording, validation of a
   future bounded snooze expiry, and append-only history. Snoozed items remain
   countable and retrievable; they are not silently erased from summaries.
6. A missing, stale, partial, failed, or invalid required input never clears an
   existing active item. The reconciliation is `partial` or `failed`, creates a
   safe evaluation event/warning, and leaves prior active lifecycle state
   intact. The Center exposes the limitation through freshness and warnings.
7. A disabled rule is not evaluated. Its previously active items retain their
   last known rule state, receive a `rule_disabled` history/configuration event,
   and are surfaced with evaluation status `disabled`; they are never silently
   cleared. A later enable/semantic change requires its own approved rule
   version and reconciliation preview.
8. Every write uses propose, preview, explicit confirmation, and persist.
   Read-only query routes and ToolTransport never materialize, acknowledge,
   snooze, resolve, or otherwise mutate Attention state.

### Failure behavior

| Condition | Required behavior |
| --- | --- |
| Invalid rule catalog or unsupported parameter | No reconciliation write; safe `invalid` result with a stable warning code |
| Broken fact/evidence/freshness references | Fail closed through `RESULT_CONTRACT_INVALID`; no current/history mutation |
| Source unavailable, stale, partial, or unknown | Preserve active item; mark reconciliation limited; emit source-freshness signal where configured; do not clear or claim healthy |
| SQLite/transaction/concurrency failure | Roll back all current/history changes for the reconciliation; return safe `DATA_ACCESS_FAILED` or operation failure code without payload/error text |
| Expired, reused, or invalid confirmation | No domain mutation; retain only the operation status allowed by the confirmed-operation boundary |
| Stale preview differs at confirmation | Re-evaluate and return the current transition preview/result; never apply the old candidate snapshot |
| Rule disabled or replaced | Retain last known current item, record a configuration event and evaluation status; do not auto-resolve it or reuse identity across a semantic-breaking rule change |

## Compatibility strategy

- Keep `management-attention` read-only and byte-for-byte compatible in its
  business projections: data, context, item ranking, severity, limit,
  warnings, facts, signals, and empty recommendations remain Phase 1 behavior.
- Introduce a separate Center use case and descriptor rather than expanding the
  existing legacy projection into a persistence side effect. Its implemented
  descriptor capabilities may advertise facts, signals, and recommendations
  only after that behavior is implemented and tested.
- Retain `UseCaseResult` and descriptor contract version `1.0`; use additive
  data/context fields rather than changing Phase 1 intelligence models.
- Keep ToolTransport, structured query CLI, and generic Dashboard query routes
  read-only thin serializers. A dedicated Attention CLI/Dashboard write
  boundary is Batch C work and must use the Attention-specific preview/confirm
  contract rather than extending a query into a write.
- Do not put Attention payloads into `execution_traces`, and do not derive
  history by replaying trace summaries.
- Keep existing dashboard operation and staffing proposal records isolated.
  A later implementation may reuse their audited one-time confirmation pattern
  only after defining Attention-specific action names and scope validation.

## Deterministic and model boundary

Deterministic code owns rule evaluation, parameter validation, severity,
identity, deduplication, evidence/freshness references, reconciliation,
lifecycle transition validation, persistence, and recommendations.

The model may select the Center, explain the returned facts/signals/history,
compare returned advisory recommendations, and explain uncertainty. It must
not invent an Attention item, alter severity or lifecycle, claim a source is
fresh, infer a missing decision owner/due date, create an action, or confirm a
write.

## Synthetic scenarios and validation standard

The eventual implementation must cover at least these synthetic scenarios:

1. Red project, overdue action, stale source, and a member above 100% active
   assignment load
   produce explained, deduplicated active items with valid reference chains.
2. Repeated unchanged reconciliation does not create duplicate current rows or
   unbounded identical history.
3. A severity, rule-version, or normalized-evidence change appends the correct
   history event while keeping the same canonical item.
4. A complete, healthy re-evaluation clears and resolves a prior item; an
   unavailable or partial re-evaluation does neither.
5. Pending-decision rule is registered disabled, emits no active item, and
   cannot be enabled without a separately approved governance definition; no
   text inference occurs.
6. Reconciliation, acknowledge, snooze, expiry, and resolve all require a
   valid Attention-specific one-time preview/confirmation transaction and
   leave an auditable history.
7. Concurrent confirmations cannot apply the same lifecycle operation twice.
8. Read-only Center, existing Management Attention, structured CLI, and
   generic Dashboard preserve their defined contracts; legacy Management
   Attention returns no persistent side effect.
9. Invalid references, malformed catalog rows, and database failures fail
   safely without raw payload/error disclosure or partial state mutation.
10. Synthetic migration, integrity, rollback, package installation, and
    portable-boundary validation prove only additive Attention storage exists.

Acceptance for Phase 2 promotion requires every item to expose its current
facts, evidence, freshness, rule version, state change, and bounded advisory
recommendation; all focused and full validation must pass; and the owner must
explicitly promote the phase.

## Implementation batches after approval

### Batch B — Deterministic storage and reconciliation core

- Register an implementation pack only after this design is approved.
- Add approved additive schema, migrations, repository APIs, rule catalog, and
  transaction-safe reconciliation/lifecycle core.
- Add synthetic migration, integrity, rollback, deduplication, and concurrency
  tests. No connector integration or interface-specific behavior.

### Batch C — Center use-case and controlled interfaces

- Add separate read-only Center query and explicit preview/confirm operations.
- Emit validated facts, signals, recommendations, evidence, freshness, and
  bounded history through the shared executor.
- Add thin CLI/Dashboard/Copilot projections and compatibility tests proving
  existing Management Attention has no persistent side effect.

### Batch D — Regression and promotion decision

- Run focused Attention, lifecycle, contract, migration, concurrency, and
  compatibility tests; then `make validate` and `make rehearse-release`.
- Review schema/portable scope, update the implementation report and
  `PROGRESS.md`, and stop for explicit Phase 2 promotion.

## Approval gate

Owner review must explicitly approve the active four-rule catalog,
pending-decision disabled status, Center query/write contracts, lifecycle
semantics, proposed schema, reconciliation write authority, recommendation
set, migration/rollback approach, and batch scope before an implementation pack
is registered or any Phase 2 runtime or schema work starts.

Owner approval was recorded on 2026-07-28 after the operation boundary,
pending-decision disabled status, resource threshold, source-freshness advice,
and Center contracts were reviewed. The owner then authorized the Batch B
review corrections and configurable project-health RAG semantics described
above. The corrected Batch B remains stopped for review. This is not Batch C,
Phase 2 promotion, release, operational, connector, or real-data approval.
