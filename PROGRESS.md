# DM Agent Evolution Progress

Last updated: 2026-07-30
Current branch: `codex/phase-4-project-health-design`
Current cleanup commit: `c068beb`
Package version: `0.2.0rc1`
Current implementation pack: `IP-030 — PHASE 4 SEVEN-DIMENSION PROJECT HEALTH`
Gate status: `PHASE 4 DESIGN PROPOSED — OWNER REVIEW REQUIRED`
Git state: independent branch is based on exact validated commit `a272890`;
the planning, Phase 1, and Phase 2 Batch A design commit chain through this
continuity record is pushed to and tracks
`origin/codex/phase-1-intelligence-contract`. The exact remote HEAD is
verified in the task handoff because a commit cannot embed its own final hash.
The approved Phase 2 implementation branch, including the accepted Batch B
result, review corrections, Batch C design handoff, accepted Batch C1
implementation and corrections, and technically validated but product-rejected
Batch C2 mapping implementation at `71d90d3`, is local-only and has no remote
tracking branch. The exact current commit is reported in the task handoff
because a commit cannot embed its own final hash. Do not push it without a
separate authorization. Do not merge or push to `main`.
The dedicated Phase 3 branch is also local-only and has no remote tracking
branch. Batch B2 is committed locally for review and has not been pushed.

## Read this first

This file is the current-state source of truth. Historical intermediate states
belong in Git history and must not be interpreted as current instructions.

## Current product

- Each Delivery Manager installs and runs the product locally.
- VS Code Copilot's `Delivery Manager` custom agent is the reasoning interface.
- Deterministic Python owns facts, filtering, calculations, validation,
  freshness, evidence, execution traces, and persistence.
- SQLite and locally configured connectors provide operational context.
- The architecture is a modular monolith with one structured agent interface;
  no embedded LLM or multi-agent runtime is planned.
- Read-only management use cases cover workload, project health, management
  attention, contract continuity, weekly brief, actions, connector status,
  connector sync results, and project snapshots.
- Staffing supports deterministic assessment and
  propose/preview/confirm/persist writes. Role is reference context rather than
  a hard eligibility constraint. HIREF number plus its project/date interval
  represents usable charge-code coverage.
- Dashboard writes use preview, explicit confirmation, one-time tokens,
  idempotency, and audit records.
- Database bootstrap owns idempotent migrations, integrity constraints,
  concurrency protection, hashed confirmation tokens, and dependent-view
  preservation.
- The recorded post-candidate evolution sequence is Phase 0 baseline proof,
  Intelligence contract, Attention, execution signals, Project Health,
  Resource Intelligence, Weekly Brief, Forecast, Simulation, and integrated
  release validation.
- The owner approved this sequence and its standard delivery gates on
  2026-07-27. The approval does not authorize Phase 1 implementation or any
  release, environment, connector, or real-data action.
- The owner accepted exact commit `a272890` as the development evolution
  baseline and deferred the `0.2.0rc1` tag, isolated operational-copy rehearsal,
  and real-environment UAT until the integrated candidate is ready. This is not
  operational or production approval.
- The owner approved the bounded Phase 1 intelligence output contract on
  2026-07-27. This authorizes sequential Phase 1 implementation beginning with
  Batch B1, not Phase 2 or any release/environment action.
- The owner promoted Phase 1 on 2026-07-28 after Batch D validation, synthetic
  installed-package upgrade/rollback rehearsal, portable review, schema review,
  and the IP-027 implementation report passed. This is a local development
  baseline, not release, remote, operational, or Phase 2 implementation
  approval.
- Each phase requires current-state inspection, bounded design approval, small
  implementation batches, focused tests, full regression, and explicit
  promotion before the next phase begins.
- The owner accepted the corrected IP-028 Batch B implementation and the
  implementation-level Batch C design review on 2026-07-28. Only Batch C1 is
  authorized by that decision. Batch C1 was subsequently accepted on
  2026-07-29; Batch C2 DM-operable RAG configuration and Phase 2 promotion
  retain separate gates.
- IP-028 Batch C1 implements the read-only Delivery Attention Center and the
  exact Attention CLI, Dashboard API, and Copilot projections. The owner
  completed review and accepted the corrected result on 2026-07-29. This does
  not authorize Batch C2 or Phase 2 promotion.
- The owner then authorized only IP-028 Batch C2. Its mapping mechanics,
  audited preview/confirm store, and interface projections passed technical
  validation at `71d90d3`, but product review did not accept mapping and source
  precedence as the DM-facing health configuration abstraction. The current
  public mapping configuration paths must not be treated as an accepted
  capability.
- The owner requires three distinct health layers: Sprint Execution,
  Release/Milestone, and seven-dimension Project Health. The factor catalog is
  fixed and versioned; the DM configures bounded conditions, thresholds,
  tolerances, windows, applicability, and approved same-layer weights.
- Story Point evidence belongs to Sprint execution and qualifying Release
  scope analysis. Missing Story Points are unavailable evidence, never a
  fabricated neutral score. Milestone and Release commitments become canonical
  Phase 3 facts, feed Phase 4 Project Health, and are reused by Phase 7
  Forecast.
- The owner approved the layered health and milestone architecture on
  2026-07-29. The bounded C2 correction removes the CLI, Dashboard, and Copilot
  mapping preview paths, rejects direct preview and legacy-token confirmation,
  removes dormant configuration mutation helpers, and retains additive storage
  unchanged. Technical re-review found no remaining P0-P2 issue. The owner
  accepted the correction and authorized the next Batch D step on 2026-07-29.
- Phase 2 Batch D focused regression, full validation, schema/portable review,
  and synthetic installed-package upgrade/rollback rehearsal passed. Phase 2
  Batch D Review was completed and accepted on 2026-07-29. The owner then
  promoted the completed implementation as the local Phase 2 development
  baseline. Phase 3/4 runtime remains unauthorized.
- The owner selected automatic system resolution for complete clear
  reconciliation: Attention is decision support, not manager supervision.
  No manager resolve command is exposed; acknowledgement and snooze remain
  optional assistance rather than mandatory closure work.
- Phase 3 current-state review confirmed that the current Jira path stores
  mutable Release Version, Issue, and Sprint snapshots plus legacy health
  scores, but no Issue changelog, Issue Link, temporal scope membership,
  canonical Release commitment, canonical Milestone, or canonical Dependency.
  The Phase 3 design is recorded in
  `architecture/09_PHASE_3_EXECUTION_AND_MILESTONE_FOUNDATION_DESIGN.md` and
  was approved by the owner on 2026-07-29. IP-029 is registered on dedicated
  branch `codex/phase-3-execution-signals`. The owner authorized only Batch B1,
  whose bounded incremental source-evidence implementation and two correction
  rounds were accepted by the owner on 2026-07-29. The owner asked to enter the
  next stage; the owner then authorized only B2 implementation. The owner
  completed B2 re-review and accepted the corrected result. The owner then
  authorized only C1 implementation. The owner completed C1 review and accepted
  the result; C2 and D reviews have passed, and the owner promoted Phase 3 as
  the local development baseline. Phase 4 and all external actions remain
  separately unauthorized. The owner then requested the Phase 4 design only;
  IP-030 is drafted on its dedicated local branch. No Phase 4 implementation is
  authorized.

## Current validation evidence

The pre-cleanup `c2c0b16` candidate passed:

- 115 isolated runtime tests;
- 21 repository-tool tests, including 19 repository-boundary subtests;
- pinned validation-tool verification;
- portable Ruff and static compilation;
- repository-boundary and synthetic-sample checks;
- wheel/sdist build and packaged Dashboard asset checks;
- synthetic wheel installation, isolated database migration, integrity checks,
  dependent-view preservation, aggregate-count preservation, and rollback;
- GitHub Actions on Python 3.10 and 3.12.

The uncommitted documentation/context cleanup also passed `make validate` and
`make rehearse-release`: 115 runtime tests, 21 repository-tool tests, Ruff,
compilation, boundary and synthetic checks, package build/inspection, temporary
wheel installation, isolated synthetic database upgrade, and rollback.

The exact pushed candidate HEAD
`a272890a7b51856c033df69b5148bc8c2fa928da` passed GitHub Actions workflow
`Validate release candidate` in run `30189452632` on 2026-07-26. Both
`validate (3.10)` and `validate (3.12)` completed successfully, including
unified validation and installed-product upgrade/rollback rehearsal.

After the development-baseline decision and UAT deferral were recorded, the
independent planning branch passed `make validate`: repository boundary,
synthetic samples, 115 runtime tests, 21 repository-tool tests with 19 subtests,
Ruff, compilation, diff check, package build/inspection, and eight release
validation checks.

The Phase 1 Batch A design working tree based on `f40f940` passed the same
`make validate` suite, including 115 runtime tests, 21 repository-tool tests
with 19 subtests, and package/release validation. No runtime or schema file
changed in this batch.

The owner-approval record based on `fdb50a3` also passed `make validate` with
the same test counts and eight release validation checks.

Phase 1 Batch B1 passed its focused contract suite with 20 tests. The final
`make validate` run passed repository-boundary and synthetic-sample checks,
135 runtime tests, 21 repository-tool tests with 19 subtests, Ruff, compilation,
diff hygiene, package build/inspection, and all eight release validation
checks. No database or schema path changed from `3d40633`.

The Batch B1 review corrections passed 23 focused contract tests. The final
post-correction `make validate` run passed repository-boundary and
synthetic-sample checks, 138 runtime tests, 21 repository-tool tests with
19 subtests, Ruff, compilation, diff hygiene, package build/inspection, and all
eight release validation checks. No database or schema path changed.

Phase 1 Batch B2 passed 27 focused contract/discovery/transport tests. The
final `make validate` run passed repository-boundary and synthetic-sample
checks, 142 runtime tests, 21 repository-tool tests with 19 subtests, Ruff,
compilation, diff hygiene, package build/inspection, and all eight release
validation checks. No database or schema path changed.

The Batch B2 review corrections passed 30 focused contract/discovery/transport
tests. The final `make validate` run passed repository-boundary and
synthetic-sample checks, 145 runtime tests, 21 repository-tool tests with
19 subtests, Ruff, compilation, diff hygiene, package build/inspection, and all
eight release validation checks. No database or schema path changed.

Phase 1 Batch C passed 40 focused contract/discovery/Management
Attention/Copilot tests. The final `make validate` run passed
repository-boundary and synthetic-sample checks, 153 runtime tests,
21 repository-tool tests with 19 subtests, Ruff, compilation, diff hygiene,
package build/inspection, and all eight release validation checks. No database
or schema path changed.

Phase 1 Batch D passed 63 combined focused contract, discovery, transport,
Management Attention, Copilot, unified-use-case, and legacy-compatibility
tests. `make validate` passed repository-boundary and synthetic-sample checks,
153 runtime tests, 21 repository-tool tests with 19 subtests, Ruff,
compilation, diff hygiene, package build/inspection, and all eight release
validation checks. `make rehearse-release` passed temporary wheel installation,
isolated synthetic database upgrade, integrity checks, and rollback. No
database or schema path changed.

