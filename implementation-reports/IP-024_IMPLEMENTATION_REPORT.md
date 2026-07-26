# IP-024 Implementation Report

Status: `TECHNICALLY VALIDATED LOCALLY — OWNER REVIEW PENDING`
Date: 2026-07-26

- Added database CHECK and uniqueness constraints for assignments, employee
  monthly allocations, and placeholder monthly allocations.
- Added fail-closed legacy validation and table-rebuild migrations.
- Migrated staffing confirmation-token storage from plaintext to SHA-256 hashes.
- Switched critical staffing acknowledgements, expiry, and confirmation times
  to timezone-aware UTC.
- Added an immediate transaction claim and aggregate capacity guard so
  concurrent proposals cannot overallocate a member period or partially commit.
- Validation: 41 focused staffing/integrity/migration tests, touched-file Ruff,
  and diff check passed.

No operational database was migrated. Real-environment upgrade requires a
backup and isolated-copy rehearsal.
