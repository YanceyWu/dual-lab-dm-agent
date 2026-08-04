# IP-034 — Structured Data Onboarding Framework

Status: `IMPLEMENTED AND OWNER-ACCEPTED LOCALLY`
Design: `architecture/14_STRUCTURED_DATA_ONBOARDING_FRAMEWORK_DESIGN.md`
Implementation branch: `data-onboarding-framework-batch-a`
Implemented local commit: `58e173364df9ffeca5be9bd5f3f31f04b65c21c5`
Previous baseline: `bc208d70ec7698fb41da4850d7f1f52897410453`

## Goal

Implement the first bounded slice of a reusable structured-data onboarding
framework so future sources can plug into a common profile / preview / confirm /
publish flow. This slice must keep the newly committed workbook onboarding v1
behavior intact while turning it into the first registered source type.

## Proposed scope (Batch A only)

- Add an onboarding-owned additive schema for:
  - saved source profiles;
  - onboarding runs / attempts;
  - source-to-domain publication linkage.
- Add a thin `pm_agent.data_onboarding` capability that owns:
  - source-type registry;
  - source-profile validation;
  - common preview result envelope;
  - common confirm/publish result summary;
  - onboarding-level replay / audit history.
- Register workbook onboarding as the first source type under that framework.
- Preserve existing domain importers as the owners of:
  - package validation;
  - publication integrity;
  - current-publication switching;
  - domain-specific audit and read contracts.
- Add a backend/CLI-only profile-oriented entrypoint suitable for later operator
  wrapping.

## Explicit non-goals

- No UI, Dashboard onboarding page, or wizard.
- No live connector pull, sync scheduling, or external secret handling.
- No workbook v2 mapping expansion beyond what the source-profile contract
  needs.
- No forced migration of every older ad hoc importer in this same slice.
- No changes to workforce, capacity, milestone, or Project Health public read
  semantics beyond the framework wrapper.

## Proposed module ownership

- `pm_agent.data_onboarding.schema`
  - onboarding-owned additive DDL only.
- `pm_agent.data_onboarding.repository`
  - source profiles, run audit, publication linkage, replay helpers.
- `pm_agent.data_onboarding.service`
  - source-type dispatch, preview orchestration, confirm orchestration, common
    result shaping.
- `pm_agent.data_onboarding.types` or `models`
  - shared source-profile and preview/confirm contract types.
- `pm_agent.workbook_onboarding`
  - remains owner of workbook parsing, validation, source-specific adaptation,
    and workbook-only policy.

Bootstrap composes only the new onboarding schema module. It must not absorb
framework business rules, queries, or transactions.

## Proposed operator contract

Batch A should expose a profile-based backend/CLI workflow:

```text
define source profile
  -> preview onboarding run
  -> review blockers / warnings / conflicts / planned publications
  -> confirm onboarding run
  -> inspect resulting domain publication linkage
```

A profile-based run must return enough detail to answer:

- which source type and profile ran;
- which canonical domain imports were planned or published;
- what blockers/warnings/conflicts were found;
- which downstream session/publication IDs were created;
- whether the run was replayed, rejected, or newly published.

## Validation plan

Focused tests should cover:

- source-profile validation and persistence;
- replay/idempotency at the onboarding-run layer;
- shared preview envelope shape;
- workbook source registration through the framework;
- linkage from onboarding run to downstream workforce/capacity sessions;
- regression that workbook semantics remain unchanged when invoked through the
  framework wrapper.

Required broader evidence:

- workbook onboarding tests;
- relevant importer and repository-tool regression;
- `make validate`;
- `make rehearse-release`;
- independent read-only review before acceptance.

## Rollback

Batch A should be software-revertable. Any added onboarding tables must be
strictly additive and unused by the previous runtime. Domain publications must
remain owned by their existing capabilities so rollback never requires
rewriting workforce/capacity data.

## Risks and transitional debt to watch

- The framework can become too broad if it starts duplicating domain import
  validation.
- Profile defaults can hide important source-specific policy if the preview
  contract is not explicit enough.
- Partial migration of older import scripts will leave mixed operator paths for
  a while; that is acceptable if recorded and bounded.

## Historical note

Batch A runtime/schema/code work is complete and committed locally at `58e1733`.
New structured onboarding work should proceed only through a later bounded
design / implementation pack.