Phase 2 Batch B passed 8 focused Attention foundation tests and 46 combined
Attention/database/bootstrap/Management Attention regression tests. The final
`make validate` run passed repository-boundary and synthetic-sample checks,
161 runtime tests, 21 repository-tool tests with 19 subtests, Ruff,
compilation, diff hygiene, package build/inspection, and all eight release
validation checks.

The Phase 2 Batch B review corrections passed 11 focused Attention foundation
tests and 49 combined Attention/database/bootstrap/Management Attention/
unified-contract regression tests. The final `make validate` run passed
repository-boundary and synthetic-sample checks, 164 runtime tests,
21 repository-tool tests with 19 subtests, Ruff, compilation, diff hygiene,
package build/inspection, and all eight release validation checks.

The follow-up Batch B review corrections passed 13 focused Attention foundation
tests and 51 combined Attention/database/bootstrap/Management Attention/
unified-contract regression tests. The final `make validate` run passed
repository-boundary and synthetic-sample checks, 166 runtime tests,
21 repository-tool tests with 19 subtests, Ruff, compilation, diff hygiene,
package build/inspection, and all eight release validation checks.

The partial-evaluation deduplication correction passed 14 focused Attention
foundation tests and 52 combined Attention/database/bootstrap/Management
Attention/unified-contract regression tests. The final `make validate` run
passed repository-boundary and synthetic-sample checks, 167 runtime tests,
21 repository-tool tests with 19 subtests, Ruff, compilation, diff hygiene,
package build/inspection, and all eight release validation checks.

The Batch C design-review handoff passed `make validate` with
repository-boundary and synthetic-sample checks, 167 runtime tests,
21 repository-tool tests with 19 subtests, Ruff, compilation, diff hygiene,
package build/inspection, and all eight release validation checks. The
handoff changes only architecture, implementation-pack, index, and continuity
documentation.

Phase 2 Batch C1 passed 69 combined focused Attention Center, foundation,
discovery, Management Attention, unified-contract, CLI-build, and Copilot-agent
tests. The final `make validate` run passed repository-boundary and
synthetic-sample checks, 174 runtime tests, 21 repository-tool tests with
19 subtests, Ruff, compilation, diff hygiene, package build/inspection, and
all eight release validation checks. No schema or migration changed in C1, and
`make rehearse-release` remains deliberately deferred to Batch D.

The Batch C1 review corrections passed 71 combined focused tests. The final
`make validate` run passed repository-boundary and synthetic-sample checks,
176 runtime tests, 21 repository-tool tests with 19 subtests, Ruff,
compilation, diff hygiene, package build/inspection, and all eight release
validation checks.

Phase 2 Batch C2 passed 82 combined focused Attention configuration, Center,
foundation, discovery, Management Attention, unified-contract, CLI-build, and
Copilot-agent tests. The final `make validate` run passed repository-boundary
and synthetic-sample checks, 187 runtime tests, 21 repository-tool tests with
19 subtests, Ruff, compilation, diff hygiene, package build/inspection, and
all eight release validation checks. `make rehearse-release` remains
deliberately deferred to Batch D.

The layered health and milestone documentation revision passed
`make validate` without runtime or schema changes: repository-boundary and
synthetic-sample checks, 187 runtime tests, 21 repository-tool tests with
19 subtests, Ruff, compilation, diff hygiene, package build/inspection, and
all eight release validation checks.

The documentation-only layered health design approval record passed the same
`make validate` suite: 187 runtime tests, 21 repository-tool tests with
19 subtests, repository-boundary and synthetic-sample checks, Ruff,
compilation, diff hygiene, package build/inspection, and all eight release
validation checks.

The bounded C2 correction passed 92 focused Attention configuration, Center,
foundation, Management Attention, agent, discovery, and unified-contract
tests. `make validate` passed repository-boundary and synthetic-sample checks,
182 runtime tests, 21 repository-tool tests with 19 subtests, Ruff,
compilation, diff hygiene, package build/inspection, and all eight release
validation checks.

The C2 mutation-boundary review fix passed 93 focused tests across the same
configuration, Center, foundation, Management Attention, agent, discovery, and
unified-contract scope. `make validate` passed repository-boundary and
synthetic-sample checks, 183 runtime tests, 21 repository-tool tests with
19 subtests, Ruff, compilation, diff hygiene, package build/inspection, and
all eight release validation checks.

Phase 2 Batch D passed 109 combined focused tests covering Attention rules,
storage, reconciliation, lifecycle, Center projections, retained
configuration storage, public-interface rejection, migration, concurrency,
Management Attention, `UseCaseResult 1.0`, discovery, CLI build, and Copilot.
`make validate` passed repository-boundary and synthetic-sample checks,
183 runtime tests, 21 repository-tool tests with 19 subtests, Ruff,
compilation, diff hygiene, package build/inspection, and all eight release
validation checks. `make rehearse-release` passed temporary wheel
installation, isolated synthetic database upgrade, integrity checks, installed
behavior, and rollback.

Phase 3 Batch B1 passed 70 combined focused and compatibility tests covering
additive bootstrap, compound cursor/replay behavior, page coverage,
idempotency, partial-state retention, authoritative-manifest tombstones,
multiple Fix Versions, directed and unsupported Issue Links, concurrency,
registry cleanup, legacy Jira/Project Health, Attention, Management Attention,
Dashboard sync confirmation, and `UseCaseResult 1.0`. The final
`make validate` run passed repository-boundary and synthetic-sample checks,
191 runtime tests, 21 repository-tool tests with 19 subtests, Ruff,
compilation, diff hygiene, package build/inspection, and all eight release
validation checks. `make rehearse-release` passed temporary wheel
installation, additive synthetic legacy-database upgrade, installed Phase 3
evidence publication, integrity/count/view checks, and rollback.

The Phase 3 Batch B1 Review corrections passed 76 combined focused and
compatibility tests. They cover stale parallel-run rejection, compound-cursor
monotonicity, authoritative-manifest isolation, ISO timestamp validation,
malformed Issue/changelog partial coverage, unexpected-failure audit,
cross-call repeated-page idempotency, connector-local configuration
preservation, and the original B1/legacy compatibility scope. The final
`make validate` run passed repository-boundary and synthetic-sample checks,
197 runtime tests, 21 repository-tool tests with 19 subtests, Ruff,
compilation, diff hygiene, package build/inspection, and all eight release
validation checks. The expanded `make rehearse-release` passed installed clean
bootstrap, populated synthetic legacy upgrade, successful evidence
publication, rejected partial staged-run retention, prior-cursor preservation,
integrity/count/view checks, and rollback.

The Phase 3 Batch B1 second-review corrections passed 22 focused source-evidence
and registry tests. They require stable Issue Link source references, reject
missing or conflicting link identity as partial coverage, canonicalize mirrored
Jira inward/outward observations, deduplicate the same relationship across
unrelated Issue timestamp changes, and extract Jira `statusCategory.key`
without substituting the status ID. The final `make validate` run passed
repository-boundary and synthetic-sample checks, 203 runtime tests, 21
repository-tool tests with 19 subtests, Ruff, compilation, diff hygiene,
package build/inspection, and all eight release validation checks.
`make rehearse-release` passed installed clean bootstrap, populated synthetic
legacy upgrade, complete and partial evidence behavior, integrity/count/view
checks, and rollback.

Phase 3 Batch B2 passed 8 focused synthetic canonicalization and Milestone
operation tests. They cover additive storage, source-identity mapping,
authoritative and non-authoritative derivation, idempotency, temporal scope
closure only from an authoritative manifest, structured Milestone
preview/confirm/no-op/stale rejection, first-observed target preservation, and
explicit Milestone/Release links. The final `make validate` run passed
repository-boundary and synthetic-sample checks, 211 runtime tests, 21
repository-tool tests with 19 subtests, Ruff, compilation, diff hygiene,
package build/inspection, and all eight release validation checks.
`make rehearse-release` passed installed clean bootstrap, populated synthetic
legacy upgrade, Phase 3 evidence behavior, B2 canonical schema presence,
integrity/count/view checks, and rollback.

The Phase 3 Batch B2 review corrections passed 12 focused synthetic tests.
They cover legacy-snapshot derivation input changes, Release scope movement,
Sprint scope membership, authoritative Issue Link removal, hash-expiring
Milestone confirmation, and fail-closed rejection of unpersisted dependency
references. The final `make validate` run passed repository-boundary and
synthetic-sample checks, 215 runtime tests, 21 repository-tool tests with 19
subtests, Ruff, compilation, diff hygiene, package build/inspection, and all
eight release validation checks. `make rehearse-release` again passed wheel
installation, isolated bootstrap/upgrade, integrity/count/view checks, and
rollback.

Phase 3 Batch C1 passed 9 focused execution-review, discovery, CLI, and
Dashboard Tool Transport tests. The final `make validate` run passed
repository-boundary and synthetic-sample checks, 217 runtime tests, 21
repository-tool tests with 19 subtests, Ruff, compilation, diff hygiene,
package build/inspection, and all eight release validation checks. C1 changes
no schema or installed behavior, so release rehearsal remains a later Batch D
gate.

Phase 3 Batch C2 passed 37 focused execution-foundation and Attention tests.
They cover the sole enabled producer, automatic critical-overdue creation,
automatic rule-clear resolution, partial retention, the complete
history-and-links publication boundary, and durable failure warnings without
cursor rollback. The final `make validate` run passed repository-boundary and
synthetic-sample checks, 219 runtime tests, 21 repository-tool tests with 19
subtests, Ruff, compilation, diff hygiene, package build/inspection, and all
eight release validation checks. `make rehearse-release` passed wheel
installation plus isolated bootstrap, upgrade, integrity, and rollback.

## Portability and data boundary

- The currently tracked runtime, tests, generic configuration examples,
  synthetic samples, tools, and documentation form the portable candidate.
- Repository checks exclude operational databases, exports, credentials,
  authentication caches, logs, backups, local environments, company
  configuration, internal documentation, and real records.
- Work-computer endpoints, credentials, database paths, source identifiers, and
  real records remain local and ignored.
- No company-derived content may be copied back without manual sanitization and
  policy approval.

## Open gates and risks

1. Historical IP-000 through IP-023 and IP-025 packs/reports were deliberately
   removed from the candidate checkout; Git history remains the archive.
2. Annotated tag `v0.2.0-rc.1` remains absent. Tagging and the current
   real-environment UAT flow are deliberately deferred rather than passed.
3. `docs/REAL_ENVIRONMENT_UAT_RUNBOOK.md` is retained as safety reference but
   must be revised and approved against the integrated candidate before use.
4. No branch may be merged or pushed to `main` under the current authorization.
5. IP-027 Phase 1 is promoted locally on its dedicated branch. Management Attention
   now intentionally duplicates existing returned-item meaning into the new
   typed intelligence projection while preserving legacy `data`; later
   maintenance must keep the single deterministic mapper and legacy projection
   aligned. Consumers that assume an exact legacy JSON key set remain a
   compatibility risk outside the repository.
6. Phase 1 commits remain unpushed, so remote CI status for this implementation
   is unknown. Local validation and synthetic release rehearsal are green.
