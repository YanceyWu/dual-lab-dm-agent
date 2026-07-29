# IP-028 — Phase 2 Delivery Attention Center

Status: `BATCH D REVIEW ACCEPTED — PHASE 2 PROMOTION DECISION REQUIRED`
Approved: 2026-07-28
Implementation branch: `codex/phase-2-attention-center`
Design: `architecture/07_PHASE_2_DELIVERY_ATTENTION_CENTER_DESIGN.md`
Revision design:
`architecture/08_LAYERED_PROJECT_HEALTH_AND_MILESTONE_EVOLUTION.md`

## Goal

Implement the approved deterministic foundation for a local Delivery Attention
Center: durable current Attention items, safe reconciliation and lifecycle
operations, deduplicated history, and evidence-backed rule evaluation.

## Batch B scope

- Add only the approved additive Attention storage: rule catalog, one-time
  Attention operations, reconciliations, current signals, and append-only
  history.
- Implement deterministic candidate evaluation for project health, overdue
  action, source freshness, and active-assignment resource overload strictly
  above 100% load.
- Store project-health RAG label mappings, source precedence, and state
  precedence as versioned rule parameters with a local DM default and optional
  stable-anonymous-project overrides; do not hard-code project-specific RAG
  semantics into evaluation.
- Register `pending_decision_attention` as disabled; it must emit no active
  signal, recommendation, or lifecycle record.
- Implement canonical identity, semantic observation hashing, deduplication,
  safe clear/partial/failed behavior, and lifecycle transition validation.
- Implement hashed one-time preview/confirm operations for reconciliation,
  acknowledgement, snooze, and resolve; keep query paths read-only.
- Add focused synthetic unit, repository, migration, integrity, rollback, and
  concurrency tests.

## Batch B non-goals

- No Center CLI, Dashboard, Copilot, or ToolTransport interface work.
- No modification of existing `management-attention` behavior or its Phase 1
  compatibility contract.
- No connector calls, source sync, real data, automatic action creation,
  project-status write, staffing change, or decision-log interpretation.
- No activation of pending-decision detection.
- No Phase 2 promotion, release, tag, merge, or push.

## Batch B acceptance criteria

1. Approved Attention tables and indexes are additive, migration-safe, and
   synthetic upgrade/rollback tests preserve existing tables, views, and data.
2. The four active rules create stable canonical identities and valid normalized
   evidence/freshness references; repeated unchanged reconciliation creates no
   duplicate current row or history event.
   Project-health RAG mappings and precedence are validated versioned
   configuration, and missing, invalid, or unmapped inputs never clear an
   active item.
3. A disabled pending-decision rule creates no Attention item under any
   synthetic decision-log input.
4. Preview tokens are hashed, expire, can be claimed once only, and stale or
   concurrent confirmation cannot partially mutate Attention state.
5. Successful clear, partial source state, failed evaluation, acknowledgement,
   snooze, and resolve follow the approved lifecycle semantics and are
   append-only auditable.
6. Existing Management Attention, trace payload boundary, repository boundary,
   and synthetic-data checks remain unchanged.
7. Focused tests and `make validate` pass. Run `make rehearse-release` before
   Batch D because Batch B introduces schema and migration behavior.

## Stop gate

After Batch B validation or review corrections, update `PROGRESS.md`, commit
the bounded result, and stop for explicit review. Do not start Batch C
interface integration until that review is approved.

The owner accepted the Batch B result and Batch C design review findings on
2026-07-28. Batch C1 below was the only authorized next implementation and is
now accepted after review of its validated local result on 2026-07-29.

## Batch C1 scope

- Add the separate read-only `delivery-attention-center` query through the
  shared executor and `UseCaseResult 1.0`.
- Return current Attention items, pre-limit zero-filled summary counts,
  explicit reconciliation coverage, validated facts/signals/advisory
  recommendations, evidence/freshness, and optional bounded event metadata.
