# Canonical Onboarding Convergence Design

Status: `BATCH A IMPLEMENTED LOCALLY THROUGH A4; POST-BATCH-A REDESIGN BELOW NOW RETIRES LEGACY SKILLS AND FREEZES B1-B4`
Date: 2026-08-04
Current-state authority: `PROGRESS.md`.
Baseline branch: `workbook-onboarding-test-20260804-1514`
Baseline commit: `8bfd9c8ef2a5b3857c63b9977c811c8d199574ae`
Previous local baseline: `IP-035 Structured Data Onboarding Workbook Presets`

Runtime closure note (2026-08-05): the frozen coverage matrix, invariants, and
slice boundaries below remain the Batch A authority. A1, A2, and A3 were
completed and committed before this session, and the current working tree closes
A4 by demoting the remaining A-scope legacy current-state staffing projections
and route markers to canonical publication authority. Post-Batch-A owner
feedback now further freezes that legacy `import_skills.py` is not a viable
onboarding candidate: it must be retired rather than migrated, and any future
skills capability requires a separate approved redesign. Contract coverage /
HIREF convergence and mutable staffing-write redesign remain deferred.

## Decision supported

Rebuild the pre-production onboarding foundation so that:

- every operator-visible import or onboarding action enters through
  `pm onboarding`;
- every business fact family has one canonical writer and one public read
  contract;
- redundant tables, views, functions, freshness IDs, and standalone import
  entrypoints can be removed;
- deprecated scripts, compatibility shims, legacy helpers, dead branches, and
  obsolete tests/docs can be removed once the new canonical path fully replaces
  them;
- runtime replacement cannot begin until a coverage/dependency audit proves what
  the legacy path currently supplies beyond its obvious primary facts;
- every runtime slice must start from explicit invariants, a state-machine
  matrix, and named semantic decisions instead of relying on review to discover
  scope gaps;
- existing user-visible capabilities remain available through the new internals.

This is a pre-production cleanup decision. The repository should preserve
functional behavior and output contracts, not legacy table authority, script
entrypoints, or migration baggage.

## Design-only review boundary

This document defines the target architecture and the recommended execution
sequence only. Runtime, schema, CLI, Dashboard, connector, and real-data changes
still require separately bounded implementation slices.

The committed IP-035 baseline remains the runtime authority until a later slice
is implemented and accepted. This redesign changes the follow-on execution plan,
not the current product behavior.

## Verified current state

### What already works

- `pm onboarding` now exists as a thin cross-source orchestration layer with
  saved profiles, preview/confirm envelopes, run audit, and publication links.
- Workbook onboarding now works under that framework and can publish versioned
  workforce planning data.
- Domain importers for workforce planning, capacity, milestones, and Project
  Health already provide controlled preview/confirm behavior inside their own
  capability boundaries.

### What the workbook UAT exposed

The isolated workbook onboarding UAT proved a deeper architectural fracture:

- the workbook onboarding run successfully published `plan_versions` plus
  `monthly_allocations`;
- `team-workload-overview` still reported `current_load = 0` because its read
  path depends on legacy `assignments` and `v_member_load`;
- freshness for workload and staffing still depends on script-era source IDs
  such as `import-resource-portal`, `import-skills-matrix`, and
  `import-hiref-report`.

This means plan-state staffing and current-state staffing are both real product
needs, but they do not yet have clean, explicit, capability-owned boundaries.

### What the failed runtime attempt exposed

The follow-on runtime attempt demonstrated that the previous plan was too
optimistic:

- the execution session treated review as the primary tool for discovering
  missing scope, instead of freezing the behavior model first;
- fixes were applied to specific examples without first codifying the
  cross-layer invariants behind them;
- broad validation passed repeatedly, but that only proved that covered tests
  still passed, not that the contract surface was complete;
- product/semantic decisions remained implicit while code changes proceeded.

Two concrete failure classes emerged from that aborted attempt and must now be
treated as required modeling inputs for A0:

