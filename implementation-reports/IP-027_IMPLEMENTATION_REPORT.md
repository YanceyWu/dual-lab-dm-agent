# IP-027 Implementation Report

Status: `BATCH D VALIDATION GREEN — PHASE 1 PROMOTION DECISION PENDING`
Date: 2026-07-28
Branch: `codex/phase-1-intelligence-contract`
Approved planning commit: `3d406334f714ccad40daa9e8441499e5b7ebdaab`

## Implemented

- Added typed subject, fact, signal, and recommendation objects to the existing
  `UseCaseResult`, with additive empty-array defaults and contract version
  `1.0`.
- Added shared fail-closed result validation for bounded and unique IDs,
  evidence/freshness/fact/signal references, derived-fact rule versions,
  non-known null values, and proposal confirmation.
- Added safe `RESULT_CONTRACT_INVALID` failure behavior without exposing
  validation details, configuration, exceptions, or handler payload values.
- Added strictly boolean descriptor intelligence capabilities and additive
  list/describe projection.
- Preserved all nine production descriptors, with Management Attention as the
  only facts/signals capability and no recommendation capability.
- Added one derived fact and one active signal for every returned Management
  Attention item while preserving its existing data, ordering, summary,
  truncation, context, warnings, severity, and reason codes.
- Added only bounded source-freshness evidence required by the new reference
  chain. Full intelligence payloads remain absent from execution traces.
- Updated Copilot result handling to prioritize facts, signals,
  recommendations, and their evidence/freshness qualifiers, and to prohibit
  invented intelligence or recommendations.

## Local commits before Batch D reporting

- `4d78f02e6ccca7cedba21c379c6a160fccf99fe2` — Batch B1 contract and validation.
- `8041e823cef2d0a6e930feca6f5f8defb8bf5b8a` — Batch B1 review corrections.
- `b22b36544ea3c23821e850741e16815a3cd9f9bd` — Batch B2 discovery and transport.
- `ea5eb7ac28c1f77ec10492ff8c4899dab4a9739c` — Batch B2 review corrections.
- `61b3d8c585d00ffe8527774c51fd3a36c59af078` — Batch C reference mapping.

The Batch D report/progress commit is the final local branch HEAD reported in
the task handoff. None of these commits is pushed.

## Validation evidence

- Combined focused Phase 1 regression: 63 tests passed, covering typed result
  validation, discovery, structured transport, Management Attention, Copilot,
  unified use-case contracts, and legacy interface compatibility.
- `make validate`: passed with 153 runtime tests, 21 repository-tool tests and
  19 subtests, Ruff, compilation, repository-boundary checks, synthetic-sample
  checks, diff hygiene, and wheel/sdist build inspection.
- `make rehearse-release`: passed temporary wheel installation, isolated
  synthetic database upgrade, integrity checks, installed behavior, and
  rollback for `ai-pm-agent 0.2.0rc1`.
- The complete Phase 1 diff from `3d40633` changes only the shared use-case
  contract/executor, Management Attention mapping, discovery transport,
  Copilot operating instructions, tests, and repository documentation.
- No file under `src/pm_agent/database` changed. No table, column, view,
  migration, or full-intelligence trace persistence was added.
- Portable boundary and synthetic-data checks passed. No connector, network,
  operational configuration, credential, real record, or company-derived
  value was accessed.

## Compatibility

- Existing `UseCaseResult` fields retain their meanings.
- `facts`, `signals`, and `recommendations` are additive and default empty.
- Result and descriptor contract versions remain `1.0`.
- Existing Management Attention `data` remains the legacy-compatible
  projection; the new intelligence objects are a deterministic parallel
  projection of returned items only.
- Structured CLI and generic Dashboard serialize the same full shared result.
- Trace retrieval remains a bounded summary with empty intelligence arrays.

## Remaining risks and controls

1. Strict external consumers may assume the pre-Phase-1 exact JSON key set.
   Repository CLI/Dashboard parity is tested, but external compatibility still
   requires consumer review.
2. Management Attention intentionally exposes the same meaning through legacy
   `data` and typed intelligence fields. Keep one deterministic mapper and
   parity tests until legacy projection retirement is separately approved.
3. Phase 1 defines output structure, not Attention lifecycle, persistence,
   recommendations, forecasting, or Phase 2 behavior.
4. Remote CI has not run for these unpushed commits. Local validation and
   rehearsal are green, but remote status is unknown.

## Promotion gate

The local Phase 1 implementation satisfies its approved design and Batch D
validation criteria. Promotion to the completed Phase 1 baseline is
recommended, subject to explicit owner approval.

Promotion does not authorize a merge, push, tag, release, deployment,
connector access, active-database migration, real-data UAT, or Phase 2
implementation. After promotion, the next action is a new Phase 2 design task,
not direct Phase 2 coding.
