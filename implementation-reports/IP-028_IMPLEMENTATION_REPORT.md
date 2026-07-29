# IP-028 Implementation Report

Status: `BATCH D REVIEW ACCEPTED — PHASE 2 PROMOTION DECISION REQUIRED`
Date: 2026-07-29
Branch: `codex/phase-2-attention-center`
Approved planning commit: `e4431dc0ab5f7122d65affaa917fa3697d634b15`

## Implemented

- Added deterministic, additive Attention rule, operation, reconciliation,
  current-signal, history, and retained legacy-configuration-operation storage.
- Added four active rules for project health, overdue action, resource
  overload strictly above 100%, and source freshness.
  `pending_decision_attention` is registered but database-constrained and
  runtime-disabled.
- Added canonical Attention identity, semantic observation hashing,
  deduplicated reconciliation, partial/failed retention, automatic `rule_clear`
  resolution, acknowledgement, snooze, and append-only lifecycle history.
- Added the read-only `delivery-attention-center` use case with explicit
  reconciliation coverage, pre-limit summaries, bounded history, evidence,
  freshness, facts, signals, and advisory recommendations.
- Added exact JSON Attention CLI and dedicated Dashboard preview/confirm
  projections for reconciliation, acknowledgement, and snooze. ToolTransport
  remains query-only, and Copilot never reconciles implicitly.
- Preserved `UseCaseResult 1.0` and the existing Management Attention business
  projection. Management Attention queries create no Attention persistence.
- Removed the rejected mapping-oriented RAG configuration CLI, Dashboard, and
  Copilot paths. Direct preview and retained legacy-token confirmation return
  `ATTENTION_RAG_CONFIGURATION_UNAVAILABLE`.
- Removed dormant configuration-operation and project-health rule-version
  mutation helpers while retaining the additive table, existing records,
  current-rule reading, and legacy-operation read detection.
- Recorded the approved future separation between Sprint Execution,
  Release/Milestone Health, and seven-dimension Project Health. No Phase 3 or
  Phase 4 runtime is included.

## Local commits before Batch D reporting

- `27687a3` — deterministic Phase 2 Attention foundation.
- `329d2e1` — first foundation review corrections.
- `f0e4eec` — remaining Attention review blockers.
- `4909290` — partial-evaluation deduplication.
- `3e93d14` — Batch C interface design approval.
- `2fd5df8` — Batch C1 Attention Center and controlled interfaces.
- `10fd4cf` — Batch C1 review corrections.
- `5663338` — Batch C1 acceptance record.
- `71d90d3` — technically validated but product-rejected RAG mapping
  configuration.
- `284410c` — layered health and milestone architecture revision.
- `5ad2cb9` — layered health design approval.
- `47c8d8b` — removal/blocking of the rejected public mapping paths.
- `ddbb55d` — mutation-boundary review fix.
- `5f2f2ad` — clean technical re-review record.

The Batch D report/progress commit is the final local branch HEAD reported in
the task handoff. None of these Phase 2 commits is pushed.

## Validation evidence

- Combined focused Phase 2 regression: 109 tests passed, covering Attention
  rules, storage, reconciliation, lifecycle, Center projections, retained
  configuration storage, public-interface rejection, migration, concurrency,
  Management Attention, `UseCaseResult 1.0`, discovery, CLI build, and Copilot.
- `make validate`: passed with 183 runtime tests, 21 repository-tool tests and
  19 subtests, Ruff, compilation, repository-boundary checks,
  synthetic-sample checks, diff hygiene, and wheel/sdist build inspection.
- `make rehearse-release`: passed temporary wheel installation, isolated
  synthetic database upgrade, integrity checks, installed behavior, and
  rollback for `ai-pm-agent 0.2.0rc1`.
- The complete Phase 2 diff from `e4431dc` is limited to Attention runtime,
  additive database bootstrap/migrations, Center/CLI/Dashboard/Copilot
  integration, synthetic tests, and repository documentation.
- Portable boundary and synthetic-data checks passed. No connector, network,
  operational configuration, credential, real record, internal identifier, or
  company-derived value was accessed.

## Schema and migration review

Phase 2 adds six tables:

- `attention_rules`;
- `attention_operations`;
- `attention_configuration_operations`;
- `attention_reconciliations`;
- `attention_signals`; and
- `attention_history`.

The schema enforces one current rule version, JSON validity, bounded lifecycle
states, non-negative reconciliation counts, stable subject uniqueness,
foreign-key references, hashed unique tokens, and disabled
`pending_decision_attention`.

Migration coverage proves:

- clean and additive bootstrap preserve existing tables, views, and rows;
- `last_evaluation_hash` is added and backfilled from the retained observation
  hash;
- Attention history is rebuilt only when needed to add `rule_changed`, with
  rows and indexes preserved;
- the fixed v1 project-health rule migrates idempotently to the legacy
  versioned v2 read semantics;
- the retained configuration-operation table and existing records are not
  removed or mutated by the correction; and
- foreign-key and integrity checks pass before rollback.

The rejected DM-facing mapping write has no runtime mutation helper. The fixed
Bootstrap v1-to-v2 migration is deterministic, idempotent, and accepts no DM
configuration input.

## Compatibility

- `UseCaseResult` and descriptor contract versions remain `1.0`.
- Existing Management Attention `data`, typed facts/signals, ordering,
  summaries, warnings, and read-only behavior remain compatible.
- The new Delivery Attention Center is a separate use case and does not change
  the Management Attention contract.
- ToolTransport remains query-only. Attention writes require the dedicated
  preview/confirm service and runtime-issued one-time tokens.
- Complete clear reconciliation resolves automatically; no manager resolve
  command is exposed.
- Missing, partial, failed, stale, and conflicting evidence never silently
  clear retained Attention state or imply health.

## Remaining risks and controls

1. The retained `attention_configuration_operations` table may contain
   historical local rows from the rejected C2 implementation. It is read-only
   in the current runtime and must not be reused for Phase 4 without an
   approved migration and contract.
2. Project-health Attention still consumes the legacy Jira grade and
   Confluence RAG observations. These are not the approved future
   Sprint/Release/Project Health model and must remain identified as legacy
   evidence.
3. Remote CI has not run for the local Phase 2 commits. Local regression and
   synthetic installed-package rehearsal are green, but remote status is
   unknown.
4. No connector, operational database, real record, notification, visual
   Dashboard Center, or real-environment UAT was exercised. Those remain
   separately gated.
5. Phase 2 does not implement canonical milestones, Release commitments,
   bounded DM health conditions, Forecast, or automatic business-object
   writes.

## Promotion gate

The local Phase 2 implementation satisfies its approved Batch D validation,
schema, compatibility, migration, and portable-scope criteria. It is ready for
an explicit owner promotion decision. The owner accepted the Batch D Review on
2026-07-29; that acceptance does not itself promote Phase 2.

Promotion would establish the completed local Phase 2 development baseline
only. It would not authorize merge, push, tag, release, deployment, connector
access, active-database migration, real-data UAT, Phase 3 implementation, or
Phase 4 implementation.
