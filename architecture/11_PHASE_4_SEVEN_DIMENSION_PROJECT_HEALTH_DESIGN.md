# Phase 4 — Seven-Dimension Project Health Design

Status: `DESIGN PROPOSED — OWNER REVIEW REQUIRED`
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

### A — Contract and read-only catalog foundation

Add additive versioned catalog/configuration/assessment contracts and a
read-only catalog/effective-configuration projection. No condition mutation,
assessment persistence, Attention change, or legacy behavior change.

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
schema/migration/rollback/portable review, implementation report, and an
explicit promotion decision.

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
- Legacy grade and layered assessment are shown together without modifying
  Management Attention, `UseCaseResult 1.0`, or legacy snapshots.
- All records, payloads, and reports use synthetic stable anonymous IDs only.

## Exact next action

Review and approve this design and the implementation-pack batch plan, or
request a revision. Do not begin Phase 4 runtime, schema, connector, real-data,
push, merge, tag, release, or deployment work.
