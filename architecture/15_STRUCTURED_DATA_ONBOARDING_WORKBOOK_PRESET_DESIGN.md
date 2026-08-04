# Structured Data Onboarding Workbook Preset Design

Status: `OWNER-APPROVED FOR BATCH B IMPLEMENTATION`
Date: 2026-08-04
Current-state authority: `PROGRESS.md`.
Baseline branch: `data-onboarding-framework-batch-a`
Baseline commit: `58e173364df9ffeca5be9bd5f3f31f04b65c21c5`
Previous implemented baseline: `IP-034 Structured Data Onboarding Framework Batch A`

## Decision supported

Define the next bounded batch after IP-034 Batch A so the new shared onboarding
framework can support multiple **approved workbook variants** without turning
`pm_agent.data_onboarding` into a second domain-validation layer.

The immediate next step should not be CSV/JSON onboarding, UI work, or a broad
importer migration. It should make the existing workbook source type more
reusable by introducing a **packaged workbook preset registry plus alias-aware
workbook parsing/validation**.

## Approval boundary

The owner approved this design on 2026-08-04 as the bounded architecture
direction for the next structured-onboarding batch. Implementation authority is
carried by the separately approved implementation pack
`implementation-packs/IP-035_STRUCTURED_DATA_ONBOARDING_WORKBOOK_PRESETS.md`.

This design still does not authorize work outside that bounded Batch B scope or
any external environment/data action.

## Verified current state after Batch A

### What now works

IP-034 Batch A now provides:

- onboarding-owned source profiles, runs, attempts, publication links, and
  replay/audit state;
- a thin `pm_agent.data_onboarding` orchestration layer with shared
  preview/confirm envelopes;
- `pm onboarding profile save/show/list`, `preview`, `confirm`, and `run show`;
- workbook onboarding registered as the first source type;
- explicit recovery, retry, reservation, and replay hardening for workbook runs.

### What still blocks practical reuse

The current workbook source is still intentionally narrow:

- `mapping_preset_id` is effectively fixed to
  `team-project-capacity-workbook-v1`;
- `source_options` are fixed defaults rather than preset-driven source
  contracts;
- workbook validation still assumes one exact sheet/header contract;
- operators cannot inspect which packaged workbook presets are available;
- preview shows the resulting canonical operations, but not a rich
  source-contract resolution summary.

That means the framework exists, but any **small approved workbook layout
variant** still forces a code change instead of a bounded preset addition.

## Why the next batch should be workbook presets, not a new source type

The current highest-value gap is not a second external format yet. It is that
the first source type is still hard-coded to one workbook contract. Expanding
workbook preset support first:

- reuses the new Batch A framework immediately;
- keeps the source boundary narrow and testable;
- avoids mixing multiple concerns at once (new source type + new preset system);
- creates the pattern that later CSV/JSON adapters can emulate.

## Recommended next batch

The next implementation slice should be **Batch B: Workbook preset registry and
alias-aware parsing**.

Batch B should let one workbook source type support multiple approved
repository-packaged contracts while preserving the same downstream canonical
packages and domain importer semantics.

## Target capability boundary for Batch B

### `pm_agent.data_onboarding` owns only

- persistence of the selected `mapping_preset_id` in the saved source profile;
- read-only projection of preset metadata in profile/preview contracts;
- orchestration of preview/confirm using the chosen workbook preset.

### `pm_agent.workbook_onboarding` owns

- the packaged workbook preset registry;
- sheet-name aliases, header aliases, optional-section rules, and related
  parser/validator behavior;
- source-contract warnings/blockers when a workbook does not satisfy the chosen
  preset;
- preview details explaining which preset and alias resolutions were used.

### Bootstrap owns

- no new business rules;
- preferably no new schema at all for Batch B unless a separately justified
  audit field proves necessary.

## Workbook preset model

Batch B should add a code-owned, versioned workbook preset definition with at
least:

- `mapping_preset_id`;
- display name and status (`active`, `deprecated`, later `retired` if needed);
- logical required sections and the accepted worksheet names for each section;
- bounded header aliases per logical worksheet contract;
- parser/validator defaults currently carried as workbook source options;
- explicit notes for any semantics that remain fixed by the workbook source type.

These presets are **packaged source contracts**, not operator-authored runtime
configuration. They must not become a generic freeform mapping DSL in this
batch.

## Operator contract

Batch B should keep the profile-oriented workflow from Batch A:

```text
choose workbook preset
  -> save/update source profile
  -> preview onboarding run
  -> review preset resolution + blockers/warnings/conflicts
  -> confirm onboarding run
```

To make that usable without UI, Batch B should expose read-only preset
inspection, for example:

- list available workbook presets;
- show one preset's accepted sections / aliases / status;
- save a profile against a non-default preset explicitly.

## Preview contract additions

The shared onboarding envelope should be extended to show workbook-contract
resolution explicitly, including:

- selected preset ID and display name;
- resolved worksheet names for each logical section;
- alias usage warnings when the workbook matched through an alias rather than
  the primary contract;
- missing optional sections vs hard blockers for missing required sections.

The preview must remain explicit. Batch B should **not** silently infer a "best"
preset among multiple possibilities.

## Explicit non-goals for Batch B

- No UI, Dashboard onboarding page, or wizard.
- No runtime-authored preset editor or freeform mapping DSL.
- No CSV/JSON/new source adapter in the same batch.
- No migration of `import_from_excel.py` or other legacy importers unless their
  source semantics match this workbook type exactly and are separately approved.
- No change to workforce/capacity importer rules or read semantics.

## Validation and acceptance expectation

Acceptance should require:

- focused tests for preset registry resolution and profile persistence;
- workbook parser/validator regression for alias-matched and ambiguity-rejected
  cases;
- framework regression proving preview/confirm semantics stay unchanged for the
  existing default workbook preset;
- `make validate`;
- `make rehearse-release`;
- independent read-only review of source-boundary ownership and ambiguity
  handling.

## Risks to keep explicit

- Alias support can become unsafe if multiple columns or worksheets match the
  same logical role ambiguously.
- If presets become too expressive, the repository will accidentally recreate a
  second mapping/configuration subsystem.
- If Batch B tries to absorb older flat exports or non-equivalent workbook
  shapes, the workbook source type will blur into a generic spreadsheet parser.

## Next gate

Begin bounded Batch B implementation in a new session using only the approved
IP-035 scope. Acceptance still requires focused regression, `make validate`,
`make rehearse-release`, and independent read-only review.
