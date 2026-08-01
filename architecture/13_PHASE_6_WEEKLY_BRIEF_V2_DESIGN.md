# Phase 6 — Weekly Brief v2 Design

Status: `DESIGN APPROVED — BATCH B1/B2/B3 OWNER-ACCEPTED — C AUTHORIZATION REQUIRED`
Date: 2026-08-01
Baseline branch: `codex/phase-6-weekly-brief-design`
Baseline commit: `7442f52cb5fc015c4efdcf20941293314f71e9db`
Previous promoted phase: `Phase 5 — Resource Intelligence`

## Decision supported

Give a Delivery Manager one management-ready weekly view of what is materially
true, what changed, what still needs attention, what was explicitly resolved,
and which evidence is insufficient. Every material statement must be generated
from deterministic, promoted public facts and remain traceable to exact
evidence and freshness.

Phase 6 composes existing capabilities. It does not become the owner of
Attention, Project Health, execution commitments, capacity, Actions, Decisions,
source freshness, or their storage.

## Authorization and review method

Only Batch A current-state inspection, gap analysis, and bounded design were
authorized. The review inspected the current branch and exact HEAD, the shared
executor and use-case registry, the legacy weekly report, the structured weekly
brief, project snapshots, Attention, layered Project Health, canonical
execution facts, Resource Intelligence, Action, Decision, source freshness,
their schemas, public projections, and focused synthetic tests.

This document creates no implementation authority. A Phase 6 implementation
pack, runtime/schema/test edit, implementation batch, or legacy replacement
requires a later explicit owner decision.

The owner approved this design after review and then separately authorized only
Batch B1 public read-contract prerequisites. IP-032 records that bounded
authorization. The owner accepted the B1 result at
`cce14e42c26c605bc76e895de8d611540eae06f8`. The owner subsequently authorized
only B2 implementation; B3 and all later slices remain unauthorized.

Four requested reading-list paths do not exist under those titles in this
checkout. The numbered repository documents actually read were
`01_TARGET_COMPONENT_MODEL.md`,
`04_COPILOT_LOCAL_AGENT_ARCHITECTURE.md`,
`07_PHASE_2_DELIVERY_ATTENTION_CENTER_DESIGN.md`, and
`09_PHASE_3_EXECUTION_AND_MILESTONE_FOUNDATION_DESIGN.md`.

## Verified current architecture

### Weekly paths

The structured path is:

```text
Copilot / pm tool query / generic Dashboard query
    -> ToolTransport / UseCaseExecutor
    -> weekly-dm-brief
    -> WeeklyReportService.weekly()
    -> generic repository queries
    -> UseCaseResult 1.0
```

The legacy CLI path is separate:

```text
pm report
    -> WeeklyReportService.weekly()
    -> deterministic Markdown text
```

`WeeklyReportService` reads current non-completed projects, the legacy
`v_member_load` view, open and overdue Actions, the ten most recent Decision
records, current Confluence status signals, change-request summaries, and the
latest Action Tracker summary. It does not read the promoted Attention Center,
layered Project Health, canonical execution facts, or effective-capacity
contracts.

`weekly-dm-brief` adds only one aggregate local evidence record, freshness for
the Confluence and ServiceNow sources, a summary, and the legacy Markdown. Its
descriptor accepts no parameters and advertises no facts, signals, or
recommendations. No focused behavioral test exercises this use case beyond
discovery; existing weekly behavior is characterized through
`WeeklyReportService` tests.

### Snapshot and history paths

`project-snapshot-list` is a public read-only projection over stored
`project_snapshots`. The legacy Dashboard snapshot endpoint reads the same
records. The `pm planning add` path writes a project snapshot directly.

These records are project-scoped planning/status artifacts containing narrative
arrays, an optional predecessor ID, and an optional source-run reference. They
are not a Weekly Brief input manifest, do not cover cross-project Attention or
capacity, and have no deterministic comparison or completeness contract.

`execution_traces` deliberately stores bounded evidence/freshness/warning
summaries without business payloads. It cannot be used to reconstruct a prior
brief. Attention and Project Health retain their own histories, but neither is
a complete cross-capability Weekly Brief baseline.

### Promoted capability contracts

