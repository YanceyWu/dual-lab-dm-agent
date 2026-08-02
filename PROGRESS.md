# DM Agent Evolution Progress

Last updated: 2026-08-02
Current branch: `codex/usability-r1-r2`
Current HEAD: R1 synthetic demo pipeline (revised with multi-state sample
data plus HIREF/contract-continuity demo), R2 synthetic walkthrough,
implemented, validated, and read-only reviewed; local commits on
`codex/usability-r1-r2` (exact hashes reported in the task handoff; IP-033
Phase 4 controlled assessment entry was accepted by the owner on 2026-08-02;
Phase 6 Weekly Brief v2 remains the promoted local baseline)
Package version: `0.2.0rc1`
Current implementation item: `R1 (REVISED, WITH HIREF DEMO) + R2 — MULTI-STATE SYNTHETIC DEMO DATA PIPELINE AND WALKTHROUGH (usability handoff 2026-08-02)`
Gate status: `USABILITY R1–R7 IMPLEMENTED AND OWNER-CONFIRMED; IP-033 ACCEPTED AND UAT RUNBOOK APPROVED ON 2026-08-02 — NEXT: OWNER DIRECTS THE NEXT BATCH (e.g., PHASE 7 DESIGN OR ENGINE COMPLETION ITEMS)`
Git state: the owner approved the design at local commit
`33fc6f100b36f6e54eec73e531590c186f4b0441` and separately authorized only
IP-032 Batch B1. The owner accepted the validated, reviewed B1 candidate at
`cce14e42c26c605bc76e895de8d611540eae06f8`. The owner has now explicitly
  authorized B2 and accepted its validated, independently reviewed local result
at `da093ba1b1f5dabc44053a2eb7edb4d237197768`. The owner then authorized only
B3 deterministic nine-section composition and accepted its validated local
result at `ce726f6c9e7bd334a5af3847141d0b66258a47b3`. The owner authorized
the corrected Batch C shared-interface implementation on 2026-08-01 and
accepted the validated, reviewed candidate at `3df79a1`. The owner authorized
Batch D on 2026-08-01; its combined regression, full validation, installed
rehearsal, and independent review passed. The owner promoted the validated,
reviewed Phase 6 Weekly Brief v2 candidate as the local Phase 6 development
baseline on 2026-08-01. On 2026-08-02 the owner authorized the Phase 4
controlled assessment entry slice (IP-033). It is implemented on
`codex/phase-4-assessment-entry`, passed focused and full validation plus
installed rehearsal, and after the R3 independent read-only review is stopped
for the owner acceptance decision. On 2026-08-02 the owner directed this
session to create `codex/usability-r1-r2` and complete R1 then R2 from the
usability handoff. R1 and R2 are implemented, validated (`make validate` 339
runtime tests plus repository/package checks; `make rehearse-release` passed),
and stopped at the review gate for owner review. The exact commit hashes are
reported in the task handoff because a commit cannot contain its own hash.
Promotion is local only; every external action remains a separate owner
decision. No push is authorized or required.
Do not push,
merge, tag, release, deploy, access a connector, or use real data without
separate authorization.

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
- Phase 6 Weekly Brief v2 is promoted as the local baseline: opt-in structured
  composition with explicit snapshot capture preview/confirm; legacy v1
  weekly brief and `pm report` remain unchanged.
- Phase 4 clean re-import confirmation now runs the deterministic
  seven-dimension assessment for every covered project and reports the real
  dimension states; `layered-project-health-review` reads those persisted
  assessments through the shared read-only contract.
- Staffing supports deterministic assessment and
  propose/preview/confirm/persist writes. Role is reference context rather than
  a hard eligibility constraint. HIREF number plus its project/date interval
  represents usable charge-code coverage.
- Dashboard writes use preview, explicit confirmation, one-time tokens,
  idempotency, and audit records.
- Database bootstrap owns idempotent migrations, integrity constraints,
  concurrency protection, hashed confirmation tokens, and dependent-view
  preservation.
- IP-031 adds a separate versioned clean-import prerequisite for workforce
  members, projects, plan versions, and monthly project allocations. It uses
  synthetic packages, authoritative coverage, preview/explicit confirmation,
  atomic publication, replay protection, audit, integrity reporting, and an
  additive rollback-compatible schema. That prerequisite itself adds no
  capacity derivation.
- IP-031 now also owns the accepted canonical capacity core and the authorized
  accepted Batch C: a generic read-only capacity heatmap plus capacity-aware
  Staffing assessment/confirmation behind a persisted marker that installs
  disabled. Only the separately named Project Health capacity-coverage reader
  and factor publication slice is now owner-accepted. Batch D validation,
  rehearsal, reporting, and review are complete, and IP-031 is now the promoted
  local Phase 5 baseline. The Phase 6 Weekly Brief v2 design is owner-approved;
  only IP-032 Batch B1 public read-contract prerequisites were subsequently
  authorized, implemented, validated, independently reviewed, and accepted.
  B2 requires a separate named authorization.
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
- Phase 3 canonical execution/Milestone/Dependency facts and Phase 4
  seven-dimension Project Health are promoted local baselines. Phase 4 remains
  a strangler comparison and creates no new Attention producer or legacy
  replacement. Their historical implementation gates remain in the change log;
  they are not current authorization. Phase 6 may consume only their promoted
  public read contracts.

## Current validation evidence

IP-033 (Phase 4 controlled assessment entry) focused Project Health
re-import suite passed 10/10 synthetic tests, including idempotent replay,
interrupted-attempt recovery, crashed-attempt reuse, and an end-to-end test
that the import-produced assessment is readable through
`layered-project-health-review`. The final post-review `make validate` passed
335 runtime tests, 21 repository-tool tests with 19 subtests,
repository-boundary and synthetic-sample checks, Ruff, compilation, diff
hygiene, package build, and 8 release-validation checks.
`make rehearse-release` passed wheel installation, isolated clean bootstrap,
synthetic upgrade, integrity, and rollback with the additive
`project_health_reimport_assessments` table.

R3 independent read-only review (2026-08-02) re-ran the recorded evidence on
the exact implementation commit `1d73765` (branch
`codex/phase-4-assessment-entry`): focused Project Health entry-point suites
passed 25/25; `make validate` passed 335 runtime tests, 21 repository-tool
tests with 19 subtests, repository-boundary and synthetic-sample checks, Ruff,
compilation, diff hygiene, package build, and 8 release-validation checks; and
`make rehearse-release` passed wheel installation, isolated clean bootstrap,
synthetic upgrade, integrity, and rollback. Full diff review of
`dd3d10f..1d73765` found no out-of-scope change and no P0–P2 finding; one P3
recovery-boundary observation is recorded in the risks and change log.
Acceptance remains an owner decision.

IP-032 Batch B1 final focused validation passed 35 synthetic tests covering the
new prerequisites plus Attention Center, Execution Review, layered Project
Health, project-capacity coverage, and connector read-boundary regression. The
final post-correction `make validate` passed 301 runtime tests, 21
repository-tool tests with 19 subtests, repository-boundary and synthetic-data
checks, Ruff, compilation, diff hygiene, package build, and 8 release-validation
checks. The first independent read-only implementation review found four P1 and
three P2 issues covering fail-open empty filters, Action completion windows,
Attention failed coverage, Execution evidence binding, Person-storage
coupling, global Project bounds, and continuity evidence. The second review
verified those corrections and found one P1 semantic-name issue plus one P2
field-specific validation-code issue. All accepted findings were corrected.
The third independent read-only review verified every correction and found no
remaining P0-P2 or new actionable finding. Reviewers made no file changes. B1
changes no schema, import, migration, packaging contract, or installed-data
behavior, so `make rehearse-release` is not required for this slice.

Phase 6 Weekly Brief v2 Batch A is documentation-only. Focused documentation
validation (`git diff --check` plus scope/gate/reference scans) passed. The
final post-correction `make validate` passed 297 runtime tests, 21
repository-tool tests with 19 subtests, repository-boundary and synthetic-data
checks, Ruff, compilation, diff hygiene, package build, and 8 release-validation
checks. The first independent read-only review found five P1 and one P2 design
or continuity issues; the second verified those core corrections and found one
P1 plus three P2 contract/continuity issues. All accepted findings were
corrected. The third independent read-only review verified every correction and
found no remaining P0-P2 or other actionable finding. Reviewers made no file
changes. Batch A changed no runtime, schema, tests, package, or installed
behavior, so `make rehearse-release` is not required at this design-only gate.

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
5. IP-027 through IP-031 are promoted local development baselines. IP-031 was
   promoted on 2026-08-01 from validated Batch D HEAD
   `c5ee57c49146eca179d0ccc2feaeeef0a7671d00`. Remote CI and remote branch state
   for IP-031 are `NOT_APPLICABLE` because no push is authorized.
6. Management Attention intentionally preserves its legacy `data` projection
   beside the typed intelligence projection. The rejected mapping-oriented
   configuration surface remains unavailable; retained additive storage is
   compatibility debt, not an accepted public contract.
7. Phase 3 execution and Milestone behavior is validated only with synthetic
   sessions. Company-specific field IDs, supported link types, connector
   behavior, and real-environment coverage remain `UNKNOWN`.
8. Phase 4 remains a strangler comparison. It has no new Attention producer and
   does not replace `project-health-review`. Its promoted Resource factor now
   consumes Phase 5 capacity coverage when that evidence is available; Quality
   and Governance remain unavailable until approved structured facts exist.
   The IP-033 slice makes the confirmed clean re-import the controlled
   assessment entry; concurrent duplicate confirmation of the same import
   session is not a supported workflow and could leave an unlinked assessment
   row, and a crashed attempt's orphan from an earlier session is not
   auto-recovered by a later session. Both are auditable and recorded in
   `implementation-packs/IP-033_PHASE_4_ASSESSMENT_ENTRY.md`. Review
   observation (P3, non-blocking): crash recovery reuses the newest
   same-project assessment run created after the session began, so a retry of
   an older session could in principle reuse an orphan left by a later
   session's crashed attempt; assessments are deterministic under the fixed
   catalog and the run remains auditable, and this boundary is accepted for
   the current slice.
9. Phase 5 is promoted locally. Skill Dependency and new Attention producers
   remain deliberately unimplemented. The owner approved the bounded Phase 6
   design and separately authorized only IP-032 Batch B1. Its additive Project,
   Attention, Action, and Execution public read prerequisites are accepted. No
   snapshot/schema, composer, interface, or later slice is authorized.
10. The existing synthetic import utility selects the execution month's
    allocation for active assignments. Its characterization test now verifies
    that temporal contract without hard-coding July; operational import
    readiness is not inferred from this test.

## Exact next actions

1. R3 (IP-033 acceptance) is at its review gate: the independent read-only
   review of `1d73765` passed with no P0–P2 finding, recorded in the change
   log and validation evidence. The owner must accept the slice or request a
   bounded correction. After acceptance, execute the remaining usability
   items one at a time and stop at each gate: R1 demo data rebuild, R2
   synthetic integration runbook, R5 integration test, R4 entry-boundary
   decisions, R6 UAT runbook revision, R7 documentation consistency scan.
2. Phase 6 Weekly Brief v2 remains the promoted local baseline. The next
   program gate is Phase 7 Forecast v1: it requires a separately approved
   design and a named implementation authorization.
3. Do not push, merge, tag, release, deploy, activate a connector, use real
   data, or start Phase 7 runtime/schema/test work without that authorization.
4. Do not activate Skill Dependency, create a new Attention producer, or infer
   a required Decision without separate authorization.
5. Preserve the promoted Phase 1–6 baselines and the accepted IP-032 records;
   IP-033 changes no promoted baseline until the owner accepts it.

## Decisions in force

