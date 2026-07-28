# Current Implementation Pack Index

Status: `PHASE 1 BATCH D VALIDATED — PROMOTION DECISION REQUIRED`
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

| Pack | Purpose | Current state | Specification | Report |
| --- | --- | --- | --- | --- |
| IP-027 | Phase 1 typed intelligence result contract, validation, discovery, transport, and Management Attention reference mapping | Batch D locally green; explicit Phase 1 promotion decision required | `implementation-packs/IP-027_PHASE_1_INTELLIGENCE_CONTRACT.md` | `implementation-reports/IP-027_IMPLEMENTATION_REPORT.md` |

## Current execution order

1. Start a new Codex task and read `AGENTS.md`, `PROGRESS.md`, and the approved
   Phase 1 design.
2. Create a dedicated Phase 1 implementation branch from the approved planning
   branch.
3. Preserve the validated Batch B1 and B2 contract/discovery foundation.
4. Preserve the validated Batch C Management Attention reference mapping.
5. Review the completed Batch D regression, rehearsal, portable review, and
   IP-027 implementation report.
6. Record an explicit promote, revise, or stop decision for Phase 1.
7. Start Phase 2 design only after explicit promotion; do not begin Phase 2
   implementation from this task.
8. Return tagging, isolated operational-copy rehearsal, and refreshed
   real-environment UAT to the integrated release-candidate phase.

## Boundary

Do not restore historical implementation material merely for model context.
Consult Git history deliberately when a specific design decision must be
investigated. Never transfer operational data, configuration, credentials, raw
logs, screenshots, or internal identifiers into an implementation report.