1. replay / uniqueness risk — current-state staffing publication could still be
   replayed incorrectly if package identity, payload identity, confirmability,
   and completion invariants are not frozen up front;
2. unknown-data semantic risk — dashboard or summary surfaces can imply "real
   zero / everybody available" when current-state staffing publication is
   actually unavailable, partial, stale, or missing.

The fix is not "more iteration". The fix is to freeze dependency coverage,
invariants, the state machine, and semantic decisions before runtime replacement
resumes.

### What remains fragmented

The repository still exposes mixed operator and storage paths:

- legacy standalone import entrypoints directly mutate business tables:
  `import_from_excel.py`, `import_skills.py`, `import_hiref.py`,
  `import_jira_boards.py`, `import_confluence_pages.py`,
  `import_project_profiles.py`, and `import_cr_csv.py`;
- newer structured JSON importers are better controlled but are still separate
  operator entrypoints outside `pm onboarding`;
- multiple import paths write overlapping business facts, especially through
  `employees`, `assignments`, and script-coupled freshness records;
- several read paths depend on low-level table shapes or script names instead of
  capability publications and public read contracts.

## Strategic decision

### Preserve functionality, not implementation

The system is still under construction. The repository should preserve:

- use-case outputs;
- CLI and Dashboard-visible behavior;
- clean bootstrap and deterministic re-import;
- evidence, audit, and explicit unknown semantics.

It should not preserve:

- legacy import scripts as permanent product entrypoints;
- dual-writer table authority;
- script-name freshness coupling;
- compatibility-only tables or views that no longer carry distinct semantics.

### Adversarial migration assumption

Every legacy import path must be treated as if it produces **more than one kind
of output**. Assume that each path may contribute some combination of:

1. canonical business facts;
2. read-model projections or helper views;
3. freshness, audit, source-evidence, or publication state;
4. auxiliary side effects such as field enrichment, registry cleanup,
   full-sync deletion behavior, or other capability-specific prerequisites.

No runtime convergence slice may assume it has replaced a legacy path until it
has checked all four categories.

### Clean re-import is the migration strategy

The cleanup path should assume an empty local database plus a versioned,
supported, structured full re-import. The target architecture must not depend on
historical backfill, dual-write, or long-lived compatibility storage.

### No runtime replacement before coverage proof

The next runtime slice must not begin by "just building the new current-state
capability". It must begin by proving:

- what the old path really supplies;
- which readers and regressions depend on those outputs;
- which outputs are in-scope for the next slice;
- which outputs are deferred and therefore must not be touched by that slice.

## Coverage-first migration model

Before any runtime replacement slice starts, the convergence program must create
and freeze a coverage/dependency matrix.

### Required coverage matrix columns

At minimum, the matrix must name:

- legacy path / importer / script / helper;
- explicit business facts written;
- implicit projections, views, or helper-path state affected;
- freshness, audit, publication, or source-evidence outputs;
- auxiliary side effects or deletion/full-sync semantics;
- dependent readers / use cases / dashboard surfaces / rules;
- dependent focused tests and broader regression surfaces;
- whether the dependency is blocking, in-scope for the next slice, or deferred;
- the exact slice that will replace it;
- whether a temporary compatibility shim is allowed, and if so, its deletion
  target.

### Required A0 artifacts beyond the matrix

A0 is incomplete unless it also produces all of the following:

1. **Invariant checklist** — the non-negotiable behavior rules that any runtime
   slice must preserve.
2. **End-to-end state-machine matrix** — the lifecycle matrix for preview,
   confirm, replay, rejection, degradation, and missing-data semantics.
3. **Product/semantic decision log** — decisions that must be explicit before
   implementation can proceed.
4. **Slice-scoped self-review checklist** — the internal contract checklist that
   must be completed before external review.

### Mandatory invariant topics

The invariant checklist must explicitly cover:

