# DM Agent Evolution Progress

Last updated: 2026-07-19
Current branch: `codex/ip-000-baseline-safety`
Current implementation pack: `IP-000 — Baseline and Private-State Safety`
Gate status: `G0 PASSED`
Git state: committed locally as `fbc3fc2`; not pushed

## Read this first

This is the cross-session source of truth for ongoing development. Read it before
using chat history or proposing the next implementation step.

## Product direction

- Each Delivery Manager runs the product locally.
- Copilot Agent is the reasoning interface.
- Deterministic Python owns facts, filtering, calculations, validation, and
  persistence.
- SQLite and connectors provide the local operational context.
- Evolution uses strangler migration; no rewrite or multi-agent framework is
  planned.

## Completed

### Architecture and governance

- Defined the Dual-Lab operating model and one-way transfer boundary.
- Created the target Copilot/local-runtime architecture and gated roadmap.
- Added IP-000 plus an implementation report and current runtime baseline.
- Added a mandatory progress-continuity rule to `AGENTS.md`.

### Repository and private-state safety

- Operational databases, exports, credentials, logs, backups, and local virtual
  environments are ignored.
- Added a path-only Git repository-boundary preflight.
- Runtime source remains public-transfer quarantined.
- The preflight currently passes.

### Synthetic standard sample data

- Reconstructed a fictional organization from scratch.
- Standard people use `Example` names; projects are Atlas, Beacon, and Cedar.
- Employee/project-style identifiers use the reserved `99` range.
- URLs and emails use `.invalid` domains.
- Rebuilt CSV, JSON, Excel, and demo SQLite assets.
- Owner approved `src/sample-data/` for future public transfer on 2026-07-19.
- Only `src/sample-data/` is exempt from the runtime-source quarantine.

### Test and demo baseline

- Added default temporary-database isolation and network denial for pytest.
- Fixed a time-fragile freshness test without changing production behavior.
- Added synthetic-data checks and clean demo characterization.
- Added offline `connector validate --portable` behavior locally.
- Runtime pytest: 42 passed.
- Tool/preflight tests: 18 passed.
- Synthetic sample check: passed.
- Static compilation and `git diff --check`: passed.

## Important local-only runtime changes

The following changes exist under the ignored `src/` quarantine and therefore do
not appear in normal Git status:

- pytest always redirects database use to a temporary location and blocks live
  socket connections;
- sample characterization tests build a clean demo database and assert stable
  semantics;
- Distribution Excel import discovers its worksheet by field contract instead
  of a personal/team worksheet name;
- portable connector validation checks connector module contracts without
  reading runtime configuration;
- the synthetic sample dataset and generated demo database were rebuilt.
- database consumers that previously cached the configured path now resolve it
  at call time; focused tests cover post-import path changes.
- connector instance endpoints, report IDs, the optional Confluence action
  tracker page, and project alias groups now require local configuration;
- a portable `.env.example` contract exists with empty endpoint/credential
  values and documented optional settings;
- the lightweight seed and touched runtime tests use Atlas, Beacon, Cedar,
  Example people, and reserved `99` identifiers;
- the HIREF spreadsheet report now reuses the shared configurable project
  alignment rule instead of embedding its own alias table.

Do not assume these changes are versioned until the relevant runtime units pass
portability review and the quarantine is narrowed.

## Current blockers to G0

No open G0 blocker remains. Portable runtime paths are visible to Git while
private state, company configuration, and internal documentation remain ignored.

## Next actions

Execute in this order:

1. Review the G0 evidence and intentionally commit the approved portable paths.
2. Begin IP-001 with one low-risk read-only use case.

## Decisions in force

- `src/sample-data/` is approved for public transfer.
- Other `src/` paths are not approved.
- Runtime connector validation and portable connector validation are distinct.
- G0 must pass before the shared use-case runtime in IP-001 begins.
- Real databases, data feeds, configuration values, and connector output must
  never be copied into this progress log.
- `src/configs/company/` and `src/docs/history/` are permanently internal-only.
- `src/docs/current/*UAT*` is permanently internal-only.
- Public Atlassian OAuth/API endpoints are vendor protocol endpoints, not
  company instance configuration.
- URL templates are allowed by the audit because they do not contain a concrete
  host; runtime connector endpoints still require local configuration.

## Change log

### 2026-07-19 — IP-000 slice 1