7. IP-028 Batch B and its review corrections are implemented, validated, and
   accepted locally. Batch C1 and its bounded review corrections are
   implemented and locally validated with reconciliation coverage, lifecycle
   no-op protection, exact interface projections, bounded history, and
   advisory recommendations. The owner accepted the corrected C1 result on
   2026-07-29. The completed Phase 2 implementation is promoted locally.
8. Batch C2's mapping-oriented product contract was not accepted. The bounded
   correction removes its CLI, Dashboard, and Copilot preview paths, rejects
   direct preview and legacy configuration confirmation with
   `ATTENTION_RAG_CONFIGURATION_UNAVAILABLE`, and retains the additive
   configuration-operation table and existing records. The review correction
   also removes dormant configuration-operation and rule-version mutation
   helpers. Technical re-review passed and the owner accepted the correction.
9. The layered health architecture and bounded Phase 3
   execution/milestone foundation design are approved. Phase 3 owns
   canonical Milestone/Release commitment facts; Phase 4 owns bounded DM
   conditions and Project Health; Phase 7 reuses promoted Milestone history.
   IP-029 Batch B1 and its first- and second-review corrections are implemented,
   locally validated, and accepted. The B2 implementation-level design is ready
   for review; B2 coding is not yet authorized.
10. Phase 2 is promoted only as a local development baseline. Remote CI for
    the local Phase 2 commits remains unknown. Connector work, real data,
    visual Dashboard Center UI, push, and operational promotion remain blocked
    pending their own gates.
11. Batch B1 Jira acquisition is validated only with synthetic sessions.
    Company-specific field IDs, supported link types, and live API behavior
    remain `UNKNOWN`; the registered evidence source intentionally starts with
    empty field mappings. Incremental acquisition never claims an
    authoritative full manifest, so removal/tombstone transitions require a
    separately complete authoritative manifest through the publication
    contract.

## Exact next actions

1. Review the frozen IP-029 B2 canonical execution/commitment design and decide
   whether to authorize bounded B2 implementation or require design changes.
2. Do not begin B2 canonical storage, derivation, or structured Milestone import
   without that separate explicit implementation authorization.
3. Do not begin Phase 3 milestone runtime, Phase 4 health configuration,
   visual Dashboard UI, connectors, real-data work, release, tag, merge, or
   push without separate authorization.

## Decisions in force

- Do not merge or rebase this independent branch into `main`.
- Do not push any current work to `main`; use independent `codex/` branches.
- Do not create, move, or push a release tag without explicit owner approval.
- Treat the current UAT runbook as deferred reference until it is revised and
  approved for the integrated Delivery Intelligence candidate.
- Do not run migration first against an active operational database.
- Connector probing or sync requires an explicit request and approved local
  configuration.
- OAuth refresh is automatic and invisible except for safe status metadata.
- Missing or non-fresh facts remain visible; the model must not infer zero,
  healthy, available, or safe.
- All writes follow propose, preview, confirm, persist.
- New Delivery Intelligence capabilities follow
  `architecture/05_DELIVERY_INTELLIGENCE_EVOLUTION_PLAN.md`; one phase and one
  bounded outcome are active at a time.
- IP-028 Batch C1 is implemented, validated, reviewed, and accepted under the
  exact approved design and pack contract.
- IP-028 Batch C2 mechanics are implemented and technically validated, but the
  mapping-oriented DM configuration contract is not accepted. Do not expose or
  promote it as an approved capability.
- The layered health and milestone architecture is approved. The bounded C2
  public-interface correction is implemented, locally validated, and passed
  technical re-review. The owner accepted it on 2026-07-29.
- The unaccepted RAG mapping configuration has no supported CLI, Dashboard, or
  Copilot preview path. Direct preview and confirmation of retained legacy
  configuration operations fail with
  `ATTENTION_RAG_CONFIGURATION_UNAVAILABLE`.
- No configuration-operation create/claim/expire/finish/fail helper or
  project-health rule-version mutation helper remains in the runtime.
  Configuration storage and legacy-operation read detection remain intact.
- IP-028 Batch D validation and Review are accepted. The owner promoted the
  result as the local Phase 2 development baseline on 2026-07-29. Promotion
  does not automatically authorize Phase 3 implementation.
- Complete clear reconciliation automatically resolves the Attention item with
  system reason `rule_clear`. Do not require or expose a separate manager
  resolve step; Attention assists management rather than supervising it.
- Project overrides, when later designed for layered health, apply only to
  existing stable-anonymous projects.
- Sprint Execution, Release/Milestone Health, and seven-dimension Project
  Health remain distinct. Story Point absence is unavailable evidence, not
  neutral health.
- Phase 3 owns canonical milestone and Release commitment facts; Phase 4 owns
  bounded DM-configurable health conditions; Phase 7 Forecast reuses promoted
  milestone history.
- The approved Phase 3 design keeps Jira target dates distinct from approved
  commitments, refuses narrative-derived Milestones, separates execution facts
  from health RAG, and recommends automatic post-sync derived reconciliation
  without an extra manager confirmation.
- IP-029 Batch B1 and its first- and second-review corrections are implemented,
  locally validated, and accepted on `codex/phase-3-execution-signals`. The
  owner authorized B2; its bounded canonical execution and Milestone foundation
  is implemented, corrected, reviewed, and accepted. C1/C2/D and all later
  batches remain unauthorized.

## Recent change log

### 2026-07-30 — Phase 3 Batch B2 canonical execution and Milestone foundation implemented

- Added only additive canonical current/observation storage for Work Items,
  source identities, Sprints, Release commitments, temporal scope memberships,
  Milestones, Milestone/Release links, Dependencies, derivation runs/inputs,
  versioned facts, and structured Milestone import operations.
- Added deterministic board derivation from published B1 evidence plus bounded
  legacy snapshots. Complete authoritative manifests may close an open scope
  membership; partial or non-authoritative evidence cannot do so and produces
  unavailable scope facts with explicit warning state.
- Added the non-public `ExecutionFoundationService` for focused derivation and
  structured Milestone preview/confirm only. Imports validate existing projects
  and explicit Release links, hash expiring one-time tokens, reject stale/no-op
  work, preserve first-observed targets, and persist atomically.
- Expanded the synthetic installed-package rehearsal to assert the new B2
  storage is present on clean bootstrap and populated legacy upgrade.
- Focused tests passed 8/8; `make validate` passed 211 runtime tests plus 21
  repository-tool tests (19 subtests), Ruff, compilation, boundary/synthetic
  checks, diff hygiene, and package build. `make rehearse-release` passed
  wheel installation, isolated bootstrap/upgrade, integrity/count/view checks,
  and rollback.
- No public use-case/CLI/Dashboard/Copilot registration, automatic post-sync
  trigger, Attention behavior, connector/live-data access, real data,
  `pending_decision_attention` change, Phase 4 work, push, merge, tag, release,
  or deployment was performed. Remaining risk: source evidence only supports
  authoritative scope closure when a future adapter explicitly supplies a
  complete manifest. The exact next action is explicit B2 review.

### 2026-07-30 — Module growth and context guardrails adopted

- Added binding repository instructions and an active architecture constraint
  requiring a named capability owner, inward dependency path, focused test
  entry point, and explicit transitional-debt decision before a new feature is
  added.
- Froze further growth of embedded Phase 3 canonical DDL in bootstrap and
  further responsibility growth of the B2 execution module. The next authorized
  change at either boundary must first perform the named behavior-preserving
  extraction; this record does not alter B2 behavior or authorize C1/C2/D.
- Refreshed the implementation index and evolution-plan gate text to the actual
  B2-review state. `make validate` passed repository-boundary and
  synthetic-sample checks, 211 runtime tests, 21 repository-tool tests (19
  subtests), Ruff, compilation, diff hygiene, and package build/inspection.
  No runtime, schema, test behavior, connector, real-data, public-interface,
  Attention, `pending_decision_attention`, push, merge, tag, release, or
  deployment change was made. This governance change is committed locally and
  remains unpushed. Exact next action remains B2 review.

### 2026-07-30 — Phase 3 Batch B2 review findings corrected

- Added a stable legacy-snapshot input fingerprint and persisted input reference
  so changes to mutable Jira Issue, Release, or Sprint snapshots trigger a new
  deterministic derivation rather than an incorrect idempotent return.
- Reconciled authoritative Release and Sprint memberships, closing obsolete
  memberships when a present Work Item moves scope. Authoritative Issue Link
  manifest removal now inactivates the canonical Dependency and appends an
  inactive observation; unrelated source IDs cannot be closed by that path.
- Release observations now preserve the legacy snapshot observation time rather
  than a derived wall-clock time, so first/latest target-date facts retain their
  true ordering. Unknown Milestone fields, including unsupported dependency
  references, now fail closed instead of being silently ignored.
- Added the required post-implementation independent review rule to
  `AGENTS.md`. Correction re-review found no P0-P2 issue. Focused tests passed
  12/12; `make validate` passed 215 runtime tests plus 21 repository-tool tests
  (19 subtests); `make rehearse-release` passed installed-package bootstrap,
  upgrade, integrity/count/view checks, and rollback.
- No public use-case/CLI/Dashboard/Copilot, automatic trigger, Attention,
  connector/live-data, real-data, `pending_decision_attention`, Phase 4, push,
  merge, tag, release, or deployment change was made. The correction is
  committed locally and remains unpushed. The owner subsequently completed B2
  re-review and accepted this corrected result; the next decision is bounded C1
  authorization or C1 design revision.

### 2026-07-30 — Phase 3 Batch B2 re-review accepted

- The owner completed review of the corrected B2 result and accepted it as the
  local Phase 3 canonical execution and Milestone foundation baseline.
- This acceptance authorizes neither C1 implementation nor C2/D, Phase 4,
  connector/live-data access, real data, Attention changes,
  `pending_decision_attention`, push, merge, tag, release, or deployment.
- Exact next action: decide whether to authorize the bounded C1 read-only
  execution-review implementation under IP-029, or require a C1 design
  revision first. This acceptance record is committed locally and remains
  unpushed.

### 2026-07-30 — Phase 3 Batch C1 read-only execution review implemented

- Added `delivery-execution-review` through the shared executor using unchanged
  `UseCaseResult 1.0`. It validates bounded project/layer/subject/window/limit
  filters and reads only the newest stored derivation facts per board.
- Added separate Sprint Execution and Release/Milestone projections, typed
  facts, evidence, freshness, source coverage, limitations, and only
  deterministic evidence-limited or Milestone schedule-exception signals.
  Recommendations remain empty.
- Added generic CLI, Dashboard Tool Transport, and Copilot agent instruction
  compatibility without a dedicated page, sync, derivation trigger, or write.
- Independent post-implementation review found no P0-P2 issue. Focused tests
  passed 9/9; `make validate` passed 217 runtime tests plus 21 repository-tool
  tests (19 subtests), Ruff, compilation, boundary/synthetic checks, diff
  hygiene, and package build. No schema changed, so no C1 release rehearsal is
  required before review.
