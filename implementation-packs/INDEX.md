# Current Implementation Pack Index

Status: `PHASE 1 DESIGN APPROVED — IMPLEMENTATION PACK REGISTRATION NEXT`
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

1. Start a new Codex task and read `AGENTS.md`, `PROGRESS.md`, and the approved
   Phase 1 design.
2. Create a dedicated Phase 1 implementation branch from the approved planning
   branch.
3. Register the Phase 1 implementation pack.
4. Implement Batch B1 only and stop after focused tests plus `make validate`.
5. Begin Batch B2 only after Batch B1 review.
6. Return tagging, isolated operational-copy rehearsal, and refreshed
   real-environment UAT to the integrated release-candidate phase.

## Boundary

Do not restore historical implementation material merely for model context.
Consult Git history deliberately when a specific design decision must be
investigated. Never transfer operational data, configuration, credentials, raw
logs, screenshots, or internal identifiers into an implementation report.