- Add the exact JSON-only Attention CLI preview/confirm commands and the
  dedicated `POST /api/attention/operations` Dashboard API contract defined by
  the approved design.
- Add Copilot routing that never reconciles implicitly and requires explicit
  user authorization for preview and separate explicit confirmation.
- Reject duplicate acknowledgement, unchanged snooze, and other lifecycle
  no-ops before creating an operation or history event. Complete clear
  reconciliation resolves automatically; no manager resolve operation is
  exposed.
- Preserve `management-attention` business projections and prove that its
  query creates no Attention current/history/operation/reconciliation write.
- Use only synthetic records and stable anonymous IDs.

## Batch C1 non-goals

- No visual Dashboard Center page.
- No RAG configuration mutation interface; Batch C1 may only read the
  currently persisted versioned configuration through rule evaluation.
- No activation of `pending_decision_attention`.
- No connector call, source sync, real record, automatic action/project/
  staffing/decision write, notification, push, or Phase 2 promotion.
- No change to the shared `UseCaseResult 1.0` models or existing
  `management-attention` contract.

## Batch C1 acceptance criteria

1. An empty or filtered Center result states whether a confirmed
   reconciliation covers the complete query scope; uncovered empty results
   never imply healthy or clear.
2. Query parameter member and cross-field validation, deterministic ordering,
   pre-limit summaries, resolved-only-on-request behavior, bounded newest-first
   history metadata, and result-local reference integrity follow the approved
   design exactly.
3. Every returned item has a stable fact, signal, and advisory recommendation.
   Health/action/resource recommendations block on unusable retained evidence;
   source-freshness advice remains available for its normalized limitation;
   clear/resolved recommendations are not applicable.
4. ToolTransport remains query-only. Direct executor, structured CLI, and
   generic Dashboard query serialize the same Center result.
5. Reconcile, acknowledge, and snooze are exposed only through the
   Attention-specific preview/confirm service. Complete clear reconciliation
   resolves automatically. Tokens remain hashed at rest, one-time, expiring,
   and returned only by preview.
6. CLI and Dashboard API preserve stable service failures and reject
   caller-supplied Dashboard actor, unsupported fields/actions, lifecycle
   no-ops, and invalid confirmation without domain mutation.
7. Existing Management Attention and unrelated query/write boundaries retain
   their contracts and create no Attention side effect.
8. Focused synthetic tests and `make validate` pass. Update `PROGRESS.md`,
   create a local commit, and stop for Batch C1 review.

## Batch C2 implemented scope

The owner authorized the following bounded implementation on 2026-07-29. This
section records what commit `71d90d3` technically implemented; review later
determined that it is not an accepted DM-facing product contract:

- add a dedicated audited store for expiring, hashed, one-time configuration
  previews;
- accept only complete default replacement, bounded stable-anonymous-project
  override, or explicit override removal;
- validate the full resulting configuration and reject unsupported fields,
  executable expressions, prompts, direct SQL, display names, malformed IDs,
  no-ops, stale previews, expiry, reuse, and concurrent duplicate confirmation;
- atomically retain the prior rule version and create one new current
  `project_health_attention` version on confirmation;
- require a separately previewed and confirmed reconciliation before the new
  version affects current Attention signals;
- expose exact JSON CLI, Dashboard API, and Copilot preview/confirm behavior;
- preserve `UseCaseResult 1.0`, Management Attention, all unrelated writes,
  and disabled `pending_decision_attention`.

## Batch C2 technical acceptance criteria

1. Preview persists no rule/configuration change and returns only an expiring
   token plus exact target, bounded change, prior/new versions, and the
   reconciliation-required flag.
2. Confirmation atomically creates one new current rule version, retains the
   prior version, and creates no reconciliation, signal, or history mutation.
3. Invalid, unchanged, stale, expired, reused, concurrent, or failed writes
   cannot produce an unintended rule version or lose the prior current version.
4. CLI, Dashboard API, and direct service preserve the same safe result and
   failure codes; caller-supplied Dashboard actor and unsupported payload
   fields are rejected.