- No C2 automatic processing or Attention producer, real data, live connector,
  `pending_decision_attention`, Phase 4, push, merge, tag, release, or
  deployment change was made. This C1 review candidate is committed locally and
  remains unpushed.

### 2026-07-30 — Phase 3 Batch C1 review accepted

- The owner completed review of the C1 read-only execution-review result and
  accepted it as the local Phase 3 public read path.
- This acceptance does not authorize C2 automatic post-sync derivation or
  Attention reconciliation, any business-object write, real data/live connector
  access, `pending_decision_attention`, Phase 4, push, merge, tag, release, or
  deployment.
- Exact next action: decide whether to authorize bounded C2 automatic derived
  Attention integration, or require a C2 design revision first. This acceptance
  record is local-only and remains unpushed.

### 2026-07-30 — Phase 3 Batch C2 automatic derived Attention implemented and reviewed

- Added exactly one enabled producer: `critical_milestone_overdue_attention`.
  It opens only for a fresh, complete, structured `critical` Milestone whose
  canonical `milestone_adherence` fact is known `overdue`, with `critical`
  severity. `pending_decision_attention` remains disabled.
- Published evidence triggers canonical derivation and scoped reconciliation
  only when a complete Issue History and Issue Link pair is present. Confirmed
  structured Milestone imports refresh each affected active board. Existing
  scoped Attention reconciliation remains the retry/recovery path.
- Complete non-match clears automatically with `rule_clear`; partial or failed
  input does not clear a prior active signal. A post-publication failure retains
  the durable cursor and records `PHASE3_RECONCILIATION_FAILED` on that run.
- Independent review found no P0-P2 issue. Focused tests passed 37/37;
  `make validate` passed 219 runtime tests plus 21 repository-tool tests (19
  subtests), and `make rehearse-release` passed. No real data, live connector,
  `pending_decision_attention`, Phase 4, push, merge, tag, release, or
  deployment action occurred.
- Exact next action: explicit authorization for Batch D regression and Phase 3
  promotion decision, or a C2 revision. This reviewed C2 result is local-only
  and remains unpushed.

### 2026-07-30 — Phase 3 Batch D regression and report implemented

- Ran combined Phase 3/Attention focused regression: 73 synthetic tests
  passed. `make validate` passed 219 runtime tests, 21 repository-tool tests
  (19 subtests), Ruff, compilation, boundary/synthetic checks, diff hygiene,
  and package build. `make rehearse-release` passed synthetic wheel install,
  isolated bootstrap/upgrade, integrity checks, and rollback.
- Added `implementation-reports/IP-029_IMPLEMENTATION_REPORT.md`, recording
  the implementation, commits, schema/migration/compatibility evidence,
  deferred risks, portable boundary, and promotion recommendation.
- No new runtime behavior, live connector, real data, `pending_decision_attention`,
  Phase 4, push, merge, tag, release, or deployment action occurred.
- Exact next action: independent Batch D review, then explicit owner decision
  to promote, revise, or reject Phase 3. This Batch D candidate is local-only
  and remains unpushed.

### 2026-07-30 — Phase 3 Batch D independent review passed

- Read-only review reconciled the IP-029 report against the Phase 3 local
  commit history, 73-test combined regression, 219-test full validation,
  installed-package rehearsal, schema/migration/rollback evidence, and
  portable data boundary. No P0-P2 issue was found.
- No code changed during review. No live connector, real data, Phase 4, push,
  merge, tag, release, deployment, or active-database operation occurred.
- Exact next action: explicit owner decision to promote, revise, or reject the
  completed local Phase 3 baseline. The branch remains local-only and unpushed.

### 2026-07-30 — Phase 3 promoted locally

- The owner accepted the completed Phase 3 Batch D review and promoted the
  execution evidence, canonical commitment, read-only review, and automatic
  derived Attention result as the local Phase 3 development baseline.
- Promotion relies on the recorded 73-test combined regression, 219-test full
  validation, and synthetic installed-package upgrade/rollback rehearsal.
- This is not a push, tag, release, deployment, active-database migration,
  real-data UAT, connector authorization, or Phase 4 authorization.
- Exact next action: separately inspect and approve the bounded Phase 4 design
  and its first implementation gate before any Phase 4 runtime work.

### 2026-07-30 — Phase 4 design proposed

- Created dedicated local branch `codex/phase-4-project-health-design` from
  promoted Phase 3 commit `bdfee9c` and drafted the bounded Phase 4 design and
  IP-030 implementation pack.
- The design fixes seven dimensions, canonical-fact allowlists, explicit
  unavailable/limited states, critical-Milestone non-averaging guards, bounded
  default/existing-project configuration, legacy strangler comparison, and four
  separately reviewed batches.
- No runtime code, schema, connector, real data, Attention producer,
  `pending_decision_attention`, push, merge, tag, release, or deployment was
  changed. Exact next action: owner design review/approval or revision; Batch A
  remains unauthorized.

### 2026-07-30 — Phase 4 production data policy clarified

- The owner confirmed that production adoption will fully re-import data; Phase
  4 need not migrate, backfill, or preserve current operational records or
  historical health snapshots.
- The Phase 4 design now requires clean bootstrap, authorized full re-import,
  integrity checks, and software rollback rehearsal instead of populated-data
  upgrade preservation. This changes no runtime, schema, connector, or gate.

### 2026-07-30 — Phase 4 clean re-import path made mandatory

- The owner clarified that all future Phase 4 design must ensure a supported
  path from empty database through bootstrap, structured full import, canonical
  derivation, health assessment, and coverage/integrity reporting.
- IP-030 Batch A now owns the design and implementation of the versioned
  structured import package, non-interactive local script/command, preview and
  validation, audit/idempotency record, additive table families, and synthetic
  clean-bootstrap/replay tests. Quality, Resource, and Governance may remain
  explicitly `not_available` until approved structured records are imported.
- No runtime/schema change or Batch A implementation is authorized by this
  clarification. Exact next action remains Phase 4 design review or revision.

### 2026-07-29 — Phase 3 Batch B1 accepted; B2 design handoff prepared

- The owner completed re-review, accepted corrected B1, and asked to enter the
  next stage.
- Rechecked exact local HEAD `bb80b4d`, branch
  `codex/phase-3-execution-signals`, clean worktree, the additive B1 schema,
  existing Jira snapshot relationships, controlled preview/confirm patterns,
  and the approved Phase 3 authority/freshness boundaries.
- Added an implementation-level B2 handoff that freezes inputs and trigger
  boundaries, additive canonical/observation/derivation/operation storage
  families, canonicalization and fact rules, structured Milestone
  preview/confirm behavior, sequential implementation order, and acceptance
  criteria.
- The design explicitly keeps current incremental Jira evidence
  non-authoritative for scope closure, legacy snapshots as current
  `legacy_observed` context only, automatic post-sync triggering in C2, and
  C1 interfaces out of B2.
- `make validate` passed repository-boundary and synthetic-sample checks, 203
  runtime tests, 21 repository-tool tests with 19 subtests, Ruff, compilation,
  diff hygiene, package build/inspection, and all eight release validation
  checks. No schema changed, so no new release rehearsal was required.
- No runtime, schema, test, connector, real-data, use-case, Attention,
  `pending_decision_attention`, Phase 4, push, merge, tag, release, or
  deployment change was made. The exact next decision is B2 implementation
  authorization or design revision.

### 2026-07-29 — Phase 3 Batch B1 second-review findings corrected

- Required every Issue Link at both the Jira adapter and repository boundaries
  to carry a bounded stable source reference. Missing IDs and conflicting
  repeated semantics now produce partial/rejected coverage with no cursor
  advance or published relationship.
- Canonicalized Jira mirrored inward/outward representations into one directed
  source-to-target relationship. The adapter retains the latest observation
  within the acquisition, while the repository dedup identity no longer changes
  because an endpoint Issue received an unrelated update.
- Corrected `status_category` normalization to use Jira's nested
  `statusCategory.key` rather than the parent status ID.
- Added six synthetic regressions covering repository rejection of empty link
  IDs, adapter partial coverage for missing IDs and conflicting stable
  identities, mirrored-link collapse, stable replay deduplication across
  timestamps, and status-category extraction.
- Focused source-evidence and registry coverage passed 22/22. `make validate`
  passed 203 runtime tests, 21 repository-tool tests with 19 subtests, Ruff,
  compilation, repository-boundary and synthetic-sample checks, package
  build/inspection, and all eight release validation checks.
  `make rehearse-release` passed the installed-package contract.
- No B2 canonical model or calculation, C1/C2/D, use-case/interface, Attention
  change, live connector, real data, operational configuration, Phase 4, push,
  merge, tag, release, or deployment was added. `pending_decision_attention`
  remains disabled. The result is stopped for another B1 re-review.

### 2026-07-29 — Phase 3 Batch B1 Review findings corrected

- Corrected concurrent publication so a run must still reference the current
  published predecessor and cannot regress the compound cursor. A stale run is
  rejected before it can publish events, alter the cursor, or apply an older
  authoritative manifest.
- Added normalized ISO timestamp validation at the repository and Jira adapter
  boundaries. Malformed Issue rows, changelog histories/items, and timestamps
  now produce partial/rejected coverage; unexpected adapter errors produce an
  audited failed/rejected run instead of leaving an unexplained staged run.
- Corrected event and link staging counts across repeated per-run calls so
  overlap pages and retries remain idempotent without negative accepted-row
  counts.
- Preserved connector-local evidence mappings, supported link types, horizons,
  overlap, and page/Issue limits when the Board registry is re-imported, while
  still refreshing registry-owned Board and Project references.
- Expanded installed-package rehearsal to verify all eight B1 tables, clean
  bootstrap, populated synthetic legacy upgrade, successful publication,
  partial staged-run retention, prior-cursor preservation, integrity/count/view
  checks, and rollback.
- Focused and compatibility coverage passed 76/76. `make validate` passed
  197 runtime tests, 21 repository-tool tests with 19 subtests, Ruff,
  compilation, repository-boundary and synthetic-sample checks, package
  build/inspection, and all eight release validation checks.
  `make rehearse-release` passed the expanded installed-package contract.
- No B2 canonical model or calculation, C1/C2/D, use-case/interface,
  Attention change, live connector, real data, operational configuration,
  Phase 4, push, merge, tag, release, or deployment was added.
  `pending_decision_attention` remains disabled. The corrected result is
  stopped for B1 re-review; the exact local commit is reported in the task
  handoff.

### 2026-07-29 — Phase 3 Batch B1 incremental source evidence validated

- The owner authorized only IP-029 Batch B1.
- Added eight additive source-evidence tables for per-source/board/dataset
  compound cursors, append-only run coverage, staged and published manifests,
  staged/published Issue history, and staged/published directed Issue Links.
- Added a transactional repository boundary with bounded normalized fields,
  stable event/semantic hashes, overlap replay deduplication, page and field
  coverage, atomic cursor publication, partial/failed rejection, and
  complete-authoritative-manifest-only tombstones.
- Added bounded synthetic Jira acquisition for updated-since search,
  paginated changelog, Issue Links, connector-local field mapping, bootstrap
  horizon, page/Issue limits, and explicit unsupported link types. It stores
  stable source references and normalized values rather than Issue summaries,
  assignee details, raw changelog bodies, or raw payloads.
