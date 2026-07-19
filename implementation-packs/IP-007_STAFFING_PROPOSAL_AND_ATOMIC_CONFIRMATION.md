# IP-007 — Staffing Proposal and Atomic Confirmation

## Goal

Turn a feasible staffing result into an immutable, expiring proposal that is
previewed and explicitly confirmed before any staffing-domain write occurs.

## Implemented scope

- A feasible demand creates a proposal with an opaque confirmation token,
  evidence snapshot, selected allocations, and expiry.
- Preview returns the intended period/member allocation changes without writing
  assignments.
- Confirmation re-runs feasibility, rejects changed decision-critical facts,
  verifies the token and expiry, then atomically writes planned assignments,
  monthly allocations, decision log, and proposal status.
- Repeated confirmation returns the original decision result without duplicate
  assignments or decisions.

## Constraints and non-goals

- Proposals are available through the local application service; a new Copilot
  write-capable transport is deliberately out of scope.
- The current scope uses planned assignments and month-level allocation rows.
- Broader concurrency, cancellation, retention, and 20+ golden scenarios remain
  required before G3 promotion.

## Rollback

The `staffing_proposals` table is isolated from existing business tables. Remove
unconfirmed proposals and the adapter only after preserving any confirmed
decision records; no confirmed assignment should be deleted automatically.
