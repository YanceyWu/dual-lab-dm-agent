# IP-000 Implementation Report

Status: `PARTIAL — G0 NOT YET PASSED (THIRD SLICE COMPLETE)`
Branch: `codex/ip-000-baseline-safety`
Date: 2026-07-19

## Outcome

The first IP-000 slice is implemented locally. Private runtime state is protected
by ignore rules and a path-only Git preflight. The current automated suite runs
in an ignored Python 3.12 environment with temporary databases and default
network denial. No production business logic, schema, connector, CLI, dashboard,
or Copilot instruction was changed.

## Repository boundaries assessed

- Root architecture/governance repository
- Untracked local runtime under `src/`
- Private database and data-feed categories by path only
- Sanitized-sample boundary under `src/sample-data/`
- Local virtual environment under `src/.venv/`

No operational database row or raw export content was inspected.

## Implemented changes

### Repository safety

- Added private-by-default database and SQLite-sidecar ignore patterns.
- Kept synthetic sample paths distinguishable, but transfer-quarantined the
  current sample tree until its contents are explicitly approved.
- Added `tools/check_repository_boundary.py`.
- The preflight examines only Git path metadata.
- Added seven focused preflight unit tests.
- Added a temporary transfer quarantine for runtime source until portability
  review is complete.

### Test isolation

- Added an autouse pytest fixture that redirects every test to a temporary
  database before execution.
- Added default socket-level network denial for the suite.
- Added a focused assertion that the default test database is isolated.
- Repaired one time-fragile fixture by deriving its fresh timestamp at runtime.
  Production freshness logic was unchanged.

### Baseline and governance

- Added the verified current-runtime baseline.
- Added the source portability review and approval process.
- Recorded known staffing-contract and atomic-write limitations without fixing
  them in this pack.

### Synthetic sample reconstruction

- Defined one canonical fictional organization and reserved identifier range.
- Rebuilt all CSV, JSON, and Excel samples from constructed values.
- Rebuilt the demo SQLite database exclusively from those inputs.
- Added a synthetic sample checker covering markers, identifier ranges, email
  domains, URL hosts, workbooks, and the generated demo database.
- Added clean-build semantic characterization for workload, capacity, contracts,
  weekly report, projects, use-case catalog, dashboard summary, and health.
- Added a sheet-contract discovery path so Distribution imports do not depend on
  a personal/team worksheet name.
- Added `connector validate --portable`, which checks module contracts without
  reading or displaying runtime configuration or making network requests.

## Validation results

| Check | Result |
| --- | --- |
| Repository-boundary and synthetic-data unit tests | 12 passed |
| Repository-boundary live preflight | passed |
| Existing/runtime pytest suite | 29 passed |
| Python static compilation | passed |
| Isolated synthetic demo database build | passed |
| Workload smoke command | passed |
| Monthly capacity smoke command | passed |
| HIREF summary smoke command | passed |
| Weekly report smoke command | passed |
| Project list smoke command | passed |
| Use-case catalog smoke command | passed |
| Synthetic sample checker | passed |
| Portable connector validation | passed |
| Clean-build semantic characterization | 6 passed |
| Excel render and formula-error review | passed |

All demo and smoke work used a database under a temporary directory.

## Findings requiring follow-up

### Public-transfer quarantine

The current `src/` checkout contains company-specific or real-looking defaults,
aliases, identifiers, configuration, fixtures, or documentation. It is not safe
to stage or push as a whole. No sensitive value is reproduced here.

### Connector-validation leakage

The existing runtime connector-validation mode prints local/company
configuration details and may return a non-zero result when credentials are
absent. It remains an internal readiness command. The new `--portable` mode is
safe for public smoke validation and deliberately does not claim runtime
readiness.

### Characterization coverage

The suite now covers core bootstrap, allocation, weekly report, HIREF, registry
import, CLI construction, dashboard health triggers, clean demo construction,
workload, monthly capacity, project language, use-case catalog, and offline
dashboard reads. Presentation-specific CLI snapshots remain intentionally out of
scope because semantic assertions are more stable.

### Dependency setup

The project declares Python 3.10 or newer. The system default was Python 3.9, so
the ignored environment was created with bundled Python 3.12. The test-focused
dependency set excludes the optional browser automation package; no browser or
live connector validation was performed.

## Deviations from the pack

- A complete editable installation was not used because the optional browser
  package was large and unnecessary for offline tests. Tests run with
  `PYTHONPATH=src` and the declared compatible dependency ranges.
- Connector validation was attempted once and immediately classified as unsafe
  for portable smoke output because it exposes configuration metadata. No live
  connector request was made.
- Full behavior characterization and demo idempotency evidence remain pending.

## Rollback verification

All implemented changes are confined to ignore rules, preflight tooling, tests,
and documentation. Removing them restores the pre-IP-000 behavior. Operational
files were neither deleted nor modified by this work.

## G0 decision

`NOT PASSED`.

The safe baseline is materially improved, but G0 still requires:

1. unit-by-unit runtime source sanitization/portability approval;
2. approval and versioning of portable runtime changes currently held under the
   source quarantine.

## Owner approval update

On 2026-07-19, the owner approved the reconstructed fictional organization as
the standard public sample dataset. The transfer quarantine is therefore lifted
for `src/sample-data/` only. All other `src/` paths remain quarantined.

## Database-path isolation update

Known module-level database-path caches in the dashboard, health sync, and import
workflows were replaced with call-time resolution. Three focused tests prove that
changing the configured database after import selects the new isolated path. The
full runtime suite now passes 32 tests.

## Source portability audit update

A local audit now reports only affected relative paths and risk categories. It
confirms that runtime source remains blocked by company configuration units,
historical documentation, endpoint defaults/templates, hard-coded identifiers,
and one remaining non-synthetic email-domain fixture. Matched values are never
printed or recorded in this report.

IP-001 must not begin until these items are completed or explicitly accepted as
documented exceptions.

## Portability slice 2 update

- Portable ServiceNow/JIRA endpoints now require explicit local configuration.
- The special Confluence action-tracker page ID and project-alias groups are no
  longer embedded company identifiers.
- The legacy HIREF report reuses the shared deterministic project-alignment
  rule instead of maintaining a second alias table.
- The lightweight seed and touched tests now use the owner-approved fictional
  organization and reserved `99` identifiers.
- A generic `.env.example` now documents local connector configuration without
  storing any endpoint, credential, or company identifier.
- The audit distinguishes public vendor protocol endpoints and URL templates
  from concrete company endpoints.
- Internal company configuration, history, and UAT artifacts have explicit
  permanent non-portable classifications.
- `--portable-only` text audit passes; the full audit remains blocked by design
  when internal-only units are included.
- Current validation: 37 runtime tests and 18 tool tests pass; clean seed and
  demo builds, static compilation, repository boundary, synthetic checker, and
  whitespace checks pass.

G0 remains `NOT PASSED` because portable runtime units have not yet received
manual approval and remain under the Git transfer quarantine.