- Do not merge or rebase this independent branch into `main`.
- Do not push any current work to `main`; use independent `codex/` branches.
- Do not create, move, or push a release tag without explicit owner approval.
- The real-environment UAT runbook is approved (2026-08-02, `UAT RUNBOOK
  APPROVED`) as the process basis; real-environment execution still requires a
  separate explicit authorization for an integrated release candidate.
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
- IP-029 B1 through D are implemented, validated, reviewed, and promoted as the
  local Phase 3 baseline. Those historical gates are closed; they do not grant
  authority for Phase 6 implementation or any later-phase action.
- The owner approved the Phase 6 design and separately authorized only IP-032
  Batch B1 public read-contract prerequisites. That authorization excludes B2,
  B3, C, D, and all external actions.
- R4 decision (2026-08-02): Phase 4 health configuration preview/confirm gets
  a controlled CLI as a separately authorized bounded batch; until then the
  product interface has no read or write configuration entry.
- R4 decision (2026-08-02): the Phase 5 capacity-aware Staffing marker stays
  Python-only and installs disabled; the product interface cannot enable
  capacity constraints (`staffing-effective-capacity-v1` applies only after a
  Python-session enable). Any future product entry needs a separate authorized
  batch with preview/confirm, audit, enable/disable semantics, release
  rehearsal, and independent review.
- R4 (b) addendum (2026-08-02): the owner authorized the enable entry;
  `pm staffing capacity-policy show|enable-preview|enable-confirm` is
  implemented with an additive audited operations table. Disable/revert is
  not provided (one-way engine); the marker still installs disabled.
- The owner approved the revised UAT runbook on 2026-08-02 (`UAT RUNBOOK
  APPROVED`). The runbook is the valid process basis; executing real-
  environment UAT still requires a separate explicit authorization for an
  integrated release candidate.
- IP-033 (Phase 4 controlled assessment entry) was accepted by the owner on
  2026-08-02 as a local development-baseline fix; Phase 7 and every external
  action remain separately gated.

## Recent change log

### 2026-08-02 — Owner accepted IP-033 and approved the UAT runbook

- The owner accepted the IP-033 Phase 4 controlled assessment entry
  (implementation `1d73765` on `codex/phase-4-assessment-entry`, R3
  independent review `0e7d077`).  Per the pack contract, acceptance promotes
  it only as a local development-baseline fix: the confirmed clean re-import
  now runs the deterministic seven-dimension assessment per covered project.
  This formalizes the dependency already used by the R1 demo pipeline and the
  R5 integration test.  It does not authorize Phase 7, promotion beyond the
  local baseline, or any external action.
- The owner approved the R6-revised real-environment UAT runbook
  (`docs/REAL_ENVIRONMENT_UAT_RUNBOOK.md`).  The approval is recorded as
  `UAT RUNBOOK APPROVED` and makes the runbook the valid process basis only;
  executing real-environment UAT still requires a separate explicit
  authorization for an integrated release candidate.
- Status files updated: `PROGRESS.md` header/gate, the IP-033 pack status,
  `implementation-packs/INDEX.md`, `ROADMAP.md`, and the runbook status.
- Documentation-only batch; `git diff --check` passes; `make validate` passes
  as part of the combined validation evidence (364 runtime tests plus
  repository/package checks).
- Commit status: committed locally on `codex/usability-r1-r2`, not pushed
  (no push instruction received for this batch).  No merge, tag, release,
  connector access, or real-data action.
- Exact next action: owner directs the next batch (e.g., Phase 7 Forecast
  design, engine completion items such as resource-dimension wiring, or the
  developer onboarding index); until then no further implementation runs.

### 2026-08-02 — Owner confirmed usability completion; branch pushed to origin

- The owner confirmed completion of the usability R1–R7 work and authorized
  pushing the branch.  `codex/usability-r1-r2` (HEAD `bc8d87c`) was pushed to
  `origin/codex/usability-r1-r2` on 2026-08-02 and its remote HEAD was
  verified equal to the local HEAD.  No pull request was created, no tag was
  pushed, no merge into `main` occurred, and no real-environment action took
  place.  This record commit was pushed afterwards, so the remote branch HEAD
  is this commit; the exact remote HEAD was reported in the task handoff.

### 2026-08-02 — R7: documentation status-consistency scan completed

- Owner authorized R7.  Scanned status declarations across PROGRESS, ROADMAP,
  architecture, implementation-packs/INDEX, agent instructions, and docs;
  dispositions applied below.  `PROGRESS.md` remains the single current-state
  authority.

| Location | Status statement | Difference vs PROGRESS | Disposition |
| --- | --- | --- | --- |
| `ROADMAP.md` | "IP-033 … awaits owner review"; duplicates current state | R3 independent review passed; slice awaits owner acceptance | Sentence fixed; header annotated "Current-state authority: PROGRESS.md" |
| `architecture/05_DELIVERY_INTELLIGENCE_EVOLUTION_PLAN.md` | "PHASE 5 PROMOTED — PHASE 6 BATCH A DESIGN AUTHORIZED" | Stale gate (Phase 6 promoted, Phase 7 not authorized) | Relabeled historical gate map; annotated |
| `architecture/07_PHASE_2_DELIVERY_ATTENTION_CENTER_DESIGN.md` | "PHASE 2 PROMOTED — IP-029 REGISTERED" | IP-029 long completed | Relabeled historical; annotated |
| `architecture/08_LAYERED_PROJECT_HEALTH_AND_MILESTONE_EVOLUTION.md` | "LAYERED HEALTH INTENT APPROVED — PHASE 4 DESIGN APPROVED" | Phase 4 implemented/promoted | Relabeled historical; annotated |
| `architecture/06_PHASE_1…`, `09_PHASE_3…`, `11_PHASE_4…`, `12_PHASE_5…`, `13_PHASE_6…` | Promoted labels | Consistent but duplicated | Added "Current-state authority: PROGRESS.md" |
| `implementation-packs/INDEX.md` | "PHASE 6 IP-032 PROMOTED LOCAL BASELINE"; Last updated 2026-08-01; IP-033 "review/acceptance required" | Stale date; IP-033 review passed; usability items missing | Status relabeled; date updated; IP-033 row corrected; usability-handoff note added; annotated |
| `implementation-packs/IP-033_…_ASSESSMENT_ENTRY.md` | "IMPLEMENTED LOCALLY — REVIEW/ACCEPTANCE REQUIRED" | R3 independent review passed | Status updated to "INDEPENDENT REVIEW PASSED — AWAITING OWNER ACCEPTANCE" |
| `.github/agents/delivery-manager.agent.md` | Direct-routing table | R4 (a)/(b) commands missing from the approved capability list | Added `pm project-health config show` and `pm staffing capacity-policy show` routes plus controlled preview/confirm workflows |
| `docs/REAL_ENVIRONMENT_UAT_RUNBOOK.md` | "DEFERRED — REVISE BEFORE INTEGRATED RELEASE UAT" | R6 revised the runbook | Status now "REVISED 2026-08-02 — PENDING OWNER APPROVAL — DO NOT EXECUTE" (R6 commit) |
| `docs/COPILOT_5_4_PROGRAM_CONTEXT.md` | Phase table 0–9 | Consistent; already declares PROGRESS precedence | No change |
| `docs/RELEASE_ENGINEERING.md`, `docs/LOCAL_PRODUCT_UPGRADE_LIFECYCLE.md`, `docs/SOURCE_PORTABILITY_REVIEW.md` | Durable decisions/status | Consistent, non-driftable | No change |
| `implementation-reports/IP-0xx` | Historical promoted labels | Historical by design; INDEX explains | No change |

- Outcome: ROADMAP/architecture/IP index no longer carry driftable current
  state without an explicit "以 PROGRESS.md 为准" annotation; agent
  instructions now match the promoted/approved capability list including the
  R4 commands.  Documentation-only batch: no runtime, schema, test, or
  sample-data change; `git diff --check` passes and `make validate` passed
  (evidence in the combined validation note below).  Read-only review pass
  found no remaining P0–P2 (same documented limitation: no sub-agent
  delegation in this session).
- Commit status: committed locally on `codex/usability-r1-r2`, not pushed;
  exact hash reported in the task handoff.  No merge, tag, release, connector
  access, or real-data action.
- Exact next action: owner review of R6 and R7 (including the runbook approval
  decision); no further usability items remain from the 2026-08-02 handoff.

### 2026-08-02 — R6: real-environment UAT runbook revised (documentation only)

- Owner authorized R6.  `docs/REAL_ENVIRONMENT_UAT_RUNBOOK.md` was revised
  against the current integration candidate; status is now
  `REVISED 2026-08-02 — PENDING OWNER APPROVAL — DO NOT EXECUTE`, and the
  runbook states that it becomes effective only after explicit owner approval
  recorded in `PROGRESS.md` as `UAT RUNBOOK APPROVED`.
- Alignment verified against the current candidate: setup/boundary on
  `codex/ip-000-baseline-safety` or an approved immutable tag; clean re-import
  rehearsal (empty DB + versioned workforce/capacity/health/milestone imports
  with dry-run → confirm and `already_completed`/`no_op` replay) plus
  upgrade-compatibility checks on isolated copies; pre-connector validation
  (`pm config validate`, `pm connector validate --portable`, `pm tool list`,
  `pm sync status`, explicit `pm connector probe`); the 14 current read-only
  use cases with the invalid-parameter fail-closed check; controlled
  configuration UAT (`pm project-health config show|preview|confirm`,
  R4 (a)); connector probe/sync one-at-a-time; staffing UAT including the
  capacity-policy marker (`pm staffing capacity-policy show|
  enable-preview|enable-confirm`, one-way enable, R4 (b)); Dashboard UAT with
  `/api/attention/operations`, `/api/weekly-brief/operations`, and
  `/api/project-health/sync` preview/confirm/replay checks and loopback
  binding; stop conditions; sanitized feedback; approval gate.
- Documentation-only batch: no runtime, schema, test, or sample-data change;
  `git diff --check` passes; `make validate` runs as part of the R6/R7
  combined validation evidence.
- Commit status: committed locally on `codex/usability-r1-r2`, not pushed;
  exact hash reported in the task handoff.  No real-environment action,
  connector access, or real-data use occurred.
- Exact next action: R7 documentation consistency scan; then owner review of
  R6 (and approval decision for the runbook).

### 2026-08-02 — R4 (b): controlled capacity-policy commands implemented

- The owner authorized the controlled product entry for the capacity-aware
  Staffing marker (overriding the earlier Python-only record for the enable
  direction).  Added `pm staffing capacity-policy show|enable-preview|
  enable-confirm` in `src/pm_agent/cli/commands/staffing_policy.py`, wrapping
  new public contracts in `database/staffing_capacity.py`:
  `policy_state`, `preview_enable_capacity_requirement(actor=...)`, and
  `confirm_enable_capacity_requirement`.
- Additive schema: `staffing_capacity_operations` (operation id, action,
  actor, status, token hash, fingerprint, preconditions, created/expires/
  confirmed timestamps, result) owned by the staffing-capacity module and
  composed by bootstrap — no table was added to `bootstrap.py` itself.  The
  enable applies the existing single-transaction guard (current publication
  required); confirm revalidates the fingerprint over the publication and
  policy state, so a replaced publication rejects with `STALE_FINGERPRINT`.
- Behavior: installation still leaves the marker disabled; preview is a
  no-op when already enabled; confirmation records actor `copilot` and the
  confirmed result in the audit table; the legacy Python API
  `enable_capacity_requirement` is unchanged and its implementation was
  refactored into a shared `_enable_in_transaction` helper without behavior
  change.  **Disable/revert is intentionally not provided** (one-way engine;
  recorded as a separate-extension boundary).