- package identity / payload identity / uniqueness invariants;
- onboarding run identity, preview reuse, confirmability, and replay invariants;
- publication completion invariants;
- missing-schema degradation invariants for read contracts;
- dashboard and summary unknown-data semantics;
- freshness-state semantics (`fresh`, `stale`, `partial`, `unknown`,
  `unavailable`) for the affected readers;
- compatibility-shim rules and deletion targets.

### Mandatory state-machine scenarios

The state-machine matrix must include, at minimum:

- same source: first preview;
- same source: repeated preview;
- same source: confirm after preview;
- same source: post-confirm preview;
- already completed replay;
- non-confirmable preview followed by confirm;
- same `package_id` with different payload;
- schema partially missing at read time;
- freshness `fresh/stale/partial/unknown` impact on dashboard summary semantics;
- missing current-state publication while planned staffing exists.

### Mandatory semantic decisions before A1

The product/semantic decision log must make these explicit before runtime A1:

- unchanged rerun semantics:
  - `already_completed`,
  - previewed but non-confirmable,
  - or conflict/rejected;
- confirmability rules for reruns and replay candidates;
- handling of same `package_id` with different payload identity;
- dashboard semantics when current-state staffing publication is missing:
  unavailable/unknown versus actual zero-load semantics;
- degradation rules when a required schema family is partially missing;
- whether any reader may show a numeric summary when its current-state evidence
  is unavailable.

No runtime slice may start while any blocking item in this list remains implicit.

### A0 freeze authority

Batch A0 is now frozen as a docs-only artifact set in
`implementation-packs/IP-036_CANONICAL_ONBOARDING_CONVERGENCE.md`.

The architecture-level outcomes fixed by that artifact are:

- package identity and payload identity remain separate replay concepts;
- identical preview identities may reuse preview lineage, but completed
  publication may never duplicate;
- same `package_id` with different payload identity fails closed as a conflict;
- missing current-state staffing publication is `unknown` or `unavailable`, never
  numeric zero or implicit availability;
- A1 through A4 now have fixed slice boundaries and stop conditions.

## Target architecture

The converged onboarding stack should be:

```text
operator source profile / preview / confirm
  -> pm onboarding orchestration + audit
  -> source adapter + normalized staging
  -> canonical capability import package
  -> capability-owned publication
  -> capability public read contract
  -> optional temporary derived compatibility projection
```

The critical boundary is that source adapters do not write business tables
directly. Only capability-owned import/publication logic writes canonical facts.

## Canonical convergence rules

1. `pm onboarding` is the only operator-visible import/onboarding entrypoint.
2. Source-specific scripts may survive temporarily only as internal adapters,
   fixtures, or migration scaffolding; they are not product entrypoints.
3. If two tables store the same fact at the same semantic grain, one must be
   removed or explicitly demoted to a derived projection.
4. Freshness and audit must attach to capability publications and onboarding
   runs, not to script names.
5. New features may consume only public read contracts, never direct legacy
   storage internals.
6. If a capability needs both current-state and plan-state staffing, it must ask
   for both explicitly; one may not silently stand in for the other.
7. Any transitional compatibility projection must be generated from canonical
   facts and must have an explicit deletion target.
8. Once a legacy storage path or helper path is no longer required for any
   user-visible capability, the deprecated code that only served that path must
   be deleted rather than retained indefinitely.
9. No runtime convergence slice may start until the coverage/dependency matrix
   for that legacy path is frozen.
10. No slice may expand to "fix everything the regression touched"; uncovered
    dependencies discovered during a slice must be added back to the matrix and
    triaged as blocking or deferred.
11. No runtime slice may enter external review until it has passed its own
    invariant checklist and state-machine self-review.

## Operator-entry convergence map

