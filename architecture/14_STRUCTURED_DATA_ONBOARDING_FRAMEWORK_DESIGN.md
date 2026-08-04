# Structured Data Onboarding Framework Design

Status: `IMPLEMENTED AS LOCAL BATCH A BASELINE`
Date: 2026-08-04
Current-state authority: `PROGRESS.md`.
Baseline branch: `data-onboarding-framework-batch-a`
Baseline commit: `58e173364df9ffeca5be9bd5f3f31f04b65c21c5`
Previous implemented baseline: `Committed IP-034 Batch A framework baseline`

## Decision supported

Turn the now-working workbook onboarding v1 path into the first source type of a
general structured-data onboarding framework, so future data sources can be
added mainly by writing adapters and source-profile mappings instead of
rebuilding preview/confirm/import orchestration from scratch.

The goal is easier and safer data onboarding, not a UI project. The framework
must preserve the current repository direction:

- clean bootstrap and full re-import remain the production path;
- source-specific formats never couple directly to domain import contracts;
- every write path stays preview/confirm/persist with audit and replay safety;
- missing evidence never becomes zero, healthy, or complete by inference.

## Design-only review boundary

This document proposes the next capability boundary and implementation order
only. It does not authorize runtime, schema, CLI, Dashboard, connector, or
real-data changes by itself. A separately reviewed implementation pack is still
required before code changes begin.

## Verified current state

### What is already working

The committed workbook onboarding v1 baseline proves the following path is
viable:

```text
workbook file
  -> workbook-native parser / validator
  -> source-specific adapter
  -> canonical workforce / capacity packages
  -> preview / confirm import contracts
  -> current publication replacement + effective read path
```

That path now supports:

- fixed-contract workbook parsing and validation;
- sparse-allocation expansion into authoritative coverage;
- optional capacity publication with explicit zero vs unknown semantics;
- conflict blocking against unabsorbed confirmed Copilot staffing adjustments;
- stable effective reads from current baseline plus later confirmed adjustments.

### What remains fragmented

The repository still exposes multiple data-entry patterns:

- source-specific scripts such as `import_workforce_planning.py`,
  `import_resource_capacity.py`, `import_team_project_capacity_workbook.py`,
  `import_milestones.py`, `import_project_health.py`, and the older
  `import_from_excel.py`;
- per-capability preview/confirm flows that are correct locally but not unified
  at the onboarding level;
- no registry of saved source profiles, mapping presets, or reusable onboarding
  run summaries;
- no common source-agnostic preview envelope showing coverage, blockers,
  warnings, conflicts, and publish intent in one contract;
- no single owner-local run history explaining which source profile created
  which canonical import session set.

The result is that the first workbook source works, but the *next* source still
costs too much to integrate.

## Target capability boundary

The next capability should be a thin cross-source orchestration layer:
`pm_agent.data_onboarding`.

It owns only:

- source profile definitions and validation;
- source-type registration;
- normalized onboarding session / attempt audit;
- a common preview result envelope and publish summary contract;
- orchestration across source adapter -> canonical package -> importer preview /
  confirm;
- replay and operator-facing run traceability at the onboarding level.

It must not own:

- workforce, capacity, milestone, or Project Health domain rules;
- domain schema internals outside additive onboarding-owned tables;
- connector credential handling, raw payload storage, or source acquisition;
- UI rendering, Dashboard pages, or wizard behavior;
- format-specific parsing rules that belong inside a source adapter.

## Four-layer onboarding model

Future onboarding sources should converge on four explicit layers:

### 1. Raw source adapters

Examples:

- workbook / Excel
- CSV
- JSON export
- approved local connector dump

Each adapter reads one external source shape and produces a source-specific raw
model only.

### 2. Normalized staging models

A staging model removes source-format differences while preserving business
meaning, warnings, and row lineage. This is where:

- column aliases are resolved;
- source rows are normalized;
- missing / conflicting source values become structured issues;
- row-level traceability is retained.

### 3. Canonical import packages

Only after normalization may a source be transformed into an existing domain
contract such as:

- workforce planning import packages;
- resource capacity import packages;
- milestone import packages;
- project health re-import packages.

This keeps external format churn out of capability-owned import contracts.

### 4. Preview / confirm / publish runtime

The final layer remains the existing domain importers plus a source-agnostic
onboarding wrapper that standardizes:

- preview summaries;
- conflict reporting;
- confirmation requirements;
- run history and replay identity;
- publish summaries;
- coverage and integrity reporting.

## Source profile model

The framework should introduce a saved source profile as the operator-level
entry point.

A profile should capture at least:

- source type (`workbook`, `csv`, `json`, later approved types);
- source locator (path or approved local reference);
- mapping preset identifier;
- default onboarding profile / key strategy;
- optional plan naming policy;
- source-specific required/optional sections;
- last successful run metadata.

Profiles are configuration objects only. They are not domain data and must not
replace domain publications or import audit owned by workforce/capacity/etc.

## Common preview result contract

Every source type should be projected into one onboarding preview envelope with:

- normalized source identity and source-profile metadata;
- blockers, warnings, and conflicts;
- planned canonical domain operations;
- counts by entity type and coverage scope;
- explicit unknown / missing coverage summary where relevant;
- required confirmations and replay/idempotency identity;
- exact downstream domain sessions created or planned.

The aim is not to hide domain detail, but to stop each new source type from
inventing a different operator-facing preview shape.

## Recommended first implementation slice

The next implementation slice should be **Batch A: Unified onboarding
framework**.

Batch A should do only the minimum needed to make workbook onboarding the first
registered source type under a general framework:

1. add onboarding-owned additive schema for source profiles and run audit;
2. register source types and a source-profile contract;
3. define the shared preview/confirm summary envelope;
4. wrap workbook onboarding v1 behind that framework without changing workbook
   semantics;
5. leave domain import contracts in their current capability owners.

This sequence gives immediate reuse value without prematurely redesigning the
source-specific adapters.

## Explicit non-goals for Batch A

- No new UI, wizard, or Dashboard onboarding screen.
- No connector-driven live acquisition or scheduling.
- No attempt to unify all domain import package schemas into one mega contract.
- No workbook v2 mapping expansion yet beyond what the saved profile needs.
- No migration of every legacy one-off script in the same batch.

## Follow-on batches after Batch A

Once Batch A exists, later bounded batches can safely add:

1. workbook mapping presets and alias support;
2. CSV / JSON source adapters targeting the same canonical packages;
3. richer post-import diff / exception summaries;
4. eventual operator-friendly command families or Dashboard projection.

## Validation and acceptance expectation

Because Batch A likely adds onboarding-owned schema and packaged behavior, its
acceptance should require:

- focused tests for source profiles, preview envelope, run audit, and workbook
  framework integration;
- existing workbook onboarding regression plus relevant domain importer suites;
- `make validate`;
- `make rehearse-release`;
- independent read-only review of module ownership, coupling, replay safety,
  clean re-import alignment, and operator contract clarity.

## Risks to keep explicit

- The framework must stay thin. If it starts owning domain validation or import
  internals, it will become a second domain layer and increase coupling.
- Source profiles must not become a hidden source of truth that competes with
  canonical domain publications.
- Batch A should not absorb older ad hoc importers blindly; each migration needs
  a bounded follow-up review.

## Historical note

This design is now implemented locally as IP-034 Batch A at commit `58e1733`.
Current-state progress and any later follow-on design must be reviewed through
`PROGRESS.md` and newer bounded design material.