| Capability | Verified public read boundary | Capability-owned storage that Weekly Brief must not read directly |
| --- | --- | --- |
| Attention | `delivery-attention-center` returns persisted items, reconciliation coverage, optional bounded history, typed facts/signals/recommendations, evidence, and freshness | `attention_*` tables and repository transaction helpers |
| Project Health | `layered-project-health-review` uses the Project Health read model to return the latest persisted seven-dimension assessment | `project_health_*` assessment/configuration/import tables |
| Execution | `delivery-execution-review` uses the execution-review reader to return latest bounded Sprint and Release/Milestone facts | canonical execution, derivation, Milestone operation, and source-evidence tables |
| Resource Intelligence | `resource-capacity-heatmap` and public effective-capacity/project-capacity readers return current published derivations | `resource_capacity_*` and workforce/planning import audit/coverage tables |
| Action | `action-followup` returns current open Actions that are overdue or lack owner/due date | direct `action_items` queries and legacy add/complete writes |
| Decision | no independent public decision-read contract exists | `decision_log` and its JSON internals |
| Freshness | source-state repository returns the latest normalized state from `data_sources` and `sync_runs` | raw source configuration, connector payloads, credentials, and raw errors |

A user-facing use case must not invoke another user-facing use case. Phase 6
therefore consumes existing capability read models where they are public and
requires a minimal capability-owned read contract where only a presentation
handler or private storage query currently exists. It never queries another
capability's private table.

## Verified gap analysis against the nine required sections

| Required section | Verified current behavior | Gap for v2 |
| --- | --- | --- |
| Overall health | Counts project status, legacy current load, Actions, and changes | Does not use layered Project Health; limited evidence can appear reassuring |
| Changes since previous snapshot | No Weekly Brief baseline or comparison | Entire section unavailable |
| Highest attention signals | Does not read persisted Attention | Entire section unavailable |
| Achievements | Lists projects and some status text | No structured weekly achievement identity, window, or evidence contract |
| Risks and dependencies | May include project notes, Confluence text, and change requests | Does not use canonical dependency/commitment or layered-health facts; statements are not individually traceable |
| Decisions required | Lists recent Decision records | `pending` is not a proved decision request; owner, due date, and eligibility are absent |
| Resource concerns | Uses `current_load >= 1.0` from the legacy workload view | Does not use effective capacity, authoritative plan coverage, state precedence, or derivation evidence |
| Next actions | Lists at most five high-priority Actions | Does not use the Action follow-up reasons or Attention recommendations; no statement reference chain |
| Freshness and limitations | Projects two source states at result level | Does not qualify every material statement or propagate upstream limitations |

Additional verified gaps:

- the current brief does not emit typed facts, signals, or recommendations;
- its one evidence record cannot identify which records support each sentence;
- its week is selected independently inside the legacy service rather than
  fixed once as a returned UTC execution boundary;
- the report text includes operational display names and narrative fields,
  while v2 comparison identity requires stable anonymous canonical IDs;
- the absence of an item has no authoritative meaning and cannot imply clear,
  healthy, resolved, zero, or available; and
- the current tests do not cover the structured Weekly Brief behavior,
  missing/partial/stale/conflicting inputs, cross-reference integrity, or
  legacy/v2 coexistence.

## Capability owner and module boundary

Phase 6 owns one bounded Weekly Brief capability. Its logical module owner is
`pm_agent.weekly_brief`; the later implementation pack must map this boundary
to exact repository files after revalidating the checkout.

It owns only:

- v2 input validation and normalized scope;
- deterministic section composition and ordering;
- stable statement identity and semantic fingerprints;
- comparison with the prior confirmed, structurally complete same-scope Weekly
  Brief snapshot;
- statement-level evidence/freshness reference assembly;
- a renderer-neutral v2 result and deterministic legacy-compatible Markdown
  projection; and
- controlled snapshot capture and immutable confirmed history for v2
  comparison.

It must not own:

- Attention rules, reconciliation, lifecycle, or storage;
- Project Health assessment, configuration, or storage;
- capacity calculation, allocation coverage, Staffing, or workforce import;
- execution/Milestone derivation or canonical storage;
- Action or Decision lifecycle and writes;
- source freshness calculation, connector acquisition, or raw source mapping;
- generic repository behavior, schema composition rules, or interface-specific
  business logic.

`database/bootstrap.py` may later compose a dedicated Weekly Brief schema
installer. It must not contain Weekly Brief DDL text, comparison rules, queries,
transactions, or result projection. A generic repository must not gain Weekly
Brief storage or cross-capability queries.

