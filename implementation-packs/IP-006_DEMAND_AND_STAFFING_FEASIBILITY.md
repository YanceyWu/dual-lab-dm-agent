# IP-006 — Demand and Staffing Feasibility Rules

## Goal

Determine deterministically whether a demand can be met in its requested period,
and explain accepted, rejected, and unknown candidates.

## Implemented scope

- Evaluates required skills, active status, monthly capacity, contractor coverage,
  allocation minimum, maximum people, splitability, and total effort.
- Produces deterministic selections ordered by available allocation then stable
  member ID.
- Returns candidate reasons such as `missing_required_skills`,
  `insufficient_capacity`, and `contract_not_covered`.

## Constraints and non-goals

- This is a read-only feasibility calculation, not a recommendation from a
  language model.
- It does not infer future plans, performance, or unrecorded workload.
- Rule versioning and a broader golden-scenario catalogue remain required before
  a G3 promotion.

## Rollback

Remove the feasibility module; no schema or operational data is changed.