- Registered a per-board `jira-evidence-*` local source with empty field
  mappings by default. Registry removal deletes obsolete mutable Jira caches
  and source registration while preserving already-published evidence history.
- Focused and compatibility coverage passed 70/70. `make validate` passed
  191 runtime tests, 21 repository-tool tests with 19 subtests, Ruff,
  compilation, repository-boundary and synthetic-sample checks, package
  build/inspection, and all eight release validation checks.
  `make rehearse-release` passed installed-package additive upgrade, Phase 3
  evidence publication, integrity/count/view checks, and rollback.
- No legacy Jira health behavior, Project Health, use-case/interface,
  Attention producer/reconciliation, business-object write, live connector,
  real data, operational configuration, B2/C1/C2/D, Phase 4, push, merge, tag,
  release, or deployment was added. `pending_decision_attention` remains
  disabled. The bounded result is stopped for B1 Review; the exact local
  commit is reported in the task handoff.

### 2026-07-29 — Phase 3 design approved and IP-029 registered

- The owner accepted all four Phase 3 architecture decisions: Release date
  authority separation, structured-only canonical Milestones, no Phase 3
  health RAG, and automatic post-sync derived reconciliation.
- Created dedicated local branch `codex/phase-3-execution-signals` from the
  history containing exact promoted Phase 2 baseline `2185334`.
- Registered
  `implementation-packs/IP-029_PHASE_3_EXECUTION_AND_MILESTONE_FOUNDATION.md`
  with bounded B1/B2/C1/C2/D scopes, acceptance criteria, compatibility,
  migration, rollback, synthetic-data, and stop gates.
- No runtime, schema, migration, connector behavior, live connector use,
  real-data access, test, push, or Phase 4 change was made.
- The documentation-only approval and registration record passed
  `make validate`: 183 runtime tests, 21 repository-tool tests with 19
  subtests, Ruff, compilation, repository-boundary and synthetic-sample
  checks, package build and inspection, and all eight release validation
  checks.
- The exact next gate is explicit authorization or rejection of only IP-029
  Batch B1.

### 2026-07-29 — Phase 3 current-state and design Review proposed

- Inspected the current SQLite bootstrap/migration path, Jira Release and
  health sync, connector wrapper, Dashboard sync confirmation, Project Health
  repository/use case, Attention rules and reconciliation, registry cleanup,
  and focused synthetic compatibility tests.
- Verified the current path has mutable Release Version, Issue, and Sprint
  snapshots and append-only legacy health scores, but no Issue changelog,
  Issue Link, temporal scope membership, canonical Release commitment,
  canonical Milestone, or canonical Dependency.
- Added
  `architecture/09_PHASE_3_EXECUTION_AND_MILESTONE_FOUNDATION_DESIGN.md` with
  canonical concepts, date authority, incremental cursor/staging semantics,
  explicit missing/partial/conflict handling, deterministic fact definitions,
  read-only use-case and Attention boundaries, migration/rollback, synthetic
  scenarios, and proposed B1/B2/C1/C2/D batches.
- Focused current-contract verification passed 44 tests covering Dashboard
  Jira sync confirmation, registry cleanup, unified use-case compatibility,
  database bootstrap, and Attention reconciliation.
- The documentation-only design working tree passed `make validate`: 183
  runtime tests, 21 repository-tool tests with 19 subtests, Ruff, compilation,
  repository-boundary and synthetic-sample checks, package build and
  inspection, and all eight release validation checks.
- No runtime, schema, migration, connector behavior, implementation pack,
  real-data access, push, promotion, or Phase 4 change was made. The design is
  stopped for owner review.

### 2026-07-29 — Phase 2 promoted locally

- The owner explicitly promoted the completed IP-028 implementation after
  accepting the Batch D Review.
- The promotion establishes only the local Phase 2 development baseline and
  preserves the exact validated runtime, schema, migration, compatibility,
  interface, and disabled `pending_decision_attention` behavior.
- No runtime, schema, test, connector, real-data, visual Dashboard, push,
  merge, tag, release, deployment, or operational action was performed.
- The documentation-only promotion record passed `make validate`: 183 runtime
  tests, 21 repository-tool tests with 19 subtests, Ruff, compilation,
  repository-boundary and synthetic-sample checks, package build and
  inspection, and all eight release validation checks.
- The next independent gate is Phase 3 current-state and design review. Phase 3
  implementation and all Phase 4 work remain unauthorized.

### 2026-07-29 — Phase 2 Batch D Review accepted

- The owner completed Review of the Batch D evidence, implementation report,
  remaining risks, and planned later-phase controls.
- No code, schema, test, connector, real-data, push, or promotion change was
  made by this review record.
- The documentation-only acceptance record passed `make validate`: 183 runtime
  tests, 21 repository-tool tests with 19 subtests, Ruff, compilation,
  repository-boundary and synthetic-sample checks, package build and
  inspection, and all eight release validation checks.
- Phase 2 remains unpromoted. The exact next gate is the explicit decision to
  promote or not promote the current local Phase 2 development baseline.

### 2026-07-29 — Phase 2 Batch D validated

- The owner accepted the bounded C2 correction and authorized the next Batch D
  validation step.
- Combined focused regression passed 109/109 across Attention rules, storage,
  reconciliation, lifecycle, Center projections, retained configuration
  storage, interface rejection, migration, concurrency, Management Attention,
  `UseCaseResult 1.0`, discovery, CLI build, and Copilot.
- `make validate` passed repository-boundary and synthetic-sample checks,
  183 runtime tests, 21 repository-tool tests with 19 subtests, Ruff,
  compilation, diff hygiene, package build/inspection, and all eight release
  validation checks.
- `make rehearse-release` passed temporary wheel installation, isolated
  synthetic database upgrade, integrity checks, installed behavior, and
  rollback for `ai-pm-agent 0.2.0rc1`.
- Schema review confirmed six additive Attention tables, bounded constraints,
  hashed tokens, migration/backfill coverage, retained legacy configuration
  rows, and disabled pending-decision enforcement. Portable review found no
  operational data, connector, credential, private path, or company-derived
  content.
- Added `implementation-reports/IP-028_IMPLEMENTATION_REPORT.md` with
  implementation, validation, schema, compatibility, remaining-risk, and
  promotion-gate evidence.
- No runtime behavior changed in Batch D. Phase 2 is not promoted; the explicit
  owner promotion decision is next. Phase 3/4 runtime, connector, real-data,
  release, push, merge, and tag work remain unauthorized.

### 2026-07-29 — Phase 2 C2 correction technical re-review passed

- Re-reviewed the mutation-boundary fix and found no remaining P0-P2 issue.
- Confirmed production code contains no configuration-operation mutation or
  project-health rule-version mutation helper. Only schema/bootstrap support,
  current-rule read support, and legacy configuration-operation read detection
  remain.
- Confirmed the fixed Bootstrap v1-to-v2 rule migration is deterministic,
  idempotent, and does not accept DM configuration input.
- The validated evidence remains 93 focused tests and a green `make validate`
  run with 183 runtime tests, 21 repository-tool tests with 19 subtests, Ruff,
  compilation, boundary/synthetic checks, package build/inspection, and eight
  release validation checks.
- No code changed during technical re-review. Owner acceptance is the exact
  next gate; Batch D, Phase 2 promotion, Phase 3/4 runtime, connector,
  real-data, release, push, merge, and tag work remain unauthorized.

### 2026-07-29 — Phase 2 C2 mutation-boundary review fix validated

- Addressed the C2 correction Review finding that public routing was blocked
  while dormant internal configuration confirmation and rule-version mutation
  code remained executable.
- Removed service-level configuration confirmation, configuration preview
  construction, configuration-change, and parameter-hash helpers.
- Removed repository helpers that created or mutated configuration operations
  or created new project-health rule versions. Retained the additive table,
  existing records, current-rule read support, and legacy-operation read
  detection.
- Added a boundary test proving the retired mutation helpers are not exposed,
  alongside existing tests proving preview/confirm rejection, record
  preservation, C1 compatibility, and disabled pending-decision state.
- Focused combined coverage passed 93/93. `make validate` passed
  repository-boundary and synthetic-sample checks, 183 runtime tests,
  21 repository-tool tests with 19 subtests, Ruff, compilation, diff hygiene,
  package build/inspection, and all eight release validation checks.
- No schema, migration, connector, real-data, visual Dashboard, Phase 3/4,
  Batch D, push, or promotion work was added. The result is stopped for C2
  correction re-review.

### 2026-07-29 — Phase 2 C2 public-interface correction validated

- Removed the unaccepted `rag-config-preview` CLI command and
  `configure-project-health-rag` Dashboard preview action.
- Updated the Delivery Manager Copilot contract to state that project-health
  RAG configuration is unavailable in the current Phase 2 interface and that
  legacy mapping configuration operations must not be invoked or confirmed.
- Made direct configuration preview fail deterministically with
  `ATTENTION_RAG_CONFIGURATION_UNAVAILABLE`. Shared confirmation now detects a
  retained legacy configuration operation and returns the same failure without
  claiming, expiring, failing, or otherwise mutating it.
- Retained the additive `attention_configuration_operations` table and existing
  rows unchanged; no schema migration or data deletion was introduced.
- Replaced superseded configuration-write tests with focused synthetic
  coverage for disabled service/CLI/Dashboard paths, blocked legacy tokens,
  bootstrap storage preservation, Management Attention compatibility, and
  disabled `pending_decision_attention`.
- Focused combined coverage passed 92/92. `make validate` passed
  repository-boundary and synthetic-sample checks, 182 runtime tests,
  21 repository-tool tests with 19 subtests, Ruff, compilation, diff hygiene,
  package build/inspection, and all eight release validation checks.
- No C1 behavior, `UseCaseResult 1.0`, Management Attention, connector,
  real-data, visual Dashboard, Phase 3/4 runtime, Batch D, push, or promotion
  work was added. The result is stopped for C2 correction review.

### 2026-07-29 — Layered health and milestone design review approved

- The owner approved the three-layer Sprint Execution, Release/Milestone, and
  seven-dimension Project Health architecture.
- The fixed factor catalog, bounded DM-configurable conditions,
  existing-project-only overrides, explicit unavailable Story Point state,
  critical milestone guards, and Phase 3/4/7 ownership are now decisions in
  force.
- The exact next implementation is the bounded IP-028 C2 correction that
  disables or removes the unaccepted public mapping configuration CLI,
  Dashboard, and Copilot paths while preserving C1, compatibility contracts,
  additive data, and disabled `pending_decision_attention`.
- No runtime, schema, test, connector, real-data, push, promotion, or Phase 3/4
  implementation change was made by this approval record.
- `make validate` passed 187 runtime tests, 21 repository-tool tests with
  19 subtests, repository-boundary and synthetic-sample checks, Ruff,
  compilation, diff hygiene, package build/inspection, and all eight release
  validation checks.

### 2026-07-29 — Layered health and milestone design revision proposed

