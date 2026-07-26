# DM Agent Evolution Progress

Last updated: 2026-07-26
Current branch: `codex/ip-000-baseline-safety`
Current implementation pack: `IP-025 — Interface Completion`
Gate status: `IP-022 TO IP-025 COMMITTED AND PUSHED — UAT PENDING`
Git state: IP-022 through IP-025 are committed and pushed on `codex/ip-000-baseline-safety`; do not merge into `main`

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

1. Before real-environment use, create a backup and rehearse IP-024 migration on
   an isolated database copy; stop if invalid or duplicate legacy rows are
   reported.
2. Run IP-022 through IP-025 real-environment UAT and record only sanitized
   outcomes.
3. After UAT, assess IP-026 Release Engineering.
3. Preserve all changes for isolated real-environment UAT; do not merge into
   `main`.

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
- G0 evidence is committed locally as `1c151c8` and remains unpushed. The next
  action is IP-001 planning and implementation on a clean working tree.

### 2026-07-19 — IP-001 unified read-only execution slice

- Added versioned `UseCaseRequest` and `UseCaseResult` envelopes plus a
  registry-based `UseCaseExecutor` with generated execution IDs.
- Migrated only `team-workload-overview`, preserving its existing deterministic
  service and CLI Rich rendering.
- The CLI workload overview and Dashboard JSON endpoint now invoke the same
  registered reference implementation; member detail and all other use cases
  remain unmigrated.
- The reference result provides local SQLite evidence and explicitly returns no
  proposed writes. No database schema or write behavior changed.
- Validation passed: 17 focused runtime/interface tests, 46 full runtime tests,
  18 repository tool tests (19 subtests), static compilation, portable-only
  audit, repository-boundary check, synthetic-sample check, and diff check.
  The new IP-001 implementation report records rollback and remaining risks.
- Changes are uncommitted and unpushed. Next action: independent G1 review,
  then prepare IP-002 and IP-003.

### 2026-07-19 — G1 review and G2 pack specification

- Rechecked the IP-001 implementation against its pack and G1 exit criteria:
  CLI and Dashboard reuse the same registered read-only implementation, while
  workload calculation and database schema remain unchanged.
- Recorded the local G1 review separately. It confirms local validation but
  retains human-owner review and an intentional commit as promotion conditions.
- Authored IP-002 for structured read-only Copilot tool transport and IP-003 for
  bounded evidence, freshness, and durable execution traces. Both packs define
  discovery, contracts, acceptance scenarios, non-goals, tests, and rollback.
- Neither G2 pack is implemented or authorized for implementation. The next
  action is owner review of the two pack scopes and acceptance scenarios.

### 2026-07-19 — IP-002 VS Code Copilot interaction clarification

- Clarified the intended IP-002 user experience: a Delivery Manager asks a
  natural-language question or issues an approved command in VS Code Copilot.
  Copilot interprets and normalizes it to the same bounded, read-only tool call.
- Kept the architectural boundary unchanged: Copilot provides interpretation and
  explanation; the local executor owns validation, deterministic workload facts,
  and persistence boundaries. The final VS Code Copilot customization mechanism
  remains a local-discovery decision, not a product-core dependency.

### 2026-07-19 — IP-002 structured Copilot transport

- Added a local `pm tool` JSON transport with read-only `list`, `describe`, and
  `query` operations for `team-workload-overview`; it reuses the IP-001 executor
  and does not calculate workload or permit writes.
- Added use-case descriptors, request operation and correlation-ID metadata, and
  structured invalid/unavailable results. The existing CLI workload renderer and
  Dashboard endpoint remain unchanged.
- Added portable VS Code Copilot repository instructions and a workload prompt.
  They direct natural-language and command-oriented requests to the same
  structured local query rather than direct SQLite inspection or CLI parsing.
- Validation passed: 14 focused tests, 49 full runtime tests, 18 repository
  tool tests (19 subtests), static compilation, portable-only audit,
  repository-boundary check, synthetic-sample check, diff check, and a
  JSON-only demo smoke query through the current module entry point.
- IP-003 remains required for freshness, assumptions, alternatives, evidence
  redaction, and durable execution trace retrieval; G2 is not complete.

### 2026-07-19 — IP-003 evidence, freshness, and execution trace