## Public input contract

Preserve `weekly-dm-brief` and `UseCaseResult 1.0`. V2 is explicit opt-in so the
empty legacy request remains unchanged.

| Parameter | Required behavior |
| --- | --- |
| `brief_version` | Optional enum `1.0` or `2.0`; absent remains legacy `1.0` behavior |
| `project_ids` | Optional unique bounded stable-anonymous project IDs; every supplied ID must exist |
| `plan_version_id` | Optional exact plan version for the execution month; omission makes Resource concerns explicitly `not_available` |
| `attention_limit` | Optional integer 1–50; default 10; limits after deterministic Attention ordering |
| `baseline_snapshot_id` | Optional exact same-scope confirmed v2 snapshot; absent selects the latest eligible prior confirmed snapshot |

V2 is a current-state brief. It does not accept a caller-selected historical or
future `as_of`, because the promoted Attention and Project Health readers expose
current/latest state rather than an as-of cut. The runtime fixes one UTC
`generated_at` at execution start and uses it for the week and Resource month.
Tests may inject a clock at the capability boundary, but the public request
cannot mix a historical timestamp with current facts.

There is no inferred plan version. B1 must add a minimal manifest owned by the
canonical Project identity/read boundary that returns the complete active
stable-anonymous project set and its coverage. Project Health assessments and
the workforce-planning manifest cannot substitute for that manifest because an
absent assessment or Resource publication must remain distinguishable from an
absent project. Workforce planning is Resource evidence only; it never defines
global Weekly Brief scope. A full-scope request uses the complete canonical
Project manifest; a project list must be a subset of it. Neither path infers a
source Board or connector scope.

Invalid identifiers, bounds, baseline scope, project-manifest coverage, or plan
references return `status = invalid` or `unavailable` with stable safe warning
codes. A query never creates or changes a snapshot operation.

## Public output contract

V2 keeps the legacy top-level business keys in `data`:

```text
week
brief
summary
```

It adds:

```text
brief_version: 2.0
generated_at
scope
comparison
sections
statements[]
snapshot
```

The nine fixed section keys are:

```text
overall_health
changes_since_previous_snapshot
highest_attention_signals
achievements
risks_and_dependencies
decisions_required
resource_concerns
next_actions
freshness_and_limitations
```

Every section contains:

- `availability`: `available | partial | not_available | not_applicable`;
- deterministic `items` in stable order;
- `limitations` containing stable codes; and
- counts before and after any limit.

Every material item is also represented in `statements[]` with:

- stable `statement_id` derived from section, producer capability, canonical
  subject, and fact/signal type, never display text or list position;
- subject kind and stable anonymous ID;
- normalized value/value state, signal state/severity, and reason codes;
- `change_state`: `new | continuing | resolved | not_comparable`;
- `changed` for a continuing identity whose semantic value changed;
- `evidence_changed` when only evidence identity, coverage, or freshness
  qualification changed;
- fact, signal, recommendation, evidence, and freshness references as
  applicable; and
- no free-form model-authored factual payload.

The top-level `facts`, `signals`, and `recommendations` use the promoted Phase 1
contract. A section item references those validated objects. The renderer builds
`brief` only from the same structured items; it must not create an additional
fact during formatting.

`summary` contains only counts and deterministic aggregate state. It cannot
turn an unavailable section into zero or a green aggregate.

`snapshot` reports only the selected confirmed baseline metadata,
`capture_state = not_requested`, and a non-secret `capture_candidate` containing
the query `execution_id`, `generated_at`, normalized input and scope
fingerprints, selected baseline ID/fingerprint, and exact result fingerprint.
The result fingerprint covers the normalized structured v2 result and excludes
only presentation text and the candidate envelope itself. A query response
never exposes a confirmation token or claims that the current result was
captured. Snapshot preview/confirmation uses the separate controlled operation
contract below.

## Composition rules for the nine sections

### Overall health

Consume only the latest persisted layered Project Health public facts for the
selected projects. Apply no averaging and no new health thresholds:

1. any known red project makes the section red;
2. otherwise any known amber project makes it amber;
3. green requires every selected project's mandatory assessment to be known,
   complete, non-conflicting, and fresh;
4. any missing, unknown, stale, conflicting, or not-available assessment makes
   the section limited/unknown with its exact reason; and
5. no assessment means `not_available`, not healthy.

### Changes since the previous snapshot

