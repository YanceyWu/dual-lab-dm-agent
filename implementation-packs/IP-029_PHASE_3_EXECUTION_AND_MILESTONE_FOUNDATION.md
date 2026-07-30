# IP-029 — Phase 3 Execution and Milestone Signal Foundation

Status: `BATCH B2 IMPLEMENTED — REVIEW REQUIRED`
Approved design: 2026-07-29
Implementation branch: `codex/phase-3-execution-signals`
Promoted Phase 2 baseline:
`2185334c890e79480a39514cf1d1e45f74e062f1`
Design review commit:
`1447407eb6e071ca00b56d8fb60ebfc71632ea6a`
Design:
`architecture/09_PHASE_3_EXECUTION_AND_MILESTONE_FOUNDATION_DESIGN.md`

## Business goal

Provide trustworthy, source-traceable Sprint Execution and Release/Milestone
facts without treating Story Point coverage, a mutable Jira snapshot, or the
legacy Jira grade as sufficient evidence.

The result must support blocker aging, scope movement, carry-over, Release
target change, Milestone adherence, and structured Dependency observations
while keeping Sprint Execution, Release/Milestone, and seven-dimension Project
Health distinct.

## Approved architecture decisions

The owner approved these decisions on 2026-07-29:

1. Jira Version `releaseDate` is an observed source target, not automatically
   an approved plan or forecast. Planned, source-target, forecast, actual, and
   first-observed target dates remain distinct.
2. Canonical Milestones come only from explicit structured adapters or a
   preview/confirmed local structured import. Legacy narrative Milestone JSON
   is not silently promoted.
3. Phase 3 exposes separate execution and commitment facts/signals, not Sprint,
   Release, or overall Project RAG. DM-configurable health conditions remain
   Phase 4.
4. After an already-authorized source sync, canonicalization, deterministic
   calculation, and high-confidence Attention reconciliation run
   automatically. Manual reconciliation remains for retry/recovery.

Automatic canonical, fact, signal, and Attention persistence is system-owned
derived state. It does not weaken preview/confirm requirements for source
access, structured Milestone import, or business-object writes.

## Verified current problem indicators

- Current Issue, Sprint, and Release Version rows are mutable snapshots.
- There is no Issue changelog, Issue Link, status-transition time, temporal
  scope membership, or as-of reconstruction.
- One current Issue row stores at most one Version reference.
- Partial pagination and true removal do not have a common published-coverage
  contract.
- Current Sprint commitment is reconstructed from current scope rather than
  captured at a commitment boundary.
- Jira Version target-date history and Release scope history are not retained.
- Current Project profile and snapshot Milestone JSON is context, not
  authoritative canonical evidence.
- Missing Story Points receive neutral-looking fallback scores in the legacy
  Jira health path.
- Current Jira acquisition hard-codes a Story Point field and calendar cutoff,
  and canonical/derived storage does not yet minimize all display/assignee/raw
  fields required by the legacy cache.

## Required outcome

IP-029 must add a backward-compatible Phase 3 vertical slice containing:

- bounded incremental source evidence with replay-safe cursor and coverage;
- canonical stable-anonymous Work Item, Sprint, Release commitment, Milestone,
  scope-membership, and Dependency concepts;
- deterministic fact calculations with explicit completeness, freshness,
  conflict, and unavailable states;
- one read-only `delivery-execution-review` contract;
- approved high-confidence automatic Attention integration;
- additive schema and practical rollback; and
- synthetic, compatibility, migration, concurrency, and installed-package
  validation.

## Required contracts

### Identity and evidence

- Canonical IDs are stable anonymous local identifiers and never display
  names.
- Source references remain private provenance. Portable tests and documents
  use synthetic source references only.
- Canonical and derived storage excludes Issue summaries, assignee display
  names, raw changelog bodies, and raw connector payloads unless a separately
  reviewed evidence contract proves they are required.
- Every derived fact references source coverage, evidence, observation time,
  freshness, and calculation/rule version.

### Source publication

- Cursor scope is source plus board/stream plus dataset.
- Incremental history uses a compound high-water mark and bounded replay
  overlap.
- Source events deduplicate by stable event reference or canonical semantic
  hash.
- Pages stage before publication. Cursor advance occurs only after a validated
  publish.
- Missing page tokens, HTTP errors, malformed pages, or unavailable required
  fields produce partial/failed coverage.
- Partial/failed runs cannot replace the last complete published view, close a
  temporal membership, or clear an active signal.
- Removal or scope movement requires a complete authoritative manifest.
- Connector-local field mappings and bootstrap horizon are bounded
  configuration; no fixed calendar year or universal Story Point field is
  embedded in the Phase 3 path.

### Date and authority

- `planned_date`, `source_target_date`, `forecast_date`, `actual_date`, and
  `first_observed_target_date` retain separate meaning.