- Focused tests added in `src/tests/test_staffing_capacity_policy_cli.py`
  (7) plus a CLI build assertion: disabled default, publication-required
  fail-closed preview, round trip with audit, no-op when already enabled,
  wrong token, expired, stale fingerprint on publication replacement, and
  policy remains disabled after a stale rejection.  Existing Staffing
  capacity-consumption suite still passes (26/26 combined).  End-to-end smoke
  on an upgraded demo copy: bootstrap upgrade adds the table, show →
  preview → confirm → show (enabled) → repeat no-op.
- `docs/SYNTHETIC_DEMO_WALKTHROUGH.md` section 2.8 documents the commands;
  the Phase 5 design and IP-031 records carry the addendum.
- Validation: `make validate` passed 364 runtime tests (up from 356,
  recorded), 21 repository-tool tests with 19 subtests, Ruff, compilation,
  diff hygiene, package build, and 8 release checks; `make rehearse-release`
  passed (wheel install, isolated upgrade with the additive table, integrity,
  rollback).  Read-only review pass found no remaining P0–P2 (same documented
  limitation: no sub-agent delegation in this session).
- Commit status: committed locally on `codex/usability-r1-r2`, not pushed;
  exact hash reported in the task handoff.  No merge, tag, release, connector
  access, or real-data action.
- Exact next action: owner review of the (b) batch; R6/R7 remain independently
  authorizable.

### 2026-08-02 — R4 (a): controlled Project Health configuration CLI implemented

- Owner confirmed the proposed command shape; this separately authorized
  bounded batch adds `pm project-health config show|preview|confirm` under
  `src/pm_agent/cli/commands/project_health_config.py`, wired into the root
  CLI as `project-health`.  It wraps the existing Python contracts only:
  `catalog_projection` (read) and `configuration.preview` / `confirm`
  (write); no business capability, engine, schema, or data change.
- `show [--project <id>]`: fixed catalog, effective configuration,
  configuration version, and override state (JSON, `status: success`);
  unknown project fails closed with `PROJECT_NOT_FOUND`.
- `preview --tolerance-days N --scope-green-minimum P [--project <id>]`:
  bounded parameters (0-90 / 0-100, rejected by the CLI before the service),
  default or existing-project scope, `proposed` with operation id + token +
  prior/proposed/effective, or `no_op` when unchanged.
- `confirm --operation-id <id> --token <token>`: one-time confirmation with
  TTL, token hash, stale-fingerprint rejection, idempotent replay, and
  expired/rejected terminal states; JSON failures exit 2.
- Focused tests added in `src/tests/test_project_health_config_cli.py` (9)
  plus a CLI build assertion for the new group: round-trip,
  default vs project override scoping, no-op, wrong token, expired, stale
  fingerprint, unknown project, out-of-range parameter.  All pass 18/18 with
  the CLI build suite; end-to-end smoke on a demo copy verified
  preview → confirm → show reflects the new effective configuration.
- `docs/SYNTHETIC_DEMO_WALKTHROUGH.md` section 2.7 documents the commands;
  the R4 decision records already state the boundary and consequences.
- Validation: `make validate` passed (runtime test count increased and
  recorded in the validation evidence below).  No schema/import/packaging
  change, so `make rehearse-release` is not required for this batch.
  Read-only review pass found no remaining P0–P2 (same documented limitation:
  no sub-agent delegation in this session).
- Commit status: committed locally on `codex/usability-r1-r2`, not pushed;
  exact hash reported in the task handoff.  No merge, tag, release, connector
  access, or real-data action.
- Exact next action: owner review of the (a) batch; R6/R7 remain independently
  authorizable.

### 2026-08-02 — R4: entry-boundary decisions recorded

- R4 asked the owner to decide two "engine exists, entry missing" boundaries.
  The owner reviewed a code-grounded impact analysis and accepted the
  recommendation:
  1. Phase 4 health configuration preview/confirm (Python-only today):
     **add a controlled CLI as a separately authorized, bounded batch**.
     Until implemented, configuration stays Python-only and the boundary is
     explicit (no read or write entry via CLI/Dashboard/Copilot).  The future
     batch must also expose the read projection, keep the unaccepted Attention
     RAG surface separate, and decide actor attribution (one additive audit
     column if wanted).
  2. Phase 5 capacity-aware Staffing marker (Python-only today):
     **maintain Python-only**; the marker installs disabled and the product
     interface cannot enable capacity constraints.  Enabling changes Staffing
     to fail-closed effective-capacity consumption; any future product entry
     requires a separate authorized batch with preview/confirm, audit,
     enable/disable semantics, release rehearsal, and independent review.
- Decision records added to
  `architecture/11_PHASE_4_SEVEN_DIMENSION_PROJECT_HEALTH_DESIGN.md`,
  `architecture/12_PHASE_5_RESOURCE_INTELLIGENCE_DESIGN.md`, and
  `implementation-packs/IP-031_PHASE_5_RESOURCE_INTELLIGENCE.md`, including
  rationale and consequences; `PROGRESS.md` "Decisions in force" updated.
- Documentation-only batch: no runtime, schema, test, or sample-data change;
  `git diff --check` passes; no `make validate`/rehearse requirement beyond the
  standard documentation consistency checks (repository checks still run in
  the next validation batch).
- Read-only review pass found no remaining P0–P2 (same documented limitation:
  no sub-agent delegation in this session).
- Commit status: committed locally on `codex/usability-r1-r2`, not pushed;
  exact hash reported in the task handoff.  No merge, tag, release, connector
  access, or real-data action.
- Exact next action: owner confirms the proposed (a) command shape
  (`pm project-health config show|preview|confirm`), then the separately
  authorized (a) batch is implemented; R6/R7 remain independently authorizable.

### 2026-08-02 — R5: cross-capability integration test implemented and validated

- Owner explicitly authorized R5 after approving the R1 coherence gate and
  the HIREF demo addition.  Added
  `src/tests/test_usability_integration_chain.py`: one automated integration
  suite that builds the complete R2 chain on an empty temporary database via
  the documented commands (bootstrap → workforce import → resource capacity
  import → board registration → synthetic evidence seeding → Milestone import
  → Project Health re-import → Attention preview/confirm via CLI token flow →
  Weekly Brief v2 query and snapshot preview/confirm), then asserts the
  integrated results through the product interfaces.
- Acceptance assertions (all verified): the import-produced assessment is
  readable through `layered-project-health-review` (Atlas red) and
  `delivery-execution-review` is non-empty; after reconciliation the
  `delivery-attention-center` returns a coverage status plus ≥5 items across
  ≥4 rules and a repeat reconcile preview proposes zero changes;
  `weekly-dm-brief-v2` succeeds with an `overall_health` section that is
  `partial` (not `not_available`) and non-empty attention items; the snapshot
  preview/confirm flow works, reusing the pre-snapshot candidate is rejected
  as stale by design (the composer then includes the new baseline), a fresh
  composition carries `baseline_snapshot_id`, a second capture confirms, and
  the brief then exposes `changes_since_previous_snapshot: available`;
  re-running the structured imports is duplicate-free (`already_completed` /
  `no_op`) with unchanged row counts.
- During development the test surfaced the real snapshot-contract nuance:
  re-previewing the same candidate after the first snapshot is confirmed is
  rejected (`WEEKLY_BRIEF_CAPTURE_CANDIDATE_INVALID`) because recomposition
  then includes the baseline; this is the documented stale-candidate
  behavior, and the test now asserts it explicitly instead of expecting a
  misleading `already_confirmed`.
- Validation: R5 suite 4/4; `make validate` passed 346 runtime tests (up from
  342, recorded), 21 repository-tool tests with 19 subtests, synthetic-sample
  and repository-boundary checks, Ruff, compilation, diff hygiene, package
  build, and 8 release checks.  Test-only batch: no runtime, schema, import,
  packaging, or sample-data change, so `make rehearse-release` is not required
  for this batch.  Read-only review pass found no remaining P0–P2 (same
  documented limitation: no sub-agent delegation in this session).
- Commit status: committed locally on `codex/usability-r1-r2`, not pushed;
  exact hash reported in the task handoff.  No merge, tag, release,
  connector access, or real-data action.
- Exact next action: owner review of R5; the remaining usability items are
  R4 (entry-boundary decisions, owner decision required), R6 (UAT runbook
  revision, documentation), and R7 (documentation consistency scan), which
  may be authorized independently.

### 2026-08-02 — Owner approved R1 coherence gate; HIREF/contract-continuity demo data added

- Owner approved the current gate (`01c8d42`, R1 coherence correction) and
  requested that sample data demonstrate HIREF/contract-renewal capabilities,
  which the clean-import demo previously lacked.
- Extended `src/scripts/seed_demo_evidence.py` (idempotent, synthetic-only):
  member 001 is STFTE with a current HIREF and a registered renewal
  (`expiring_with_next`); member 002 is STFTE expiring 2026-09-30 without a
  renewal (`critical`, `requires_action`); member 003 is STFTE with no current
  contract (`missing_current_hiref`); one free HIREF slot and one open
  staffing placeholder demonstrate the slots/placeholders views.  `_clear`
  resets the demo members' legacy columns and deletes the seeded rows, so
  `--replay` remains duplicate-free (verified: hiref=4, placeholders=1,
  stfte=3, attention=8, assessments=2, snapshots=1 before and after replay).
- Verified demo outputs: `pm hiref summary` shows STFTE 3 / missing 1 /
  expiring-without-next 1 / expiring-with-next 1 / free slots 1 / open
  placeholders 1; `pm hiref review` lists member-003 (missing, critical),
  member-002 (59 days, critical), member-001 (ok); `pm hiref slots` shows one
  free and one reserved-for-next slot; `contract-continuity-review` returns
  success with 2 contracts, `attention_count: 2`, `reviewed_count: 3`.
- Added a focused demo test for the HIREF states; updated the demo counts
  test (hiref=4, staffing_placeholders=1) and the walkthrough/README.
- Validation: focused demo + HIREF suites 13/13; `make validate` passed 342
  runtime tests, 21 repository-tool tests with 19 subtests, synthetic-sample
  and repository-boundary checks, Ruff, compilation, diff hygiene, package
  build, and 8 release checks; `make rehearse-release` passed.  Read-only
  review pass found no remaining P0–P2 (same documented limitation: no
  sub-agent delegation in this session).
- Commit status: committed locally on `codex/usability-r1-r2`, not pushed;
  exact hash reported in the task handoff.  No merge, tag, release,
  connector access, or real-data action.
- Exact next action: owner review of the HIREF demo addition; after explicit
  authorization, start R5 (cross-capability integration test) on this branch.

### 2026-08-02 — R1 coherence correction: member load and monthly allocation now agree

- Owner correctly flagged that the multi-state demo was internally
  inconsistent: `member-synthetic-001` showed 1.2 legacy load (fabricated to
  trigger the overload Attention rule) against a 0.5 canonical monthly
  allocation.  This entry records the correction; it supersedes the overload
  hack described in the previous revision entry.
- Corrected by making the two data worlds agree from the source: the versioned
  `workforce_planning_import.sample.json` now includes
  `member-synthetic-003` (analyst) and a second active project
  `project-synthetic-beacon`, with a full 3×2 allocation matrix (member 001 =
  0.5 Atlas / 0.0 Beacon, member 002 = 0.0/0.0 explicit zeros, member 003 =
  0.6 Atlas + 0.6 Beacon = 1.2 genuinely overloaded).  The capacity sample
  gained member 003 observations (3 derivations / 9 observations).  Legacy
  `assignments` now mirror the canonical allocations exactly (001 = 0.5,
  002 = 0.0/no row, 003 = 1.2), so the legacy load view, the capacity
  heatmap, and the overload Attention rule all agree.
- Demo topology updated for coherence: `jira_board_configs.sample.csv` gains
  `beacon-board` (→ `project-synthetic-beacon`), the health re-import package
  covers both boards, the Milestone sample gains two Beacon milestones, and
  the seed script provides Beacon legacy snapshots (amber) without source
  evidence, so Beacon shows an honest `unknown`/partial assessment contrast
  to Atlas's red.