Project the deterministic comparison states from the snapshot algorithm below.
With no eligible baseline, return `not_available` and
`WEEKLY_BRIEF_BASELINE_NOT_AVAILABLE`. Do not label every current item new on
the first run.

### Highest attention signals

Consume persisted Attention current state and reconciliation coverage through
an Attention-owned public read contract. Preserve the Center's severity and
ordering. An empty result is clear only when complete coverage proves it;
otherwise the section is partial or not available. No new producer or
reconciliation occurs.

For a project-scoped brief, include an Attention item only when its public fact
contains an explicit canonical project association. Project-subject items are
directly eligible. Action-, member-, source-, or other-subject items are not
mapped from titles, source strings, assignments, private tables, or prose. They
are excluded with `ATTENTION_PROJECT_SCOPE_NOT_PROVED` unless the owning public
contract explicitly supplies the association. A global brief may include them
under the explicit global scope.

### Achievements

The initial bounded achievement set is limited to:

- a canonical Milestone adherence fact that became `achieved_on_time` or
  `achieved_late` inside the comparison window with complete, fresh evidence;
  and
- a recorded Action whose explicit `completed_at` falls inside the comparison
  window, after a capability-owned Action reader exposes that fact.

No project narrative, title, summary, model interpretation, or missing prior
record can become an achievement. If neither supported producer can prove
coverage, the section is `not_available` rather than empty success.

### Risks and dependencies

Compose, without re-scoring:

- red/amber layered Project Health facts and their guard/factor evidence;
- active canonical execution/Milestone/dependency exception signals; and
- covered active Attention items relevant to the selected projects.

Deduplicate only when the same canonical subject, fact/signal type, rule
version, and evidence identity are equal. Similar prose is not a deduplication
key.

### Decisions required

The current Decision store has no approved required-decision definition. This
section is therefore `not_available` with
`DECISION_REQUIRED_DEFINITION_NOT_AVAILABLE`. A recent or `pending` Decision
record must not be treated as a request for decision.

Phase 6 does not add owner/due/type governance, activate
`pending_decision_attention`, or inspect Decision JSON narrative. A later
separately approved upstream contract may make this section available without
changing the Weekly Brief section contract.

### Resource concerns

When an exact plan version is supplied, consume the promoted effective-capacity
and project-capacity public readers for the execution month. Preserve known,
unknown, stale, and conflicting states and the existing overload rule/version.
An authoritative empty assignment set remains known empty but is not described
as spare capacity or healthy. Without an exact plan, coverage, or current
derivation, return the corresponding limitation.

### Next actions

Consume only Action follow-up facts and advisory Attention recommendations from
public contracts. Preserve supported recommendation state. A blocked or absent
recommendation is not converted into an Action. Phase 6 creates, assigns,
completes, or confirms nothing.

### Freshness and limitations

Aggregate the limitations already attached to every statement and list each
material producer's coverage/freshness state. This section never substitutes a
global source timestamp for capability-specific freshness. It includes the
baseline state, section availability, truncation, and safe warning codes.

## Evidence and freshness contract

Every material statement must have at least one fact or signal reference. Every
known fact must reference exact evidence. Every source-dependent fact must
reference freshness. Upstream IDs are namespaced by capability when assembled
to prevent result-local collisions while preserving the original identity in
normalized metadata.

The composer copies only the minimum normalized public evidence required by the
result. It does not copy raw payloads, internal table rows, endpoints,
credentials, source configuration, names, or model prose.

State propagation is fail closed:

- a conflicting value remains `value_state = conflicting`;
- a missing or partial expected input remains unknown/partial;
- stale evidence remains stale even when a newer unrelated source is fresh;
- failed/unavailable evidence remains unavailable;
- a section can be available only to the degree justified by all mandatory
  inputs; and
- a top-level success may contain partial or unavailable sections, but its
  limitations must remain explicit.

Comparison keeps three separate hashes:

- the identity key contains section, producer capability, canonical subject,
  and fact/signal type;
- the business semantic fingerprint contains normalized value/value state,
  signal state/severity, reason codes, and rule version; and
- the evidence-state fingerprint contains evidence identities, coverage, and
  freshness states.

`changed` compares only the business semantic fingerprint.
`evidence_changed` compares only the evidence-state fingerprint and never
claims that the business fact changed. All hashes exclude execution ID, display
text, render order, and generation timestamp.

