# Phase 3 — Execution and Milestone Signal Foundation

Status: `APPROVED — BATCH C2 REVIEW PASSED; BATCH D AUTHORIZATION REQUIRED`
Date: 2026-07-29
Baseline branch: `codex/phase-2-attention-center`
Baseline commit: `2185334c890e79480a39514cf1d1e45f74e062f1`
Previous promoted phase: `Phase 2 — Delivery Attention Center`

## Decision supported

Give a Delivery Manager trustworthy, source-traceable answers to two distinct
questions without pretending that Story Point coverage or a legacy Jira grade
is sufficient:

1. Is the current Sprint executing as observed?
2. Are Release commitments and Milestones changing, blocked, due, achieved, or
   missed according to structured evidence?

Phase 3 creates canonical execution, Release, Milestone, and Dependency facts.
It does not calculate the seven-dimension Project Health model, accept
DM-configurable health conditions, or forecast future dates.

## Review method and verified current state

The review inspected the current SQLite bootstrap and migrations, Jira release
and health sync paths, connector wrapper, Dashboard sync confirmation,
Project Health repository/use case, Attention rules and reconciliation
boundary, board registry importer, and focused synthetic compatibility tests.

The verified current path is:

```text
confirmed Dashboard sync or explicit CLI sync
    -> Jira Release Version fetch
    -> current version and Issue snapshot upsert
    -> active Sprint fetch and legacy health calculation
    -> append legacy jira_health_snapshot
    -> project-health-review reads the latest local snapshots
    -> Phase 2 Attention may consume the legacy Jira grade
```

Current storage provides:

- `jira_stream_versions`: one mutable current row per Jira Version and board;
- `jira_issues`: one mutable current row per Issue and board, with at most one
  `version_id`;
- `jira_sprints`: one mutable current row per Sprint and board;
- `jira_health_snapshots`: append-only snapshots of the legacy four-score
  calculation;
- `sync_runs` and `data_sources`: source-run audit and freshness;
- unstructured `project_profiles.milestones` and project-snapshot milestone or
  dependency JSON intended for context, not canonical evidence; and
- the promoted Phase 2 Attention rule, reconciliation, current-item, and
  history stores.

Focused current-contract verification passed 44 tests covering Dashboard Jira
sync confirmation, registry cleanup, unified use-case compatibility, database
bootstrap, and Attention reconciliation behavior.

## Current-state findings

### What can be reused

- active project and board registry relationships;
- Jira connector authentication and explicit sync authorization;
- `sync_runs` freshness and safe failure reporting;
- current Release Version and Issue snapshot tables as legacy read models;
- idempotent SQLite bootstrap/migration patterns;
- `UseCaseResult 1.0`, shared executor, discovery, CLI, Dashboard Tool
  Transport, and Copilot projections;
- Phase 2 Attention identity, deduplication, lifecycle, history, and automatic
  `rule_clear` resolution; and
- repository boundary and synthetic-data controls.

### Gaps that block Phase 3

1. Issue changes overwrite the current row. There is no changelog event cache,
   status-transition time, continuous blocked interval, or as-of reconstruction.
2. Jira Issue Links are not acquired or normalized. Dependency direction and
   readiness therefore cannot be supported.
3. An Issue can have multiple Fix Versions, but the current row stores only one
   `version_id`. Release scope is not a canonical many-to-many relationship.
4. Removed or moved Issues are not reconciled from a complete scope manifest.
   A partial fetch cannot be distinguished safely from true removal.
5. Sprint commitment is reconstructed from the currently returned Issues, not
   captured at a commitment boundary. Scope churn and carry-over are therefore
   not reproducible.
6. Jira Version rows are mutable current snapshots. Target-date change,
   Release scope change, and historical commitment state are not retained.
7. Jira `releaseDate` is an observed source target. It is not automatically an
   approved contractual baseline, a forecast, an actual completion date, or a
   general Milestone.
8. There is no canonical Milestone, Release commitment, or Dependency model.
   Existing profile and snapshot JSON lacks lifecycle, authority, evidence,
   completeness, and version semantics.
