# IP-005 — Canonical Staffing Read Model

## Goal

Provide one period-aware, read-only staffing model that combines member skills,
monthly allocations, active plan version, and contractor coverage without
renaming or bulk-migrating existing tables.

## Implemented scope

- `StaffingDemand` defines target project, inclusive period, effort, role,
  skills, allocation constraints, splitability, priority, and plan version.
- `staffing_read_model` reads only the requested months and active members.
- Each member period exposes monthly load, employment status, and contract facts.
- The selected plan version remains explicit; missing period facts remain visible.

## Constraints and non-goals

- No write occurs in this pack.
- Existing tables remain source adapters; no table rename or data migration.
- Capacity is monthly only. Day/week capacity and unrecorded work are `UNKNOWN`.

## Acceptance evidence

Synthetic tests prove period/plan selection and contract facts. Full validation
is recorded in the IP-005 through IP-007 report set.

## Rollback

Remove the read-model module; it owns no schema or business data.