## New, continuing, and resolved semantics

Comparison uses the newest prior confirmed, structurally complete snapshot with
the same normalized scope and comparison-rule version, or the explicitly
selected eligible baseline. Scope is either `global` over one complete project
manifest or `projects` over the exact sorted project ID set. The plan version,
limits, and generated time are input provenance, not scope identity; their
business effect remains visible through statement semantics and evidence.

For a material concern identity:

- `new`: absent from the eligible baseline statement manifest and currently
  proved active/material by complete usable evidence;
- `continuing`: present as active/material in both manifests; `changed = true`
  only when its business semantic fingerprint changed;
- `resolved`: active/material in the baseline and currently proved clear,
  resolved, completed, or green by the owning capability with complete usable
  evidence; and
- `not_comparable`: no eligible baseline, changed scope, unsupported history,
  or evidence that is missing, partial, stale, failed, unavailable, or
  conflicting at the point needed to prove a transition.

`new` additionally requires the baseline manifest to prove complete coverage
for that producer and scope. Absence from a limited baseline is not new.
Snapshots with limited sections may still be structurally eligible baselines;
comparison fails closed per statement and producer rather than disabling every
other covered section.

Current absence alone never means resolved. An Attention item uses its explicit
rule/lifecycle transition and coverage. A Project Health or capacity concern
uses an explicit current known clear/green fact with complete evidence. An
Action uses explicit completion. `continuing` with a limitation is allowed only
when the owning current public contract explicitly proves that the same concern
identity remains active/material despite limited qualification, for example a
retained current Attention item whose freshness is stale. If only the baseline
item is known, the current item is absent, or the current public contract cannot
prove either active/material or clear/resolved state, the result is
`not_comparable`; it is never inferred as continuing or resolved.

Achievements use an event inside the baseline-confirmed-at to `generated_at`
interval rather than the generic concern classification. B1 must expose the
exact source observation/completion time through the owning public contract;
otherwise the item is not comparable. The same achieved Milestone is not
emitted as a new achievement every week.

## Snapshot and history strategy

The current project-snapshot and execution-trace stores cannot protect the
required Weekly Brief comparison invariant. The v2 query must remain genuinely
read-only: it selects a prior confirmed baseline and returns a composition, but
never changes the state used by a later query.

After separate implementation approval, add one dedicated controlled
snapshot-operation table owned by the Weekly Brief capability. One table is
sufficient for the initial invariant and combines the expiring capture
operation with its immutable confirmed snapshot; do not create a general event
store or snapshot framework.

The explicit lifecycle is:

```text
v2 query
  -> snapshot capture preview
  -> exact preview shown to the manager
  -> explicit confirmation
  -> revalidate input and baseline fingerprint
  -> confirmed snapshot becomes comparison-eligible
```

The two public controlled-operation names and their minimum contracts are:

| Operation | Request | Response |
| --- | --- | --- |
| `weekly-brief-snapshot-preview` | The exact query `execution_id`, `generated_at`, normalized v2 query input, scope/input fingerprints, selected baseline ID/fingerprint, result fingerprint, and a caller idempotency key | `status = previewed`, stable `operation_id`, the complete normalized capture candidate and fingerprints, `confirmation_required = true`, expiry, safe warnings, and the plaintext one-time confirmation token returned exactly once |
| `weekly-brief-snapshot-confirm` | Exact `operation_id` and plaintext one-time confirmation token | `status = confirmed | already_confirmed | expired | stale | failed`, immutable `confirmed_snapshot_id` when successful, `confirmed_at`, normalized scope, result fingerprint, and safe warnings; it never returns the token |

Preview validates that the candidate envelope and normalized query input
reproduce the referenced query's exact scope, baseline, structured result, and
fingerprints from current public inputs. It rejects an unknown execution,
altered envelope, or result drift before issuing a token. The stored proposed
row is the complete candidate shown for approval; the user does not approve a
later recomposition implicitly. Confirmation atomically claims that exact
proposal, recomposes current public inputs, and requires the scope, input,
baseline, statement, evidence-state, and overall result fingerprints to remain
identical before persisting it as confirmed. Thus a query result cannot be
captured by reference alone after its evidence has changed.

Stable safe result/warning codes include:

```text
WEEKLY_BRIEF_CAPTURE_CANDIDATE_INVALID
WEEKLY_BRIEF_CAPTURE_CANDIDATE_STALE
WEEKLY_BRIEF_CAPTURE_OPERATION_EXPIRED
WEEKLY_BRIEF_CAPTURE_TOKEN_INVALID
WEEKLY_BRIEF_CAPTURE_ALREADY_CONFIRMED
WEEKLY_BRIEF_CAPTURE_CONFLICT
WEEKLY_BRIEF_CAPTURE_DATA_ACCESS_FAILED
```

An identical confirm replay returns `already_confirmed` with the original
snapshot identity and creates no row. Expired, stale, invalid-token, conflict,
or failed results create no confirmed baseline and expose no sensitive token or
raw exception. Preview and confirm report non-read-only operation metadata and
are never routed through the read-only generic query transport.

The row records:

- stable operation/snapshot ID, v2 contract/comparison-rule version,
  normalized scope and scope fingerprint;
- generated time, week, baseline snapshot ID, input fingerprint, idempotency
  key, token hash, expiry, actor, and status
  `proposed | claimed | confirmed | expired | failed`;
- `structural_status = complete | failed`, separate section/producers coverage
  states, and safe limitation codes;
- normalized statement-state manifest with separate business-semantic and
  evidence-state fingerprints; and
- evidence/freshness identity summary sufficient for integrity checking,
  without rendered names or raw source data.

`structural_status = complete` means the scope, contract/rule versions,
manifest shape, reference integrity, and persisted fingerprint are valid. It
does not mean all nine sections are available. A confirmed structurally
complete snapshot is eligible as a baseline even when one section is partial
or `not_available`; comparison eligibility for an individual statement still
requires the baseline producer/scope coverage needed by that transition.
Structural/reference failure cannot become a baseline.

Preview stores only a hashed, expiring, one-time confirmation token and returns
the plaintext token once. Changed inputs reject the preview as stale and persist
no confirmed baseline. Identical confirmed replay is idempotent; concurrent or
reused confirmation cannot create two snapshots. A failed capture does not
change the prior eligible baseline.

The capture boundary is separate from read-only ToolTransport query routing and
must report non-read-only operation metadata accurately. CLI, Dashboard, and
Copilot may preview or confirm it only through the dedicated controlled
operation contract and only after explicit user authorization. Snapshot capture
is not publication, email, or a business-object change, but it follows the same
propose/preview/confirm/persist safety rule because it changes future comparison
semantics.

Snapshots from a different scope or contract/comparison version are not
silently used. Retention, deletion, publication, and export are outside Phase
6; no automatic cleanup is added. Confirmed snapshot content is immutable;
only operation status fields transition under the controlled lifecycle.

## Clean bootstrap, derivation, integrity, and rollback

The production path is:

```text
empty local database
  -> idempotent bootstrap including dedicated Weekly Brief snapshot schema
  -> promoted versioned upstream imports and derivations
  -> public-contract coverage checks
  -> deterministic v2 composition
  -> explicit capture preview and confirmation
  -> immutable confirmed snapshot
  -> statement-reference, scope, baseline, and SQLite integrity report
```

Weekly Brief snapshots are confirmed derived local history, not imported
business facts. No separate Weekly Brief data import or backfill is required.
After a clean full re-import, the first v2 query explicitly has no baseline;
history begins only after its separate capture confirmation. Existing project
snapshots and legacy reports are not migrated or reinterpreted.

Software rollback before snapshot persistence removes only v2 code. After the
additive table exists, the prior runtime ignores it and legacy weekly behavior
continues unchanged. Rollback never deletes operations/snapshots or rewrites
other capability data. Installed-package rehearsal must prove clean bootstrap,
preview/confirm, token safety, stale/concurrent/idempotent replay,
structural-versus-coverage eligibility, integrity, prior-runtime legacy
behavior, and additive-data preservation.

## Deterministic and model boundary

Deterministic code owns:

- input validation, scope, one UTC `generated_at`, and baseline selection;
- all public reader calls and coverage checks;
- section availability, filtering, ordering, limiting, and deduplication;
- overall-health aggregation without averaging;
- statement IDs, semantic fingerprints, and change classification;
- evidence/freshness propagation and reference integrity;
- deterministic Markdown projection;
- snapshot capture preview/confirm, idempotency, persistence, and integrity;
- safe status, warnings, and execution metadata.

The model may:

- select v2 when the user asks for the Weekly Brief and supply known exact
  scope inputs;