9. Missing Story Points are converted into neutral-looking legacy scores:
   Release burndown returns 50, Sprint completion returns 50, and scope returns
   70 when their Story Point baselines are absent.
10. The legacy health calculation also assumes a 90-day Release line and
    selects a primary unreleased Version. It cannot represent independent
    Milestones or multiple Release commitments.
11. The current Jira queries hard-code a Story Point custom field and a
    calendar cutoff. Non-success search responses may stop pagination without
    a complete published-scope contract, so a truncated response can look like
    a usable snapshot.
12. Current source caches retain Issue summary, assignee identifiers/display
    names, and a raw Version payload. Phase 3 canonical and derived storage
    needs stricter field minimization.
13. The new layered facts and signals have no read-only use case and no
    approved post-sync evaluation path.

The legacy tables and calculations remain compatibility evidence. Phase 3 must
not reinterpret or silently rewrite their historical meaning.

## Phase 3 scope

### In scope after design approval

- bounded incremental Jira Issue changelog acquisition;
- bounded Jira Issue Link acquisition;
- canonical stable-anonymous Work Item, Sprint, Release commitment, Milestone,
  scope-membership, and Dependency concepts;
- append-only normalized observations needed for duration and change facts;
- explicit completeness, freshness, conflict, and Story Point coverage states;
- deterministic Sprint Execution and Release/Milestone facts and signals;
- a separate read-only Delivery Execution review projection;
- high-confidence additional Attention producers;
- automatic deterministic derivation after an already-authorized successful
  source sync, without an extra manager confirmation step;
- additive migration, synthetic legacy upgrade, rollback, concurrency, and
  compatibility tests; and
- generic CLI, Dashboard Tool Transport, and Copilot query projections through
  the shared use-case contract.

### Non-goals

- no seven-dimension Project Health or overall Project RAG;
- no DM health-condition configuration, arbitrary expressions, prompts, SQL,
  Python, or source-field rules;
- no Forecast, predictive completion date, velocity forecast, or black-box ML;
- no automatic project-status, Milestone, action, staffing, or decision write;
- no parsing of Issue titles, Version names, profile prose, or other narrative
  to invent a Milestone, dependency, criticality, commitment, or completion;
- no replacement or semantic rewrite of the current Jira snapshot and legacy
  health paths;
- no activation of `pending_decision_attention`;
- no visual Dashboard Center;
- no real source, credential, operational database, or company record in
  portable implementation or tests; and
- no push, merge, tag, release, deployment, or Phase 4 implementation.

## Canonical concepts and identity

Business capabilities depend on canonical concepts, not Jira field names.
Every canonical ID is a stable anonymous local identifier. Source identifiers
remain private provenance and are represented by synthetic values in portable
artifacts.

| Concept | Required meaning |
| --- | --- |
| `WorkItem` | normalized delivery work with current lifecycle and source identity reference |
| `WorkItemEvent` | immutable normalized field or relationship change observed from source history |
| `Sprint` | bounded execution timebox with observed start/end and explicit commitment-capture state |
| `ReleaseCommitment` | delivery scope container with observed target, baseline authority, actual state, and history |
| `Milestone` | delivery outcome, gate, readiness point, contractual date, or governance commitment |
| `ScopeMembership` | temporal Work Item membership in one Sprint or Release |
| `Dependency` | structured directed relationship between supported canonical subjects |
| `SourceCoverage` | run-level completeness, cursor, pages, requested fields, and publication state |

Canonical identity must not use a display name. A local source-identity mapping
may associate a canonical ID with a source system, source type, and private
source reference. Changing labels or names does not change canonical identity.

## Release and Milestone date semantics

Dates must remain separate:

| Date | Meaning |
| --- | --- |
| `planned_date` | approved commitment date with explicit source authority |
| `source_target_date` | latest target observed from the source system |
| `forecast_date` | explicit source-provided forecast, never model-invented |
| `actual_date` | supported achievement/completion date |
| `first_observed_target_date` | earliest locally observed target, usable for change comparison but not silently promoted to an approved plan |

