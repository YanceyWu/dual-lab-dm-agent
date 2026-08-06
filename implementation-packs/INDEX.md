# Current Implementation Pack Index

Status: `HISTORICAL PACK INDEX — CURRENT STATE AUTHORITY IS PROGRESS.md`
Last updated: 2026-08-06

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
| IP-027 | Phase 1 typed intelligence result contract, validation, discovery, transport, and Management Attention reference mapping | Phase 1 promoted locally on 2026-07-28; retained in the current Phase 4 branch history | `implementation-packs/IP-027_PHASE_1_INTELLIGENCE_CONTRACT.md` | `implementation-reports/IP-027_IMPLEMENTATION_REPORT.md` |
| IP-028 | Phase 2 Delivery Attention Center: deterministic Attention storage, reconciliation, lifecycle, and controlled Center integration | Phase 2 promoted as the local development baseline on 2026-07-29 | `implementation-packs/IP-028_PHASE_2_DELIVERY_ATTENTION_CENTER.md` | `implementation-reports/IP-028_IMPLEMENTATION_REPORT.md` |
| IP-029 | Phase 3 incremental execution evidence, canonical Release/Milestone/Dependency facts, read-only review, and automatic derived Attention | Phase 3 promoted locally on 2026-07-30 | `implementation-packs/IP-029_PHASE_3_EXECUTION_AND_MILESTONE_FOUNDATION.md` | `implementation-reports/IP-029_IMPLEMENTATION_REPORT.md` |
| IP-030 | Phase 4 fixed seven-dimension Project Health, bounded configuration, and legacy strangler comparison | Promoted as local development baseline | `implementation-packs/IP-030_PHASE_4_SEVEN_DIMENSION_PROJECT_HEALTH.md` | `implementation-reports/IP-030_IMPLEMENTATION_REPORT.md` |
| IP-031 | Phase 5 Resource Intelligence | Promoted as the local Phase 5 development baseline on 2026-08-01 | `implementation-packs/IP-031_PHASE_5_RESOURCE_INTELLIGENCE.md` | `implementation-reports/IP-031_IMPLEMENTATION_REPORT.md` |
| IP-032 | Phase 6 Weekly Brief v2 | Promoted as the local Phase 6 development baseline on 2026-08-01 | `implementation-packs/IP-032_PHASE_6_WEEKLY_BRIEF_V2.md` | `implementation-reports/IP-032_IMPLEMENTATION_REPORT.md` |
| IP-033 | Phase 4 controlled assessment entry: import confirm runs the seven-dimension assessment and links it to the import audit | Owner-accepted on 2026-08-02 as a local development-baseline fix | `implementation-packs/IP-033_PHASE_4_ASSESSMENT_ENTRY.md` | none yet |
| IP-037 | Dashboard synthetic demo alignment: canonical sample publication readiness plus null-safe legacy rendering | Owner-approved on 2026-08-06 for phased local follow-on work; runtime unchanged until Batch A starts | `implementation-packs/IP-037_DASHBOARD_SYNTHETIC_DEMO_ALIGNMENT.md` | none yet |

## Usability handoff (2026-08-02)

R1 (synthetic demo pipeline, multi-state + HIREF), R2 (walkthrough), R5
(cross-capability integration test), R4 (a) `pm project-health config
show|preview|confirm`, and R4 (b) `pm staffing capacity-policy
show|enable-preview|enable-confirm` are implemented on
`codex/usability-r1-r2` and validated; R6 (UAT runbook revision) and R7
(documentation consistency scan) are in progress. These are usability items,
not implementation packs; see `PROGRESS.md` for the exact gate.

## Approved design

| Phase | Purpose | Current state | Design |
| --- | --- | --- | --- |
| Phase 5 | Resource Intelligence: effective capacity, resource risk, heatmap, and shared Staffing capacity facts | Promoted locally; Skill Dependency and new Attention producers remain excluded | `architecture/12_PHASE_5_RESOURCE_INTELLIGENCE_DESIGN.md` |
| Phase 6 | Weekly Brief v2 from promoted facts | Promoted as the local Phase 6 development baseline on 2026-08-01 | `architecture/13_PHASE_6_WEEKLY_BRIEF_V2_DESIGN.md` |
| Structured onboarding Batch B | Workbook preset registry plus alias-aware parsing/validation under the existing workbook source type | Owner-approved on 2026-08-04 for a separate follow-on implementation session | `architecture/15_STRUCTURED_DATA_ONBOARDING_WORKBOOK_PRESET_DESIGN.md` |

## Current execution order

1. Preserve the promoted IP-027 contract and Management Attention compatibility
   baseline.
2. Preserve the accepted corrected IP-028 Batch C1 implementation on
   `codex/phase-2-attention-center`.
3. Preserve the approved
   `architecture/08_LAYERED_PROJECT_HEALTH_AND_MILESTONE_EVOLUTION.md`.
   Do not use the current mapping configuration surface as an accepted
   DM-operable contract.
4. Phase 6 Weekly Brief v2 (IP-032) is the promoted local baseline.
5. IP-033 is owner-accepted on 2026-08-02 as a local development-baseline fix.
6. IP-034 Structured Data Onboarding Framework Batch A is committed locally at
   `58e1733`. The next planned gate is the owner-approved IP-035 Batch B
   implementation for workbook preset registry plus alias-aware parsing.
7. Return tagging, isolated operational-copy rehearsal, and refreshed
   real-environment UAT to the integrated release-candidate phase.

## Boundary

Do not restore historical implementation material merely for model context.
Consult Git history deliberately when a specific design decision must be
investigated. Never transfer operational data, configuration, credentials, raw
logs, screenshots, or internal identifiers into an implementation report.
