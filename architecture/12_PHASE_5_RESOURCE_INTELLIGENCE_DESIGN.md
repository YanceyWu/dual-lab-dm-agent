# Phase 5 — Resource Intelligence Design

Status: `DESIGN REVIEW REQUIRED`
Date: 2026-07-30
Baseline: Phase 4 promoted local development baseline

## Decision supported

Give a Delivery Manager an explainable, period-aware answer to: what usable
capacity exists, where overload or skill dependency is material, and whether a
Staffing proposal remains feasible. This is decision support, not automated
assignment or personnel evaluation.

## Verified baseline

- `employees`, `monthly_allocations`, plan versions, assignments, placeholders,
  skills, HIREF, and controlled Staffing preview/confirm already exist.
- Staffing revalidates allocation and HIREF constraints transactionally, but it
  has no versioned effective-capacity input.
- Existing capacity/workload views read planned allocation only. They have no
  canonical leave, BAU, or other non-project commitment model, no heatmap, and
  no Resource Intelligence signals.
- Project Health Resource remains `not_available` until an approved structured
  capacity fact exists. Phase 5 must not fabricate that fact from narratives.

## Boundary and ownership

Phase 5 owns canonical, structured capacity availability and deterministic
resource-risk calculation. It may depend on employee, allocation, plan-version,
skills, placeholder, HIREF, and Project Health read contracts; it must not read
connector payloads or Project Health storage internals. Staffing consumes the
same published effective-capacity facts rather than recalculating capacity.

No live HR connector, real HR record, performance score, automatic staffing
assignment, change of confirmation authority, or Phase 4 Attention/legacy
change is in scope.

## Canonical capacity contract

For a stable anonymous member/placeholder and month, deterministic code derives:

```text
planned_project_allocation
  + approved_bau_commitment
  + approved_non_project_commitment
  + approved_leave_fraction
  = committed_fraction

effective_capacity = max(0, base_capacity - leave_fraction - bau_fraction
                         - non_project_fraction)
available_capacity = max(0, effective_capacity - planned_project_allocation)
```

All inputs are explicit structured records with source, observation month,
completeness, freshness, and rule version. Missing or partial input produces
`unknown`/`not_available`; it never becomes zero capacity or a green heatmap.
The initial base capacity is `1.0` only where the existing active worker record
is complete; placeholders remain demand context, not human capacity.

## Fixed signals and outputs

- `resource_capacity_coverage`: known only with complete/fresh effective-capacity
  facts; otherwise `not_available` or `unknown`.
- `resource_overload`: active when committed allocation exceeds effective
  capacity; severity derives from bounded overload bands fixed by code.
- `resource_skill_dependency`: active only when a structured demand has no
  eligible fresh skill coverage; missing skill evidence is `unknown`, not a
  failure claim.
- Read-only heatmap returns member/month state, capacity components, evidence,
  freshness, warnings, and no recommendation that writes staffing.

Phase 5 may publish a structured `capacity_coverage` fact for Phase 4 only
after its completeness/freshness contract is proven. It does not create an
Attention producer.

## Clean re-import and write boundary

Production starts from empty bootstrap plus a versioned, structured synthetic
capacity package. The package contains only stable anonymous IDs and bounded
monthly commitment records; it has preview/validation, idempotent replay,
session/run audit, derivation, coverage/integrity report, and rollback proof.

Capacity commitment writes use propose/preview/confirm/persist. Batch B must
not expose a public write interface; future public writes require a separate
Batch C gate. Existing Staffing confirmation remains its own controlled write.

## Batch plan

### A — Design and boundary review

Verify current capacity/Staffing paths, freeze the formula, contracts,
freshness, empty-bootstrap/re-import path, synthetic scenarios, and non-goals.
No runtime or schema change.

### B — Canonical effective-capacity core

Add additive structured commitment/import/audit storage, deterministic capacity
derivation, coverage states, and synthetic bootstrap/replay/integrity tests.
No public heatmap or Staffing behavior change.

### C — Read-only heatmap and Staffing consumption

Expose the heatmap through generic transport and switch Staffing assessment to
the published capacity fact only after compatibility tests prove the shared
formula. No automatic assignment or Attention producer.

### D — Regression and promotion decision

Run combined capacity/Staffing/Project Health regression, `make validate`,
`make rehearse-release`, portable review, implementation report, independent
review, and explicit promotion decision.

## Required synthetic scenarios

- Complete fresh leave/BAU/non-project commitments reduce capacity exactly once.
- Missing leave or commitment evidence yields `unknown`, never available or
  green.
- A proposal that was feasible becomes infeasible when published effective
  capacity changes; confirmation makes no partial domain write.
- Placeholder demand is visible but does not create human capacity.
- Re-import replay creates no duplicate observation or derivation; partial
  package failure leaves no partial current capacity view.
- Heatmap and Staffing return the same capacity formula and evidence.

## Exact next action

Owner review and approval of this Phase 5 design, then a separate authorization
for Batch B only. No implementation, connector, real data, push, merge, tag,
release, or deployment is authorized by this design.