| Current operator entry | Current shape | Target onboarding source family | Retained canonical owner | Retirement outcome |
| --- | --- | --- | --- | --- |
| `import_workforce_planning.py` | Structured JSON preview/confirm | Workforce planning source under `pm onboarding` | Workforce planning import capability | Remove separate operator path; keep domain importer |
| `import_resource_capacity.py` | Structured JSON preview/confirm | Resource capacity source under `pm onboarding` | Resource intelligence import capability | Remove separate operator path; keep domain importer |
| `import_milestones.py` | Structured JSON preview/confirm | Milestone source under `pm onboarding` | Execution / milestone import capability | Remove separate operator path; keep domain importer |
| `import_project_health.py` | Structured JSON preview/confirm | Project Health re-import source under `pm onboarding` | Project Health re-import capability | Remove separate operator path; keep domain importer |
| Workbook planning source | Workbook profile already under `pm onboarding` | Keep workbook planning source | Workforce planning import capability | Retain as canonical planning path |
| `import_from_excel.py` | Mixed roster + current-load + plan-state workbook path | Split into explicit onboarding-managed planning and current-state staffing sources | Workforce planning plus a new canonical current-state staffing capability | Retire script as product entrypoint |
| `import_skills.py` | Team/skills enrichment JSON | No retained onboarding source in IP-036; retire unsupported feature | None in IP-036; any future skills capability requires a separate redesign | Remove script and all product/runtime dependence |
| `import_hiref.py` | HIREF/contract Excel import | Contract coverage source under `pm onboarding` | Contract coverage capability | Retire script as product entrypoint |
| `import_jira_boards.py` | Board registry CSV | Execution source registry source under `pm onboarding` | Execution source registry capability | Retire script as product entrypoint |
| `import_confluence_pages.py` | Confluence page registry CSV | Status source registry source under `pm onboarding` | Status source registry capability | Retire script as product entrypoint |
| `import_project_profiles.py` | Project profile workbook | Project profile source under `pm onboarding` | Project profile capability | Retire script as product entrypoint |
| `import_cr_csv.py` | Change request CSV | Change request source under `pm onboarding` | Change request import capability | Retire script as product entrypoint |

## Canonical fact families

| Fact family | Semantic question answered | Target canonical owner | Fate of current surfaces |
| --- | --- | --- | --- |
| Member and project identity | Who exists in the planning universe? | Workforce identity / reference publication | Keep identity facts canonical; remove scattered direct-writer ownership |
| Planned staffing | What is planned by month and plan version? | Workforce planning import capability | Keep `plan_versions` and `monthly_allocations` as canonical plan-state facts |
| Current staffing | What is active right now? | New canonical current-state staffing capability | Replace `assignments` / `v_member_load` as authority; allow temporary derived projection only if still needed during migration |
| Member profile context | What retained role/level/email context is available for members? | Existing supported planning/current-state/member sources until a later approved redesign proves a separate owner is needed | Keep only facts still supplied by supported sources; do not preserve `import_skills.py` as an authority path |
| Skills matching | What skill-proficiency facts are available for staffing decisions? | No retained canonical owner in IP-036; unsupported feature is retired in Batch B1 | Remove runtime dependence on `employees.skills` and `import-skills-matrix`; any future reintroduction requires a new design/pack |
| Contract coverage | What HIREF / contract / resource-type facts are in force? | Contract coverage capability | Move away from direct employee-field mutation as the authority path |
| Execution source registry | Which JIRA sources are configured and current? | Execution source registry capability | Keep canonical registry facts; remove standalone CSV operator path |
| Status source registry | Which Confluence sources are configured and current? | Status source registry capability | Keep canonical registry facts; remove standalone CSV operator path |
| Project profile facts | What project-specific static context is published? | Project profile capability | Keep canonical profile facts; remove standalone workbook operator path |
| Change request facts | What change request facts are imported? | Change request import capability | Keep canonical change facts; remove standalone CSV operator path |
| Onboarding audit and freshness | What ran, what published, and how fresh is it? | `pm_agent.data_onboarding` plus capability publication freshness | Keep onboarding run/publication audit as operator authority; demote script-name source IDs to low-level internal evidence only where still useful |