- Added first-class freshness, assumptions, and alternatives fields to the
  shared result envelope. The workload reference now emits bounded evidence,
  explicit source-state freshness, an active-assignment assumption, and warning
  codes without changing workload calculations.
- Added a local, payload-free `execution_traces` table and executor trace
  retrieval by execution ID. Stored traces contain metadata, safe evidence and
  freshness summaries, warnings, and write counts only; result rows, connector
  configuration, endpoints, credentials, and raw payloads are excluded.
- Mapped the workload reference only to the registered resource-portal and
  skills imports. Missing or never-synced data is `unknown`, failures are
  `unavailable`, and fresh/stale/partial remain distinct.
- Retention is bounded to the 500 most recently completed traces. No existing
  business table or workload calculation changed.
- Validation passed: 26 focused tests, 53 full runtime tests, 18 repository
  tool tests (19 subtests), static compilation, portable-only audit,
  repository-boundary check, synthetic-sample check, and diff check.
- G2 is locally validated but requires owner review and an intentional commit
  before IP-004 assessment.

### 2026-07-19 — Local commit

- Committed the approved IP-001 through IP-003 implementation, documentation,
  Copilot guidance, and test changes locally after all recorded validation
  passed. The branch has not been pushed.

### 2026-07-19 — IP-004 context-package assessment

- Assessed the committed G2 reference result and specified IP-004 around one
  `TeamCapacityContext` for `team-workload-overview` only.
- The context is explicitly current-state only: it uses active-assignment facts
  and does not infer next-week capacity, future plans, or staffing decisions.
- The pack requires deterministic classification, bounded/truncated context,
  source-state propagation, and a VS Code Copilot playbook that explains rather
  than calculates facts.
- IP-004 remains unimplemented and uncommitted. Next action: implement its
  context builder and synthetic scenario coverage without expanding to another
  use case or write path.

### 2026-07-19 — IP-004 team capacity context and Copilot playbook

- Added a deterministic, bounded `TeamCapacityContext` to the workload reference
  result. It reuses existing result facts and does not perform additional data
  access or business calculations.
- Context scope is explicitly `current`, based on active assignments only.
  Members are classified by the existing workload thresholds and limited to 20
  with deterministic sorting and visible truncation.
- Updated the VS Code Copilot workload prompt to use the structured context,
  identify evidence/freshness/assumptions/warnings/execution ID, and qualify any
  non-fresh result before a management commitment.
- Validation passed: 25 focused tests, 54 full runtime tests, 18 repository
  tool tests (19 subtests), static compilation, portable-only audit,
  repository-boundary check, synthetic-sample check, and diff check.
- IP-004 changes are uncommitted and require owner review. IP-005 remains a
  separate future pack for canonical, period-aware staffing facts.

### 2026-07-19 — IP-005 to IP-007 staffing core

- Added a period-aware staffing read model that adapts active members, monthly
  allocation, plan version, skills, and contractor coverage without renaming
  existing tables.
- Added deterministic demand feasibility checks for skills, active status,
  capacity, contract coverage, allocation minimum, splitability, maximum people,
  and total effort. Results expose selected and rejected candidates with reasons.
- Added immutable expiring staffing proposals, preview, confirmation-time
  revalidation, and atomic SQLite persistence of planned assignments, monthly
  allocations, decision log, and proposal status. Repeated confirmation is
  idempotent; changed facts are rejected before domain writes.
- Validation passed: 4 new staffing scenarios, 10 focused regression scenarios,
  58 full runtime tests, 18 repository tool tests (19 subtests), static
  compilation, portable-only audit, repository-boundary check, synthetic-sample
  check, and diff check.
- G3 was not yet claimed at this point; IP-008 provides the remaining scenario
  and manager-confirmation evidence below.

### 2026-07-19 — IP-008 and G3 local validation

- Added a local manager-facing JSON command group for staffing assessment,
  proposal, preview, explicit confirmation, cancellation, and rejection. The
  command group is not a write-capable Copilot transport.
- Added proposal cancellation/rejection, expiry persistence, and rule-version
  evidence. Cancelled, rejected, expired, and changed proposals cannot create
  staffing-domain writes.
- Added 23 synthetic staffing scenarios covering time, effort, skills, contract,
  overload/capacity, split demand, source-state visibility, expiry, cancellation,
  rejection, and changed-fact/idempotency behavior.