- summarize and compare returned structured statements;
- explain trade-offs, freshness, and uncertainty; and
- ask for a missing exact plan version when Resource concerns matter;
- request a snapshot capture preview only after the user explicitly asks to
  establish that exact brief as a baseline; and
- confirm only that exact preview after the user explicitly approves it.

The model must not:

- create a statement, achievement, risk, dependency, decision request, Action,
  or resolution absent from the result;
- change severity, rule version, value state, freshness, or change state;
- convert missing evidence into zero, green, healthy, safe, or available;
- treat `pending` Decision as required;
- infer a plan, baseline, Milestone, owner, due date, or capacity from prose;
- call connectors, reconcile Attention, invent/reuse a token, or confirm a
  snapshot without explicit approval of the exact preview; or
- turn the brief into publication, email, Action, Decision, Staffing, or
  project-state mutation.

## Focused validation entry points

The later implementation pack must map capability-named focused suites to the
actual checkout before editing. The minimum focused entry is a Weekly Brief v2
contract/comparison suite. Combined regression must include the existing
weekly report, unified use-case/discovery/transport, Attention Center, layered
Project Health, execution review, Resource capacity, Action follow-up,
snapshot, and Delivery Manager agent tests.

Required synthetic scenarios:

1. First v2 run has no baseline and labels comparison `not_available`, not all
   current concerns new.
2. A covered Attention item is new, remains continuing on replay/change, and
   becomes resolved only after explicit complete-clear evidence.
3. Partial or stale Attention evidence retains the prior concern and cannot
   resolve it.
4. Red layered health dominates overall health; missing mandatory assessments
   prevent green.
5. A critical achieved Milestone inside the window is an achievement once;
   narrative text cannot create one.
6. The Decisions Required section remains not available despite a recent
   `pending` Decision row.
7. Known capacity overload is shown with exact derivation/plan evidence;
   missing plan, unknown, stale, and conflicting capacity remain limitations.
8. Explicit authoritative empty allocation is not described as spare capacity.
9. Action completion and Action follow-up retain distinct meanings and exact
   evidence.
10. Every statement reference resolves; malformed upstream references fail
    closed without a snapshot baseline.
11. The v2 query performs no snapshot write; identical capture confirmation is
    idempotent, and changed scope/input/baseline rejects the preview as stale.
12. Limited but structurally complete confirmed snapshots remain eligible only
    for producer scopes whose coverage they prove; failed/unconfirmed
    operations never replace the latest confirmed baseline.
13. Legacy empty-parameter `weekly-dm-brief`, `pm report`, data keys, Markdown,
    and current tests remain unchanged.
14. Generic CLI, Dashboard, direct executor, and Copilot routing preserve the
    same v2 business contract.
15. Clean bootstrap, upstream synthetic re-import, first/second v2 generation,
    integrity, installed-package rollback, and prior-runtime legacy behavior
    pass without active data.
16. Portable artifacts contain only stable anonymous synthetic identifiers and
    no operational names, source payloads, credentials, or internal URLs.

Focused documentation validation for Batch A is `git diff --check` plus a
scope/gate/reference scan over this design and `PROGRESS.md`, followed by
`make validate`. Schema/import/installed behavior is unchanged in Batch A, so
`make rehearse-release` is not required for this design-only batch.

## Separately reviewable implementation slices after approval

The design itself authorizes no slice. The owner subsequently authorized only
B1 through the named IP-032 gate; B2 and later slices remain unauthorized.

### B1 — Public read-contract prerequisites

- add the minimum complete active-project scope manifest in the canonical
  Project identity/read boundary; workforce planning remains Resource evidence
  and cannot define project existence or global brief scope;
- add or extract the minimum Attention current/history and Action
  current/completion capability-owned read models needed for Weekly Brief
  composition, including explicit project association when it is actually
  known;
- expose the exact current comparison-window observation/completion time needed
  for supported execution achievements; do not claim historical as-of reads;
- verify the existing Project Health, Resource, and source-state readers expose
  the required normalized current facts without private-table access, and add
  only the minimum owner-local reader field if a proved contract gap remains;
- define global versus exact-project eligibility per producer; an unproved
  Action/member/source-to-project association is excluded with a limitation;
- add no schema, producer, reconciliation, lifecycle, business write, or Weekly
  interface behavior; and
- prove behavior-preserving parity with the existing public use cases.

