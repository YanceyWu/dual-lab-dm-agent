# Current Implementation Pack Index

Status: `PHASE 1 BATCH C VALIDATED — REVIEW REQUIRED`
Last updated: 2026-07-28

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

## Active implementation

| Pack | Purpose | Current state |
| --- | --- | --- |
| IP-027 | Phase 1 typed intelligence result contract, validation, discovery, transport, and Management Attention reference mapping | Batch C validated locally; review required before Batch D | `implementation-packs/IP-027_PHASE_1_INTELLIGENCE_CONTRACT.md` |

## Current execution order

1. Start a new Codex task and read `AGENTS.md`, `PROGRESS.md`, and the approved
   Phase 1 design.
2. Create a dedicated Phase 1 implementation branch from the approved planning
   branch.
3. Implement and validate IP-027 Batch B1 only.
4. Stop for Batch B1 review after focused tests plus `make validate`.
5. Begin Batch B2 only after explicit Batch B1 review approval.
6. Return tagging, isolated operational-copy rehearsal, and refreshed
   real-environment UAT to the integrated release-candidate phase.

## Boundary

Do not restore historical implementation material merely for model context.
Consult Git history deliberately when a specific design decision must be
investigated. Never transfer operational data, configuration, credentials, raw
logs, screenshots, or internal identifiers into an implementation report.
