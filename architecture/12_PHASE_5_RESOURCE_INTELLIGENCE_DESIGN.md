# Phase 5 — Resource Intelligence Design

Status: `REVISED DESIGN REVIEW REQUIRED`
Date: 2026-08-01
Baseline branch: `codex/phase-4-project-health-design`
Baseline commit: `c2b51f2f8707eada9a4a774cd158df22740005ba`

## Decision supported

Give a Delivery Manager an explainable, period-aware answer to: what usable
capacity exists, where overload is material, and whether a Staffing proposal
remains feasible. This is decision support, not automated assignment, personnel
evaluation, or evidence-free inference.

## Verified baseline and prerequisite gap

- `employees`, `projects`, `monthly_allocations`, plan versions, assignments,
  placeholders, employee skill JSON, HIREF, and controlled Staffing
  preview/confirm already exist.
- Current Staffing calculates availability as `1.0 - planned allocation`. It
  re-evaluates before confirmation, but its final database-transaction guard
  only rejects planned allocation above `1.0`; it has no versioned
  effective-capacity fact or transactional capacity-version check.
- Existing capacity/workload views read planned allocation only. They have no
  canonical leave, BAU, or other non-project commitment model, no heatmap, and
  no Resource Intelligence signals.
- The current repository has individual synthetic import utilities, but no
  single supported, versioned full-import contract that proves an empty
  database can receive the workforce, project, plan-version, and allocation
  dependencies required by effective-capacity derivation. This is a blocking
  clean-re-import prerequisite, not evidence that absent rows mean zero.
- Project Health Resource remains `not_available` until an approved structured
  capacity fact exists. Phase 5 must not derive it from narratives, legacy
  workload projections, placeholders, or employee skill JSON.

## Capability ownership and dependency direction

Phase 5 owns canonical structured capacity availability and deterministic
resource-overload calculation. It does not own employee identity, project and
plan lifecycle, Staffing writes, Project Health assessment, source acquisition,
or presentation-specific behavior.

| Boundary | Owns | Allowed dependencies | Must not own |
| --- | --- | --- | --- |
| Resource Intelligence repository | capacity observations, authoritative coverage manifests, import audit, published derivations, integrity queries | SQLite platform contract and canonical stable IDs | connector payloads, Staffing operations, Project Health storage |
| Resource Intelligence service | package validation, deterministic freshness/state resolution, derivation, publication, replay safety | repository plus employee, allocation, and plan-version read contracts | schema composition, interface formatting, business writes outside capacity import |
| Effective-capacity reader | immutable member/month result and exact derivation version | published Resource Intelligence facts | source schema or import internals |
| Capacity-coverage reader | aggregate project/month coverage fact for Project Health | effective-capacity reader and allocation read contract | Project Health tables or assessment rules |
| Resource heatmap use case | read-only filtering and `UseCaseResult 1.0` projection | effective-capacity reader | calculations, persistence, connector access |
| Staffing integration | consumes the effective-capacity reader and revalidates it inside confirmation | Staffing-owned proposal/confirm flow | recalculating a second capacity formula or mutating capacity facts |

Dependencies point inward through these readers. Resource Intelligence may read
employee, allocation, plan-version, placeholder, and HIREF contracts. It may
not read connector payloads, Project Health storage internals, or another
capability's private tables. Bootstrap composes a dedicated capability schema;
it does not absorb capacity queries, derivation, or import behavior.

Focused synthetic test entry points are capability-named, not phase- or
batch-named: capacity contract/state tests, capacity import/replay tests,
capacity heatmap contract tests, and capacity/Staffing transaction tests. The
implementation pack must map those entries to discovered repository paths
before runtime editing begins.

## Canonical subject and observation contract

Effective capacity is derived only for a stable anonymous human member and a
calendar month. A placeholder is demand context and may appear in coverage-gap
output, but it never receives base capacity, contributes available capacity, or
offsets overload.

Each capacity package contains:

- package ID, schema version, generated time, source ID, and package
  idempotency key;
- an authoritative member/month coverage manifest;
- one bounded observation for every covered
  `member_id × effective_month × commitment_kind` combination;
- commitment kind `leave`, `bau`, or `non_project`;
- fraction in the closed interval `0.0..1.0`;
- explicit value state, source reference, observed time, rule version, and
  evidence metadata containing no narrative or personal data; and
- a stable logical key of member, effective month, commitment kind, and
  approved authoritative source, plus a monotonic source observation version.

The manifest is authoritative only for the member/months and kinds it names.
Complete coverage requires an observation for every named combination. A
known absence is represented by an explicit known `0.0` observation; a missing
row is never zero. Repeating an identical package or observation is idempotent.
The initial contract permits exactly one approved authoritative source for each
commitment kind under a fixed, versioned source-authority policy. A second
source or two current values for the same logical key are conflicting, not
additive. A higher source observation version supersedes the prior value only
through a complete, atomic publication; the same version with different
content is conflicting and cannot replace the current view.

The initial base-capacity policy is `resource-base-capacity-v1`:

- base capacity is `1.0` only when the member exists, is active for the whole
  effective month according to an explicit effective-dated workforce record,
  is not a placeholder, and the authoritative workforce dependency package
  declares that member/month complete; a current active snapshot without an
  effective interval is insufficient;
- a partial month, inactive state, missing workforce coverage, or conflicting
  employment state is `unknown`; and
- Phase 5 does not infer a fractional base capacity from role, level, narrative,
  contract type, or allocation history. A future fractional-work policy needs a
  separate approved contract.

## Deterministic capacity formula

For a known member/month, retain every raw component and derive exactly once:

```text
non_project_deduction = leave_fraction
                      + bau_fraction
                      + non_project_fraction

effective_capacity_raw = base_capacity - non_project_deduction
effective_capacity = max(0, effective_capacity_raw)

available_capacity_raw = effective_capacity - planned_project_allocation
available_capacity = max(0, available_capacity_raw)

total_commitment = planned_project_allocation + non_project_deduction
overload_amount = max(0, planned_project_allocation - effective_capacity)
```

`planned_project_allocation > effective_capacity` and
`total_commitment > base_capacity` are equivalent overload checks. The first is
the authoritative rule. `total_commitment` is never compared with already
reduced effective capacity, which would double-count leave, BAU, and
non-project commitments. Values above capacity remain visible in raw totals;
clamping is only for the displayable effective and available quantities.

For `resource-overload-v1`, no overload is clear, an overload greater than zero
and at most `0.10` is amber, and an overload greater than `0.10` is red. These
bands are deterministic code constants, not DM-configurable values in Phase 5.

## Completeness, freshness, and state matrix

The first freshness rule is `resource-capacity-freshness-v1`: an observation is
fresh only when its source observation is no more than 720 hours old at the
assessment time. Effective month and observation time are separate fields;
future-month plans still become stale when not refreshed. Assessment time and
the freshness rule version are persisted with every derivation.

State resolution is deterministic. `not_available` applies only when the
approved capability or prerequisite contract does not exist. Once a producer
is expected, precedence is `conflicting`, then `unknown`, then `stale`, then
`known`:

| Condition | Result state |
| --- | --- |
| No approved producer or dependency import contract exists | `not_available` |
| More than one current value exists for the same canonical identity | `conflicting` |
| Expected package/manifest/record is absent or partial | `unknown` |
| Complete values exist but any required value exceeds the freshness window | `stale` |
| Workforce, allocation, and all three commitment kinds are complete, fresh, non-conflicting, and valid | `known` |

Invalid values fail package validation and are not published. `unknown`,
`conflicting`, `stale`, and `not_available` never produce available capacity,
a green cell, a Staffing candidate, or a Project Health green Resource
dimension. No freshness override may convert a missing or conflicting capacity
fact into a decision-ready Staffing input.

## Fixed outputs and deferred skill boundary

