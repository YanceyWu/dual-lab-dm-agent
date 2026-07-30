# Phase 4 — Seven-Dimension Project Health Design

Status: `BATCH D REVIEW ACCEPTED — PROMOTION DECISION REQUIRED`
Date: 2026-07-30
Baseline branch: `codex/phase-3-execution-signals`
Baseline commit: `bdfee9c7c764ea5eff353b31e7a1d5873577192b`

## Decision supported

Give a Delivery Manager an explainable, evidence-bounded view of whether a
project needs attention across Schedule, Delivery, Scope, Quality, Resource,
Dependency, and Governance. It must distinguish a limited or unknown state
from healthy, and must never average away a critical missed Milestone.

## Verified baseline and boundary

- The promoted `project-health-review` is a legacy read-only projection of
  latest Jira health snapshots and status-page RAG; it is not the Phase 4
  health engine and remains compatible evidence during strangler comparison.
- Phase 3 supplies canonical execution facts, Milestone adherence, Release
  scope, dependencies, derivation completeness/freshness, and the one approved
  critical-Milestone Attention producer.
- Phase 2 supplies versioned Attention reconciliation, lifecycle, audit, and
  manual scoped retry. `pending_decision_attention` remains disabled.
- No live connector, real data, forecast, source-field configuration, automatic
  business-object write, or Phase 5+ capability is in scope.

## Deployment data policy

Production adoption will use a clean local database followed by a full,
authorized re-import. Phase 4 therefore does not require migration, backfill,
or preservation of current operational records, legacy health snapshots, or
historical configuration data. The legacy projection remains only a development
and strangler-comparison compatibility boundary until the clean deployment.
Schema changes must still bootstrap idempotently, and release rehearsal must
verify clean initialization, full synthetic re-import, integrity, and software
version rollback; it need not prove populated-data upgrade preservation.

## Clean re-import is a product capability

All Phase 4 design and implementation is based on a supported clean re-import
path, not a one-off development procedure. Batch A must define and implement
the deterministic local workflow below before any health assessment is treated
as available:

```text
empty local database
  -> idempotent bootstrap of Phase 3 and Phase 4 tables
  -> validated Phase 3 evidence and structured-Milestone import
  -> validated Phase 4 structured-input import package
  -> canonical derivation and health assessment
  -> integrity, coverage, freshness, and reconciliation report
```

The import package uses only stable anonymous IDs and versioned structured
records. It must have a non-interactive local script/command path, a dry-run
or preview result, deterministic validation errors, an import-run audit, and
an explicit final report. It must be possible to repeat the same package
without duplicating observations or assessments. No live connector is required
or implied by this path.

The required additive table families are:

| Table family | Purpose |
| --- | --- |
| Phase 3 evidence/canonical tables | imported source evidence, Milestones, and the facts Phase 4 consumes |
| health factor catalog and condition versions | fixed catalog plus versioned default condition definitions |
| project override and configuration-operation audit | existing-project scoped preview/confirm changes and replay safety |
| structured health-input observations | validated Quality, Resource, and Governance records when an approved source is available; no narrative blobs |
| assessment run, dimension, and factor results | versioned result, evidence references, freshness, guard outcomes, and legacy comparison |
| re-import session/run records | package identity, ordered step status, counts, warnings, integrity result, and idempotency key |

The first clean package may legitimately omit Quality, Resource, or Governance
records. Their dimensions then report `not_available` with the import coverage
reason. Later approved source adapters extend the package and their structured
observation family; they do not change the re-import contract or fabricate
history.

## Decisions proposed for approval

1. Phase 4 owns a new, versioned Project Health assessment; it does not
   reinterpret, overwrite, or remove legacy Jira snapshots or their Attention
   behavior.
2. Deterministic code owns the fixed factor catalog, source-fact allowlist,
   operators, state semantics, critical guards, aggregation, validation,
   persistence, and evidence. A DM may configure only bounded condition values
   and existing-project overrides through propose/preview/confirm.
3. Factor states are `red`, `amber`, `green`, `unknown`, `stale`, `missing`,
   `conflicting`, `not_available`, or `not_applicable`. Incomplete evidence is
   never converted to green or a neutral numeric score.
4. A fresh, complete critical overdue or missed Milestone is a deterministic
   Schedule guard. It makes Schedule red and prevents an overall green state;
   a red dimension is never averaged away.
5. The first release creates assessments and comparison projections only.
   It creates no new automatic Attention producer and does not replace
   `project_health_attention`; that decision belongs to a later, separate gate.

## Fixed catalog and source boundaries

