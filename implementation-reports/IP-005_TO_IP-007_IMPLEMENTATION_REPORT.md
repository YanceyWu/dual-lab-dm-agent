# IP-005 to IP-007 Implementation Report

Status: `CORE IMPLEMENTATION COMPLETE — G3 PROMOTION NOT YET CLAIMED`
Date: 2026-07-19

## Outcome

Implemented the dependency chain for period-aware staffing: canonical read
facts, deterministic feasibility, then proposal/preview/atomic confirmation.
All implementation and tests use synthetic identifiers and temporary databases.

## What is now deterministic

- Monthly capacity is read by requested period and selected plan version.
- Contractor coverage is checked against the whole requested month.
- Required skills, active status, capacity, minimum allocation, splitability,
  maximum people, and total effort are checked before a proposal exists.
- Confirmation revalidates feasibility and writes planned assignments, monthly
  allocations, a decision record, and proposal status in one SQLite transaction.
- A confirmed proposal is idempotent; a changed capacity causes confirmation to
  fail before any domain write.

## Validation

- New staffing pipeline scenarios: `4 passed`.
- Focused allocation/contract regression scenarios: `10 passed`.
- Full runtime suite: `58 passed`.
- Repository tool suite: `18 passed, 19 subtests passed`.
- Static compilation, portable-only audit, repository-boundary check,
  synthetic-sample check, and diff check: passed.

## Deliberate limits before G3

- The new service is not yet exposed through a write-capable Copilot transport.
- Staffing rules do not yet have the required 20+ golden scenarios.
- Proposal cancellation, explicit rejection, configurable expiry, and more
  extensive concurrent-confirmation coverage remain to be added.
- The feasibility rule set is not yet separately versioned/configurable.

## Rollback

The proposal table is additive. The new application modules can be removed
without changing existing workload or legacy allocation behavior. Confirmed
writes remain normal planned assignments/monthly allocations and decision-log
records, and must be handled through a deliberate operational reversal.

## Recommended next action

Do not claim G3 yet. Extend the scenario catalogue and add the approved local
write transport/manager confirmation UX before assessing the next business use
case.