- Verified per-member agreement on the committed demo database: load vs
  allocation = 0.5/0.5 (001), 0.0/0.0 (002), 1.2/1.2 (003); heatmap rows
  3 with member 003 `overload_state: red`; Attention Center 8 items across 5
  rules (project health Atlas critical + Beacon high, critical milestone
  overdue, resource overload 003, overdue action, 3 source-freshness items);
  layered review 2 assessments (Atlas red, Beacon unknown); Weekly Brief v2
  project_count 2, overall red, 10 statements.
- Test and tooling updates: sample-derived assertions in workforce/capacity
  import, heatmap, project capacity coverage, staffing consumption, demo
  characterization, and `tools/rehearse_release.py` were updated to the
  coherent 3-member/2-project sample (including installed-member-003 overload
  and project-health capacity red assertions).  Focused suites passed 94/94;
  `make validate` passed 341 runtime tests plus repository/package checks;
  `make rehearse-release` passed wheel install, isolated upgrade, integrity,
  and rollback.
- Read-only review: separate read-only pass over the correction diff against
  the owner's coherence requirement; no remaining P0–P2 findings (same
  documented limitation: no sub-agent delegation in this session).
- Commit status: committed locally on `codex/usability-r1-r2`, not pushed;
  exact hash reported in the task handoff.  No merge, tag, release,
  connector access, or real-data action.
- Exact next action: owner review; after authorization, start R5 on this
  branch.

### 2026-08-02 — R1 revision: multi-state synthetic demo data (owner request)

- Owner requested demo data that shows both usable and unusable states
  instead of an all-`unknown`/`not_available` database.  This revision is
  sample-data and test tooling plus two minimal contract fixes; no new
  business capability was added.
- Added `src/scripts/seed_demo_evidence.py`: deterministic, idempotent
  synthetic seeding into existing tables (authoritative `source_evidence_runs`
  + cursors + published items, `jira_issue_events`, `jira_issues`,
  `jira_stream_versions`, `jira_sprints`, `jira_health_snapshots`,
  `confluence_status_snapshots`, one overdue `action_items` row, two active
  `assignments` for an overloaded member, and one inactive second project
  that exists only so the legacy load view can exceed 100% without widening
  the active-project manifest).  All rows are `SYNTHETIC_DATASET_V1`-marked
  and the script deletes its own prior rows, so `--replay` is duplicate-free.
- Reordered the pipeline: bootstrap → workforce → capacity → board
  registration → evidence seeding → Milestone import → Project Health
  re-import → Attention reconciliation → Weekly Brief v2 snapshot.  Milestone
  and evidence data now precede the IP-033 assessment, and the separate
  derivation replay step was removed (the single in-entry derivation sees all
  inputs).  This supersedes the previous "assessment runs before Milestone
  import / schedule stays unknown" limitation recorded in the R1 entry.
- Demo states now verified: Project Health `overall red` with
  `schedule=red` (critical milestone overdue guard), `scope=amber`
  (release completion below green minimum), `dependency=unknown`,
  `delivery/quality/resource/governance=not_available` (no approved
  producer, reserved structured input family, and the IP-033 entry does not
  pass a capacity scope, respectively); Delivery Attention Center shows 6
  items across 5 rules (project health red, critical milestone overdue,
  resource overload, overdue action, two source-freshness items); execution
  review shows sprint + release + milestone layers; Weekly Brief v2 overall
  `red` with 8 statements and non-empty next-actions; achievements stay empty
  on snapshot day per the event-window contract.
- Minimal contract fixes surfaced by the richer data (same defect class as
  the R1 fixes): `delivery_execution_review` now emits `value=None` for
  non-`known` facts (the `release_target_date_change` fact is `unknown` with
  a value, which failed executor validation), and `project_health/evaluation`
  latest-run tie-break now uses creation order (`rowid`) instead of random
  `derivation_run_id` ordering.  Both have focused regression tests.
- `tools/rehearse_release.py` assertions became demo-content-relative:
  `jira_issue_events` upgrade count is `before + 1` and the installed-run
  cursor check is scoped to the rehearsal's own source/board/dataset, so the
  richer demo database no longer breaks the release rehearsal.
- Validation: focused suites passed 23/23 (demo characterization, Project
  Health re-import, execution review, layered health, weekly brief shared
  interface); `make validate` passed 341 runtime tests, 21 repository-tool
  tests with 19 subtests, synthetic-sample and repository-boundary checks,
  Ruff, compilation, diff hygiene, package build, and 8 release checks;
  `make rehearse-release` passed wheel install, isolated upgrade, integrity,
  and rollback.
- Read-only review: separate read-only pass over the revision diff against
  the owner request and `AGENTS.md`; no remaining P0–P2 findings.  Same
  documented limitation as before: sub-agent delegation was unavailable, so
  the review was executed by the implementing agent read-only.
- Commit status: committed locally on `codex/usability-r1-r2`, not pushed;
  exact hash reported in the task handoff.  No merge, tag, release,
  connector access, or real-data action.
- Exact next action: owner review of the revised demo; after authorization,
  start R5 on this branch.

### 2026-08-02 — R2: synthetic integration walkthrough documented and reviewed

- Added `docs/SYNTHETIC_DEMO_WALKTHROUGH.md` per R2 of
  `docs/USABILITY_REQUIREMENTS_HANDOFF_2026-08-02.md`: from-clean-database
  walkthrough of the full DM weekly workflow with commands, expected-output
  points, and troubleshooting for every step.
- Coverage verified against the acceptance criteria: clean DB → all structured
  imports → derivation → seven-dimension assessment → Attention
  reconciliation → Weekly Brief v2 composition including snapshot
  preview/confirm → Dashboard/CLI reads; idempotent `--replay` section;
  explicit UNKNOWN section (real connectors, real data, UAT, external branch
  actions, R3/R4 gates, Phase 7, legacy-view semantics, missing re-assessment
  entry).
- Live verification of the documented commands: one-command build,
  the five R1 verification commands, the manual snapshot preview/confirm flow
  (`previewed` → `confirmed` → `already_confirmed` with the same idempotency
  key), `--replay` output, and heatmap values quoted in the document
  (0.7/0.9 effective capacity). One document defect was found and corrected
  during verification: the capture candidate lives under
  `data.snapshot.capture_candidate` in the CLI query output, not
  `snapshot.capture_candidate`.
- Read-only review: separate read-only pass over the document against the R2
  acceptance list and `AGENTS.md`; no remaining P0–P2 findings. As recorded in
  the R1 entry, sub-agent delegation was unavailable in this session, so the
  review was executed by the implementing agent in a read-only capacity.
- `git diff --check` passes. R2 is documentation-only: no runtime, schema,
  test, sample-data, or package change; `make rehearse-release` is not
  required for this batch. Full `make validate` evidence for the combined
  R1+R2 working tree is recorded in the R1 entry (339 runtime tests,
  repository/package checks) and was re-run after R1's final commit; the R2
  document adds no runtime surface.
- Commit status: R2 is committed locally on `codex/usability-r1-r2` and NOT
  pushed; the exact hash is reported in the task handoff. No merge, tag,
  release, connector access, or real-data action was performed.
- Exact next action: owner review of R1+R2; after explicit authorization,
  start R5 (cross-capability integration test) on this branch.

### 2026-08-02 — R1: reconstructed synthetic demo data pipeline implemented and validated

- Owner directed this session to create `codex/usability-r1-r2` (from
  `0e7d077`) and complete R1 then R2 from
  `docs/USABILITY_REQUIREMENTS_HANDOFF_2026-08-02.md`. This entry covers R1
  only; R2 is the next named batch and was not started.
- Rebuilt `src/sample-data/demo/sample_pm.db` through one repeatable command
  (`src/scripts/load_sample_data.py --force`) from an empty database using the
  versioned clean re-import path: bootstrap → workforce planning import →
  resource capacity import → board registration (data prerequisite of the
  IP-033 entry) → Project Health re-import (derivation + seven-dimension
  assessment, IP-033 entry) → canonical Milestone import → one deterministic
  derivation replay (existing `execution.derive_board` API, fingerprint
  idempotent, so Milestone facts are readable) → Delivery Attention
  reconciliation → confirmed Weekly Brief v2 snapshot. `--replay` re-runs the
  chain idempotently on an existing database.
- Added `src/scripts/import_milestones.py` and
  `src/sample-data/json/milestone_import.sample.json`; updated
  `project_health_reimport.sample.json` (board `atlas-board`) and
  `jira_board_configs.sample.csv` (board maps to the structured project
  `project-synthetic-atlas`); documented build/replay/verification commands in
  `README.md` and `src/sample-data/README.md`.
- The demo database now contains the versioned clean-import organization
  (`member-synthetic-001/002`, `project-synthetic-atlas`,
  `plan-synthetic-baseline-001`), not the legacy Excel-imported Example
  organization; the versioned imports require an empty target, so the legacy
  importers are not part of this pipeline.
- R1 acceptance verification passed: the five documented commands
  (`layered-project-health-review`, `delivery-execution-review`,
  `delivery-attention-center`, `resource-capacity-heatmap`,
  `weekly-brief query`) each return non-empty, contract-compliant results for
  the demo database; one project has a `completed` seven-dimension assessment
  (`assessment_state` per IP-033 semantics; overall state `unknown` because
  the assessment runs before Milestone import per the handoff order and
  Quality/Resource/Governance inputs are intentionally absent); replay is
  duplicate-free for assessments, attention items, derivation runs, milestones,
  and snapshots; the synthetic sample checker passes.
- Accepted defect corrections surfaced by the integration pipeline (no new
  business capability; minimal changes in the owning modules):
  1. `pm_agent.database.execution_review`: latest-run tie-break changed from
     random `derivation_run_id` string order to creation order (`rowid`) so
     two derivation runs finishing in the same second resolve to the newest
     run (previously the health-reimport run could shadow the Milestone replay
     run and hide all facts).
  2. `pm_agent.use_cases.layered_project_health`: facts for non-`known`
     assessment states now emit `value=None` (data/context still carry the
     full assessment), matching the executor contract that non-known facts
     must not carry a value; previously an `unknown` assessment failed the
     executor validation (`RESULT_CONTRACT_INVALID`) even though the handler
     unit test bypassed the executor.
  3. `pm_agent.use_cases.weekly_brief_v2`: same non-known value contract fix
     for brief facts.
  Each correction has a focused regression test; the two existing unit tests
  that enshrined the invalid behavior were corrected.
- Validation evidence: focused suites (demo characterization, layered health,
  execution review, weekly brief shared interface, Project Health re-import,
  weekly brief prerequisites/snapshots, intelligence contract) passed 68/68;
  `make validate` passed 339 runtime tests, 21 repository-tool tests with 19
  subtests, repository-boundary and synthetic-sample checks, Ruff,
  compilation, diff hygiene, package build, and 8 release-validation checks;
  `make rehearse-release` passed wheel installation, isolated clean bootstrap,
  synthetic upgrade, integrity, and rollback.
- Independent read-only review: performed as a separate read-only review pass
  over the full diff against the handoff and `AGENTS.md`; no remaining P0–P2
  findings. Limitation recorded honestly: sub-agent delegation was unavailable
  in this session (two spawned reviewer agents reported the task message did
  not reach them), so the review was executed by the implementing agent in a
  read-only capacity; the owner may request a genuinely separate reviewer.
- Unresolved risks / known boundaries: (a) the assessment is derived before
  Milestone import per the documented order, so `schedule` stays `unknown`
  until a re-assessment entry is separately authorized; (b) each `--replay`
  run creates one expiring proposed Attention preview audit row (no new items)
  and does not create a second Weekly Brief snapshot when one already exists
  for the demo idempotency key; (c) the three runtime defect corrections await
  owner acceptance; (d) `prompts/INTERNAL_FEATURE_EFFECTIVENESS_REVIEWER.md`
  remains untracked and was not staged.
