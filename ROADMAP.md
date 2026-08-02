# Delivery Manager Roadmap

Status: `PHASE 6 PROMOTED LOCALLY — PHASE 7 FORECAST REQUIRES SEPARATE AUTHORIZATION`
Last updated: 2026-08-02

Current-state authority: `PROGRESS.md`. This roadmap records approved stage
intent and historical gate evidence; any conflict with `PROGRESS.md` resolves
in favor of `PROGRESS.md`.

This roadmap begins from the current release candidate. Earlier IP migration
sequences are historical evidence, not work still waiting to start.

Owner decision on 2026-07-27: exact commit `a272890` is accepted as the
development evolution baseline after successful local and remote validation.
The `0.2.0rc1` tag, work-computer migration rehearsal, and real-environment UAT
are deferred until the integrated Delivery Intelligence candidate is assembled.
This exception is not production or operational approval.

## Stage 1 — Candidate context cleanup

Goal: ensure the work-computer model sees only current operating, validation,
and safety instructions.

Exit criteria:

- obsolete baseline, migration, and release-readiness files are removed;
- `README.md`, `PROGRESS.md`, portability status, and Agent instructions agree;
- historical implementation material has an explicit owner disposition;
- reference checks, `make validate`, and `make rehearse-release` pass;
- cleanup is reviewed and pushed to the independent branch.

## Stage 2 — Immutable candidate

Status: deferred to the integrated release-candidate stage.

Goal: make the exact validated source reproducible.

Exit criteria:

- GitHub Actions is green for the exact cleanup commit;
- the working tree is clean;
- the owner explicitly authorizes annotated tag `v0.2.0-rc.1`;
- the immutable tag is pushed without moving or recreating it.

The tag is a test candidate, not production approval and not authorization to
merge into `main`.

## Stage 3 — Work-computer migration rehearsal

Status: deferred to the integrated release-candidate stage.

Goal: prove that the candidate can upgrade the real schema safely without first
touching the active database.

Follow `docs/REAL_ENVIRONMENT_UAT_RUNBOOK.md`.

Exit criteria:

- a local backup exists;
- migration runs only on an isolated database copy;
- integrity and foreign-key checks pass;
- dependent views remain queryable;
- confirmation tokens use only the hash column;
- pre/post aggregate counts are unchanged;
- no raw data or evidence leaves the approved environment.

## Stage 4 — Controlled real-environment UAT

Status: deferred to the integrated release-candidate stage. The runbook must be
updated and approved after the promoted capability iterations are complete.

Goal: validate the actual operating workflow using approved local data and
configuration.

Validate in this order:

1. configuration and portable connector contracts;
2. structured read-only use cases and failure behavior;
3. one approved connector probe/sync at a time;
4. staffing assess/propose/preview/cancel;
5. staffing confirmation only with authorized manager approval;
6. Dashboard read paths, write preview/confirm/replay protection, and loopback
   binding.

Any credential exposure, raw error, unexpected scope, integrity failure,
changed aggregate, non-fresh decision input, or confirmation mismatch is a stop
condition.

## Stage 5 — Candidate decision

Status: replaced for now by the explicit development-baseline decision. Final
operational candidate approval remains pending.

After sanitized UAT evidence:

- promote the candidate for local operational use when all gates pass; or
- record a sanitized defect category, restore the previous local version and
  database backup, and create a new `rcN` candidate.

Do not move an existing tag, publish automatically, or merge into `main`.

## Post-0.2 iteration themes

The Delivery Intelligence sequence is defined in
`architecture/05_DELIVERY_INTELLIGENCE_EVOLUTION_PLAN.md`:

1. Intelligence output contract;
2. Delivery Attention Center foundation;
3. delivery-execution, milestone, and Release commitment foundation;
4. layered seven-dimension Project Health;
5. Resource Intelligence;
6. Weekly Brief v2;
7. Forecast v1;
8. What-if Simulation v1;
9. integrated release-candidate validation.

Each phase follows architecture review, phase-specific gap analysis, design
approval, small implementation batches, focused tests, full regression, and an
explicit promotion decision.

Phase 1 was promoted on 2026-07-28 after its bounded contract, discovery,
Management Attention reference mapping, regression, portable review, and
synthetic release rehearsal passed. In Phase 2, the corrected Batch C1
Attention Center is accepted. Batch C2's mapping mechanics passed local
technical validation, but product review did not accept mapping and source
precedence as the DM-facing health configuration abstraction.

The owner approved
`architecture/08_LAYERED_PROJECT_HEALTH_AND_MILESTONE_EVOLUTION.md` on
2026-07-29. It
separates Sprint Execution, Release/Milestone, and Project Health; assigns the
canonical milestone and Release commitment foundation to Phase 3; assigns
bounded DM-configurable health conditions to Phase 4; and requires Phase 7
Forecast to reuse promoted milestone history. The bounded C2 correction
removes or blocks the unaccepted public mapping paths, removes dormant
configuration mutation helpers, and passed technical re-review. Owner
accepted the correction. Batch D regression, schema/portable review, and
synthetic release rehearsal passed. The owner accepted the Batch D Review and
promoted the result as the local Phase 2 development baseline on 2026-07-29.
The Phase 3 current-state review and execution/milestone foundation are
recorded in
`architecture/09_PHASE_3_EXECUTION_AND_MILESTONE_FOUNDATION_DESIGN.md`.
The owner approved all four design decisions, completed IP-029 on the
dedicated local Phase 3 branch, and promoted Phase 3 locally on 2026-07-30.
Phase 4 (IP-030) is a promoted local baseline. On 2026-08-02 the owner
authorized the IP-033 controlled assessment entry slice: the confirmed clean
re-import now runs the deterministic seven-dimension assessment per covered
project and links each run to the import audit. That slice is implemented and
validated on `codex/phase-4-assessment-entry`; the R3 independent read-only
review passed and the slice now awaits the owner acceptance decision. It adds
no standalone CLI, Attention producer, connector, or real-data path.
Phase 5 (IP-031) was promoted locally on 2026-08-01; Skill Dependency and new
Attention producers remain deliberately excluded. Phase 6 (IP-032 Weekly
Brief v2) was promoted locally on 2026-08-01 as the current development
baseline.
Deferred
migration rehearsal and real-environment
UAT return as Phase 9 gates under a refreshed, approved runbook.
