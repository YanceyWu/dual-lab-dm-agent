# Current Implementation Pack Index

Status: `NO ACTIVE PACK — PHASE 1 DESIGN APPROVAL PENDING`
Last updated: 2026-07-27

This checkout intentionally contains only implementation material that remains
useful as validated-baseline reference. Completed IP-000 through IP-023 and
IP-025 specifications and reports were removed to prevent coding agents from
treating historical intermediate states as current work. They remain
recoverable from Git history.

## Retained baseline material

| Pack | Purpose | Current state | Report |
| --- | --- | --- | --- |
| IP-024 | Database integrity, concurrency, token migration, and isolated operational-copy rehearsal | Synthetic rehearsal passed; real-environment rehearsal deferred to the integrated candidate | `implementation-reports/IP-024_IMPLEMENTATION_REPORT.md` |
| IP-026 | Package identity, validation toolchain, CI, candidate tagging, release rehearsal, and rollback | Portable and remote CI validation green; tag and real UAT deferred to the integrated candidate | `implementation-reports/IP-026_IMPLEMENTATION_REPORT.md` |

## Current execution order

1. Review
   `architecture/06_PHASE_1_INTELLIGENCE_OUTPUT_CONTRACT_DESIGN.md`.
2. Approve it or record bounded revisions.
3. Register a new Phase 1 implementation pack only after that approval.
4. Implement and validate one reversible vertical slice at a time.
5. Return tagging, isolated operational-copy rehearsal, and refreshed
   real-environment UAT to the integrated release-candidate phase.

## Boundary

Do not restore historical implementation material merely for model context.
Consult Git history deliberately when a specific design decision must be
investigated. Never transfer operational data, configuration, credentials, raw
logs, screenshots, or internal identifiers into an implementation report.