- Jira `releaseDate` populates only the observed source target unless explicit
  authority establishes another meaning.
- Jira `released` supports a Release completion observation but does not prove
  every linked Milestone achieved.
- A Version name, Issue title, or narrative field cannot create a Milestone,
  criticality, dependency, or commitment.

### Missing and partial evidence

- Fact `value_state` is `known`, `unknown`, `unavailable`, or `conflicting`.
- Freshness is independently `fresh`, `stale`, `partial`, `failed`, or
  `never_observed`.
- Story Point absence never becomes zero, a neutral score, or green.
- Count-based and Story Point-based readiness remain separate.
- Scope churn and carry-over are unavailable when no commitment boundary was
  captured.
- Missing criticality cannot be inferred.

### Compatibility

- Preserve `UseCaseResult 1.0`.
- Preserve `management-attention`, `project-health-review`, and their current
  discovery/interface contracts.
- Preserve the promoted Phase 2 Attention identity, lifecycle, history,
  Center, CLI, Dashboard API, and Copilot behavior.
- Preserve current Jira snapshot tables and legacy sync/read behavior through
  strangler migration.
- Keep `project_health_attention` on its legacy Jira-grade/Confluence evidence
  until Phase 4 explicitly replaces it.
- Keep `pending_decision_attention` registered and disabled.

## Batch B1 — Incremental source evidence core

### Scope

- Add only the approved additive cursor, run-coverage, staged-publication,
  Issue history, and Issue Link storage.
- Implement bounded read-only Jira acquisition adapters for changelog and
  links using connector-local field mapping and bootstrap horizon.
- Implement compound cursor, overlap replay, stable deduplication,
  pagination/error coverage, publication, and tombstone/scope-movement rules.
- Minimize stored fields to those required by approved Phase 3 facts.
- Adapt registry cleanup so obsolete current source caches can be removed
  without deleting canonical history required by a published run.
- Add focused synthetic repository, pagination, idempotency, partial-state,
  concurrency, migration, integrity, and rollback tests.

### Non-goals

- No canonical Milestone import or Release/Milestone calculation.
- No `delivery-execution-review` registration or interface change.
- No Attention producer or automatic reconciliation change.
- No change to the legacy Jira health calculation or Project Health.
- No live connector call, real data, operational configuration, or credential.
- No Phase 4, visual Dashboard, business-object write, push, merge, tag,
  release, or deployment.

### Acceptance criteria

1. Clean bootstrap and synthetic legacy upgrade create only additive storage
   and preserve existing tables, views, foreign keys, indexes, and counts.
2. Duplicate events, replay overlap, equal timestamps, repeated pages, and a
   repeated complete run are idempotent.
3. Cursor advance is atomic with validated publication.
4. Partial/failed pagination cannot publish a truncated scope, close
   membership, create a false deletion, or discard the prior published cursor.
5. Multiple Fix Versions and directed Issue Links are retained without
   flattening or inferred dependency semantics.
6. Unknown link types remain unsupported evidence.
7. Stored portable records contain only synthetic values and stable anonymous
   identifiers.
8. Existing Jira sync, Project Health, Management Attention, Attention Center,
   `UseCaseResult 1.0`, Dashboard sync confirmation, and registry tests remain
   green.
9. Focused tests and `make validate` pass. Because B1 adds schema, migration,
   and installed behavior, `make rehearse-release` also passes before B1
   review.

### Stop gate

After B1 validation, update `PROGRESS.md`, create a bounded local commit, and
stop for explicit B1 Review. Do not begin B2 without owner acceptance and
separate authorization.

## Batch B2 — Canonical execution and commitment core

### Scope

- Add canonical Work Item, temporal Sprint/Release scope membership, Release
  commitment, Milestone, structured Dependency, and append-only observation
  storage.
- Add structured Milestone import preview/confirm with existing-project-only
  validation, hashed expiring one-time tokens, stale/no-op rejection, and no
  narrative migration.
- Calculate approved Sprint and Release/Milestone facts with explicit
  Story Point coverage, authority, completeness, freshness, and conflict.
- Record deterministic derivation runs and input published-run references.

### Implementation-level design handoff

#### Inputs and trigger boundary

- B2 reads only published B1 evidence, existing stable-anonymous Project/Board
  relationships, current legacy Jira Release/Sprint/Issue snapshots, and
  explicitly confirmed structured Milestone imports.
- B1 evidence is authoritative only when its published run explicitly records
  complete coverage and an authoritative manifest. The current incremental Jira
  adapter does not claim that manifest; B2 must therefore return unavailable or
  partial scope facts rather than treating incremental results as full scope.
- Legacy Jira snapshot rows may seed a current `legacy_observed` projection.
  They cannot create prior transitions, commitment boundaries, approved plans,
  historical target changes, or Milestone achievement.