A Jira Version `releaseDate` initially supplies `source_target_date`. Its
earliest observation may support a `target_date_changed` fact, but does not by
itself claim contractual approval. A Jira `released` flag supports a Release
completion observation; it does not prove that every linked Milestone was
achieved.

Release Version and Milestone remain many-to-many. A Version must not be parsed
by name to invent Milestone type, criticality, or commitment authority.

## Milestone input boundary

Phase 3 accepts Milestones only from structured, schema-validated observations:

1. approved connector adapters that expose explicit structured Milestone
   fields; or
2. an explicit local structured import using stable anonymous Project IDs and
   propose/preview/confirm/persist.

The existing `project_profiles.milestones` and project-snapshot JSON remain
legacy context. They may be projected as `legacy_unverified` evidence but
cannot activate a Milestone signal or critical guard. Any later promotion of a
legacy entry requires an explicit structured preview; there is no silent
backfill.

Required Milestone fields are:

- stable anonymous `milestone_id` and existing `project_id`;
- bounded `milestone_type`;
- bounded `criticality`, including explicit `unknown`;
- planned, source-target, forecast, and actual dates kept distinct;
- observed lifecycle state;
- optional Release and Dependency references;
- authority, completeness, evidence, freshness, and rule/schema version; and
- source-observation time and append-only observation history.

Observed lifecycle and derived adherence are distinct:

```text
observed lifecycle:
planned | in_progress | achieved | cancelled | unknown

derived adherence:
on_track | due_soon | overdue | target_slipped |
achieved_on_time | achieved_late | unknown |
unavailable | stale | conflicting
```

`at_risk` and `missed` must not blur source assertion with deterministic
calculation. A source-provided at-risk label may be retained as evidence; the
runtime derives adherence from approved dates and lifecycle facts.

## Incremental acquisition and publication

### Cursor and overlap

- Cursor granularity is source plus board/stream plus dataset.
- Bootstrap horizon and Jira field mappings are bounded connector-local
  configuration. The Phase 3 path must not embed a fixed calendar year or
  assume one universal Story Point custom-field ID.
- Issue history uses a compound high-water mark such as source update time plus
  stable source reference, not timestamp alone.
- Every incremental query uses a bounded overlap window so equal timestamps,
  late-arriving events, and pagination retries are replay-safe.
- Source events are idempotent by stable source event reference when available,
  otherwise by a canonical semantic hash.
- Cursor advance occurs only after the staged run is validated and published.

### Staging and coverage

Each run records:

- requested scope and fields;
- pages expected and received when known;
- source watermark and overlap;
- rows read, accepted, deduplicated, rejected, and published;
- field and relationship coverage;
- status `complete`, `partial`, `failed`, or `unavailable`;
- safe warning codes; and
- the prior and new published run IDs.

Partial or failed acquisition may retain additive observations for audit, but
must not replace the last complete published view or clear an active signal.
HTTP errors, missing pagination tokens, malformed pages, and unavailable
required fields produce partial/failed coverage rather than a successful
truncated snapshot.

### Removal and scope movement

- A Work Item missing from a partial response remains unknown, not removed.
- Membership closes only after a complete authoritative scope manifest proves
  removal or movement.
- Source deletion or loss of access creates a bounded unavailable/tombstone
  observation; historical events are not physically deleted.
- Board registry removal must clean current source caches safely while
  preserving canonical historical evidence required by promoted facts.

## Deterministic fact definitions

Phase 3 calculates facts, not an overall health score.

### Sprint Execution

- `status_age`: elapsed time since the latest complete status transition;
- `blocked_duration`: elapsed time in one continuous structured blocked
  interval;
- `sprint_scope_added` and `sprint_scope_removed`: membership changes after the
  captured commitment boundary;
- `sprint_carry_over`: Work Item remained incomplete at one Sprint end and
  entered a later Sprint;
- `sprint_completion`: completed versus captured committed scope, with
  count-based and Story Point views kept separate;
- `sprint_story_point_coverage`: estimated eligible scope divided by eligible
  scope, including zero-scope and unavailable states; and
- `sprint_dependency_readiness`: supported structured blocking relationships
  affecting committed scope.