Rollback: revert the additive readers; existing handlers remain unchanged.

### B2 — Weekly snapshot and comparison core

- add dedicated additive schema composition and the one-table controlled
  snapshot-operation/confirmed-history repository;
- implement hashed one-time preview/confirm, stale and concurrent rejection,
  scope/input/baseline fingerprints, idempotency, structurally complete versus
  producer-coverage eligibility, statement comparison, and integrity reporting;
- expose no public v2 route yet; and
- run focused schema, concurrency, replay, clean-bootstrap, and rollback tests.

Rollback: prior runtime ignores the additive table; preserve all rows.

### B3 — Nine-section deterministic composition

- compose the fixed nine sections from public readers;
- emit typed facts/signals/recommendations and statement reference chains;
- implement fail-closed section availability and deterministic rendering; and
- keep Decisions Required explicitly unavailable until its upstream governance
  contract is separately approved.

Rollback: remove the composer while preserving upstream data and snapshots.

### C — Shared interface and legacy strangler integration

- add explicit `brief_version = 2.0` routing to the existing shared executor;
- preserve the empty legacy request and `pm report` exactly;
- keep generic ToolTransport/Dashboard query genuinely read-only;
- add a dedicated snapshot capture preview/confirm CLI/Dashboard operation and
  Copilot contract requiring explicit approval of the exact preview; and
- create no dedicated Dashboard UI, publication, email, or business-object
  write action.

Rollback: stop advertising/routing v2 and retain v1 plus additive snapshots.

### D — Regression and promotion decision

- run combined focused regression and `make validate`;
- run `make rehearse-release` because B2 changes schema and installed behavior;
- independently review contracts, privacy, clean import, schema, rollback,
  traceability, freshness, and legacy compatibility;
- add the implementation report and reconcile `PROGRESS.md`; and
- stop for explicit owner promotion, revision, or rejection.

Passing any slice does not authorize the next one.

## Non-goals

- no Phase 6 implementation or implementation-pack registration in Batch A;
- no new Attention producer, reconciliation trigger, lifecycle meaning, or
  `pending_decision_attention` activation;
- no Decision-required governance, Action creation/completion, Project update,
  Staffing change, capacity edit, publication, email, or notification;
- no replacement or semantic change of `WeeklyReportService`, `pm report`,
  legacy `weekly-dm-brief`, `project-health-review`, or project snapshots;
- no direct read of another capability's private tables or repository internals;
- no generic snapshot/event framework, broad repository split, schema redesign,
  Forecast, Simulation, or future-section plugin system;
- no live connector, active operational database, real data, company-derived
  content, credentials, or internal identifier;
- no push, merge, tag, release, deployment, or automatic next Batch.

## Risks and controls

| Risk | Control |
| --- | --- |
| Snapshot capture changes future comparison semantics | Keep query read-only; use a separate hashed one-time preview/confirm operation with stale/concurrency checks |
| Cross-capability coupling | Consume capability-owned read contracts only; B1 is a separate parity-reviewed prerequisite |
| Missing item is called resolved | Require explicit complete clear/resolved evidence and coverage; absence alone is never resolution |
| First run labels everything new | No eligible baseline produces `not_comparable` and an explicit limitation |
| Rendered prose diverges from structured facts | Deterministic renderer uses only structured statements; model cannot add facts |
| Resource section guesses a plan | Exact plan is optional input; omission is `not_available` |
| Recent pending Decision becomes a false request | Keep Decisions Required unavailable until a separately approved governance contract exists |
| Additive snapshot becomes a future generic framework | One capability-owned operation/history table protects only the current comparison invariant; no plugin/event abstraction |
| Legacy consumers break | Explicit v2 opt-in; empty request and `pm report` remain unchanged; parity tests |
| Confidential detail enters snapshots | Store normalized stable IDs, states, fingerprints, refs, and safe codes only; no display names or raw payloads |

## Approval gate and exact next action

The exact next action is owner review of this bounded design. The owner must
approve or revise the capability boundary, v2 opt-in compatibility, public
inputs/output, nine-section rules, evidence/freshness propagation,
new/continuing/resolved semantics, one-table snapshot strategy, clean-import
position, rollback, tests, non-goals, and proposed B1–D gates.

Until explicit approval and one named implementation authorization, do not
register a Phase 6 implementation pack or modify runtime, schema, or tests.
Do not begin B1 automatically.