- B2 exposes a deterministic derivation service callable by focused tests and
  future orchestration. It does not wire automatic post-sync execution;
  automatic triggering and Attention reconciliation remain C2.

#### Additive storage contract

B2 adds only these canonical storage families:

1. canonical Work Item current projection plus separate source-identity mapping;
2. canonical Sprint and Release commitment current projections;
3. temporal Sprint/Release scope membership with explicit boundary basis,
   valid-from/to, and open/closed state;
4. current Milestones plus append-only date, lifecycle, authority, and
   completeness observations;
5. explicit many-to-many Milestone/Release links;
6. current structured Dependencies plus append-only relationship observations;
7. deterministic derivation runs, typed input-run references, and versioned
   fact rows; and
8. structured Milestone import operations containing hashed expiring tokens,
   request fingerprints, proposed normalized changes, status, and safe result.

Current projections and append-only observations remain separate. Canonical
identity never uses a display label. JSON may retain bounded audit metadata but
must not own filtering, identity, dates, lifecycle, authority, membership,
dependency direction, value state, freshness, or current-state transitions.
All foreign keys and uniqueness constraints are enforced with additive indexes;
legacy tables are not rebuilt.

#### Canonicalization and fact rules

- A canonical Work Item identity is stable for source, board, and private source
  reference; label changes do not create a new item.
- Mirrored supported Issue Links create one directed Dependency. Unsupported
  link types remain evidence only and never become canonical Dependencies.
- A complete authoritative manifest may close a current scope membership.
  Partial, failed, incremental-only, or stale evidence may add audit context but
  cannot close membership or replace the last complete fact.
- The first complete observation is not silently relabeled as a Sprint or
  Release commitment boundary. Scope-change and carry-over facts remain
  unavailable until a boundary with an explicit basis is captured.
- Count and Story Point completion are separate facts. Missing, incomplete, or
  conflicting Story Point evidence produces `unavailable` or `conflicting`, not
  zero and not an inferred percentage.
- Jira `releaseDate` remains `source_target_date`; `planned_date` requires
  explicit authority. Target history never overwrites an approved baseline.
- Every derivation run records rule/schema version, completeness, safe warnings,
  and the exact published evidence or legacy sync inputs used. Replaying the
  same input set and rule version is idempotent.
- B2 persists facts only. It does not register `delivery-execution-review`,
  expose C1 projections, create Phase 3 Attention, or calculate a Phase 4 RAG.

#### Structured Milestone import contract

- The input is a bounded structured object, not narrative text or legacy
  `project_profiles.milestones`/snapshot JSON.
- Each Milestone references an existing stable-anonymous Project and supplies
  explicit type, criticality, lifecycle, date fields, authority, observation
  time, and schema version. Optional Release and Dependency references must
  resolve to existing or same-operation canonical subjects.
- Preview validates the complete request, canonicalizes ordering and dates,
  computes a decision fingerprint against the relevant current canonical state,
  and returns proposed creates/changes/no-ops without mutating Milestones.
- A no-op preview is rejected without creating a confirmable operation.
  Confirmation requires the operation ID and one-time plaintext token; only its
  hash is stored. Expired, malformed, already-consumed, stale-fingerprint, or
  concurrently claimed operations fail closed.
- Confirmation revalidates Projects, references, fingerprint, and no-op state
  inside one immediate transaction, then persists current rows and append-only
  observations atomically. It never creates or updates a Project, Action,
  Staffing assignment, Decision, or legacy profile/snapshot row.
- B2 provides the service/repository contract and synthetic tests only. No CLI,
  Dashboard, Copilot, connector, or live-data import path is added in B2.

#### B2 implementation order

1. Add idempotent canonical, observation, derivation, fact, and operation
   storage with clean-bootstrap and populated-legacy upgrade tests.
2. Add deterministic canonicalization and fact calculation from synthetic
   published evidence, including unavailable/conflicting paths and replay.
3. Add structured Milestone preview/confirm with stale, no-op, expiry, token,
   rollback, and concurrency coverage.
4. Keep each step independently reviewable with focused validation and a
   bounded local commit. After the complete B2 scope passes compatibility,
   `make validate`, and `make rehearse-release`, update continuity records and
   stop for explicit B2 Review.

### Acceptance criteria

1. Canonical identity is stable and replay-idempotent without using names.
2. Partial or non-authoritative evidence cannot close membership or replace the
   last complete fact.
3. Multiple Fix Versions and directed supported Dependencies remain lossless;
   unsupported types never become Dependencies.
4. Count completion remains available independently when Story Point coverage
   is unavailable; no neutral or zero value is fabricated.
5. Release target, approved plan, forecast, actual, and first-observed target
   dates remain distinct and append-only observations remain traceable.
6. Milestone preview/confirm is schema-validating, hashed-token, expiring,
   stale/no-op rejecting, atomic, one-time, and concurrency-safe.