- `resource_capacity_coverage` is known only for complete, fresh,
  non-conflicting member/month facts; otherwise it preserves the state matrix.
- `resource_overload` is evaluated only for known capacity. Its evidence names
  the exact component observations, allocation plan version, derivation
  version, assessment time, and reason code.
- The read-only heatmap returns member/month state, raw and bounded components,
  overload state, evidence, freshness, warnings, plan version, and no
  recommendation that writes Staffing.
- Phase 5 may publish a structured `capacity_coverage` fact for Phase 4 only
  after the reader contract and completeness/freshness tests pass. For one
  project/month it is known only when allocation coverage is authoritative and
  every assigned human member has known effective capacity; an authoritative
  empty assignment set is known empty, while an absent allocation row or
  manifest is unknown. It creates no Attention producer.

`resource_skill_dependency` remains registered as `not_available` in the first
Phase 5 slice. Current employee skill JSON and request-local Staffing demand do
not prove versioned demand coverage, per-skill freshness, proficiency, or the
difference between missing evidence and confirmed absence. Activating this
signal requires a separately reviewed structured Demand and Skill Evidence
contract defining identity, proficiency threshold, eligibility, freshness,
coverage, and conflict behavior. It must not be inferred during capacity work.

## Clean bootstrap and full re-import contract

The supported production path is:

```text
empty local database
  -> idempotent schema bootstrap
  -> versioned workforce/project/plan/allocation dependency import
  -> dependency coverage and integrity gate
  -> versioned capacity package preview and deterministic validation
  -> atomic capacity observation publication
  -> deterministic effective-capacity derivation
  -> coverage, freshness, conflict, integrity, and reconciliation report
```

Before the canonical capacity core begins, the existing workforce/planning
capability must either prove this dependency import path or receive a bounded,
independently reviewable remediation slice. Resource Intelligence must not
silently implement another capability's import inside its repository.

Capacity import uses synthetic stable anonymous IDs only. Preview performs all
schema, identity, reference, month, range, manifest-completeness, duplicate,
conflict, timestamp-syntax, and freshness-state calculations without publishing
a current view. A syntactically valid but old observation may publish only as
`stale`; age alone is not a malformed-package error.
Confirmation records a session and ordered run/attempt audit, publishes all
observations and derivations atomically, and emits final counts and reason
codes. Any validation, derivation, integrity, or report failure leaves the
prior complete published view current and records the failed attempt outside
that publication transaction. Replay creates no duplicate observation,
derivation, or current-view row.

Additive schema belongs to a dedicated Resource Intelligence schema module.
For the capacity-core stage, software rollback means the Phase 4 runtime ignores
the additive tables and existing Staffing behavior remains unchanged. Before
Staffing consumption can switch, a separately reviewed compatibility slice
must add a persisted capacity-required policy marker and a fail-closed check
while leaving the marker disabled. The switch enables that marker atomically.
The supported post-switch rollback target is the capacity-core compatibility
build that understands the marker and blocks Staffing confirmation; an older
Phase 4 runtime is not a safe write-capable rollback target. No rollback may
silently resume the legacy `1.0` capacity assumption for writes. Rollback
rehearsal must prove additive-data preservation, read-only compatibility, and
the confirmation write stop.

Capacity-package import confirmation is a controlled ingestion operation, not
a DM commitment editor. Any future public commitment write uses
propose/preview/confirm/persist and requires a separate gate.

## Staffing consumption and atomic confirmation

The heatmap and Staffing assessment consume the same immutable
effective-capacity result; Staffing does not reimplement the formula.
Assessment and proposal evidence include the capacity derivation ID, capacity
rule version, plan version, component observation IDs, state, and decision
fingerprint.

Confirmation must, inside the same `BEGIN IMMEDIATE` transaction that writes
assignments and monthly allocations:

1. reload the selected member/month effective-capacity derivations and planned
   allocation rows;