If a commitment boundary was not captured, scope-change and carry-over facts
are `unavailable`; the runtime does not reconstruct them from the current
snapshot.

### Release and Milestone

- `release_scope_added` and `release_scope_removed` after the published
  baseline observation;
- `release_scope_readiness` by Issue count and, only when coverage is
  sufficient, by Story Point;
- `release_story_point_coverage`;
- `release_target_date_change` from append-only target observations;
- `milestone_adherence` from authoritative planned/actual dates and lifecycle;
- `milestone_target_or_forecast_slip`, keeping target and forecast sources
  explicit;
- `dependency_readiness` from structured canonical links; and
- `evidence_completeness` and `freshness` for every evaluated scope.

Story Point absence produces `unavailable`; it never produces 0%, 50%, 70%, or
green. Count-based scope readiness remains a separate known fact when complete.

### Value and freshness states

Every fact exposes:

```text
value_state:
known | unknown | unavailable | conflicting

freshness_state:
fresh | stale | partial | failed | never_observed
```

No clear or green interpretation is allowed from missing, partial, stale,
failed, unavailable, or conflicting mandatory evidence.

## Signal boundary

Phase 3 may emit versioned individual signals such as:

- aging blocker;
- Sprint scope change;
- Sprint carry-over;
- Release scope change;
- Release target-date change;
- Milestone overdue or achieved late; and
- structured dependency not ready.

These are observations about execution or commitments, not Sprint Health,
Release Health, or overall Project Health grades. Phase 4 owns configurable
condition bands, critical guards, dimension aggregation, and RAG.

Initial Phase 3 severity must be conservative:

- exact overdue/blocked/changed facts may activate a signal;
- critical severity requires structured criticality evidence;
- missing criticality cannot be inferred from names, priority prose, or the
  model;
- blocker age and scope-growth thresholds remain facts until a fixed
  implementation threshold is separately approved or Phase 4 supplies an
  approved configurable condition;
- configurable threshold bands are not exposed to the DM in Phase 3; and
- facts that need a later configurable threshold remain facts or informational
  signals rather than premature red/amber judgments.

## Read-only use-case contract

Register one `delivery-execution-review` use case after implementation-level
approval. It uses unchanged `UseCaseResult 1.0` and supports bounded filters:

- existing stable anonymous `project_id`;
- layer `sprint`, `release_milestone`, or `all`;
- optional canonical Sprint, Release, or Milestone subject;
- bounded observation window; and
- bounded item limit.

The result separates:

- `data.sprint_execution`;
- `data.release_milestone`;
- `facts[]`;
- `signals[]`;
- evidence and freshness;
- source coverage and limitations; and
- safe assumptions and warnings.

The descriptor advertises facts and signals. Recommendations remain disabled
in the first slice unless a separately reviewed advisory mapping is added.
Generic Tool Transport, CLI, and Dashboard projections remain renderer-neutral;
no dedicated visual Dashboard is included.

Copilot may explain and compare returned facts, but must not:

- combine the two layers into an overall RAG;
- invent a missing commitment, Milestone, criticality, dependency, or date;
- treat an observed target as an approved baseline;
- convert Story Point absence into neutral progress;
- infer a forecast; or
- create or update a business object.

Canonical and derived projections exclude Issue summaries, assignee display
names, raw changelog bodies, and raw connector payloads unless a later
use-case-specific evidence contract proves they are required. Phase 3 facts
reference stable anonymous subjects and minimal normalized evidence.

## Attention integration and manager effort

Recommended design:

1. Connector network access and source-sync mutation retain the existing
   explicit preview/confirm authorization.
2. After an authorized sync publishes a complete or partial source run,
   canonicalization and deterministic Phase 3 fact calculation run
   automatically as system-owned derived processing.
3. High-confidence Phase 3 Attention producers reconcile automatically from
   that published result. No second manager confirmation is required.
4. The existing manual Phase 2 reconciliation interface remains available for
   scoped retry, recovery, and audit compatibility.
5. Partial or failed evidence cannot clear the last complete active item.
6. Complete clear evidence resolves automatically with `rule_clear`; there is
   no manager resolve task.