- Validation passed: 23 staffing scenarios, 77 full runtime tests, 18 repository
  tool tests (19 subtests), static compilation, portable-only audit,
  repository-boundary check, synthetic-sample check, and diff check.
- G3 is validated locally. Owner review and an intentional commit remain
  required before promotion; next architecture work is IP-009 Project Health.

### 2026-07-19 — IP-004 to IP-008 handoff commit

- Committed and pushed the validated IP-004 through IP-008 implementation on
  `codex/ip-000-baseline-safety`, including the structured workload context,
  staffing read/feasibility/proposal flow, and the G3 scenario evidence.
- The repository is ready for model-agnostic continuation: begin with this
  file, then read the numbered implementation packs and implementation reports
  before modifying the next pack. The operating boundary remains Copilot (or a
  compatible model interface) for reasoning and deterministic local code for
  facts and writes.
- Next recommended action: assess IP-009 Project Health as a separate,
  independently reviewable implementation pack; do not expand the staffing
  write scope without a new contract, scenarios, and tests.

### 2026-07-22 — Batch A G3 technical revalidation

- Re-ran the committed G3 evidence on the current branch: 77 runtime tests,
  18 repository-tool tests (19 subtests), source-portability audit,
  repository-boundary check, synthetic-sample check, and diff check all passed.
- Corrected the record: IP-004 through IP-008 were already committed and
  pushed in `3873edb`; no technical evidence remains that the implementation is
  merely an uncommitted local change.
- G3 remains **technically validated but owner-sign-off pending**. Only a human
  owner may approve the manager-facing confirmation workflow for operational
  use. Do not claim that business acceptance without that explicit decision.

### 2026-07-22 — G3 owner sign-off and Batch B start

- The human owner explicitly approved the G3 staffing workflow for operational
  use after reviewing the technical revalidation record.
- G3 is promoted. Began IP-009 assessment as the first G4, read-only Project
  Health vertical slice; it must not broaden the staffing write scope.

### 2026-07-22 — Batch B IP-009 Project Health reference slice

- Added `project-health-review` to the shared executor and structured local
  tool transport. It adapts active projects, board mappings, latest local JIRA
  health snapshots, Confluence status snapshots, and source freshness without
  triggering a sync or changing domain data.
- The result distinguishes observed RED/AMBER/GREEN states from `unknown` when
  no local evidence exists. It reports component scores, snapshot dates,
  evidence, freshness, assumptions, warnings, rule version, and bounded
  `ProjectHealthContext`; JIRA grade takes precedence over a status-page RAG
  label without hiding the conflicting local observation.
- Validation passed: 79 runtime tests, 18 repository-tool tests (19 subtests),
  static compilation, portable-only audit, repository-boundary check,
  synthetic-sample check, and diff check.
- IP-009 is technically validated and awaits owner review before G4 promotion.

### 2026-07-22 — Batch C IP-010 and IP-012 read-only slices

- Owner approved IP-009 semantics and authorized Batch C.
- Added `management-attention`: deterministic attention ranking from locally
  observed project health, overdue action items, and non-fresh health sources.
  The use case never creates an action or predicts a risk.
- Added `contract-continuity-review`: a bounded review of existing HIREF
  coverage, expiry, next-contract linkage, and project alignment for active
  STFTE staff. It never creates a contract, assignment, proposal, or action.
- Validation passed: 80 runtime tests, 18 repository-tool tests (19 subtests),
  static compilation, portable-only audit, repository-boundary check,
  synthetic-sample check, and diff check.
- Both packs are technically validated and await owner review before G4
  promotion and Batch D assessment.

### 2026-07-22 — G4 owner approval and Batch D start

- The human owner approved the IP-009/IP-010/IP-012 read-only semantics,
  including local-evidence-only behavior and the documented priority rules.
- G4 is promoted. Began IP-011 Weekly DM Brief and IP-013 Action Follow-up;
  both remain read-only structured use cases.

### 2026-07-22 — Batch D implementation

- Added `weekly-dm-brief` and `action-followup` as read-only structured use cases.
- Validation passed: 80 runtime tests, 18 repository-tool tests (19 subtests), static compilation, portability audit, boundary check, synthetic-sample check, and diff check.

### 2026-07-22 — IP-014 connector status reference slice

- Added `connector-status-review`, a credential-free structured view of connector validation, local source freshness, and latest local sync state.
- It performs no connector invocation, sync, network call, or configuration inspection. Validation passed: 80 runtime tests, 18 repository-tool tests (19 subtests), static compilation, and all repository safety checks.

