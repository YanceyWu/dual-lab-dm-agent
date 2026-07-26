# IP-024 — Data Integrity and Concurrency

## Business goal

Make SQLite the final correctness boundary for staffing allocations even when
application code is bypassed, two confirmations race, or an upgrade encounters
invalid historical rows.

## Integrity contract

- Assignment and monthly allocation values must remain between 0 and 1.
- Month must remain between 1 and 12.
- One employee/project/month/plan-version row is allowed.
- Placeholder allocations follow the same month/allocation constraints.
- Confirmation tokens are stored only as SHA-256 hashes.
- Proposal and confirmation timestamps use timezone-aware UTC.
- Confirmation obtains an immediate write transaction, conditionally claims a
  proposed record, checks aggregate member-period load, and atomically writes
  assignments, monthly allocations, decision record, and final proposal state.

## Migration and rollback

The additive/rebuild migration validates invalid values and duplicates before
changing a table. Dirty legacy data stops the migration with repair guidance.
Tests prove the dirty table remains untouched and legacy plaintext tokens
migrate to hashes. Operational upgrade still requires the documented pre-upgrade
backup and isolated-copy rehearsal.
