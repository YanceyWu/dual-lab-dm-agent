# IP-024 Implementation Report

Status: `SYNTHETIC ISOLATED MIGRATION PASSED — REAL UAT PENDING`
Date: 2026-07-26

- Added database CHECK and uniqueness constraints for assignments, employee
  monthly allocations, and placeholder monthly allocations.
- Added fail-closed legacy validation and table-rebuild migrations.
- Migrated staffing confirmation-token storage from plaintext to SHA-256 hashes.
- Switched critical staffing acknowledgements, expiry, and confirmation times
  to timezone-aware UTC.
- Added an immediate transaction claim and aggregate capacity guard so
  concurrent proposals cannot overallocate a member period or partially commit.
- Added migration handling that temporarily removes and then restores views
  dependent on the legacy assignments table inside a savepoint. This was found
  when the first isolated rehearsal correctly stopped on a dependent-view
  schema error.
- Added a regression test proving assignment constraints can be installed
  without losing or breaking a dependent view.
- Validation after the migration repair: 40 focused
  staffing/integrity/migration tests, 114 full runtime tests, 18 repository
  tool tests (19 subtests), touched-file Ruff, static compilation, portability
  audit, repository-boundary check, synthetic-sample check, and diff check
  passed.

An isolated copy of the repository's synthetic legacy demo database upgraded
successfully. Core aggregate counts were unchanged, SQLite integrity passed,
foreign-key inspection returned no violations, dependent views remained
queryable, and the original demo database hash was unchanged. No operational
database was migrated; real-environment backup, isolated-copy rehearsal, and
operator-approved UAT are still required.
