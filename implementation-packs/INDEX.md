# Current Implementation Pack Index

Status: `IP-028 PHASE 2 PROMOTED LOCALLY — PHASE 3 DESIGN REVIEW REQUIRED`
Last updated: 2026-07-29

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
| IP-027 | Phase 1 typed intelligence result contract, validation, discovery, transport, and Management Attention reference mapping | Phase 1 promoted locally on 2026-07-28; commits remain unpushed | `implementation-packs/IP-027_PHASE_1_INTELLIGENCE_CONTRACT.md` | `implementation-reports/IP-027_IMPLEMENTATION_REPORT.md` |
| IP-028 | Phase 2 Delivery Attention Center: deterministic Attention storage, reconciliation, lifecycle, and controlled Center integration | Phase 2 promoted as the local development baseline on 2026-07-29; Phase 3 design review is separately gated | `implementation-packs/IP-028_PHASE_2_DELIVERY_ATTENTION_CENTER.md` | `implementation-reports/IP-028_IMPLEMENTATION_REPORT.md` |

## Current execution order

1. Preserve the promoted IP-027 contract and Management Attention compatibility
   baseline.
2. Preserve the accepted corrected IP-028 Batch C1 implementation on
   `codex/phase-2-attention-center`.
3. Preserve the approved
   `architecture/08_LAYERED_PROJECT_HEALTH_AND_MILESTONE_EVOLUTION.md`.
   Do not use the current mapping configuration surface as an accepted
   DM-operable contract.
4. Begin Phase 3 current-state and design review only with explicit
   authorization. Do not begin Phase 3 implementation, Phase 4, release, push,
   merge, or tag work under the current gate.
5. Return tagging, isolated operational-copy rehearsal, and refreshed
   real-environment UAT to the integrated release-candidate phase.

## Boundary

Do not restore historical implementation material merely for model context.
Consult Git history deliberately when a specific design decision must be
investigated. Never transfer operational data, configuration, credentials, raw
logs, screenshots, or internal identifiers into an implementation report.
