# IP-033 — Phase 4 Controlled Assessment Entry

Status: `INDEPENDENT REVIEW PASSED — AWAITING OWNER ACCEPTANCE`
Implementation branch: `codex/phase-4-assessment-entry`
Base: `dd3d10f51b566a207897cba11ba811ebff15f68e` (promoted Phase 6 local baseline)
Related design: `architecture/11_PHASE_4_SEVEN_DIMENSION_PROJECT_HEALTH_DESIGN.md`

## Goal

Close the Phase 4 effectiveness gap found by the Phase 1–6 feature review:
the seven-dimension assessment engine existed but had no production entry
point. This slice makes the confirmed clean re-import the controlled
assessment entry: after canonical derivation, one deterministic assessment
run is created per covered project and reported in the import coverage.

## Approved scope

- After `confirm_reimport` runs `execution.derive_board`, run
  `project_health.evaluation.evaluate(project_id, ...)` once per distinct
  covered project.
- Link every assessment run to its import session in the new additive
  `project_health_reimport_assessments` audit table so sequential replay is
  idempotent and an interrupted attempt can be recovered without duplicate
  assessment runs.
- Extend the import coverage report with real per-project dimension states and
  an `assessments` summary; `assessment_state` becomes `completed` when
  assessments ran and stays `not_available` for an empty package.
- Update the preview `planned_steps` and the `health_coverage` step counts.

## Non-goals

- No standalone assessment CLI or Dashboard endpoint; the controlled write
  boundary remains the import preview/confirm path.
- No change to the assessment engine, configuration preview/confirm, legacy
  Project Health, Management Attention, Attention, or `UseCaseResult 1.0`.
- No new Attention producer, connector, real data, capacity input, or Phase 7
  work.

## Module ownership and dependencies

- Schema owner: `pm_agent.database.project_health_schema` (additive DDL only;
  bootstrap composes it).
- Persistence/flow owner: `pm_agent.project_health.service`
  (`confirm_reimport`, `_assess_projects`, `_coverage`).
- Evaluation dependency: `pm_agent.project_health.evaluation.evaluate`
  (imported lazily to avoid a module cycle; unchanged).
- Test entry points: `src/tests/test_project_health_reimport.py`,
  `src/tests/test_layered_project_health_review.py`,
  `src/tests/test_project_capacity_coverage.py`.

## Validation evidence

- Focused Project Health re-import suite: 10/10 passed, including a new
  end-to-end test that the import-produced assessment is readable through
  `layered-project-health-review`.
- `make validate`: 335 runtime tests, 21 repository-tool tests (19 subtests),
  repository-boundary and synthetic-sample checks, Ruff, compilation, diff
  hygiene, package build, and 8 release-validation checks, all passed.
- `make rehearse-release`: wheel installation, isolated clean bootstrap,
  synthetic upgrade, integrity, and rollback passed.

## Transitional debt and recorded risks

- Sequential replay is duplicate-free (session-linked assessment rows plus
  same-session crash recovery). Concurrent duplicate confirmation of the same
  import session is not a supported workflow; it could leave an unlinked
  assessment row, which is auditable but not auto-recovered.
- Assessment recovery matches only assessment rows created after the same
  session was created; an orphan left by a crashed attempt of an earlier
  session is not auto-linked by a later session.
- `assessment_state` semantics changed from always `not_available` to
  `completed`/`not_available`; consumers of the import report (currently the
  CLI output and tests) must read the new field.

## Rollback

Software-only revert of this slice. The added table is additive and unused by
the previous runtime; assessment rows created by the new flow remain readable
and are not relied upon for rollback. No data migration or backfill is
required.

## Next gate

Owner review of this validated slice. Acceptance promotes it only as a local
development-baseline fix; Phase 7 Forecast and every external action remain
separately gated.