- Established private-state ignore rules, boundary preflight, isolated Python
  environment, current runtime baseline, and initial test evidence.

### 2026-07-19 — IP-000 slice 2

- Rebuilt synthetic samples, added the synthetic-data standard and checker,
  added demo characterization, and introduced portable connector validation.

### 2026-07-19 — Sample approval and continuity

- Owner approved the fictional sample organization for public transfer.
- Narrowed quarantine only for `src/sample-data/`.
- Established this progress log as the cross-session source of truth.

### 2026-07-19 — Database path isolation and source audit

- Added call-time database path resolution and removed known module-level path
  caches from dashboard, health sync, and import workflows.
- Added three focused path-isolation tests; full runtime suite reached 32 passed.
- Added a source-portability audit that suppresses matched values and reports
  only relative path plus category.
- Recorded the blocked audit baseline and sanitization sequence.
- Permanently classified company configuration and historical documentation as
  internal-only units.
- Added a Codex memory pointer to this progress file for new-session recovery.

### 2026-07-19 — Endpoint, alias, and fixture portability

- Removed instance-level ServiceNow and JIRA defaults from portable runtime
  paths; report IDs and the optional Confluence action-tracker page are local
  configuration.
- Moved project alias groups to validated local JSON configuration and reused
  the shared deterministic alignment rule in the HIREF report generator.
- Rebuilt the lightweight seed and touched tests with the approved fictional
  organization and added a clean seed regression test.
- Added a portable `.env.example`; real `.env` variants remain protected and
  the example remains under runtime-source quarantine until unit approval.
- Added permanent internal-only handling for current UAT artifacts and a
  `--portable-only` source audit mode.
- Portable-only audit, repository boundary, synthetic checker, seed build, demo
  build, static compilation, 37 runtime tests, and 18 tool tests pass.
- Full source audit remains blocked only by explicitly internal-only company
  configuration, historical documentation, and UAT artifacts.
- Changes remain local, unstaged, uncommitted, and unpushed.

### 2026-07-19 — Generic bootstrap portability approval

- Added a temporary-directory contract test for starter-repository bootstrap:
  first-run artifacts contain only generic defaults and empty connector
  endpoints, while default initialization never rewrites an existing `.env`.
- Manually approved the generic bootstrap unit in the source-portability review;
  this is not approval for the broader runtime tree.
- Validation passed: 39 runtime tests, 18 tool tests, portable-only audit,
  repository boundary, synthetic checker, static compilation, and diff check.
- Changes remain local, unstaged, uncommitted, and unpushed; source quarantine
  remains in force except for `src/sample-data/`.

### 2026-07-19 — Dashboard safety and portability approval

- Changed dashboard and CLI defaults from all-interface binding to loopback-only
  binding; callers may still explicitly select a host when appropriate.
- Added a regression test that fixes both defaults at `127.0.0.1`.
- Manually approved the dashboard surface after terminology and endpoint scans;
  a dedicated source-specific connector branch was instead classified
  `SANITIZE`, with no connector code approved by this entry.
- Validation passed: 40 runtime tests, 18 tool tests, portable-only audit,
  repository boundary, synthetic checker, static compilation, and diff check.
- Changes remain local, unstaged, uncommitted, and unpushed; source quarantine
  remains in force except for `src/sample-data/`.

### 2026-07-19 — Connector portability sanitization

- Removed a dedicated source-specific Confluence discovery branch and made page
  synchronization depend only on locally configured registry rows.
- Restricted Atlassian token discovery to this runtime's local state; removed
  reads from unrelated agent directories.
- Replaced the opaque tracker name with `action_tracker` and added a migration
  that copies legacy local rows before dropping the old table.
- Replaced remaining company-derived CLI examples and touched test identifiers
  with the approved synthetic vocabulary.
- Validation passed: 42 runtime tests, 18 tool tests, portable-only audit,
  repository boundary, synthetic checker, and diff check. Source quarantine
  remains in force pending final path-level approval and narrowing.

### 2026-07-19 — G0 passed

- Approved runtime, scripts, tests, and synthetic samples are now visible to
  Git; private state, company configuration, and internal documentation remain
  ignored.
- Final evidence passed: 42 runtime tests, 18 tool tests, static compilation,
  portable-only audit, repository-boundary check, synthetic-sample check, and
  diff check.
- G0 evidence is committed locally as `fbc3fc2` and remains unpushed. The next
  action is IP-001 planning and implementation on a clean working tree.