| Dimension | Initial Phase 4 factors | Allowed evidence | If evidence is insufficient |
| --- | --- | --- | --- |
| Schedule | critical Milestone adherence; target change | canonical Milestone/Release facts | `unknown` or `stale` |
| Delivery | Sprint completion; carry-over | canonical Sprint facts | `not_available` |
| Scope | Release scope change/readiness | canonical scope and Release facts | `unknown` |
| Quality | quality/readiness gate | explicitly structured local gate fact only | `not_available` |
| Resource | capacity coverage | promoted local capacity fact only | `not_available` |
| Dependency | dependency readiness | canonical Dependency facts | `unknown` |
| Governance | decision/readiness gate | explicitly structured local governance fact only | `not_available` |

Phase 4 does not manufacture Quality, Resource, or Governance evidence from
legacy narratives. Until an approved upstream source supplies a permitted
fact, those dimensions report `not_available` and explain that limitation.

## Evaluation and configuration contract

Each factor result contains: factor and catalog version, dimension, state,
severity (if applicable), allowed source facts, evidence references,
completeness, freshness, warnings, and deterministic reason codes. An
assessment contains the seven factor groups, dimension states, guard outcomes,
overall state, comparison to the legacy observation, and no model-generated
facts.

Configuration is structured, bounded data over the fixed catalog. Supported
operators are restricted to `in`, `equals`, numeric comparisons, `days_before`,
and `days_after`. There are no arbitrary expressions, SQL, prompts, field
paths, or cross-factor Boolean logic. A request may target the default or an
existing canonical project only. Preview exposes prior/proposed/effective
configuration and its version; confirmation is one-time, expiring, atomic,
idempotent, and rejects stale/no-op operations. Confirmation changes
configuration only; evaluation is a distinct, auditable operation.

## Aggregation

1. Read only the latest complete/fresh applicable canonical facts for a project.
2. Evaluate factors independently and preserve unavailable/limited states.
3. Apply critical guards before dimension aggregation.
4. A dimension is red if a guard or applicable factor is red; amber is visible
   when no red applies; green requires all mandatory applicable factors to be
   fresh, complete, and green.
5. Overall Project Health is red when any dimension is red, amber when no red
   dimension exists but one is amber, green only when all mandatory dimensions
   are green, and otherwise limited/unknown with reasons.

## Batch plan and gates

### A — Clean re-import contract and catalog foundation

Add additive versioned catalog/configuration/assessment contracts, the clean
re-import session/audit and structured-input boundary, and a read-only
catalog/effective-configuration projection. Prove clean bootstrap followed by
synthetic package import, canonical derivation, coverage reporting, and
idempotent replay. No condition mutation, Attention change, or legacy behavior
change.

### B — Controlled configuration and deterministic assessment

Add bounded default and existing-project override preview/confirm, version and
audit records, deterministic evaluation, assessment persistence, and legacy
comparison. Do not replace the legacy `project-health-review` contract.

### C — Read-only Phase 4 projection and later Attention decision

Expose a separate layered-health review through existing generic transport and
Copilot compatibility. First review its evidence, lifecycle, and reconciliation
implications before any separately approved Attention integration.

### D — Regression and promotion decision

Run combined focused regression, `make validate`, `make rehearse-release`,
clean-bootstrap/full-reimport/integrity/software-rollback/portable review,
implementation report, and an explicit promotion decision.

Every batch requires independent review before the next gate. This design
authorizes no implementation batch.

## Required synthetic scenarios

- Sprint completion green with an overdue critical Milestone: Schedule and
  overall state remain red.
- Missing Story Points do not produce a neutral score or green Delivery state.
- Missing Quality/Resource/Governance fact remains `not_available`.
- Fresh complete noncritical evidence can clear a condition only under its
  bounded configured rule; partial/stale/conflicting evidence cannot imply
  green.
- Default/override preview, stale confirmation, one-time token, no-op,
  nonexistent project, replay, and concurrency behavior are deterministic.
- A clean database can be bootstrapped and loaded through the supported local
  import path; malformed/partial packages fail without a partial current view,
  and replay produces no duplicate canonical observation or assessment.
- Legacy grade and layered assessment are shown together without modifying
  Management Attention, `UseCaseResult 1.0`, or legacy snapshots.
- All records, payloads, and reports use synthetic stable anonymous IDs only.

## Exact next action

The owner accepted Batch B, authorized Batch C, and accepted the Batch D review.
The completed local baseline now requires an explicit promotion decision. Do
not begin Attention integration, connector, real-data, push, merge, tag,
release, or deployment work without separate authorization.
