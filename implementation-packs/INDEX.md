# Current Implementation Pack Index

Status: `0.2.0rc1 CANDIDATE — REAL-ENVIRONMENT UAT PENDING`
Last updated: 2026-07-26

This checkout intentionally contains only implementation material that remains
useful for the current release gate. Completed IP-000 through IP-023 and IP-025
specifications and reports were removed from the candidate checkout to prevent
coding agents from treating historical intermediate states as current work.
They remain recoverable from Git history.

## Active material

| Pack | Purpose | Current state | Report |
| --- | --- | --- | --- |
| IP-024 | Database integrity, concurrency, token migration, and isolated operational-copy rehearsal | Synthetic rehearsal passed; real-environment rehearsal pending | `implementation-reports/IP-024_IMPLEMENTATION_REPORT.md` |
| IP-026 | Package identity, validation toolchain, CI, candidate tagging, release rehearsal, and rollback | Portable validation green; immutable tag and real UAT pending | `implementation-reports/IP-026_IMPLEMENTATION_REPORT.md` |

## Current execution order

1. Validate the exact candidate checkout with `make validate` and
   `make rehearse-release`.
2. Commit and push only after reviewing the portable change scope.
3. Create annotated tag `v0.2.0-rc.1` only with explicit owner authorization.
4. On the work computer, follow `docs/REAL_ENVIRONMENT_UAT_RUNBOOK.md` and
   rehearse IP-024 against an isolated operational-database copy.
5. Run controlled read-only, connector, staffing, and Dashboard UAT.
6. Promote locally or create a new release candidate from sanitized failure
   evidence. Do not move an existing tag.

## Boundary

Do not restore historical implementation material merely for model context.
Consult Git history deliberately when a specific design decision must be
investigated. Never transfer operational data, configuration, credentials, raw
logs, screenshots, or internal identifiers into an implementation report.