- Commit status: R1 changes are committed locally on
  `codex/usability-r1-r2` and NOT pushed; the exact commit hash is reported in
  the task handoff. No merge, tag, release, connector access, or real-data
  action was performed.
- Exact next action: owner review of R1; after explicit authorization, start
  R2 (synthetic integration walkthrough) on this branch.

### 2026-08-02 — R3: IP-033 independent read-only review completed

- Reviewed `dd3d10f..1d73765` against
  `implementation-packs/IP-033_PHASE_4_ASSESSMENT_ENTRY.md` on branch
  `codex/phase-4-assessment-entry`. Scope matches the pack: schema, service,
  focused tests, and documentation only; no evaluation-engine, configuration,
  Attention, connector, or real-data change.
- Verified the flow in code: preview lists `health_assessment`; `confirm_reimport`
  derives boards, runs one deterministic seven-dimension assessment per
  covered project through `project_health.evaluation.evaluate`, links each run
  in the additive `project_health_reimport_assessments` table, and reports
  real dimension states, an `assessments` summary, and
  `assessment_run_count`; `assessment_state` is `completed` for a non-empty
  covered package and `not_available` for an empty package. Bootstrap composes
  the DDL from the dedicated `project_health_schema` module; no table was
  added to `database/bootstrap.py`.
- Re-ran evidence on the exact commit: focused Project Health entry-point
  suites passed 25/25; `make validate` passed 335 runtime tests, 21
  repository-tool tests with 19 subtests, Ruff, compilation, diff hygiene,
  package build, and 8 release checks; `make rehearse-release` passed wheel
  installation, isolated clean bootstrap, upgrade, integrity, and rollback.
- Findings: no P0–P2. One P3 observation recorded: crash recovery reuses the
  newest same-project assessment run created after the session began, which
  could in principle reuse an orphan from a later session's crashed attempt;
  results are deterministic and auditable, so this does not block review.
- Conclusion: the reviewer recommends acceptance; the acceptance decision
  remains with the owner. No promotion, push, merge, tag, or external action
  was performed. `prompts/INTERNAL_FEATURE_EFFECTIVENESS_REVIEWER.md` remains
  an untracked working-tree file and was not staged.

### 2026-08-02 — Usability requirements handoff recorded

- Recorded R1–R7 usability requirements with acceptance criteria in
  `docs/USABILITY_REQUIREMENTS_HANDOFF_2026-08-02.md`, including the demo
  data rebuild, synthetic integration runbook and test, IP-033 acceptance,
  entry-boundary decisions, UAT runbook revision, and documentation
  consistency scan.
- The handoff includes a copy-ready session prompt; it changes no runtime,
  schema, test, or data. `PROGRESS.md` remains the single source of truth.

### 2026-08-02 — IP-033 Phase 4 controlled assessment entry implemented and validated

- The owner authorized the Phase 4 controlled assessment entry on
  2026-08-02 after the Phase 1–6 feature-effectiveness review found that the
  seven-dimension assessment engine had no production entry point.
- `confirm_reimport` now runs `project_health.evaluation.evaluate` once per
  covered project after canonical derivation, links each assessment run to the
  import session in the new additive `project_health_reimport_assessments`
  table, and reports real dimension states plus an `assessments` summary.
- Sequential replay is idempotent: linked assessments are skipped, and an
  assessment left by a crashed attempt is reused instead of re-evaluated.
- No standalone CLI, Dashboard endpoint, Attention producer, connector, real
  data, or Phase 7 work was added. The controlled write boundary remains the
  import preview/confirm path.
- Validation: 10/10 focused re-import tests, `make validate` with 335 runtime
  tests and 21 repository-tool tests, and `make rehearse-release` passed with
  clean bootstrap, upgrade, integrity, and rollback.
- Recorded risks: concurrent duplicate confirmation of one session is not a
  supported workflow; cross-session orphan recovery is limited to the same
  session. Branch is stopped for owner review; no promotion, push, merge, tag,
  or external action was performed.

### 2026-08-01 — Phase 6 Weekly Brief v2 promoted locally

- The owner promoted the validated, independently reviewed Phase 6 Weekly
  Brief v2 candidate as the local Phase 6 development baseline on 2026-08-01.
- Promotion covers the accepted B1 public read contracts, B2 snapshot and
  comparison core, B3 nine-section composition, Batch C shared-interface
  integration, and the Batch D regression/rehearsal/review record.
- Promotion is local only. No push, merge, tag, release, deployment,
  connector, real-data, producer, or external action was performed.
- Exact next action: Phase 7 Forecast v1 requires a separately approved
  design and named authorization.

### 2026-08-01 — IP-032 Batch D validated and reviewed

- The owner explicitly authorized Batch D regression/promotion preparation on
  2026-08-01.
- Combined focused regression passed 78 tests covering the Weekly Brief v2
  composer, snapshot, shared-interface, and prerequisite suites plus weekly
  report, unified discovery/transport, Attention Center, layered Project
  Health, execution review, Resource capacity, and Delivery Manager agent
  routing.
- `make validate` passed: 332 runtime tests, 21 repository-tool tests (19
  subtests), Ruff, compilation, diff check, package build, and 8 release
  validation checks.
- `make rehearse-release` passed: wheel install, clean bootstrap, isolated
  prior-runtime upgrade and rollback, additive Weekly Brief capture
  preview/confirm/replay/stale/concurrent checks, and legacy weekly behavior
  preservation.
- The independent read-only review covered contracts, privacy, clean import,
  schema, rollback, traceability, freshness, and legacy compatibility and
  found no remaining P0-P2 actionable finding.
- No promotion, push, merge, tag, release, deployment, connector, real-data,
  producer, or external action was performed.
- Exact next action: owner decides promotion, revision, or rejection of the
  Phase 6 Weekly Brief v2 baseline.

### 2026-08-01 — IP-032 Batch C accepted

- The owner accepted the validated, independently reviewed Batch C
  shared-interface implementation at local commit
  `3df79a1` (opt-in `weekly-dm-brief-v2` use case, dedicated `pm weekly-brief`
  CLI, dedicated Dashboard operations endpoint, Copilot contract, and the
  focused shared-interface suite).
- Acceptance covers the shared-interface/legacy-strangler integration only.
  Batch D regression/promotion and every external action remain separately
  unauthorized. No push, merge, tag, release, deployment, connector,
  real-data, producer, or external action was performed.
- Exact next action: explicitly authorize, revise, or decline named Batch D
  (combined focused regression, `make validate`, `make rehearse-release`,
  independent review, and promotion decision).

### 2026-08-01 — IP-032 Batch C shared interface implemented, reviewed, corrected, and owner-authorized

- Independently reviewed the uncommitted Batch C working tree: the opt-in
  `weekly-dm-brief-v2` use-case registration, dedicated `pm weekly-brief`
  query/preview/confirm CLI, the dedicated Dashboard
  `/api/weekly-brief/operations` preview/confirm endpoint, and the controlled
  capture facade.
- Defects fixed: the Copilot contract
  `.github/agents/delivery-manager.agent.md` did not register
  `weekly-dm-brief-v2` and lacked the snapshot-capture explicit-approval
  workflow, which failed `test_delivery_manager_agent`; the typed
  intelligence projection mislabeled subject kinds and dropped known section
  states; and the Dashboard operations endpoint omitted the interface-contract
  header. Added a focused shared-interface suite covering the use case, CLI,
  Dashboard, generic transport v1 boundary, legacy parity, and typed
  projection.
- Validation passed: 332 runtime tests, 21 repository-tool tests (19
  subtests), Ruff, compilation, diff check, package build, and 8 release
  validation checks via `make validate`.
- The owner explicitly authorized Batch C implementation on 2026-08-01 after
  the corrected, validated candidate review, and selected the existing opt-in
  `weekly-dm-brief-v2` routing design without change. No push, merge, tag,
  release, deployment, connector, real-data, producer, or external action was
  performed.
- Exact next action: record the owner acceptance of the validated Batch C
  candidate; then Batch D requires a separate owner authorization.

### 2026-08-01 — IP-032 Batch B3 accepted

- The owner accepted the validated, independently reviewed B3 deterministic
  nine-section composition at local commit
  `ce726f6c9e7bd334a5af3847141d0b66258a47b3`.
- Acceptance covers only the non-routed composer, public-contract composition,
  B2 lookup/recompose seam, and related compatibility/rehearsal evidence.
- Batch C shared-interface/legacy strangler integration and Batch D promotion
  remain separately unauthorized. No push, merge, tag, release, deployment,
  connector, real-data, producer, or external action is authorized.
- Exact next action: explicitly authorize, revise, or decline named Batch C.

### 2026-08-01 — IP-032 Batch B3 implemented and independently reviewed

- Added only `pm_agent.weekly_brief` B3 composition and focused synthetic tests:
  fixed nine sections, public-reader-only aggregation, explicit partial or
  unavailable evidence, typed facts/signals/recommendations, reference chains,
  exact baseline selection, and the B2 injected lookup/recompose seam.
- No route, CLI, Dashboard, Copilot registration, legacy replacement, producer,
  connector, Staffing, Decision write, real data, or external action was added.
- Final focused suite passed 28 tests; `make validate` passed 325 runtime tests,
  21 repository-tool tests (19 subtests), Ruff, compilation, package build, and
  release checks. `make rehearse-release` passed clean bootstrap, installed
  capture stale/concurrency/idempotency behavior, and prior-runtime additive
  rollback preservation. Independent read-only final review found no P0-P2.
- Exact next action: owner accept, revise, or reject B3. Do not enter C/D.

### 2026-08-01 — Phase 6 design approved; IP-032 Batch B1 implemented

- Recorded owner design approval and the separate authorization for only Batch
  B1 public read-contract prerequisites.
- Registered `implementation-packs/IP-032_PHASE_6_WEEKLY_BRIEF_V2.md` and added
  owner-local active Project manifest, Attention current/history, Action
  current/completion, and Execution event-time contracts.
- Kept Action and non-Project Attention project associations explicitly
  unavailable rather than inferring from names, prose, sources, assignments, or
  private tables. Milestone event precision remains an explicit date.
- Reused the promoted Project Health, Resource, and source-state readers. No
  schema, bootstrap, import, write, Weekly v2 interface, new producer, Staffing,
  Decision, connector, or real-data behavior changed.
- Final focused B1 plus related public-contract regression passed 35 synthetic
  tests. The final `make validate` passed 301 runtime tests and the complete
  repository/static/build suite. Three independent read-only reviews found and
  corrected four P1/three P2, then one P1/one P2; the final review found no
  remaining P0-P2 or actionable finding.
- Exact next action: commit the completed B1 candidate locally and stop for
  owner acceptance, revision, or rejection. Passing checks does not authorize
  B2.

### 2026-08-01 — IP-032 Batch B1 accepted

- The owner accepted the validated and independently reviewed Batch B1 candidate
  at local commit `cce14e42c26c605bc76e895de8d611540eae06f8`.
- Acceptance covers only the registered public read-contract prerequisites:
  canonical Project manifest, Attention current/history and safe coverage,
  Action current/completion, and evidence-bound Execution event time.
- No schema, snapshot/history operation, Weekly v2 composition/interface,
  producer, connector, real-data, release, or remote action is accepted or
  authorized by this decision.
- Exact next action: separately authorize or decline named Batch B2. B1
  acceptance and its passing evidence do not authorize B2.

### 2026-08-01 — IP-032 Batch B2 authorized

- The owner explicitly authorized only Batch B2 Weekly Brief snapshot/comparison
  core after accepting B1. B2 is bounded to capability-owned additive snapshot
  schema, controlled preview/confirm persistence, integrity, synthetic tests,
  clean-bootstrap rehearsal, and rollback preservation.
