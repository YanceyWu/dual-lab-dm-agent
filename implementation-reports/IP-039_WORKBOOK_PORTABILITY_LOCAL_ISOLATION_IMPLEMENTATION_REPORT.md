# IP-039 implementation report

Status: core Team/Project + Capacity/HIREF source-facts export correction
implemented; independent review pending.

## What changed and why

- Workbook export now reads only maintained Team/Project source facts: members,
  projects, one explicitly selected (or sole active) plan, monthly allocations,
  the retained capacity input package, HIREF requests, member current/next
  HIREF references, and open-demand allocations.
- `workforce_planning_import` owns the public source reader for canonical
  member/project/plan/allocation tables. `resource_intelligence` owns a source
  reader that reconstructs Capacity rows from the completed input package,
  without querying a capacity publication, observation, freshness, or
  derivation row.
- Export no longer requires current-state staffing, contract coverage, Project
  Health, snapshot, onboarding-link, workforce-publication, capacity-
  publication, freshness, generation, or audit coherence. Those are derived
  after source import and are not serialized.
- The existing atomic write/no-overwrite behavior and v1 parser/validator
  self-check remain unchanged. The temporary data-onboarding generation-context
  reader introduced by the earlier correction was removed.

## Usable functionality

`pm onboarding export-workbook --output <path>` exports the existing
`team-project-capacity-workbook-v1` contract. It fails when no active plan is
available, when more than one active plan is not explicitly selected, or when
the retained source facts are internally invalid. Capacity is optional: no
completed capacity input package produces an empty Capacity sheet.

## Impact and compatibility

The workbook sheets and import contract are unchanged. A generated workbook
still previews through the existing handler and preserves HIREF open-demand
rows. Derived-data corruption or staleness no longer prevents an otherwise
valid source export. Re-import regenerates workforce, staffing, capacity,
coverage, health, freshness, evidence, and audit state.

## Intentionally unimplemented scope and next gate

Project Profile and connector-registry exports, bundle/setup changes, and
demo-to-local switching are outside this core correction. No schema, connector,
Dashboard, real-data, commit, push, tag, release, or deployment action was
taken. Next gate: independent read-only review of the bounded IP-039 diff.

## Test and review evidence

- `src/.venv/bin/python -m pytest src/tests/test_workbook_onboarding.py src/tests/test_workforce_planning_import.py -q` — `62 passed`.
- Focused coverage proves source export succeeds with stale/mismatched or
  absent derived publication detail, preserves no-overwrite/overwrite behavior,
  rejects ambiguous plan selection, validates output through the v1 parser and
  handler preview/import into a separate SQLite database, and retains HIREF
  open demand.
- `src/.venv/bin/python -m ruff check` on the touched runtime/test modules and
  `git diff --check` both passed.
- Independent read-only review is not yet complete.

## Integration evidence and active blocker

- Combined focused suite across workbook/workforce/source exports/data
  onboarding/config path/bundle/release-engineering surfaces: `128 passed`.
  After the two demo compatibility fixes below, the directly affected subset
  reports `102 passed`; touched-module Ruff and `git diff --check` pass.
- `make rehearse-release` passed: wheel build/install plus isolated database
  upgrade and rollback. `make validate` was invoked twice but the execution
  host ended both sessions during `runtime-tests` at about 41% without an exit
  status; this is not a validation pass. Full-repository Ruff is independently
  blocked by 12 pre-existing findings in `src/scripts/generate_hiref_report.py`,
  outside this slice; changed-file Ruff passes.
- An isolated lean bundle was built at
  `/private/tmp/ip039-lean-bundle.v8IpeD/out-final`; archive SHA-256 is
  `cc4ee401caa3a222b5aebcd6d5ee8596598621e539fdb143452ddf4de90dd910`.
  Its manifest contains the workbook kit, source artifacts, and primary Copilot
  files, and excludes `src/configs/` and `.github/prompts/`.
- Normal isolated `setup --install --mode demo` reached the expected explicit
  `package_index_unavailable` result because package-index networking was not
  available. No install path was bypassed. With the existing local dependency
  environment, the bundle's setup helper selected the synthetic demo and its
  writable copy matched the packaged demo SHA-256.
- Bundle smoke exposed and fixed two legacy source compatibility defects:
  HIREF request projects stored directly as canonical IDs are now accepted, and
  `junior`/`mid`/`senior`/`lead` member levels map to valid workbook levels.
  The synthetic demo intentionally retains member 003 as `STFTE` without a
  current HIREF to demonstrate a Legacy HIREF alert. It is not source-complete
  for v1 re-import. Export now rejects it *before* writing with the stable,
  privacy-safe `WORKBOOK_EXPORT_STFTE_HIREF_REQUIRED` code rather than a
  generic write failure. The generated Workbook guide and Copilot agent direct
  users to correct the maintained HIREF facts through preview/confirm before
  retrying; they must not invent a HIREF or change resource type.