2. require the same derivation and plan versions used by the proposal;
3. reject missing, stale, conflicting, superseded, or changed facts;
4. prove `existing planned allocation + proposed allocation <= effective capacity`
   for every selected member/month; and
5. write assignment, monthly allocation, and decision audit records only after
   all members and months pass.

Any failure writes no partial domain record and requires a new proposal.
Existing confirmation authority, one-time token, expiry, HIREF checks,
idempotency, and concurrency behavior remain intact.

## Batch plan and named gates

### A — Design and boundary review

Freeze this formula, state matrix, dependency remediation gate, import contract,
public readers, Staffing transaction rule, rollback behavior, synthetic
scenarios, and non-goals. No runtime or schema change.

### B — Canonical effective-capacity core

First prove or separately remediate the workforce/planning clean-import
prerequisite. Then add dedicated additive capacity schema, structured
commitment import/audit, deterministic derivation, immutable readers, coverage
states, and synthetic bootstrap/replay/integrity tests. Do not expose a public
heatmap, change Staffing behavior, publish Project Health capacity facts, or
activate skill dependency.

### C — Read-only heatmap and Staffing consumption

Expose the heatmap through generic transport. In a separately reviewable
Staffing compatibility slice, first install the disabled capacity-required
marker check; then switch assessment and transactional confirmation to the
published effective-capacity reader only after compatibility, concurrency, and
rollback tests pass. Project Health capacity publication is a separate named
slice after its contract tests pass. No automatic assignment, public capacity
editor, skill-dependency activation, or Attention producer.

### D — Regression and promotion decision

Run combined capacity/Staffing/Project Health regression, focused capability
tests, `make validate`, `make rehearse-release`, clean full-import and rollback
rehearsals, portable review, implementation report, independent review, and an
explicit promotion decision.

## Required synthetic scenarios

- Complete fresh leave, BAU, and non-project observations reduce capacity
  exactly once; both overload identities produce the same result.
- Explicit known zero is usable, while an absent commitment observation or
  incomplete manifest yields `unknown`, never available or green.
- Stale, conflicting, malformed, out-of-range, duplicate-identity, and partial
  package cases fail closed with deterministic reason codes.
- An empty database can be bootstrapped and loaded through the dependency and
  capacity packages without using migration/backfill or pre-existing records.
- Identical replay creates no duplicate observation, derivation, or audit
  effect; a conflicting replay cannot replace the current view.
- Package failure after staging or derivation leaves the previous complete
  published capacity view current and records a failed attempt.
- A proposal that was feasible becomes invalid when capacity or plan version
  changes; concurrent confirmation creates no partial domain write.
- Every selected member/month is checked against effective capacity inside the
  confirmation transaction, not only against `1.0`.
- Placeholder demand is visible but never creates human capacity.
- Heatmap, Staffing, and the Project Health capacity projection cite the same
  capacity formula, derivation, plan version, and evidence.
- Missing or unversioned skill evidence leaves skill dependency
  `not_available`; it never creates a negative personnel claim.
- Software rollback preserves additive data and prevents legacy-capacity
  Staffing writes after capacity-aware Staffing has been promoted.

## Non-goals

- no live HR connector, real HR record, operational identifier, or portable HR
  data;
- no automatic assignment, personnel scoring, ranking from missing evidence,
  or change of confirmation authority;
- no DM commitment editor in the canonical-core stage;
- no narrative-derived capacity, leave, demand, or skill fact;
- no skill-dependency activation without its separate structured-input review;
- no Attention producer, Phase 4 legacy replacement, connector, push, merge,
  tag, release, deployment, or active-database operation; and
- no implementation pack or runtime/schema change before owner design
  approval.

## Exact next action

Owner review and approval or revision of this corrected Phase 5 design. After
approval, register a Phase 5 implementation pack that names the discovered
module owners, reader contracts, focused capability tests, dependency-import
remediation disposition, validation evidence, and transitional debt. Runtime
work still requires separate authorization for the canonical
effective-capacity core only.