### 2026-07-22 — IP-015 local lifecycle reference

- Added a versioned install, upgrade, validation, recovery, and private-state lifecycle for the existing Poetry package and local backup mechanism.
- No package was published and no operational database/configuration was changed.

### 2026-07-22 — independent release-candidate revalidation

- Revalidated the candidate branch: 80 runtime tests, 18 repository-tool tests
  (19 subtests), portability audit, boundary check, synthetic-sample check, and
  diff check all passed.
- Confirmed `main` has no merge base with this branch. The candidate remains
  independently published on its own branch; no merge, tag, package release,
  backup, or live upgrade was performed.

### 2026-07-22 — IP-016 connector sync-result contract

- Added a credential-free, raw-error-redacted view of the latest local
  connector sync outcome, including freshness, rows, target tables, and retry
  recommendation. Validation passed: 81 runtime tests and all repository
  safety checks.

### 2026-07-22 — real-environment UAT runbook

- Added a portable runbook for isolated setup, backup, local configuration,
  read-only checks, controlled connector/staffing UAT, stop conditions, and
  sanitized feedback.
- It explicitly preserves the independent branch boundary and excludes real
  configuration, records, connector output, screenshots, and logs.

### 2026-07-26 — IP-020 staffing fail-closed safety

- Confirmed with the owner that recorded roles are reference-only because
  cross-functional skills may be more relevant than a job-profile label.
- Clarified HIREF as an SFTE/STFTE project charge-code authorization over a
  start/end period. Staffing now evaluates current plus next/extend HIREF
  coverage against the target project and requested months.
- Owner confirmed that an existing HIREF number means the charge code is usable
  for its recorded project and date range; no separate pending/approved state
  is inferred.
- Missing, mismatched, or partial HIREF no longer disqualifies a candidate.
  Covered options rank first; selecting an option with a gap requires an
  explicit DM action note for submitting/extending HIREF or changing the plan.
- Resource, skill, and HIREF freshness block proposals by default, with a
  deliberate, reason-bearing DM exception. Invalid plan versions and unknown
  target projects remain non-overridable.
- Added a deterministic decision fingerprint and retained safety decisions in
  proposal evidence and the confirmed decision log. Pre-IP-020 proposals must
  be recreated before confirmation.
- Validation passed: 34 focused staffing tests, 93 runtime tests, 18 repository
  tool tests (19 subtests), touched-file Ruff, static compilation,
  portable-only audit, repository-boundary check, synthetic-sample check, and
  diff check.
- Owner approved IP-020 for commit on 2026-07-26. The implementation is
  committed locally and remains unpushed; do not merge it into `main`.
- Exact next action: assess IP-021 read-only connector contract repair, while
  preserving IP-020 for real-environment staffing UAT.

### 2026-07-26 — IP-021 read-only connector contract repair

- Removed runtime connector validation from `connector-status-review`,
  `pm connector status`, and `pm connector list`. These paths now use only
  portable module metadata and local source/sync records, and explicitly report
  that runtime readiness was not probed.
- Added an explicit, single-connector `pm connector probe` command with bounded
  JSON output. It does not expose endpoints, credentials, cloud IDs, token
  paths, or raw validation errors.
- Owner specified that OAuth refresh should be automatic and low-friction. JIRA
  and Confluence probes now report `token_refreshed=true` and
  `OAUTH_TOKEN_AUTO_REFRESHED` when refresh occurs, including when a later probe
  step fails.
- Preserved detailed `pm connector validate` as a local-only diagnostic
  compatibility command and documented that its output must not be exported
  without sanitization.
- Validation passed: 5 focused connector boundary tests, 98 runtime tests,
  18 repository tool tests (19 subtests), touched-file Ruff, static compilation,
  portable-only audit, repository-boundary check, synthetic-sample check, and
  diff check.
- Owner approved IP-021 for commit on 2026-07-26. The implementation is
  committed locally and remains unpushed; do not merge it into `main`.
- Exact next action: assess IP-022 Dashboard Write Boundary.

### 2026-07-26 — workspace Delivery Manager custom agent

- Added a VS Code workspace custom agent that maps common Delivery Manager
  intents directly to the approved structured read-only commands, avoiding
  repeated catalogue/schema calls when the route is already known.