5. Management Attention, `UseCaseResult 1.0`, pending-decision disabled state,
   connector/real-data boundaries, and unrelated write contracts remain
   unchanged.
6. Focused synthetic and compatibility tests plus `make validate` pass. Update
   `PROGRESS.md`, create a local commit, and stop for Batch C2 review.

## Batch C1 result

Batch C1 and its bounded review corrections are implemented and locally
validated. Focused combined coverage passed 71 tests, and `make validate`
passed 176 runtime tests, 21
repository-tool tests with 19 subtests, Ruff, compilation, boundary/synthetic
checks, package build/inspection, and eight release validation checks.
`pending_decision_attention` remains disabled. The result is stopped for
separate Batch C2 authorization. The owner subsequently supplied that bounded
authorization; Phase 2 promotion remains unauthorized.

## Batch C2 result and review disposition

Batch C2 is implemented and locally technically validated. It adds only the dedicated
configuration operation store, strict versioned default/project-override
preview/confirm service, exact JSON CLI/Dashboard/Copilot projections, and
focused synthetic/compatibility coverage. Focused combined coverage passed
82 tests, and `make validate` passed 187 runtime tests, 21 repository-tool
tests with 19 subtests, Ruff, compilation, boundary/synthetic checks, package
build/inspection, and eight release validation checks.

Configuration confirmation creates a new current rule version but no
reconciliation, signal, or history mutation. `pending_decision_attention`
remains disabled.

Product review did not accept this mapping-oriented configuration surface.
The required DM-facing model keeps a fixed factor catalog but makes bounded
conditions configurable, separates Sprint Execution, Release/Milestone, and
seven-dimension Project Health, treats unavailable Story Point evidence
explicitly, and makes milestone commitments first-class inputs. The accepted
C1 behavior and compatibility contracts remain unchanged.

The replacement architecture in
`architecture/08_LAYERED_PROJECT_HEALTH_AND_MILESTONE_EVOLUTION.md` was
approved on 2026-07-29. The bounded C2 correction is implemented: the
unaccepted configuration CLI, Dashboard, and Copilot preview paths are
removed; direct preview and legacy-token confirmation fail safely; additive
storage is retained unchanged. It adds no Phase 3 milestone runtime or Phase 4
health engine.

The first correction review found that dormant internal configuration
confirmation and repository mutation helpers remained executable. The review
fix removes those helpers while retaining the table, existing records, and
read-only legacy-operation detection.

Focused synthetic and compatibility coverage passed 93 tests. `make validate`
passed 183 runtime tests, 21 repository-tool tests with 19 subtests, Ruff,
compilation, boundary/synthetic checks, package build/inspection, and eight
release validation checks. Technical re-review found no remaining P0-P2 issue.
The result is stopped for owner acceptance; Batch D and Phase 2 promotion
remain unauthorized.

## Batch D result

The owner accepted the corrected C2 result and authorized the next Batch D
validation step on 2026-07-29.

Combined focused regression passed 109 tests across Attention rules, storage,
reconciliation, lifecycle, Center projections, retained configuration
storage, interface rejection, migration, concurrency, Management Attention,
`UseCaseResult 1.0`, discovery, CLI build, and Copilot.

`make validate` passed 183 runtime tests, 21 repository-tool tests with
19 subtests, Ruff, compilation, repository-boundary and synthetic-sample
checks, diff hygiene, package build/inspection, and eight release validation
checks. `make rehearse-release` passed temporary wheel installation, isolated
synthetic database upgrade, integrity checks, installed behavior, and
rollback.

Schema and portable-scope review found no blocking issue. The full result is
recorded in `implementation-reports/IP-028_IMPLEMENTATION_REPORT.md`. Phase 2
Batch D Review was accepted by the owner on 2026-07-29. Phase 2 is not
promoted; the exact next gate is the explicit owner promotion decision.
Phase 3/4, connector, real-data, release, push, merge, and tag work remain
unauthorized.