## Read-side convergence

The following product surfaces must stop reading storage internals directly:

- `team-workload-overview`;
- Dashboard team-load summaries;
- Attention rules that reason over active load;
- Staffing availability and feasibility readers;
- other helper flows built on `get_all_members()` / `get_member_projects()` style
  repository shortcuts.

The converged rule is:

- current-state readers consume the canonical current-staffing read contract;
- plan-state readers consume the canonical plan-state staffing read contract;
- mixed use cases must request both explicitly;
- freshness is reported from capability publications, not from script registration
  names.

## Recommended execution sequence

### Batch A0 — Coverage, invariants, state machine, and decision audit

This slice is now complete as a documentation-only handoff unit. Its normative
outputs live in `implementation-packs/IP-036_CANONICAL_ONBOARDING_CONVERGENCE.md`
and include:

- the frozen coverage/dependency matrix;
- the missing-coverage register;
- the invariant checklist;
- the end-to-end state-machine matrix;
- the product/semantic decision log;
- the frozen slice plan for A1 through A4;
- the regression-scope map;
- the runtime slice self-review checklist.

### Batch A1 — Current-state staffing contract skeleton

Scope:

- define the canonical current-state staffing capability boundary;
- add the minimal import/publication/read contract skeleton;
- create the minimal onboarding entry skeleton for that capability;
- avoid reader migration and avoid freshness replacement in this slice.

### Batch A2 — Reader migration

Scope:

- migrate the current-load readers named in the frozen matrix;
- keep scope limited to the readers explicitly assigned to A2;
- avoid unplanned enrichment or registry work.

### Batch A3 — Freshness and evidence migration

Scope:

- replace script-name freshness checks with capability publication freshness for
  the A-scope readers;
- wire the required publication-state evidence and warnings;
- avoid broader data-family migration outside the frozen A-scope.

### Batch A4 — Compatibility closure for current-state staffing

Scope:

- remove or demote temporary shims/projections introduced only for A1-A3;
- close the A-scope deletion targets for legacy current-state staffing authority;
- run the batch-level acceptance closure for the completed A-slices.

### Batch B0 — Post-Batch-A redesign freeze

This slice is now complete as a documentation-only redesign handoff unit.

Scope:

- freeze the owner-approved redesign that retires legacy skills instead of
  migrating it into onboarding;
- freeze the retained contract-coverage / HIREF convergence slices and their
  boundaries;
- avoid runtime, schema, or behavior changes in this slice.

### Batch B1 — Skills retirement

Scope:

- remove product dependence on `employees.skills` and
  `import-skills-matrix` freshness;
- retire `import_skills.py` and its attached operator/test/doc surfaces as a
  bounded deletion slice;
- keep role/level/email handling bounded to already supported sources and do
  not invent a replacement skills onboarding path.

### Batch B2 — Contract coverage contract skeleton

Scope:

- define the canonical contract-coverage capability boundary;
- add the minimal onboarding import/publication/read contract skeleton for
  HIREF / contract facts;
- avoid reader migration and avoid broad employee-field cleanup in this slice.

### Batch B3 — Contract coverage reader and freshness migration

Scope:

- migrate staffing, contract continuity, dashboard, and other explicitly mapped
  read surfaces from direct `employees` / `hiref` sidecar authority to the B2
  contract;
- replace retained HIREF freshness checks with contract-coverage publication
  freshness and evidence semantics;
- avoid unrelated staffing-write redesign or skills reintroduction.

### Batch B4 — Contract coverage closure and legacy deletion

Scope:

- remove or demote temporary HIREF / contract compatibility shims introduced
  only for B2-B3;
- retire the legacy `import_hiref.py` product entry once its readers and
  freshness semantics have converged;
- run the batch-level acceptance closure for the completed B-slices.

### Batch C — Registry and auxiliary onboarding convergence

Converge the remaining onboarding-capable sources.

