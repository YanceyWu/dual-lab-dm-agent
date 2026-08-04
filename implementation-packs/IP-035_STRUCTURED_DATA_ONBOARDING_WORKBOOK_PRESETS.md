# IP-035 — Structured Data Onboarding Workbook Presets

Status: `OWNER-APPROVED FOR BATCH B IMPLEMENTATION`
Design: `architecture/15_STRUCTURED_DATA_ONBOARDING_WORKBOOK_PRESET_DESIGN.md`
Implementation branch: `TBD IN FOLLOW-ON SESSION`
Baseline: `58e173364df9ffeca5be9bd5f3f31f04b65c21c5`

## Goal

Implement the next bounded slice after IP-034 Batch A so the shared onboarding
framework can reuse the workbook source type across multiple **approved workbook
contracts**. This batch should add a packaged preset registry and alias-aware
workbook parsing/validation without broadening into a generic mapping engine or
a new source type.

## Authorized outcome

The owner approved this bounded Batch B direction on 2026-08-04. A follow-on
session may implement only the scope recorded in this pack. UI, new source
types, connector acquisition, freeform mapping configuration, and broader
legacy importer migration remain separately gated.

## Proposed scope (Batch B only)

- Add a packaged workbook preset registry that is owned by
  `pm_agent.workbook_onboarding`.
- Allow saved onboarding profiles to select an approved workbook
  `mapping_preset_id` beyond the current single hard-coded default.
- Extend workbook parsing/validation to support bounded sheet/header aliases
  defined by the selected preset.
- Extend the shared onboarding preview contract so operators can see:
  - which preset was selected;
  - which worksheet names resolved to each logical section;
  - which aliases were used;
  - which contract mismatches are blockers versus warnings.
- Add CLI-first preset inspection suitable for a local operator review flow.
- Preserve the existing default workbook preset as the backward-compatible
  baseline.

## Explicit non-goals

- No UI, Dashboard onboarding screen, or wizard.
- No runtime-authored preset editor or freeform mapping DSL.
- No CSV, JSON, connector dump, or other new source adapter in this batch.
- No migration of `import_from_excel.py` or other legacy importers unless a
  later approved design proves they share the same workbook semantics.
- No change to workforce, capacity, milestone, or Project Health importer rules.
- No schema expansion unless a bounded audit need is proven during implementation
  review.

## Proposed module ownership

- `pm_agent.workbook_onboarding`
  - owns the workbook preset registry, alias-aware parser/validator behavior,
    preset metadata, and source-contract diagnostics.
- `pm_agent.data_onboarding`
  - owns profile persistence of `mapping_preset_id`, preview/confirm envelope
    shaping, and preset metadata projection.
- `pm_agent.cli.commands.onboarding`
  - owns read-only preset inspection and existing profile save/show/list command
    extensions.
- `pm_agent.database.bootstrap`
  - remains composition only; do not add workbook business logic there.

## Proposed operator contract

Batch B should expose a bounded CLI-first workflow:

```text
inspect available workbook presets
  -> save/update source profile with chosen preset
  -> preview onboarding run
  -> review preset resolution details + blockers/warnings/conflicts
  -> confirm onboarding run
```

At minimum, the operator should be able to answer:

- which workbook presets are available;
- which preset a given profile uses;
- whether a workbook matched the preset exactly or through allowed aliases;
- whether a workbook failed because a required section/column was missing or
  because matching was ambiguous.

## Validation plan

Focused tests should cover:

- preset registry discovery and validation;
- profile persistence with explicit preset selection;
- workbook parsing/validation for exact-match and alias-match layouts;
- ambiguity rejection when two aliases could satisfy the same logical field;
- preview contract projection of preset resolution details;
- regression that the current default workbook preset produces the same
  downstream canonical packages as IP-034 Batch A.

Required broader evidence:

- workbook onboarding regression;
- relevant onboarding regression;
- `make validate`;
- `make rehearse-release`;
- independent read-only review before acceptance.

## Rollback

Prefer a software-only rollback. If Batch B stays within packaged preset
definitions plus existing profile fields, reverting the software is enough.
Avoid introducing persistent runtime-authored preset data in this batch.

## Risks and transitional debt to watch

- Ambiguous alias support can silently mis-map data if matching rules are not
  explicit and deterministic.
- A too-flexible preset structure would recreate the rejected pattern of a broad
  configurable mapping surface.
- Legacy source-specific scripts will remain mixed operator entrypoints for a
  while; that is acceptable if clearly recorded and not widened in this batch.

## Next gate

Begin bounded Batch B runtime/code work in a new session from this approved
baseline. Before acceptance, the implementation must complete focused tests,
`make validate`, `make rehearse-release`, and independent read-only review.