- B3 v2 composition, public route/CLI/Dashboard/Copilot integration, legacy
  replacement, Attention producers, Staffing/confirmation changes, connectors,
  real data, push, merge, tag, release, and deploy remain unauthorized.
- Exact next action: implement and independently review B2, correct accepted
  findings, then stop for owner acceptance or revision.

### 2026-08-01 — IP-032 Batch B2 implemented and independently reviewed

- Added only the capability-owned Weekly Brief v2 snapshot/history core:
  additive schema composition, atomic preview/confirm capture, immutable
  confirmed history, typed anonymous envelope validation, deterministic
  comparison primitive, fingerprints, baseline integrity, and safe errors.
- Installed release rehearsal proves clean bootstrap; preview/confirm, replay,
  stale and concurrent confirmation; and prior-runtime legacy
  `WeeklyReportService` from local baseline `8cb5f69` preserves two confirmed
  snapshot rows. No B3 composer, public v2 route, legacy replacement, producer,
  connector, real data, or external action was added.
- Focused Weekly Brief tests passed 9; final `make validate` passed 310 runtime
  tests and 21 repository-tool tests (19 subtests); final
  `make rehearse-release` passed. A repeated independent read-only final review
  found no P0-P2 findings.
- Exact next action: owner acceptance, revision, or rejection of B2. B3 and all
  later slices remain unauthorized.

### 2026-08-01 — IP-032 Batch B2 accepted; B3 authorized

- The owner accepted the locally committed B2 snapshot/comparison core at
  `da093ba1b1f5dabc44053a2eb7edb4d237197768` after its validation and repeated
  independent review.
- The owner explicitly authorized only B3 deterministic nine-section
  composition. C shared-interface integration, D promotion, routes, legacy
  replacement, producers, connectors, real data, and external actions remain
  unauthorized.
- Exact next action: implement, validate, and independently review B3; then
  stop for owner acceptance or revision.

### 2026-08-01 — Phase 6 Weekly Brief v2 Batch A design completed

- Confirmed the exact required workspace, branch
  `codex/phase-6-weekly-brief-design`, baseline HEAD
  `7442f52cb5fc015c4efdcf20941293314f71e9db`, and clean worktree before
  discovery. No reset, stash, cleanup, or user-change mutation occurred.
- Inspected the actual legacy and structured Weekly Brief paths,
  `WeeklyReportService`, project snapshot/history schema, Attention Center,
  layered Project Health, execution review, Resource Intelligence, Action,
  Decision, source freshness, shared executor/transport, and focused tests.
- Added `architecture/13_PHASE_6_WEEKLY_BRIEF_V2_DESIGN.md`. It defines an
  explicit opt-in v2 strangler contract, nine fixed sections, statement-level
  evidence/freshness, fail-closed new/continuing/resolved semantics, one minimal
  capability-owned derived snapshot table, clean-bootstrap/rollback behavior,
  deterministic/model boundaries, synthetic scenarios, and separately gated
  B1/B2/B3/C/D slices.
- The design preserves empty-parameter `weekly-dm-brief`, `pm report`, project
  snapshots, and all Phase 1–5 storage. It does not register an implementation
  pack or change runtime, schema, tests, connectors, real data, Attention,
  Staffing, Action, Decision, release, or remote state.
- Focused documentation validation and the final post-correction
  `make validate` passed. Three independent read-only review rounds corrected
  all accepted contract and continuity findings; the final round found no
  remaining P0-P2 or other actionable finding.
- Exact next action: commit this design and continuity record locally, then stop
  for owner design approval or revision. Passing checks does not authorize B1.

### 2026-08-01 — Phase 5 promoted locally; Phase 6 design session authorized

- The owner explicitly promoted the validated and reviewed IP-031 candidate at
  `c5ee57c49146eca179d0ccc2feaeeef0a7671d00` as the local Phase 5 development
  baseline. This does not authorize push, merge, tag, release, deployment,
  connector/real-data access, or active-database work.
- The owner requested a new dedicated branch and new session for Phase 6 Weekly
  Brief v2 design and later implementation. The initial new-session gate is
  Batch A only: inspect current code/schema/call paths/tests, produce a gap
  analysis and bounded design, and stop for explicit design approval. General
  intent to continue does not bypass that design-review gate.
- Phase 6 must compose promoted public facts, distinguish new/continuing/
  resolved and unavailable evidence, make every material statement traceable,
  preserve legacy Weekly Brief compatibility, and create no automatic
  publication, email, action, decision, Attention producer, or Phase 7 work.
- Promotion/handoff documentation passed `make validate`: 297 runtime tests,
  21 repository-tool tests with 19 subtests, repository-boundary and synthetic
  checks, Ruff, compilation, diff hygiene, and package build. Independent
  read-only continuity review reconciled `PROGRESS.md`, the evolution plan,
  Phase 5 design/pack/report, implementation-pack index, program context,
  continuation kit, and first-session prompt and found no remaining stale
  current gate or actionable finding.

### 2026-08-01 — IP-031 Batch D validated and repeatedly reviewed

- Added `implementation-reports/IP-031_IMPLEMENTATION_REPORT.md`, reconciling
  the full Phase 5 scope, module ownership, public contracts, local commits,
  compatibility, rollback, risks, deferred work, and promotion gate.
- Combined focused capacity/Staffing/Project Health and shared-contract
  regression passed 169 synthetic tests. `make validate` passed 297 runtime
  tests, 21 repository-tool tests with 19 subtests, repository-boundary and
  synthetic-sample checks, Ruff, compilation, diff hygiene, and package build.
- Initial review found one accepted evidence gap: the installed-wheel rehearsal
  reached workforce/planning import, capacity, and Staffing but did not execute
  Project Health capacity. The rehearsal now evaluates the installed Project
  Health Resource factor, verifies the same `effective-capacity-v1` derivation,
  and proves no Attention creation.
- Enhanced `make rehearse-release` passed wheel install, empty-database
  bootstrap, idempotent dependency and capacity import/replay, capacity-aware
  Staffing, Project Health capacity, isolated populated upgrade, integrity, and
  software rollback. No active database or real data was used.
- Repeated whole-branch read-only review checked all changes from baseline,
  dedicated schema/module boundaries, exact formula and state precedence,
  preview/confirm atomicity, replay/conflict behavior, Staffing transaction
  ordering, Project Health reader isolation, portable privacy, rollback, report
  accuracy, and prohibited scope. It found no remaining P0-P2 or actionable
  issue. The final continuity pass then corrected one stale top-level
  implementation-pack index status that still named Batch C. Passing evidence
  does not promote Phase 5; explicit owner decision is next.

### 2026-08-01 — IP-031 Project Health capacity slice accepted; Batch D authorized

- The owner accepted the Project Health capacity-coverage slice at local commit
  `e7e24b6049155f3a001dc80b95816ba59e8f8ed1` and authorized the next named
  Batch D regression and promotion-decision preparation stage.
- Batch D is limited to combined capacity/Staffing/Project Health regression,
  focused capability tests, full validation, installed-package clean-import and
  rollback rehearsal, portable review, the IP-031 implementation report, and
  repeated independent read-only review. Passing evidence does not itself
  promote Phase 5.
- No Skill Dependency, Attention, legacy replacement, connector/real-data,
  active operational database, push, merge, tag, release, deployment, or later
  phase work is authorized.

### 2026-08-01 — IP-031 Project Health capacity slice validated and reviewed

- Added the public workforce/planning `project_allocation_snapshot` contract.
  It proves one exact project/month/plan assignment set from the authoritative
  manifest and coverage, preserves explicit zero as non-assignment evidence,
  and returns `unknown` for absent or partial scope.
- Added the Resource Intelligence `get_project_capacity_coverage` reader. It
  aggregates only positively assigned human members, requires the same
  workforce publication and exact plan/month, preserves conflicting, unknown,
  and stale states, and reuses the published derivation/overload evidence rather
  than recalculating capacity.
- Extended the existing Project Health evaluator with an optional exact
  year/month/plan scope. Without that complete scope, old calls retain Resource
  `not_available`; with it, authoritative empty remains known evidence but the
  health factor is `unknown`, complete clear coverage is green, and canonical
  overload maps amber/red. Existing assessment tables persist the result; no
  schema, generic repository, Attention producer, or configurable threshold was
  added.
- First read-only review corrected the legacy no-scope availability behavior,
  removed contradictory gate wording, and expanded state-matrix tests for
  missing, unknown, conflicting, stale, authoritative-empty, clear, and red
  coverage. The independent whole-diff review then blocked an invalid known
  overload state from becoming clear and prevented an execution-store fact with
  the same key from bypassing the dedicated capacity reader. Corrected focused
  evidence is 45 contract tests and 169 combined capability regressions.
- The corrected `make validate` passed 297 runtime tests, 21 repository-tool
  tests with 19 subtests, Ruff, compilation, diff checks, and package build.
  The corrected `make rehearse-release` passed wheel installation, clean
  bootstrap, isolated upgrade, and software rollback without active database
  use.
- Final repeated read-only review rechecked the complete diff, untracked-file
  scope, dependency direction, execution-fact bypass protection, authoritative
  zero/missing semantics, state precedence, evidence identity, old-call and
  rollback compatibility, privacy, and prohibited scope. It found no remaining
  P0-P2 or actionable issue. The result is committed together with this record
  as current local HEAD. Exact next action: stop for owner acceptance; do not
  begin Batch D.

### 2026-08-01 — IP-031 Batch C accepted; Project Health capacity slice authorized

- The owner accepted the completed Batch C audit at local commit
  `5773d6c7afd887892bbb295efb85ca737958ff8d` and authorized the next separately
  named Project Health `capacity_coverage` publication slice.
- The slice is bounded to a public authoritative project/month allocation
  reader, a Resource Intelligence capacity-coverage reader over canonical
  effective-capacity facts, and consumption by the existing Project Health
  assessment. First-principles scope requires reuse of existing assessment
  storage and no new table unless a current invariant proves it necessary.
- Skill Dependency, Attention, legacy replacement, Batch D promotion work,
  connectors, real data, active operational databases, push, merge, tag,
  release, and deployment remain unauthorized.

### 2026-08-01 — IP-031 Batch C implemented; revalidation/review in progress

- Added the `resource-capacity-heatmap` read-only `UseCaseResult 1.0` contract
  through the existing `UseCaseExecutor` and `ToolTransport`. It projects only
  persisted current derivations, exact evidence/freshness, and deterministic
  overload signals; it creates no recommendations or writes.
- Added one minimum persisted `staffing_capacity_policy` singleton. Bootstrap
  installs it disabled. It can be enabled only when a complete current capacity
  publication exists; a missing marker fails closed instead of restoring the
  legacy `1.0` assumption.
- When the marker is enabled, Staffing assessment consumes the canonical
  effective-capacity derivation and combines it with current plan allocation.
  Proposal evidence fixes the derivation/publication/rule/plan context.
  Confirmation reloads the same current derivation and current allocations
  inside the existing `BEGIN IMMEDIATE` write transaction before any assignment,
  allocation, or decision record is written.
- The marker-disabled path preserves the promoted Staffing behavior. Missing,
  stale, superseded, multi-month partial, changed-plan, or over-limit capacity
  evidence fails closed without a partial domain write. A completed Staffing
  write does not require capacity re-import merely to assess the remaining
  effective-capacity headroom.
- Added capability-focused heatmap and Staffing-capacity tests and extended the
  installed-wheel rehearsal for schema installation, disabled-default marker,
  explicit synthetic enablement, and capacity-aware assessment.
- First independent review accepted four corrections: fail closed on a missing
  policy row, reject missing member/month capacity, bound heatmap array filters,
  and remove the over-restrictive equality between live planned allocation and
  the capacity publication's planned snapshot. The corrected confirmation
  instead pins effective-capacity identity and compares transaction-current
  allocation with proposal evidence and the effective limit.
