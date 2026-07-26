# IP-020 Implementation Report

Status: `OWNER APPROVED — COMMITTED LOCALLY`
Date: 2026-07-26

## Delivered

- Staffing assessments now distinguish mathematical feasibility from decision
  readiness and expose structured safety blockers and decision conditions.
- Recorded role remains reference-only context; it does not exclude or rank
  cross-functional candidates.
- Resource, skill, and HIREF source freshness block proposals by default. A
  Delivery Manager can explicitly allow non-fresh evidence only with an audited
  reason.
- Current and next/extend HIREF records are evaluated together for continuous
  target-project charge-code coverage. Missing, mismatched, or partial HIREF
  does not disqualify a person; covered options rank first, and a selected gap
  requires an audited DM action note.
- The owner confirmed that an existing HIREF number represents a usable charge
  code for its recorded project and date range. The implementation therefore
  does not invent a separate pending/approved state.
- Invalid, archived, or missing plan versions and unknown target projects remain
  non-overridable write blockers.
- Proposal confirmation recomputes a SHA-256 fingerprint over demand, project,
  plan, candidates, allocations, HIREF context, freshness run identity, selected
  options, and rule version.
- Confirmed decision records retain the fingerprint, source state, role policy,
  freshness exception, and HIREF action acknowledgement.

## Compatibility and safety

- No schema migration was introduced.
- Existing proposals created before the IP-020 fingerprint must be recreated
  before confirmation.
- Staffing writes remain planned assignments and monthly allocations; an HIREF
  action acknowledgement does not claim that a charge code already exists.
- Copilot receives explainable context but does not gain proposal or confirmation
  authority.

## Validation

- Focused staffing suite: `34 passed`.
- Full runtime suite: `93 passed`.
- Repository tools: `18 passed, 19 subtests passed`.
- Touched-file Ruff, static compilation, portable-only source audit,
  repository-boundary check, synthetic-sample check, and diff check passed.

## Owner decision

The owner approved these semantics for commit:

1. role is reference-only;
2. valid target-project HIREF coverage is preferred but not an eligibility gate;
3. selected HIREF gaps require an explicit DM action note;
4. non-fresh source facts require an explicit DM exception reason;
5. invalid plan/write targets cannot be overridden;
6. an existing HIREF number is valid coverage only for its recorded project and
   date interval.