7. No Attention result automatically creates or changes a Project, Milestone,
   Action, Staffing assignment, or Decision.

This keeps the product auxiliary: the manager authorizes source access and
reviews useful results, but does not maintain the derived system state.
Automatic canonical, fact, signal, and Attention persistence is system-owned
derived state, not a business-object write. It does not weaken the required
propose/preview/confirm/persist boundary for source access, structured
Milestone import, or any future business mutation.

`pending_decision_attention` remains registered and disabled.

## Logical additive storage

Exact SQL and names are frozen only in an approved implementation pack. The
logical storage families are:

| Family | Purpose and required constraints |
| --- | --- |
| source cursor/coverage | one published cursor per source/stream/dataset; append-only run coverage |
| Jira Issue history cache | immutable deduplicated source events with observed time and safe normalized changed fields |
| Jira Issue Link cache | current and historical directed link observations with explicit source semantics |
| canonical Work Items | stable anonymous current projection and private source identity reference |
| canonical scope memberships | many-to-many temporal Sprint/Release membership with valid-from/to and evidence |
| Release commitments and observations | current canonical row plus append-only target/scope/lifecycle history |
| Milestones and observations | current canonical row plus append-only authoritative date/lifecycle history |
| Milestone/Release links | explicit many-to-many references; no inferred name matching |
| canonical Dependencies | directed subjects, bounded dependency type/state, evidence, freshness |
| execution derivation runs | version, input published-run IDs, completeness, fact/signal counts, safe warnings |

Indexes must support source-event deduplication, cursor replay, current scope,
subject history, date windows, dependency traversal, and as-of reconstruction.
Filtering and state transitions must not depend on arbitrary JSON text.

## Compatibility and strangler rules

- Preserve `UseCaseResult 1.0`.
- Preserve the exact `management-attention` and `project-health-review`
  compatibility contracts.
- Preserve the promoted Phase 2 Center, lifecycle, history, and interface
  contracts.
- Keep `project_health_attention` consuming the legacy Jira grade and
  Confluence RAG until Phase 4 explicitly replaces it through a strangler
  comparison.
- Keep current Jira tables readable and current sync commands functioning.
- Do not reinterpret historic legacy scores as Sprint, Release, Milestone, or
  Project Health.
- Do not silently migrate legacy profile milestone prose into canonical facts.
- Keep `pending_decision_attention` disabled.

## Migration and rollback

- All Phase 3 tables are additive.
- Existing Jira, Project Health, Attention, use-case, Dashboard, and Staffing
  tables are not rebuilt merely to add Phase 3.
- Initial canonical history starts from the first complete Phase 3 observation.
  Current snapshot rows may seed a current `legacy_observed` projection but
  cannot invent prior transitions, commitment boundaries, target history, or
  Milestone achievement.
- Bootstrap and migration are idempotent with foreign keys enabled.
- Synthetic legacy upgrade preserves all existing counts, views, indexes, and
  compatibility queries.
- A prior runtime can roll back safely by ignoring the additive tables.
  Automatic downgrade deletion is forbidden.
- Installed-package rehearsal must include clean bootstrap, populated legacy
  upgrade, partial staged run, successful publication, and rollback.

## Required synthetic scenarios

1. Initial complete sync creates canonical current facts but no invented prior
   Issue or commitment history.
2. Replayed overlap pages and duplicate changelog events create no duplicate
   canonical event.
3. Equal update timestamps paginate without skipping or duplicating events.
4. Partial pagination does not advance the published cursor, close scope
   membership, or clear an active signal.
5. A Work Item moves between Releases and Sprints; temporal memberships retain
   the prior relationship.
6. One Work Item belongs to multiple Fix Versions without data loss.
7. A Sprint has no Story Points: count-based scope remains visible, Story Point
   facts are unavailable, and no neutral score is fabricated.
8. A Release Version exists without Story Points; a structured critical
   Milestone can still be overdue or achieved from complete date evidence.
9. Jira target date changes twice; every observation remains traceable and the
   approved plan is not silently overwritten.
10. An observed target exists without approved baseline authority; target
    change is known while commitment adherence is unknown.