- A second review found that bootstrap could recreate a deleted existing marker
  as disabled and silently restore legacy behavior. Installation now writes and
  commits disabled only for a newly created table; a pre-existing table without
  its marker fails closed. The final installation-transaction review also
  confirmed that the initial row cannot be rolled back by a later bootstrap
  failure.
- Final focused evidence: 76 combined heatmap, discovery, capacity import,
  Staffing compatibility, transaction, and Delivery Manager agent tests passed.
- Final `make validate` passed 285 runtime tests, 21 repository-tool tests and
  19 subtests, Ruff, compile, diff check, and package build. Final `make
  rehearse-release` passed wheel installation, clean bootstrap, dependency and
  capacity import/replay, disabled marker proof, explicit synthetic enablement,
  capacity-aware assessment, isolated upgrade, integrity, and rollback.
- Final repeated read-only review found no remaining blocking or actionable
  findings across dependency direction, write ordering, fail-closed state,
  generic transport, excluded scope, and privacy. The candidate is ready for
  owner acceptance and is committed together with this continuity record as
  current HEAD; the exact hash is reported in the task handoff. No push was
  performed.

### 2026-08-01 — IP-031 Batch C authorized

- The owner explicitly authorized Phase 5 Batch C after accepting the
  canonical capacity core.
- Implementation is bounded to C1 read-only heatmap through generic transport,
  C2 a persisted disabled capacity-required compatibility marker, and C3
  Staffing assessment plus same-transaction confirmation consumption of the
  immutable effective-capacity contract.
- The marker must remain disabled when merely installed; synthetic tests may
  activate it only after a complete capacity publication. No active operational
  database operation is authorized.
- Project Health capacity publication remains a separate named slice. Skill
  Dependency, Attention, connectors, real data, automatic assignment, public
  capacity editing, Batch D, push, merge, tag, release, and deployment remain
  unauthorized.

### 2026-08-01 — IP-031 capacity core accepted; first-principles guardrail recorded

- The owner accepted the explanation, audit, and locally committed canonical
  effective-capacity core at
  `1b33d0c9e012909e1ac3eae2b4842497aeb3448a`.
- The governing principle is minimum sufficient design from first principles:
  every table, module, audit layer, and persisted field must protect a current
  invariant or acceptance criterion. Do not add structures for hypothetical
  future flexibility, and prefer consolidation or deletion when the protected
  invariant no longer exists.
- The accepted seven-table core is retained because it currently separates
  package/session audit, attempts, step runs, atomic current publication,
  authoritative coverage, source observations, and deterministic derivations.
  This acceptance is not a precedent for similarly granular schemas without
  the same demonstrated requirements.
- No runtime or schema behavior changed in this acceptance record. Phase 5
  Batch C, including heatmap and Staffing consumption, remains unstarted and
  requires separate explicit authorization. No push was performed.
- Documentation-only acceptance validation passed `make validate`: 272 runtime
  tests, 21 repository-tool tests and 19 subtests, Ruff, compile, diff check,
  and package build. Read-only review found the gate, exclusions, commit, and
  first-principles record consistent; release rehearsal was not repeated
  because runtime, schema, installation, and rollback behavior did not change.

### 2026-08-01 — IP-031 canonical effective-capacity core implemented

- Added the dedicated `pm_agent.resource_intelligence` schema, persistence,
  service, and immutable read-model boundaries. Bootstrap only composes the
  additive DDL; generic repositories and existing Staffing/Project Health
  behavior are unchanged.
- Added `resource-capacity-import-v1`: a stable anonymous synthetic package
  with authoritative member/month/kind coverage, exact leave/BAU/non-project
  observations, fixed source authority, explicit zero, monotonic observation
  versions, preview, explicit confirmation, audit, atomic current publication,
  deterministic derivation, coverage/integrity report, idempotent replay,
  conflict rejection, and software-rollback evidence.
- Added the workforce/planning public `dependency_snapshot` contract so the
  capacity core does not read that capability's private coverage/audit storage.
  Added the single member/month `get_effective_capacity` reader; missing current
  evidence returns `unknown`, never zero or healthy.
- Added `scripts/import_resource_capacity.py`, portable synthetic sample data,
  capability-focused tests, and installed-wheel release rehearsal assertions.
- First validation evidence: 33 focused workforce/capacity tests, 270 runtime
  tests, 21 repository-tool tests and 19 subtests, full static/build validation,
  and installed-wheel release rehearsal passed.
- First independent read-only review accepted three findings: confirmation was
  not bound to the exact preview dependency/derivation, idempotency-key reuse
  lacked a conflict guard, and rollback evidence relied too heavily on a
  declaration. Added deterministic preview fingerprints with confirm-time
  revalidation, idempotency-key preview plus transaction guards, and core-table
  before/after evidence.
- After correction, 35 focused tests passed; `make validate` passed with 272
  runtime tests, 21 repository-tool tests and 19 subtests, Ruff, compile, diff
  check, and package build; `make rehearse-release` again passed installed-wheel
  clean bootstrap/import/replay, isolated upgrade, integrity, derivation, audit,
  and rollback.
- Repeated independent read-only boundary, DDL, transaction, current-pointer,
  privacy, and excluded-scope review found no remaining blocking or actionable
  findings. The candidate is ready for a local commit and owner acceptance.
  Nothing is pushed.

### 2026-08-01 — IP-031 prerequisite accepted; capacity core authorized

- The owner accepted the implemented, validated, and reviewed workforce,
  project, plan-version, and monthly-allocation clean-import prerequisite at
  local commit `624ba356ff838a89baa39138e99aa73128957339` and authorized the
  next Phase 5 step.
- The next step is bounded to dedicated additive capacity schema, versioned
  synthetic leave/BAU/non-project commitment import and audit, deterministic
  effective-capacity derivation, immutable readers, explicit completeness and
  freshness states, replay/conflict protection, and rollback-compatible tests.
- This does not authorize a heatmap or other public use case, Staffing
  assessment/confirmation changes, Project Health capacity publication, Skill
  Dependency, Attention, connector/live-data use, active database work, push,
  merge, tag, release, or deployment.

### 2026-08-01 — IP-031 workforce/planning clean-import prerequisite implemented

- Verified the legacy Distribution Excel path is not a supported production
  clean-import contract: it destructively clears data with multiple commits and
  lacks package/schema version, authoritative coverage, explicit confirmation,
  atomic publication, session/run/attempt audit, conflicting-replay protection,
  integrity reporting, and software-rollback proof.
- Registered IP-031 and added the dedicated
  `pm_agent.workforce_planning_import` schema/repository/service boundary. A
  `workforce-planning-import-v1` synthetic package previews exact deterministic
  validation, requires explicit confirmation, then atomically publishes only
  members, projects, plan versions, and monthly project allocations.
- Added authoritative member/project/plan identity, member-month, and complete
  member-month/project/plan allocation-key coverage. Explicit `0.0` rows remain
  known zero; a missing row or manifest key fails closed. Identical replay is
  idempotent; conflicting replay cannot replace the complete current view; a
  failed publication rolls back all domain rows and retains attempt audit.
- Added the local non-interactive script and stable-anonymous sample package,
  capability-named focused tests, and installed-package rehearsal coverage.
  Additive import audit/coverage tables are ignored by the Phase 4 read path;
  existing canonical dependency tables remain its rollback-compatible read
  target.
- Final focused validation passed 16 capability tests and 22 combined
  capability/bootstrap/import-contract tests. Final `make validate` passed 254
  runtime tests, 21 repository-tool tests with 19 subtests, Ruff, compilation,
  boundary and synthetic checks, diff hygiene, package build, and all eight
  release checks. `make rehearse-release` passed wheel installation, clean
  bootstrap, installed-package structured import/audit/replay, isolated sample
  upgrade, integrity checks, and rollback.
- Independent read-only review found and corrected bootstrap-to-workflow import
  coupling, boolean year/month acceptance, unconstrained member role/level, and
  unhashable enum inputs that could escape stable validation errors. The full
  focused/validation/rehearsal suite passed after correction. The final repeated
  review checked the complete diff, import graph, schema ownership, atomicity,
  coverage/zero semantics, replay/conflict protection, rollback, prohibited
  scope, portable boundary, and gate wording and found no remaining P0-P2 issue.
- No effective capacity, leave/BAU/non-project calculation, heatmap, Staffing,
  Project Health capacity fact, Skill Dependency, Attention, legacy replacement,
  connector/live-data, active database, push, merge, tag, release, or deployment
  work was performed. Exact next action: commit locally, record the exact final
  Git state, and stop for owner acceptance or revision.

### 2026-08-01 — Phase 5 corrected design approved

- The owner approved the corrected Phase 5 Resource Intelligence design and
  authorized a new session to create
  `codex/phase-5-resource-intelligence`, register the implementation pack, and
  inspect and implement only the bounded workforce/project/plan/allocation
  versioned clean-import prerequisite.
- Effective capacity, heatmap, Staffing integration, Project Health capacity
  publication, Skill Dependency, Attention, connector/real-data use, push,
  merge, tag, release, and deployment remain unauthorized.
- This approval record changes no runtime, schema, tests, data, connector, or
  implementation pack. Exact next action: validate and commit this continuity
  record, then begin the authorized work in a new session from that commit.
- `make validate` passed 237 runtime tests, 21 repository-tool tests with 19
  subtests, Ruff, compilation, boundary and synthetic checks, package build,
  and all eight release checks. Read-only authorization review found and
  corrected stale local/remote HEAD wording and a stale Phase 1 publication
  statement; repeated review found no remaining scope or gate defect.

### 2026-08-01 — Phase 5 design review corrections

- Corrected the Phase 5 capacity formula so leave, BAU, and non-project
  commitments are deducted exactly once, and fixed overload to compare planned
  project allocation with effective capacity using explicit amber/red bands.
- Defined authoritative member/month/kind coverage, explicit known-zero
  observations, one versioned authoritative source per commitment kind, a
  720-hour freshness rule, deterministic limited-state precedence,
  effective-dated human-member-only capacity, and placeholder demand semantics.
- Recorded the missing workforce/project/plan/allocation clean-import path as a
  blocking prerequisite that must be proven or remediated in its owning
  capability before the canonical capacity core proceeds.
- Defined Resource Intelligence repository/service/read-contract ownership,
  capability-named synthetic test boundaries, atomic import publication,
  replay/conflict behavior, software rollback write-stop behavior, and exact
  Staffing confirmation revalidation inside the domain-write transaction.
- Kept `resource_skill_dependency` explicitly `not_available` until a separate
  structured Demand and Skill Evidence contract is reviewed. No Attention
  producer, public capacity editor, connector, real data, runtime, schema, or
  implementation pack was added.
- Corrected the stale evolution-plan next action and synchronized the Pack Index
  and this continuity record. Exact next action: focused validation and
  independent read-only review of the corrected design, followed by owner
  approval or revision. No Phase 5 implementation is authorized.
- The first full validation run exposed two existing calendar-sensitive
  synthetic tests after the date advanced to August: demo workload expected a
  hard-coded July active load even though the importer intentionally selects
  the current month, and a Release-history fixture let its initial observation
  default to the execution date after its explicit July change. Stabilized only
  those test fixtures/assertions against their intended temporal contracts; no
  runtime, schema, sample, or business behavior changed.
- The two corrected temporal tests passed 2/2. Final `make validate` passed the
  repository-boundary and synthetic-sample checks, 237 runtime tests, 21
  repository-tool tests with 19 subtests, Ruff, compilation, diff hygiene,
  package build/inspection, and all eight release validation checks.
