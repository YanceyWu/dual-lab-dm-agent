# IP-036 — Canonical Onboarding Convergence Batch A0

Status: `OWNER-REQUESTED REVISED IMPLEMENTATION HANDOFF (A0 ONLY)`
Design: `architecture/16_CANONICAL_ONBOARDING_CONVERGENCE_DESIGN.md`
Implementation branch: `TBD IN FOLLOW-ON SESSION`
Baseline: `5f13ee346e629213f8e91e7d4b7d1e95edeb794b`

## Goal

Prevent the convergence program from looping on hidden dependencies and
late-discovered semantics by making the legacy current-state staffing path fully
explicit **before** runtime replacement begins.

This pack is intentionally redesigned from the earlier A1-first plan. The first
follow-on session must do **Batch A0 only**:

- produce the frozen coverage/dependency matrix;
- produce the invariant checklist;
- produce the end-to-end state-machine matrix;
- produce the product/semantic decision log;
- freeze the later runtime slices A1-A4 so regression scope is explicit before
  coding starts.

## Why the plan was redesigned

The earlier follow-on plan jumped directly to current-state runtime
implementation. That caused looping because:

- the new onboarding path currently publishes only part of what the legacy path
  used to supply;
- regressions then touched readers that still depend on legacy projections,
  freshness keys, enrichment fields, registry side effects, or other auxiliary
  outputs;
- broad validation passed but did not prove contract completeness;
- final review kept finding uncovered dependencies and unresolved semantics that
  had never been frozen as explicit slice scope.

This pack fixes that by making coverage proof and behavior modeling the first
acceptance unit.

## Authorized outcome

Batch A0 is a documentation / analysis / planning slice only. It does not
authorize runtime convergence yet.

Any unfinished runtime experiment performed before A0 acceptance is **diagnostic
input only**. It is not partial implementation to continue.

The accepted result of A0 should be a frozen matrix and a frozen slice plan that
lets later runtime sessions work in small, reviewable steps instead of trying to
replace the whole current-state stack in one pass.

## Known concrete failure classes that A0 must model

At minimum, A0 must explicitly model and classify these observed failure
classes:

1. **Replay / uniqueness failure class**
   - same `package_id`
   - different payload identity
   - multiple previews
   - later confirm steps
   - risk of duplicate completed publication

2. **Unknown-data semantic failure class**
   - missing or unusable current-state staffing publication
   - dashboard or summary still showing "real zero / everyone available" style
     output instead of unavailable / unknown semantics

If A0 does not explicitly freeze these as invariants/decisions/scenarios, later
runtime slices are incomplete by definition.

## Proposed scope (Batch A0 only)

- Inventory the legacy current-state staffing path and its adjacent supporting
  paths for outputs that matter to runtime replacement.
- Capture not only primary facts, but also:
  - projections and helper views;
  - freshness, audit, publication, and source-evidence semantics;
  - auxiliary side effects and full-sync behaviors;
  - reader/test dependencies.
- Include at minimum the dependencies currently associated with:
  - `import_from_excel.py`
  - legacy current-load projections such as `assignments` / `v_member_load`
  - script-name freshness assumptions
  - known adjacent enrichment dependencies such as skills / HIREF where they
    affect the same readers or regressions
- Produce the frozen coverage/dependency matrix with exact replacement ownership.
- Produce the invariant checklist and state-machine matrix.
- Produce the product/semantic decision log for blocking questions.
- Freeze the later runtime slices:
  - A1: current-state staffing contract skeleton
  - A2: reader migration
  - A3: freshness/evidence migration
  - A4: compatibility closure
- Identify the minimum synthetic fixtures/data needed so each later slice has the
  required inputs or explicit out-of-scope markers.
- Update continuity documentation (`PROGRESS.md` and, if needed, the design
  handoff) so the next runtime session cannot reopen A0 implicitly.

## Explicit non-goals

- No runtime code changes.
- No schema changes.
- No reader migration.
- No freshness logic replacement.
- No legacy table or code deletion.
- No Batch B/C/D work.
- No broad full-product acceptance of the eventual runtime convergence.

## Required deliverables

### 1. Coverage/dependency matrix

The matrix must name, at minimum:

- legacy path / importer / helper;
- primary facts written;
- projections / views / helper state affected;
- freshness / audit / evidence / source-state outputs;
- auxiliary side effects / deletion semantics;
- dependent readers / dashboard surfaces / rules;
- dependent focused tests / broader regression surfaces;
- replacement slice (`A1`, `A2`, `A3`, `A4`, later batch, or explicit defer);
- whether a compatibility shim is allowed, and its deletion target.

### 2. Missing-coverage register

For every dependency the new onboarding path does not yet replace, record:

- why it is currently missing;
- whether it blocks the next runtime slice;
- whether it belongs to current-state staffing or a later batch such as
  enrichment / contract coverage / registry convergence.

### 3. Invariant checklist

The checklist must explicitly cover:

- package identity / payload identity / uniqueness invariants;
- preview reuse / confirmability / replay invariants;
- publication completion invariants;
- missing-schema degradation invariants;
- dashboard unknown-data semantics;
- freshness-state semantics for affected readers;
- compatibility-shim rules and deletion targets.

### 4. End-to-end state-machine matrix

The matrix must cover, at minimum:

- first preview;
- repeated preview;
- confirm after preview;
- post-confirm preview;
- already-completed replay;
- non-confirmable preview followed by confirm;
- same `package_id` + different payload;
- partial schema missing at read time;
- freshness `fresh/stale/partial/unknown` impact on reader semantics;
- missing current-state publication while planned staffing exists.

### 5. Product / semantic decision log

The decision log must make explicit, at minimum:

- unchanged rerun semantics;
- confirmability rules for reruns and replay candidates;
- handling of same `package_id` with different payload identity;
- dashboard semantics when current-state staffing publication is missing;
- degradation rules when a required schema family is partially missing;
- whether any reader may emit numeric summaries while its current-state evidence
  is unavailable.

### 6. Frozen slice plan

For A1 through A4, record:

- exact goal;
- exact files/modules/capabilities allowed to change;
- focused tests expected for that slice;
- exact stop condition;
- what must not be touched in the slice.

### 7. Regression-scope map

Map the known regressions/use cases/tests to the slice that should legitimately
exercise them, so later sessions do not treat every full-product regression hit
as proof that the current slice is incomplete.

### 8. Slice self-review checklist

Define the self-review checklist that each runtime slice must complete before it
requests external final review.

## Anti-loop rules for later slices

1. One session implements one slice only.
2. A runtime slice may not start until its scope, acceptance criteria, focused
   tests, and self-review checklist are frozen from the A0 outputs.
3. Full validation / rehearsal belongs at slice closure, not after every
   intermediate adjustment.
4. Slice review happens before moving to the next slice; final review is a
   closure check, not a second design phase.
5. Findings that are real but out-of-scope go back into the matrix; they do not
   automatically reopen the current slice.
6. A slice gets at most one correction round before it must either close or be
   re-scoped explicitly.
7. If runtime work discovers a missing invariant or missing semantic decision
   that should have been frozen in A0, stop and reopen A0 outputs instead of
   patching forward.

## Acceptance criteria

Batch A0 is complete only when all of the following are true:

1. the current-state staffing legacy path has a frozen coverage/dependency matrix;
2. the matrix includes business facts, projections, freshness/audit semantics,
   and auxiliary side effects rather than only the obvious primary import data;
3. the invariant checklist is frozen and includes the mandatory topics;
4. the state-machine matrix is frozen and includes the mandatory scenarios;
5. the semantic decision log resolves or explicitly defers every blocking
   product decision;
6. each dependent reader / rule / regression surface is assigned to an in-scope
   slice or an explicit defer decision;
7. A1-A4 are frozen as small execution slices with exact stop conditions;
8. the next runtime session can start A1 without rediscovering basic scope.

## Validation plan

Batch A0 is documentation-only. Validation should therefore stay documentation-
appropriate:

- `git diff --check` for the changed handoff documents;
- read-only review of scope, gate, contract clarity, mandatory scenarios, and
  slice boundaries;
- `PROGRESS.md` update with the revised next action and redesign rationale.

`make validate` and `make rehearse-release` are **not** required for A0 because
it does not change runtime, schema, imports, or packaging behavior.

## Rollback

Batch A0 is documentation-only and can be rolled back by reverting the handoff
documents. No data or schema rollback path is needed for this slice.

## Next gate after A0

Only after A0 acceptance should the next session start **A1 — current-state
staffing contract skeleton**. A1 must still remain narrow and must not include
reader migration or freshness replacement.