7. Legacy narrative Milestones are neither promoted nor deleted.
8. Existing Jira, Project Health, Management Attention, Attention Center,
   Staffing, Dashboard, and `UseCaseResult 1.0` behavior remains unchanged.
9. Focused tests, `make validate`, and `make rehearse-release` pass using only
   synthetic data.

### Stop gate

B2 implementation requires explicit authorization after this design review.
After any future B2 validation, stop for explicit B2 Review before C1.

## Batch C1 — Read-only execution review

### Scope

- Register `delivery-execution-review` through the shared executor using
  unchanged `UseCaseResult 1.0`.
- Return separate Sprint Execution and Release/Milestone projections with
  facts, signals, evidence, freshness, source coverage, limitations, and
  bounded context.
- Add generic structured CLI, Dashboard Tool Transport, and Copilot
  compatibility only; no dedicated visual Dashboard.
- Keep recommendations disabled in the first slice unless separately reviewed.

### Stop gate

C1 remains unauthorized. After any future C1 validation, stop for explicit C1
Review before C2.

## Batch C2 — Automatic derived Attention integration

### Scope

- Add only approved high-confidence Phase 3 Attention producers.
- Run canonicalization, fact calculation, and Phase 3 Attention reconciliation
  automatically after an already-authorized published sync.
- Retain manual scoped reconciliation for retry/recovery.
- Retain last complete active state on partial/failed evidence and resolve
  automatically only on complete clear evidence.
- Create no automatic Project, Milestone, Action, Staffing, or Decision write.

### Stop gate

C2 remains unauthorized. After any future C2 validation, stop for explicit C2
Review before Batch D.

## Batch D — Regression and promotion

- Run combined Phase 3 focused regression.
- Run `make validate` and `make rehearse-release`.
- Review schema, migration, rollback, portable scope, package behavior, and
  compatibility.
- Create the IP-029 implementation report and update `PROGRESS.md`.
- Stop for explicit owner Phase 3 promotion, revision, or rejection.

Batch D remains unauthorized.

## Mandatory constraints

- Use synthetic data and stable anonymous identifiers only.
- No company records, identifiers, URLs, names, payloads, credentials, or
  configuration in tracked artifacts or test output.
- Deterministic code owns acquisition validation, normalization, calculation,
  persistence, freshness, and signal state.
- The model owns explanation and uncertainty only.
- No automatic business-object write.
- No Phase 4 health aggregation or configurable condition interface.
- No Forecast or predictive date.
- No `pending_decision_attention` activation.
- No silent migration or deletion of legacy Milestone/profile data.
- Every batch is independently reviewable and reversible.

## Local repository discovery

Before each implementation batch, re-check:

- current Git branch, exact HEAD, and clean worktree;
- `AGENTS.md`, `PROGRESS.md`, the evolution plan, and the approved Phase 3
  design;
- current SQLite bootstrap/migration and repository transaction patterns;
- Jira Release, health, connector, sync-confirmation, and registry-cleanup call
  paths;
- current Project Health and Attention compatibility behavior; and
- focused synthetic tests relevant to that batch.

Use `UNKNOWN` for any company-specific source field, link type, workflow,
Milestone source, or connector behavior not verified in the portable
repository.

## Test and validation requirements

Each batch requires:

- focused synthetic unit and contract tests;
- missing, partial, stale, conflicting, retry, replay, and concurrency cases
  applicable to the batch;
- exact compatibility coverage for preserved public contracts;
- repository-boundary and synthetic-sample checks;
- `make validate`; and
- `make rehearse-release` whenever schema, migration, package, or installed
  behavior changes.

No default test may access the network or the operational database.

## Rollback requirements

- Schema changes are additive.
- A prior runtime ignores Phase 3 tables safely.
- Automatic downgrade deletion is forbidden.
- Failed or partial staged runs do not replace the prior published view.
- Synthetic populated legacy upgrade and installed-package rollback must
  preserve existing foreign keys, views, indexes, and aggregate counts.

## Required final report

The Batch D report must record:

- exact approved design and implementation commits;
- implemented storage, calculations, use-case, and Attention behavior;
- focused and full validation evidence;
- schema, migration, rollback, and portable-scope review;
- compatibility evidence;
- unresolved risks and deferred Phase 4/7 work;
- branch, push, CI, and release state; and
- explicit Phase 3 promotion recommendation.

## Current authorization

The owner accepted corrected Batch B1 on 2026-07-29, entered the B2 design
stage, and subsequently authorized bounded B2 implementation. B2 is complete
and stopped for explicit review under this frozen contract.

The exact next decision is B2 acceptance, required corrections, or rejection.
C1/C2/D, live connector access, real data, Phase 4, push, merge, tag, release,
and deployment remain unauthorized.