- Recorded that Batch C2 commit `71d90d3` passed technical validation but
  failed product-contract review: label mapping and source precedence are not
  the accepted DM-facing RAG configuration model.
- Proposed distinct Sprint Execution, Release/Milestone, and Project Health
  layers with a fixed factor catalog and bounded DM-configurable conditions,
  thresholds, tolerances, windows, applicability, and approved same-layer
  weights.
- Made milestone and Release commitments first-class Phase 3 concepts, inputs
  to Phase 4 Project Health, and promoted history reused by Phase 7 Forecast.
  Story Point evidence is never required for milestone-based Release Health,
  and missing Story Points remain explicitly unavailable.
- Recorded the existing-project-only override rule, critical milestone guards,
  non-averaging aggregation, read-only prior/proposed/effective configuration
  projections, and required synthetic scenarios.
- No runtime, schema, migration, connector, real-data, Dashboard UI, or
  automatic project/action/staffing/decision write was added. The exact next
  gate is design review; only after approval may a bounded C2 correction
  disable or remove the unaccepted public mapping paths.
- `make validate` passed repository-boundary and synthetic-sample checks,
  187 runtime tests, 21 repository-tool tests with 19 subtests, Ruff,
  compilation, diff hygiene, package build/inspection, and all eight release
  validation checks.

### 2026-07-29 — Phase 2 Batch C2 RAG configuration validated

- Added the dedicated additive `attention_configuration_operations` store for
  expiring, hashed, one-time configuration previews without changing existing
  reconciliation/lifecycle operation contracts.
- Added strict full-result validation for complete default replacement,
  bounded stable-anonymous-project overrides, and explicit override removal.
  Unsupported fields, prompts/SQL-shaped fields, malformed IDs/labels, empty
  overrides, and no-op removal fail before an operation is created.
- Confirmation rechecks the current rule version and canonical parameter hash,
  rejects stale previews, retains prior versions, and atomically creates one
  new current `project_health_attention` version. It creates no reconciliation,
  signal, or history mutation and explicitly reports that reconciliation is
  required.
- Added exact JSON `rag-config-preview` CLI behavior, the
  `configure-project-health-rag` Dashboard API preview action, shared confirm
  behavior, safe HTTP conflicts, and Copilot instructions requiring explicit
  preview/confirmation plus separately confirmed reconciliation.
- Added focused synthetic coverage for clean/additive bootstrap, hashed token
  storage, default/override/removal, invalid/no-op input, stale previews,
  expiry, reuse, concurrent confirmation, transaction rollback, exact
  CLI/Dashboard projections, Management Attention compatibility, and disabled
  pending-decision state.
- Focused combined tests passed 82/82. `make validate` passed
  repository-boundary and synthetic-sample checks, 187 runtime tests,
  21 repository-tool tests with 19 subtests, Ruff, compilation, diff hygiene,
  package build/inspection, and all eight release validation checks.
- No visual Dashboard Center, connector, source sync, real data, automatic
  action/project/staffing/decision write, pending-decision activation, push,
  Batch D, or Phase 2 promotion was introduced. The local result is stopped
  for Batch C2 review.

### 2026-07-29 — Phase 2 Batch C1 review accepted

- The owner completed review and accepted the corrected IP-028 Batch C1 local
  result.
- Scheme A remains the accepted lifecycle: complete clear reconciliation
  automatically resolves an item with `rule_clear`; no public manager resolve
  step is exposed.
- No runtime, schema, test, connector, configuration, real-data, push, or
  promotion change was made by this gate update.
- The documentation-only gate update passed `make validate`: 176 runtime
  tests, 21 repository-tool tests with 19 subtests, Ruff, compilation,
  repository-boundary and synthetic-sample checks, package build/inspection,
  and all eight release validation checks.
- Batch C2 remains unstarted and requires separate explicit authorization. The
  exact next action is the owner's Batch C2 authorization decision.

### 2026-07-28 — Phase 2 Batch C1 review corrections validated

- Applied the owner decision that Attention is decision support rather than a
  manager-supervision workflow. Complete clear reconciliation continues to
  resolve automatically with `rule_clear`; public CLI, Dashboard, and Copilot
  resolve-preview routing was removed. Internal defensive resolution
  validation remains unexposed for compatibility.
- Corrected Center array-member validation so unhashable or unsupported
  `attention_states` return the stable invalid result instead of a domain
  execution failure.
- Made same-second reconciliation coverage and per-item history ordering use
  SQLite insertion order rather than random UUID lexical order.
- Projected the latest limited evaluation freshness while retaining the last
  known active fact, so complete-to-partial transitions visibly block advice
  without falsely presenting the retained freshness as current.
- Preserved normalized source observation time for project-health facts and
  exposed reconciliation time separately as `evaluated_at`.
- Hardened reconciliation scope validation to reject non-string identifiers
  and non-canonical subject kinds before creating an operation.
- Added a JSON Attention CLI parsing boundary so missing options, unknown
  commands, and the intentionally unavailable public resolve command return a
  stable JSON failure with a non-zero exit code.
- Focused combined tests passed 71/71. `make validate` passed
  repository-boundary and synthetic-sample checks, 176 runtime tests,
  21 repository-tool tests with 19 subtests, Ruff, compilation, diff hygiene,
  package build/inspection, and all eight release validation checks.
- No schema, migration, RAG configuration write, visual Dashboard Center,
  connector, real-data, business-object write, pending-decision activation,
  push, or Phase 2 promotion was introduced. The corrected local result is
  stopped for Batch C1 review.

### 2026-07-28 — Phase 2 Batch C1 Attention Center validated

- Added the separate read-only `delivery-attention-center` use case through the
  shared executor and unchanged `UseCaseResult 1.0`. It reads persisted
  Attention state only and returns deterministic filtering/order, pre-limit
  zero-filled summaries, explicit reconciliation coverage, stable result-local
  references, bounded newest-first history metadata, and one advisory
  recommendation per returned item.
- Added the exact JSON-only `pm attention` reconciliation/lifecycle
  preview-confirm commands and dedicated Dashboard
  `POST /api/attention/operations` projection. Dashboard actor is server
  derived, payload fields are action-specific and fail closed, safe service
  failures map to the approved HTTP statuses, and only successful preview
  exposes a confirmation token.
- Updated Copilot routing so Center queries never reconcile implicitly and
  write previews/confirmation require separate explicit user authorization.
  ToolTransport remains query-only.
- Corrected lifecycle no-op handling so duplicate acknowledgement, unchanged
  normalized snooze, and repeated resolve fail before an operation or history
  event is created.
- Added focused synthetic coverage for empty/scoped reconciliation coverage,
  validation, ordering, pre-limit counts, history bounds, fact/signal/
  recommendation integrity, recommendation states, direct/CLI/Dashboard
  projection compatibility, operation status mapping, no-op zero-write
  behavior, and Management Attention read-only compatibility.
- Focused combined tests passed 69/69. `make validate` passed
  repository-boundary and synthetic-sample checks, 174 runtime tests,
  21 repository-tool tests with 19 subtests, Ruff, compilation, diff hygiene,
  package build/inspection, and all eight release validation checks.
- `pending_decision_attention` remains disabled. No schema, migration, RAG
  configuration write, visual Dashboard Center, connector, real-data,
  business-object write, push, or Phase 2 promotion was introduced. The local
  result is stopped for Batch C1 review.

### 2026-07-28 — Phase 2 Batch C design review approved

- Owner accepted the corrected Batch B result and required an explicit Batch C
  design review before implementation.
- Closed the interface-design gaps by defining reconciliation coverage for
  empty/scoped queries, deterministic ordering and pre-limit summaries,
  bounded history metadata, stable result-local references, and exact advisory
  recommendation state mapping.
- Defined JSON-only Attention CLI commands and the dedicated Dashboard
  `POST /api/attention/operations` contract, including server-derived actor,
  token exposure, safe status mapping, and explicit Copilot preview/confirm
  behavior. Batch C1 contains API projection only, not a visual Dashboard
  Center page.
- Required lifecycle no-op rejection for duplicate acknowledgement, unchanged
  snooze, and repeated resolve before any operation/history write.
- Split Batch C into C1 Center/interfaces and separately gated C2 DM-operable
  RAG configuration. The existing persisted rule parameters remain
  data-configurable; no configuration mutation interface is claimed yet.
- Reverted the premature uncommitted Attention repository query helper so this
  handoff contains documentation only. No runtime, schema, migration, test,
  connector, real-data, pending-decision activation, push, or promotion change
  was made.
- `make validate` passed with 167 runtime tests, 21 repository-tool tests and
  19 subtests, Ruff, compilation, boundary/synthetic checks, package
  build/inspection, and all eight release validation checks.
- Exact next action: implement only Batch C1 in a new session, validate, commit
  locally, and stop for Batch C1 review.

### 2026-07-28 — Repeated partial Attention history deduplicated

- Corrected the final Batch B review blocker in which repeated identical
  partial evaluations compared against the retained active snapshot and
  appended duplicate `evaluation_limited` events indefinitely.
- Added `last_evaluation_hash` as an additive current-signal field, distinct
  from the retained `observation_hash`. Preview and confirmation now compare
  the same latest semantic evaluation while the last known active snapshot
  remains intact.
- Added an idempotent migration that adds the field to an existing Batch B
  database and backfills it from the retained snapshot hash. Synthetic coverage
  proves the backfill, changed partial audit, and unchanged partial
  deduplication behavior.
- Focused Attention tests passed 14/14. Combined Attention/database/bootstrap/
  Management Attention/unified-contract regression passed 52/52.
  `make validate` passed repository-boundary and synthetic-sample checks,
  167 runtime tests, 21 repository-tool tests with 19 subtests, Ruff,
  compilation, diff hygiene, package build/inspection, and eight release
  validation checks.
- No Batch C interface, connector, real-data, pending-decision activation,
  business-object write, promotion, tag, merge, push, deployment, or `main`
  change was introduced. The result remains stopped for corrected Batch B
  review.

### 2026-07-28 — Phase 2 Batch B follow-up review findings corrected

- Corrected project-health completeness so every source selected by the
  versioned default or project override must provide a recognized value for
  every evaluated board before an inactive observation can clear an active
  Attention item. Missing or unmapped configured inputs remain partial; a
  source is optional only when the versioned configuration omits it.
- Hardened nested RAG configuration validation so non-string precedence items
  and mapping states return the safe Attention preview failure instead of
  leaking a `TypeError`. Synthetic tests cover arrays in source precedence,
  state precedence, and mapping values.
- Added the distinct `rule_changed` history event required by the approved
  audit contract. A migration expands the existing history event constraint
  while preserving all prior rows, foreign-key integrity, and history indexes;
  ordinary semantic changes remain `observed_again`.
- Focused Attention tests passed 13/13. Combined Attention/database/bootstrap/
  Management Attention/unified-contract regression passed 51/51.
  `make validate` passed repository-boundary and synthetic-sample checks,
  166 runtime tests, 21 repository-tool tests with 19 subtests, Ruff,
  compilation, diff hygiene, package build/inspection, and eight release
  validation checks.