### Batch D — Final redundancy and deprecated-code cleanup

Remove old operator entrypoints, redundant storage, and deprecated runtime code
only after the earlier slices have already replaced them.

## Execution anti-patterns now forbidden

The convergence program must not repeat these execution patterns:

- using review as the main tool for discovering basic contract scope;
- fixing an example raised by review without first codifying the invariant it
  belongs to;
- entering repeated broad validation loops before the state machine and
  self-review checklist are frozen;
- coding through unresolved product semantics and hoping final review will decide
  them implicitly;
- resuming an abandoned runtime attempt instead of feeding its findings back into
  A0.

## Anti-loop implementation rules

1. **One session = one slice.** Do not try to complete all of Batch A in one
   session.
2. **Freeze acceptance criteria before coding.** Each slice must name its exact
   modified modules, intended outputs, and focused tests before code changes
   begin.
3. **Use focused regression during slice development.** Do not treat full-product
   regression as the primary development loop.
4. **Treat each slice as the review unit.** Run an early read-only slice review
   before starting the next slice; do not wait for one final mega-review.
5. **Triage findings by scope.** Blocking in-scope findings must be fixed in the
   current slice; out-of-scope findings go back into the matrix and are assigned
   to a later slice.
6. **Allow one correction round per accepted slice.** The re-review after a
   correction must check the correction diff and the previously-blocking finding,
   not rediscover the whole program again.
7. **Run broad validation at slice closure, not on every edit.** Each runtime
   slice still needs the repository-required validation before acceptance, but
   that validation happens after the slice is frozen rather than after every
   intermediate fix.
8. **Self-review before external review.** Every runtime slice must be checked
   against its invariant checklist and state-machine matrix before asking for a
   final review.
9. **Stop and re-scope when a missing invariant appears.** If runtime work finds a
   missing invariant or missing semantic decision that should have been frozen in
   A0, stop the slice and reopen the matrix/decision log instead of patching
   forward blindly.

## Acceptance expectations

### Batch A0 acceptance

Batch A0 is complete only when:

- the coverage/dependency matrix is frozen;
- the matrix explicitly lists legacy facts, projections, freshness/evidence, and
  auxiliary side effects for the current-state staffing path;
- the invariant checklist is frozen and includes the mandatory topics;
- the state-machine matrix includes the mandatory scenarios;
- the product/semantic decision log resolves or explicitly defers every blocking
  decision;
- dependent readers and regressions are assigned to A1, A2, A3, A4, or a later
  batch;
- the slice plan prevents runtime work from rediscovering unnamed blocking
  dependencies late.

### Runtime slice acceptance

Each runtime slice should prove all of the following before acceptance:

- the slice's scoped outputs are complete;
- focused regression for the slice passes;
- required repository-level validation for that slice passes;
- read-only review finds no remaining blocking in-scope issue;
- deferred findings are recorded back into the matrix instead of silently folded
  into the current slice.

### Final converged state

The final converged state should satisfy:

- one operator entrypoint;
- one canonical writer per fact family;
- one public read contract per capability;
- no remaining dual-authority path;
- no deprecated runtime code path kept solely for historical compatibility;
- no undocumented legacy side effect still required by regression or product
  behavior.

## Risks to keep explicit

- Current-state staffing convergence can become a hidden second planning system
  if current versus planned semantics are not kept distinct.
- Over-aggressive cleanup of `employees` can blur identity facts with enrichment
  facts instead of separating them.
- Registry-source migration must preserve source-specific deletion/full-sync
  semantics without reintroducing direct table mutation outside capability
  owners.
- If A0 is skipped or rushed, the program will likely fall back into the same
  regression/review loop with a different slice label.

## Next gate

After accepting the frozen A0 artifact set, open a separate implementation
session and perform **only Batch A1 — current-state staffing contract
skeleton**. Do not start A2/A3/A4 in the same session, and do not resume any
abandoned runtime attempt.