- Independent read-only review checked the complete diff, capacity arithmetic,
  state precedence, source authority, effective-dated workforce requirement,
  atomic publication and Staffing confirmation, rollback target, deferred
  skill boundary, privacy limits, gate wording, and test assertion strength.
  The review found and corrected ambiguity in observation supersession,
  Project Health allocation coverage, stale-package handling, and safe
  post-switch rollback. A repeated continuity review also removed stale open
  gates that still described Phase 3 B2 and Phase 1 publication as current.
  The final repeated review found no remaining P0-P2 defect.
- The corrected design remains unapproved and creates no implementation
  authority. Exact next action: owner approval or requested revision; only
  after approval may an implementation pack be registered, and runtime work
  still requires a separate authorization.

### 2026-07-30 — Copilot full-program context added

- Added `docs/COPILOT_5_4_PROGRAM_CONTEXT.md` and expanded the first-session
  prompt to require the whole Phase 0–9 roadmap, architecture/design history,
  current gate, and explicit authorization boundaries. This makes a new Copilot
  Chat aware of future dependencies without treating planned phases as approved
  work. No runtime, schema, data, or gate change was made. Validation:
  `make validate` passed (237 runtime tests, 21 repository tool tests, Ruff,
  compile, and package build); read-only document review found the current-gate
  precedence and future-phase non-authorization explicit. Committed locally;
  not pushed.

### 2026-07-30 — First Copilot session prompt added

- Added `prompts/COPILOT_5_4_FIRST_SESSION_PROMPT.md`, a copy-ready first-chat
  preflight that restores the repository state, audits the current Phase 5
  design, and explicitly blocks implementation until a later owner approval.
  It is linked from the Copilot continuation kit. No runtime or gate change was
  made. Validation: `make validate` passed (237 runtime tests, 21 repository
  tool tests, Ruff, compile, package build); read-only document review found no
  gate, privacy, or scope-boundary defect. Committed locally; not pushed.

### 2026-07-30 — Copilot 5.4 continuation kit created

- Added `docs/COPILOT_5_4_CONTINUATION_KIT.md` plus reusable design,
  implementation, read-only review, and promotion task templates. The kit
  freezes preflight, scope, validation, review, handoff, and stop rules for
  future Copilot-led phases without granting any implementation authority.
- It starts from the current Phase 5 design-review gate and directs future
  sessions to existing repository contracts rather than chat history. No
  runtime, schema, connector, real data, or Phase 5 implementation change was
  made.

### 2026-07-30 — Phase 5 Resource Intelligence design and boundary review

- Inspected the promoted capacity/allocation, plan-version, Staffing,
  placeholder, skills, HIREF, workload, and Project Health boundaries.
- Added `architecture/12_PHASE_5_RESOURCE_INTELLIGENCE_DESIGN.md`, defining
  structured effective capacity, fail-closed availability, heatmap and signal
  boundaries, clean re-import, shared Staffing formula, synthetic scenarios,
  and A–D gates. No runtime/schema/import pack, connector, real data, Attention,
  push, merge, tag, release, or deployment change was made.
- Exact next action: owner design review/approval or revision; Batch B requires
  separate authorization.

### 2026-07-30 — Phase 4 promoted locally

- The owner promoted the completed IP-030 implementation after accepting the
  Batch D review. Promotion relies on the recorded 52/52 focused regression,
  237-test full validation, and synthetic installed-package rehearsal.
- This establishes only a local development baseline. It does not authorize a
  push, merge, tag, release, deployment, active-database migration, live
  connector, real-data action, Attention producer, or legacy replacement.

### 2026-07-30 — Phase 4 Batch D review accepted

- The owner completed and accepted review of the IP-030 validation evidence and
  implementation report. This authorizes no promotion, push, merge, tag,
  release, deployment, connector, or real-data action.
- Exact next action: explicit owner decision to promote, revise, or reject the
  completed local Phase 4 baseline.

### 2026-07-30 — Phase 4 Batch D validated

- Combined Project Health regression passed 52/52. `make validate` passed 237
  runtime tests and 21 repository-tool tests; `make rehearse-release` passed
  synthetic wheel install, clean bootstrap, isolated upgrade, integrity, and
  rollback.
- Added `implementation-reports/IP-030_IMPLEMENTATION_REPORT.md`. No runtime
  behavior changed in Batch D. Owner review and an explicit promotion decision
  remain required; no push, merge, tag, release, or deployment occurred.

### 2026-07-30 — Phase 4 Batch C implemented and self-reviewed

- Added `layered-project-health-review`, a separate read-only projection over
  the latest persisted seven-dimension assessment per selected project. It
  returns factors, dimensions, guards, configuration version, legacy comparison,
  evidence, fail-closed freshness, and deterministic red/amber signals through
  the shared CLI, Dashboard Tool Transport, and Delivery Manager agent route.
- The legacy `project-health-review` contract remains unchanged. The projection
  does not evaluate health, mutate configuration, reconcile or create Attention,
  call a connector, or use real data. Batch D, Attention integration, and any
  replacement of the legacy review remain outside scope.
- Read-only review corrected assessment freshness so persisted limited evidence
  is `unknown` and stale evidence remains `stale`, never `fresh`. Focused
  regression passed 52/52; `make validate` passed 237 runtime tests and 21
  repository-tool tests. The result is committed locally, unpushed, and awaits
  owner review.

### 2026-07-30 — Mandatory implementation completion report adopted

- The owner required every completed implementation batch to undergo focused
  validation and read-only self-review before any completion claim. The final
  handoff must cover: changes and rationale; usable functionality and use;
  module/data/compatibility impact; excluded scope and next gate; test/review
  evidence; and commit/push status. This requirement is now binding in
  `AGENTS.md`.

### 2026-07-30 — Project Health capability naming cleanup

- Renamed the tracked local re-import entrypoint, synthetic re-import package,
  and Project Health test artifacts to capability-based names. Runtime paths,
  sample identifiers, and module documentation no longer encode delivery-phase
  or batch labels; architecture and gate records retain those labels only where
  they express approved delivery governance.
- The synthetic-sample checker and 15 focused Project Health tests passed. No
  assessment behavior, schema, public interface, Attention, connector, real
  data, or later-gate behavior changed. The cleanup is local-only and unpushed.

### 2026-07-30 — Phase 4 Batch B implementation completed and self-reviewed

- Completed controlled health configuration through the capability-owned
  `project_health.configuration` module: fixed-key bounded default and
  existing-project override preview/confirm, effective-version projection,
  hashed expiring one-time token, atomic claim, stale/no-op/expiry rejection,
  idempotent replay, and append-only change/version audit.
- Completed deterministic assessment in `project_health.evaluation`: fixed
  per-factor canonical-fact allowlists, explicit factor metadata/evidence,
  freshness/completeness fail-closed handling, critical-Milestone Schedule
  guard, non-averaging dimension/overall aggregation, persisted configuration
  version/guard outcomes/legacy comparison, and no model-generated facts.
- Renamed capability files and tests to remove phase/batch runtime naming.
  No public use case, Attention producer, legacy health replacement, connector,
  real data, or Batch C/D work was added.
- Focused synthetic Project Health tests passed 15/15; `make validate` passed
  234 runtime tests and 21 repository-tool tests; `make rehearse-release`
  passed wheel installation, isolated bootstrap/upgrade, integrity, and
  rollback. Read-only self-review found no P0-P2 issue. The result is committed
  locally, remains unpushed, and awaits owner review. Exact next action: owner
  review or bounded correction only.

### 2026-07-30 — Phase 4 Batch A accepted

- Owner accepted the corrected and self-reviewed IP-030 Batch A foundation:
  fixed catalog/read projection, supported structured re-import contract,
  board-bound canonical derivation audit, fail-closed integrity reporting, and
  retryable partial-failure protection.
- Acceptance authorizes no Batch B code. Deterministic assessment persistence,
  DM configuration preview/confirm, overrides, public Phase 4 projection,
  Attention integration, legacy health replacement, connector/live-data work,
  push, merge, tag, release, and deployment remain blocked.
- Batch A corrections are committed locally at the current branch HEAD and
  remain unpushed. Exact next action: separately authorize Batch B or request a
  design revision.

### 2026-07-30 — Phase 4 Batch A review findings corrected and self-reviewed

- Bound each versioned re-import package to validated stable-anonymous board
  IDs, executed Phase 3 canonical derivation for exactly those boards, and
  stored per-session derivation IDs, coverage/freshness, SQLite integrity,
  foreign-key results, and explicit reconciliation limitation in the report.
- Made interrupted or failed sessions retryable with append-only attempt audit.
  Integrity failure is fail-closed (`failed`), never a completed import.
  Added additive assessment/configuration contract table families only; no
  assessment evaluation, configuration mutation, Attention, or public Phase 4
  projection was added.
- Focused synthetic tests passed 7/7, including bound derivation, interrupted
  replay, failure audit, and integrity failure. `make validate` passed 226
  runtime tests and 21 repository-tool tests (19 subtests); `make
  rehearse-release` passed wheel installation, isolated bootstrap/upgrade,
  integrity, and rollback. Self-review found no P0-P2 finding.
- The repair is committed locally and remains unpushed. The exact next action
  is owner acceptance of Batch A; Batch B remains separately unauthorized.

### 2026-07-30 — Phase 4 Batch A clean re-import and catalog foundation implemented

- Added additive Phase 4 catalog/default-condition, structured-input reserve,
  and re-import session/run audit tables through a dedicated schema module.
  The fixed seven-dimension catalog is read-only; the effective projection
  explicitly reports configuration mutation and overrides as `not_available`.
- Added the internal versioned structured re-import preview/confirm boundary
  and non-interactive local script. Empty Quality, Resource, and Governance
  inputs are valid and report `not_available`; nonempty records fail closed
  until a separately approved structured producer exists. Replays are
  idempotent; execution failure records a failed session without coverage view.
- Added a portable stable-anonymous sample package and five focused synthetic
  tests. Focused tests passed 5/5; `make validate` passed 224 runtime tests,
  21 repository-tool tests (19 subtests), Ruff, compilation, boundary/synthetic
  checks, diff hygiene, and package build. `make rehearse-release` passed wheel
  installation, isolated bootstrap/upgrade, integrity, and rollback.
- Read-only implementation review found no P0-P2 issue; the required
  independent review remains the next gate. No Phase 4 assessment persistence,
  DM configuration mutation, override, public use case, Attention producer,
  legacy health replacement, connector/live-data action, real data,
  `pending_decision_attention` activation, push, merge, tag, release, or
  deployment was performed. The Batch A change is committed locally and remains
  unpushed. The exact next action is independent Batch A review.

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

### 2026-07-30 — Global clean re-import policy adopted

- The owner set clean bootstrap plus supported versioned full re-import as the
  production data path for every future phase. Production readiness must not
  depend on migration, backfill, or preservation of current records.
- Existing Phase 1–3 bootstrap, import, and migration paths were inspected.
  They support portions of the lifecycle but do not yet provide one complete
  canonical-evidence-to-layered-health re-import path. Phase 4 Batch A is the
  bounded remediation owner; no unrelated rewrite of promoted behavior is
  authorized or required before that slice.
- The repository instructions and phase plan now require every persisted
  capability to define bootstrap, import, validation, idempotent replay, audit,
  derivation, coverage/integrity report, and software rollback. This policy
  change creates no runtime/schema/connector change; Phase 4 design review
  remained the next gate at that time.

### 2026-07-30 — Phase 4 design approved

- The owner approved the bounded seven-dimension Project Health design and
  IP-030, including clean bootstrap/full structured re-import, explicit
  unavailable states, critical-Milestone non-averaging guards, and the
  controlled configuration boundary.
- This authorizes no runtime, schema, import script, connector, Attention,
  real-data, push, merge, tag, release, or deployment work.
- Exact next action: explicit authorization for IP-030 Batch A clean re-import
  contract and catalog foundation, or a design revision.

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