- No Batch C interface, connector, real-data, pending-decision activation,
  business-object write, promotion, tag, merge, push, deployment, or `main`
  change was introduced. The result remains stopped for corrected Batch B
  review.

### 2026-07-28 — Phase 2 Batch B review corrections validated

- The owner authorized correction of the Batch B review findings and required
  project-health RAG definitions to be configurable for different local DMs
  and projects rather than fixed in evaluation code.
- Added versioned project-health rule parameters for source-specific label
  mappings, source precedence, and normalized state precedence. Configuration
  has a local DM default plus bounded overrides keyed only by stable anonymous
  project ID. Bootstrap migrates the original fixed v1 seed to configurable v2
  without deleting v1 history references; later parameter changes require a
  new rule version and reconciliation preview/confirm.
- Restored Management Attention-compatible default source precedence and
  limited expected Jira sources to active boards attached to active projects.
  Unknown, missing, invalid, or unmapped project-health/action inputs now
  produce incomplete evaluation and cannot clear an active Attention item.
- Made preview counts include snooze expiry, disabled-rule transitions, and
  limited evaluations that confirmation can apply. Corrected history metadata
  so severity/rule-version columns match the new normalized observation.
- `pending_decision_attention` remains disabled and is not evaluated.
  Configuration changes add no Batch C interface or direct business write;
  every Attention effect still uses its dedicated preview/confirm boundary.
- Focused Attention tests passed 11/11. Combined Attention/database/bootstrap/
  Management Attention/unified-contract regression passed 49/49.
  `make validate` passed repository-boundary and synthetic-sample checks,
  164 runtime tests, 21 repository-tool tests with 19 subtests, Ruff,
  compilation, diff hygiene, package build/inspection, and eight release
  validation checks.
- Only synthetic records and stable anonymous identifiers were used. No
  connector, real-data, action/project/staffing write, interface, release,
  promotion, tag, merge, push, deployment, or `main` behavior was added. The
  corrected result remains stopped for Batch B review.

### 2026-07-28 — Phase 2 Batch B Attention foundation validated

- Confirmed a clean worktree on `codex/phase-2-attention-center` at exact
  approved commit `e4431dc0ab5f7122d65affaa917fa3697d634b15` before
  implementation.
- Added five additive `attention_*` tables and supporting indexes for the
  versioned rule catalog, hashed one-time operations, reconciliation audit,
  canonical current signals, and append-only history. Bootstrap is idempotent,
  creates no historical backfill, preserves existing tables/views/data, and
  keeps prior runtimes safe by leaving additive storage unused.
- Added the internal deterministic Attention core with canonical identity,
  semantic observation hashing, deduplication, complete/partial/disabled
  evaluation handling, safe clear/reopen behavior, and bounded lifecycle
  transitions. It is not exposed through CLI, Dashboard, Copilot, or
  ToolTransport.
- Implemented only the four approved active rules: project health, overdue
  action, required-source freshness, and active-assignment load strictly
  greater than 100%. `pending_decision_attention` is registered disabled and
  protected by a database constraint; synthetic decision-log input produces no
  Attention item or history.
- Added an Attention-specific five-minute preview/confirm boundary for
  reconciliation, acknowledgement, snooze, and resolve. Tokens are stored only
  as hashes, confirmation is atomically claimed with `BEGIN IMMEDIATE`, and
  confirmation re-evaluates the current bounded scope so stale previews and
  concurrent reuse cannot partially mutate current/history state.
- Focused Attention tests passed 8/8. Combined
  Attention/database/bootstrap/Management Attention regression passed 46/46.
  `make validate` passed repository-boundary and synthetic-sample checks,
  161 runtime tests, 21 repository-tool tests with 19 subtests, Ruff,
  compilation, diff hygiene, package build/inspection, and eight release
  validation checks.
- No existing Management Attention, execution-trace payload, connector,
  configuration, credential, real-data, action/project/staffing write,
  interface, release, tag, merge, push, deployment, or `main` behavior was
  changed. `make rehearse-release` remains deliberately deferred to Batch D as
  specified by IP-028.
- The bounded result is committed locally on the Phase 2 branch and is stopped
  for Batch B review. The exact commit is reported in the task handoff; no push
  occurred.

### 2026-07-28 — Phase 2 design approved and IP-028 registered

- Owner explicitly approved the reviewed Phase 2 Delivery Attention Center
  design, including the separate Attention operation boundary, disabled
  pending-decision rule, greater-than-100% resource-overload threshold, source
  freshness advisory behavior, contracts, lifecycle, and proposed additive
  storage.
- Created local implementation branch `codex/phase-2-attention-center` from
  the approved design state and registered IP-028 for sequential Phase 2 work.
- Batch B alone is ready: additive Attention storage, deterministic rules,
  one-time operation/reconciliation/lifecycle core, and focused synthetic
  tests. Batch C interfaces and all connector/real-data work remain blocked.
- No runtime, test, database, schema, migration, connector, configuration,
  credential, real-data, push, merge, tag, PR, release, deployment, or `main`
  action was performed by this approval/registration record.
- `git diff --check` and approval-status scans passed. `make validate` passed:
  repository boundary, synthetic samples, 153 runtime tests, 21 repository-tool
  tests with 19 subtests, Ruff, compilation, diff hygiene, package
  build/inspection, and eight release validation checks.
- This approval/registration record is committed locally on the Phase 2 branch
  but intentionally not pushed; the exact local HEAD is reported in the task
  handoff. The exact next action is IP-028 Batch B implementation.

### 2026-07-28 — Phase 2 review corrections accepted

- Owner accepted the review decision to use an Attention-specific one-time
  preview/confirm operation boundary rather than repurposing the existing
  sync-only Dashboard operation path.
- Owner accepted that `pending_decision_attention` is registered but disabled
  in Phase 2. It emits no active signal or recommendation until a separately
  approved governance definition provides eligible types, ownership/due
  semantics, threshold, evidence, and rule version.
- The design also resolves the resource-overload threshold to strictly greater
  than 100% active-assignment load, makes source-freshness advice available
  from its normalized local metadata, and specifies bounded Center and write
  contracts. No runtime/schema/migration or implementation-pack change is
  authorized.
- `git diff --check` and stale-design scans passed. `make validate` passed:
  repository boundary, synthetic samples, 153 runtime tests, 21 repository-tool
  tests with 19 subtests, Ruff, compilation, diff hygiene, package
  build/inspection, and eight release validation checks.
- This correction record is committed locally but intentionally not pushed; the
  exact local HEAD is reported in the task handoff. The next action remains
  final owner review and explicit Phase 2 design approval or revision.

### 2026-07-28 — Phase 2 Batch A Delivery Attention Center design

- Confirmed a clean worktree on `codex/phase-1-intelligence-contract` at the
  exact Phase 1 promotion commit
  `289837855a230a14256a5ed00f5c8e353b1c3d36` before this documentation-only
  task.
- Inspected the real Management Attention handler, shared executor/result
  contract, descriptor registration, SQLite bootstrap/schema, repositories,
  confirmation pattern, and focused synthetic tests. Current Management
  Attention is a request-time read-only ranking of local project health,
  overdue actions, and source freshness; it has no durable Attention identity,
  history, lifecycle, or persistence.
- Added `architecture/07_PHASE_2_DELIVERY_ATTENTION_CENTER_DESIGN.md` as the
  reviewable Batch A design. It defines verified state, separate Center
  compatibility boundary, canonical identity/deduplication, proposed additive
  storage, lifecycle, confirmed reconciliation, failure handling, synthetic
  validation, and Batch B through D plan.
- The design uses only anonymous stable identifiers and synthetic scenarios.
  It explicitly preserves the existing `management-attention` response and
  forbids connector access, real data, schema/runtime change, automatic action
  creation, project-status mutation, and Phase 2 implementation before
  approval.
- No implementation pack was registered. No runtime, test, database, schema,
  migration, connector, configuration, credential, real-data, push, merge,
  tag, PR, release, deployment, or `main` action was performed.
- Documentation consistency checks (`git diff --check` and stale-status scan)
  passed. `make validate` also passed: repository boundary, synthetic samples,
 153 runtime tests, 21 repository-tool tests with 19 subtests, Ruff,
  compilation, diff hygiene, package build/inspection, and eight release
  validation checks.
- This documentation-only design record is committed locally; the exact final
  HEAD is reported in the task handoff because a commit cannot contain its own
  hash. No push occurred. The exact next action is owner review and
  approval/revision of the Phase 2 design.

### 2026-07-28 — Authorized independent-branch publication

- Owner authorized publication of the current local commit chain to remote.
  The scope is only `codex/phase-1-intelligence-contract`; no PR, tag, merge,
  release, deployment, connector, real-data, or `main` action is authorized.
- The local GitHub CLI OAuth token is invalid, but direct Git HTTPS credentials
  are a separate mechanism. Direct Git HTTPS successfully created and pushed
  `origin/codex/phase-1-intelligence-contract`; no PR was created. Exact remote
  HEAD verification is completed in the task handoff. Remote CI status remains
  unknown until a successful remote workflow is observed.

### 2026-07-28 — Phase 1 promoted

- Owner explicitly promoted the completed Phase 1 implementation after
  reviewing the Batch D result.
- Updated the evolution plan, roadmap, Phase 1 design, IP-027 report, pack
  index, and continuity record to show the promoted local baseline.
- Promotion preserves the exact validated behavior and introduces no runtime,
  test, schema, migration, connector, real-data, or interface change.
- The next action is a new Phase 2 Batch A design task. No Phase 2
  implementation pack or runtime/schema change is authorized.
- No remote push, merge, tag, PR, release, deployment, connector access,
  active-database migration, or real-data action was performed.

### 2026-07-28 — Phase 1 Batch D validated

- Owner explicitly authorized Batch D after the validated Batch C handoff.
- Confirmed a clean worktree at exact Batch C commit `61b3d8c`.
- Batch D is limited to combined regression, synthetic installed-package and
  rollback rehearsal, portable/schema review, implementation reporting, and a
  Phase 1 promotion recommendation.
- Combined focused regression passed 63/63 across contract, discovery,
  transport, Management Attention, Copilot, unified-use-case, and legacy
  interface coverage.
- `make validate` passed 153 runtime tests, 21 repository-tool tests with
  19 subtests, Ruff, compilation, repository boundary, synthetic samples, diff
  hygiene, package build, and eight release checks.
- `make rehearse-release` passed temporary wheel installation, isolated
  synthetic database upgrade, integrity checks, installed behavior, and
  rollback for `ai-pm-agent 0.2.0rc1`.
- Complete diff review from exact approved planning commit `3d40633` found no
  database/schema, migration, full-intelligence persistence, connector,
  operational configuration, credential, real-data, or unrelated business
  behavior change.
- Added `implementation-reports/IP-027_IMPLEMENTATION_REPORT.md` with
  implementation, evidence, compatibility, risk, rollback, and promotion
  position.
- Phase 1 promotion is recommended but remains an explicit owner decision.
  No Phase 2, connector, real-data, remote push, tag, PR, release, deployment,
  or `main` action was performed.

### 2026-07-28 — Phase 1 Batch C validated