- The substitute valid-local smoke passed under the existing local dependency
  environment: bundle helper demo -> local preserved the demo SHA; the bundled
  valid Workbook imported to local, local source export succeeded, and that
  export previewed and confirmed into a second isolated SQLite database. The
  source-month horizon correction preserves actual Allocation/Capacity months
  rather than expanding the workbook from project dates.

## Commit and push status

Uncommitted working-tree changes only. No commit or push was made.

## Final lean artifact

- Fresh artifact: `dist/ip039-source-facts-final-20260809/delivery-manager-usage-lean-v0.2.0rc1.zip`.
  SHA-256 `d50d7b38efb8e5c19991fa45b6640a9c77d5933c093dd8b3efae8ca1b2275268`;
  `641756` bytes. Manifest/archive inspection found exactly one `src/`, the
  root README, only `.github` agent/instructions, workbook/source kits, and a
  read-only synthetic demo DB; forbidden prompt/config/build/dev-data entries
  were absent.
- Offline setup preflight returned `ready_to_install`. The selector helper
  correctly did not run before setup creates `src/.env` (`SETUP_ENV_MISSING`);
  no demo data was mutated. Existing bundle-inclusive focused validation remains
  `38 passed`; no builder source changed since. `make validate` has no terminal
  result and normal online install remains `package_index_unavailable`.

## Core source-context corrective implementation

- The core Team/Project + Capacity/HIREF export now binds solely to the latest
  completed Workbook onboarding source receipt for the selected plan. Its existing
  `source_preview_json` retains the original Setup start/end and whether/how
  many Capacity rows were supplied, with the exact source Capacity package ID.
  It reads no publication link, current-state, contract-coverage, freshness,
  derivation, or audit-history data. A corrupt/incomplete newest receipt fails
  as source-context invalid and never falls back to an older receipt.
  Equal receipt timestamps use SQLite insertion order, and boolean Capacity
  row counts are rejected.
- The preserved Setup range is emitted exactly. A later valid Workbook source
  with no Capacity rows exports none, while a missing or corrupt referenced
  package returns a stable source error without falling back to an earlier
  Capacity session. Facts outside the source Setup range fail closed.
- Export now preserves only exact `active`/`inactive` employee status facts;
  unsupported canonical statuses fail with
  `WORKBOOK_EXPORT_MEMBER_STATUS_UNSUPPORTED`. The temporary derived export
  functions in current-state staffing, contract coverage, workforce planning,
  and resource capacity were removed.
- Focused synthetic evidence: `65 passed` for workbook onboarding and workforce
  source-reader coverage, including zero-Capacity currentness, missing/corrupt
  current Capacity package, exact sparse 09..12 Setup horizon, status failure,
  and existing valid export → preview → confirm with HIREF open demand.
  Targeted Ruff passes. The final `git diff --check` is run after the EOF
  correction; independent re-review remains required. No full validation,
  rehearsal, build, commit, push, release, connector, or real-data action was
  performed in this corrective pass.

## Auxiliary source-export subsection (separate from core workbook correction)

- Added `pm onboarding export-source` for the existing
  `project-profile-workbook`, `jira-board-registry-csv`, and
  `confluence-page-registry-csv` contracts. Each owner exports only editable
  facts: project profile rows joined to project identity, JIRA board mapping
  rows, or non-global Confluence page mappings. It does not read derived
  snapshots, sync/audit history, publication state, freshness, or credentials.
- Exports use a same-directory temporary file, create-if-absent no-overwrite
  protection, explicit overwrite, source-format suffix checks, and structured
  one-line JSON metadata. Confluence deliberately emits blank sync timestamps
  and content summary because they are not reusable source facts; JIRA retains
  only its contract-defined local mapping fields.
- Bundle composition now adds `sources/` with a concise source guide,
  header-only Project Profile/JIRA/Confluence templates, existing synthetic
  samples, and generated Copilot export → edit → preview → explicit confirm
  routing.
- Focused auxiliary validation: `35 passed` via
  `src/.venv/bin/python -m pytest -q src/tests/test_onboarding_source_exports.py src/tests/test_auxiliary_onboarding_importers.py src/tests/test_registry_importers.py tools/tests/test_build_usage_bundle.py`; targeted Ruff and `git diff --check` passed. Independent read-only review remains required.

### Auxiliary review correction

- Each auxiliary owner now self-validates its temporary output through its
  existing parser and preview handler, then compares parser-normalized exported
  facts to the source facts before atomic finalization. This remains read-only;
  none of the preview handlers persisted data during the correction.
- Project Profile rejects malformed/lossy JSON and noncanonical priority/focus
  values; JIRA rejects boolean values outside canonical `0`/`1` and values its
  parser would normalize; Confluence rejects duplicate board mappings that
  `_desired_pages` would collapse and fields the parser would default/change.
  Each failure returns a source-specific safe code and leaves no final output.
- Focused correction validation: `38 passed` across source export, existing
  importer, registry, and bundle tests; targeted Ruff and `git diff --check`
  passed. No full validation/rehearsal, commit, push, release, connector, or
  real-data action occurred.
