# IP-012 — Contract Continuity Use Case

## Goal

Expose a read-only view of recorded HIREF continuity risks for active STFTE
staff, including missing coverage, expiry, next-contract coverage, and project
alignment.

## Scope and rules

- Adapt existing HIREF/staff review facts for a bounded window of 1–365 days.
- Return only rows requiring action, with the existing deterministic urgency and
  alignment outcomes as evidence.
- Do not create a HIREF, assignment, staffing proposal, or action item.

## Acceptance

Missing current coverage, expiring coverage, and project mismatch are visible;
the tool query remains JSON-only and creates no domain record.