- Committed the validated Batch B2 review corrections locally as `ea5eb7a`
  without pushing.
- Entered owner-authorized Batch C on the existing independent implementation
  branch.
- Inspected the current Management Attention ranking, truncation, embedded item
  evidence, top-level evidence/freshness, descriptor path, generic interfaces,
  bounded trace storage, and Copilot operating instructions.
- Added one derived fact and one active signal for each returned Management
  Attention item, with deterministic bounded IDs, fact/evidence/freshness
  references, existing severity and reason codes, and rule version
  `management-attention-v1`.
- Preserved existing item order, limit, summary, context, warnings, status, and
  embedded legacy data. Added only selected source-freshness evidence needed
  for reference integrity; recommendations remain empty.
- Updated the Management Attention descriptor to facts/signals true and
  recommendations false; every other production descriptor remains all false.
- Updated Copilot result handling to prioritize facts, signals,
  recommendations, and their qualifiers, and to prohibit invented objects,
  severity changes, unsupported evidence/freshness, and invented actions from
  an empty recommendation list.
- The initial focused run exposed that bootstrap already registers the
  Confluence source and that B2 expectations needed the approved Management
  Attention capability transition. Tests were corrected to use the verified
  bootstrap state without changing production behavior.
- Focused tests passed 40/40. Final `make validate` passed 153 runtime tests,
  21 repository-tool tests with 19 subtests, Ruff, compilation, repository
  boundary, synthetic samples, diff hygiene, package build, and eight release
  checks.
- Git diff review found no database/schema, production recommendation,
  connector, real-data, configuration, credential, persistence, or unrelated
  business behavior change.
- Batch C is ready only for review. No Batch D, remote push, tag, PR, release,
  deployment, or `main` action was performed.

### 2026-07-28 — Phase 1 Batch B2 review corrections

- Added runtime enforcement requiring exact boolean capability values and an
  `IntelligenceCapabilities` object on every descriptor.
- Strengthened discovery coverage to assert the exact nine production
  use-case IDs before checking their all-false capabilities.
- Focused B1/B2 tests passed 30/30. Final `make validate` passed 145 runtime
  tests, 21 repository-tool tests with 19 subtests, Ruff, compilation,
  repository boundary, synthetic samples, diff hygiene, package build, and
  eight release checks.
- Owner authorized Batch C after these corrections. No Batch C code, remote
  push, tag, PR, release, deployment, or `main` action was performed in this
  correction.

### 2026-07-27 — Phase 1 Batch B2 validated

- Owner approved the corrected Batch B1 and explicitly authorized entry into
  Batch B2.
- Confirmed a clean worktree at exact corrected B1 commit `8041e82`.
- Extended IP-027 with bounded discovery and transport scope. All nine current
  production use cases must advertise facts, signals, and recommendations as
  false until Batch C implements a production mapping.
- Added typed descriptor capability metadata with all-false defaults and
  included it additively in list/describe transport projections.
- Added four focused tests proving explicit capability round-trip, accurate
  all-false production discovery, structured CLI and generic Dashboard parity,
  and bounded trace-summary behavior without intelligence persistence.
- Focused B1 plus B2 tests passed 27/27. The first full validation run passed
  142 runtime tests but exposed a Ruff import-name collision; the dataclass
  helper was aliased without behavior change. The final `make validate` passed
  142 runtime tests, 21 repository-tool tests with 19 subtests, Ruff,
  compilation, repository boundary, synthetic samples, diff hygiene, package
  build, and eight release checks.
- Git diff review found no database/schema, production mapping, Copilot,
  connector, real-data, configuration, credential, or unrelated behavior
  change.
- Batch B2 is ready only for review. No Batch C, remote push, tag, PR, release,
  deployment, or `main` action was performed.

### 2026-07-27 — Phase 1 Batch B1 review corrections

- Configured all four new intelligence models to reject unknown fields instead
  of silently dropping misspelled optional references or other malformed
  output.
- Restricted `RESULT_CONTRACT_INVALID` classification to validation errors
  raised by `UseCaseResult` and the new intelligence contract models.
  Unrelated handler domain-model validation retains the existing
  `DOMAIN_VALIDATION_FAILED` classification.
- Added three focused regression tests: executor fail-closed behavior for an
  unknown intelligence field, unknown-field rejection by every intelligence
  model, and preservation of unrelated domain-validation classification.
- Focused tests passed 23/23. Final `make validate` passed 138 runtime tests,
  21 repository-tool tests with 19 subtests, Ruff, compilation, repository
  boundary, synthetic samples, diff hygiene, package build, and eight release
  checks.
- Git diff review found no database/schema, connector, real-data, configuration,
  credential, interface, descriptor, or unrelated behavior change.
- Batch B1 remains stopped for corrected review. No B2, remote push, tag, PR,
  release, deployment, or `main` action was performed.

### 2026-07-27 — Phase 1 Batch B1 validated

- Confirmed a clean planning worktree at exact approved commit `3d40633` and
  verified the Phase 1 design status is approved.
- Created independent branch `codex/phase-1-intelligence-contract` directly
  from that commit.
- Confirmed the historical pack sequence extends through IP-026 and registered
  IP-027 for the bounded Phase 1 intelligence contract implementation.
- Added typed subject, fact, signal, and recommendation models to the existing
  `UseCaseResult`; the three additive arrays default empty and contract version
  remains `1.0`.
- Added executor-level result revalidation, same-type ID uniqueness, bounded ID,
  reference-integrity, derived-fact, non-known-value, and proposal-confirmation
  checks. Invalid output is replaced with a clean failed result containing only
  safe warning code `RESULT_CONTRACT_INVALID`.
- Added 20 focused synthetic tests covering valid and empty output,
  unknown/unavailable/conflicting values, duplicate and bounded IDs, all
  reference levels, invalid semantics, and mutated handler output.
- Focused tests passed 20/20. Final `make validate` passed 135 runtime tests,
  21 repository-tool tests with 19 subtests, Ruff, compilation, repository
  boundary, synthetic samples, diff hygiene, package build, and eight release
  checks.
- Git diff review found no database/schema path changes, confidential values,
  credentials, configuration, real data, or unrelated behavior changes.
- Batch B1 is ready only for review. No B2, schema, connector, real-data,
  remote push, tag, PR, release, deployment, or `main` action was performed.

### 2026-07-27 — Delivery Intelligence phase planning

- Added the durable Phase 0 through Phase 9 Delivery Intelligence evolution
  plan, standard design/implementation/regression gates, definitions of ready
  and done, and cross-session continuation rules.
- Owner approved the phase sequence and standard delivery gates. This approval
  did not authorize Phase 1 implementation, a release tag, a merge, connector
  access, migration of an active database, or real-data operations.
- Added ADR-011 for phase-gated vertical-slice delivery and updated roadmap and
  repository navigation.
- Kept IP-024 and IP-026 as the only active implementation packs. No Phase 1
  implementation pack, runtime change, database migration, tag, merge,
  connector access, or real-data operation was performed.
- `make validate` passed for this uncommitted planning batch: repository
  boundary, synthetic samples, 115 runtime tests, 21 repository-tool tests with
  19 subtests, Ruff, compilation, diff check, and package build/inspection.
- Re-ran `make validate` after recording owner approval and remote CI evidence;
  the exact `a272890` working tree plus planning changes passed the same checks
  and built the `0.2.0rc1` wheel and source distribution.
- Confirmed the exact remote candidate HEAD `a272890` passed GitHub Actions run
  `30189452632`; Python 3.10 and 3.12 validation jobs, including install,
  upgrade, and rollback rehearsal, completed successfully.
- Confirmed by read-only remote-ref lookup that reserved tag `v0.2.0-rc.1`
  remains absent. No tag was created or pushed.
- Owner accepted `a272890` as the development evolution baseline and deferred
  the release tag, isolated operational-copy rehearsal, and real-environment
  UAT until the integrated candidate.
- Created independent branch `codex/delivery-intelligence-evolution-plan`.
  Updated the roadmap, evolution plan, ADRs, implementation-pack index, and UAT
  runbook status for the deferred gate. No runtime, schema, connector,
  real-data, tag, or `main` operation was performed.
- `make validate` passed after the deferral decision was fully recorded: 115
  runtime tests, 21 repository-tool tests with 19 subtests, Ruff, compilation,
  boundary and synthetic checks, diff check, package build, and eight release
  validation checks.
- Completed the Phase 1 Batch A inspection of the shared request/result model,
  executor, use-case registry, nine registered read-only use cases, structured
  CLI, generic Dashboard projection, Copilot operating instructions,
  execution-trace storage, database bootstrap, and contract tests.
- Drafted the bounded Phase 1 intelligence output contract: additive typed
  `facts`, `signals`, and `recommendations`; executor reference validation;
  descriptor capability metadata; Management Attention as the only production
  reference mapping; no schema change and no new recommendation behavior.
- No implementation pack was registered and no runtime or schema code was
  changed during Batch A. Owner design approval was recorded afterward.
- `make validate` passed for the Phase 1 design batch: boundary and synthetic
  checks, 115 runtime tests, 21 repository-tool tests with 19 subtests, Ruff,
  compilation, diff check, package build, and eight release validation checks.
- Owner completed review and approved the Phase 1 intelligence output contract.
  Batch B1 is ready for a new Codex task on dedicated branch
  `codex/phase-1-intelligence-contract`.
- This approval record changed no runtime, schema, implementation pack, tag,
  connector, real-data, remote branch, or `main` state.
- `make validate` passed after the approval and new-session handoff state were
  recorded.

### 2026-07-26 — IP-024 isolated migration rehearsal

- Repaired migration handling for dependent SQLite views and added rollback,
  integrity, concurrency, and legacy-dirty-data regression coverage.
- Synthetic isolated migration and rollback passed. Real operational data was
  not accessed.

### 2026-07-26 — IP-026 release engineering

- Added pinned unified validation, package/release identity, temporary
  wheel-install rehearsal, database upgrade/rollback rehearsal, and read-only
  GitHub Actions.
- Base commit `c2c0b16` is pushed and green on Python 3.10 and 3.12.
- No tag, publication, deployment, active-database migration, real record
  access, or merge into `main` was performed.

### 2026-07-26 — Repository context cleanup

- Removed obsolete runtime-baseline, portability-audit, release-readiness,
  reconstruction-prompt, nested Agent, legacy migration-wrapper, and unsafe
  direct project-profile writer files.
- Replaced repository onboarding, roadmap, portability status, and progress
  context with current candidate instructions.
- Owner selected the minimal candidate context: removed completed IP-000 through
  IP-023 and IP-025 packs/reports, retained only IP-024 and IP-026, and replaced
  the queue with a current candidate index. Removed material remains available
  from Git history.
- Validation passed: 115 runtime tests, 21 repository-tool tests, Ruff,
  compilation, boundary and synthetic checks, package build/inspection,
  temporary wheel installation, isolated synthetic database upgrade, and
  rollback.
- Context cleanup was committed as `c068beb` and pushed to
  `origin/codex/ip-000-baseline-safety`; no PR, tag, main-branch merge,
  publication, or deployment was performed.