- Limited the agent to terminal execution and disabled subagent invocation; it
  has no source-editing or web tool.
- Defined the staffing assess/propose/preview/confirm boundary, non-fresh and
  HIREF decision ownership, explicit-only connector probing, structured-result
  handling, and a handoff to the standard coding agent for platform changes.
- Updated repository-wide Copilot guidance and the real-environment UAT setup
  to select and verify the workspace agent while keeping terminal approvals.
- Added contract tests requiring every registered structured use case to remain
  represented in the Agent and preserving its terminal-only, no-subagent tool
  boundary.
- Validation passed: DM Agent structure/route inventory, 100 runtime tests,
  18 repository tool tests, portable-only audit, repository-boundary check,
  synthetic-sample check, and diff check.
- Owner approved the customization for commit and push on 2026-07-26.
- The customization is committed and pushed with IP-020 and IP-021 on the
  current branch. It remains separate from `main`.
- Exact next action: assess IP-022 Dashboard Write Boundary.

### 2026-07-26 — IP-022 Dashboard write boundary

- Replaced the direct project-health sync POST with a two-stage preview and
  confirmation workflow. Preview selects exact active/stale board targets
  without invoking a connector.
- Added short-lived one-time confirmation tokens stored only as hashes, atomic
  claim/replay protection, actor and immutable scope recording, safe result
  codes, and durable Dashboard operation audit state.
- Removed raw sync output and exception strings from browser responses.
- Non-loopback Dashboard binding now requires explicit operator opt-in.
- Validation passed: 5 focused Dashboard tests, touched-file Ruff, and diff
  check. No network or real operational data was used.
- Changes are local, uncommitted, and unpushed. Exact next action: implement
  IP-023 executor contract enforcement.

### 2026-07-26 — IP-023 executor contract enforcement

- Added executor-level enforcement for parameter types, required fields,
  unknown fields, numeric ranges, enums, lengths, contract version, and safe
  correlation IDs. Invalid input does not invoke the handler.
- Read-only classification now comes from the registered use-case descriptor
  rather than confirmation-token presence.
- Added stable structured error codes and safe exception categories without raw
  error text.
- Validation passed: 25 focused contract/connector tests, touched-file Ruff,
  and diff check.
- Changes are local, uncommitted, and unpushed. Exact next action: implement
  IP-024 data-integrity and concurrency protections.

### 2026-07-26 — IP-024 data integrity and concurrency

- Added database checks for valid months and allocation bounds plus uniqueness
  for employee/project/month/plan-version rows. Placeholder allocations and
  assignment allocation use the same hard limits.
- Staffing confirmation tokens are now stored only as hashes, with a tested
  legacy-token migration. Critical proposal timestamps are timezone-aware UTC.
- Confirmation uses an immediate transaction, conditional state claim, and
  aggregate member-period capacity guard. A concurrent race test proves only
  one conflicting proposal can commit and no partial decision is retained.
- Legacy migration validates dirty values and duplicates before rebuilding; a
  test proves invalid legacy rows stop without modifying the source table.
- Validation passed: 41 focused staffing/integrity/migration tests,
  touched-file Ruff, and diff check.
- Changes are local, uncommitted, and unpushed. Exact next action: implement
  IP-025 interface completion.

### 2026-07-26 — IP-025 interface completion

- Added repeatable generic CLI `--param key=value` input with JSON value
  decoding and duplicate/collision rejection.
- Added a generic read-only Dashboard executor endpoint returning the complete
  result contract. Write-capable descriptors are not allowed through it.
- Preserved legacy Dashboard payloads while marking direct-SQL routes and
  envelope projections in response headers for incremental migration.
- Added CLI/Dashboard/direct-executor equivalence tests and updated the DM Agent,
  README, and UAT commands for generic snapshot filters.
- Combined validation for IP-022 through IP-025 passed: 113 runtime tests,
  18 repository tool tests, touched-file Ruff, static compilation,
  portable-only audit, repository-boundary check, synthetic-sample check, and
  diff check.
- No live network, connector, database, configuration, or real record was used.
  The owner authorized commit and push on 2026-07-26.
- IP-022 through IP-025 are committed and pushed on the current branch and
  remain separate from `main`.
- Exact next action: isolated-copy migration and real-environment UAT before
  assessing IP-026 Release Engineering.
