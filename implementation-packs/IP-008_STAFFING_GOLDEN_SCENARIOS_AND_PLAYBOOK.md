# IP-008 — Staffing Golden Scenarios and Manager Confirmation Playbook

## Goal

Make the staffing workflow safe to promote by proving deterministic behavior
across normal and failure conditions, and by giving a manager an explicit local
confirmation path.

## Implemented scope

- Added 23 synthetic staffing scenarios covering time periods, effort,
  skill match/gaps, contract coverage, capacity boundaries, split and non-split
  demand, maximum people, inactive people, source-state visibility, changed
  capacity, expiry, cancellation, rejection, and idempotent confirmation.
- Added `rule_version` to every staffing demand/feasibility result and proposal
  evidence snapshot.
- Added local JSON-only manager commands:
  `pm staffing assess`, `propose`, `preview`, `confirm`, `cancel`, and `reject`.
- Preserved deterministic code as the sole authority for eligibility,
  allocation, revalidation, and persistence. Copilot may explain a result but
  may not create or confirm staffing writes on its own.

## Acceptance evidence

- A proposal is the only path that can create planned assignments and monthly
  allocation rows.
- Confirmation requires the proposal ID and opaque token, revalidates facts,
  and is idempotent.
- Expired/cancelled/rejected/changed proposals make no staffing-domain write.
- All scenarios are synthetic and use isolated temporary databases.

## Non-goals

- Autonomous Copilot confirmation, remote approval, or direct database access.
- Workforce-performance inference, future data fabrication, and real-data tests.

## Rollback

Remove the manager command group and staffing service only after reviewing any
confirmed decisions. Cancelled/rejected proposals have no domain-side effects;
confirmed planned assignments require an explicit manager reversal.