11. A critical Milestone is overdue with fresh complete evidence; a
    high-confidence Attention item appears automatically after the authorized
    sync and clears automatically only on complete clear evidence.
12. Missing, stale, partial, failed, and conflicting evidence never clears the
    last complete active signal.
13. A structured dependency blocks a committed Work Item; direction, evidence,
    and affected scope are explainable.
14. An unknown Jira link type remains unsupported evidence and does not become
    a dependency.
15. Legacy `project-health-review`, Management Attention, `UseCaseResult 1.0`,
    Attention Center, CLI, Dashboard Tool Transport, and Copilot contracts
    remain unchanged.
16. Registry removal preserves required canonical history while safely
    removing the obsolete current source cache.
17. Synthetic upgrade and rollback preserve foreign keys, dependent views,
    legacy aggregate counts, and installed-package behavior.
18. Portable artifacts contain only synthetic records and stable anonymous
    identifiers.

## Proposed implementation batches

### Batch B1 — Incremental source evidence core

- additive cursor, coverage, Issue history, and Issue Link storage;
- staged publish, overlap replay, idempotency, partial-state, and tombstone
  behavior;
- connector adapter changes limited to required read-only Jira acquisition;
- no canonical Milestone write interface or use-case projection; and
- focused source, migration, pagination, concurrency, and rollback tests.

### Batch B2 — Canonical execution and commitment core

- canonical Work Item, temporal scope, Release commitment, Milestone, and
  Dependency storage/adapters;
- structured Milestone import preview/confirm;
- deterministic fact calculations and derivation-run audit;
- explicit Story Point coverage and unavailable/conflict behavior; and
- focused calculation, authority, history, and migration tests.

### Batch C1 — Read-only execution review

- register `delivery-execution-review`;
- exact facts, signals, evidence, freshness, coverage, warning, and context
  projections;
- generic CLI, Dashboard Tool Transport, and Copilot compatibility;
- no dedicated visual Dashboard and no recommendation write; and
- focused synthetic and `UseCaseResult 1.0` compatibility tests.

### Batch C2 — Automatic derived Attention integration

- approved high-confidence Phase 3 Attention producers;
- automatic post-sync derivation/reconciliation with manual retry retained;
- partial/failed retention and complete-clear automatic resolution;
- no business-object write and no pending-decision activation; and
- focused idempotency, recovery, lifecycle, Center, Management Attention, and
  interface compatibility tests.

### Batch D — Regression and promotion decision

- combined focused Phase 3 regression;
- `make validate`;
- `make rehearse-release`;
- schema, migration, rollback, portable-scope, and package review;
- implementation report and continuity update; and
- explicit owner decision to promote, revise, or stop.

Each implementation batch requires its own review before the next batch.

## Approved decisions and exact next action

The owner approved these four decisions on 2026-07-29:

1. Jira Version `releaseDate` is an observed source target, not automatically
   an approved plan or forecast; dates and authority remain separate.
2. Canonical Milestones come only from explicit structured adapters or a
   preview/confirmed local structured import; legacy narrative milestone JSON
   is not silently promoted.
3. Phase 3 exposes separate execution and commitment facts/signals, not Sprint,
   Release, or overall Project RAG; configurable health conditions remain
   Phase 4.
4. After an already-authorized source sync, derived canonicalization,
   calculation, and high-confidence Attention reconciliation are automatic,
   with manual reconciliation retained only for retry/recovery.

The approved design is registered as
`implementation-packs/IP-029_PHASE_3_EXECUTION_AND_MILESTONE_FOUNDATION.md` on
dedicated branch `codex/phase-3-execution-signals`, whose history contains the
exact promoted Phase 2 baseline
`2185334c890e79480a39514cf1d1e45f74e062f1`.

IP-029 B1/B2/C1 and the approved C2 automatic Attention slice are implemented,
locally validated, and independently reviewed. The exact next decision is
whether to authorize bounded Batch D regression and the Phase 3 promotion
decision, or require a C2 revision. D, live connector use, real-data access,
Phase 4, push, merge, tag, release, and deployment remain unauthorized.
