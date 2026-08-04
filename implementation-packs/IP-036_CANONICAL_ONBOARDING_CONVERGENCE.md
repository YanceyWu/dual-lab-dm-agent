# IP-036 — Canonical Onboarding Convergence Batch A0

Status: `A0 FROZEN DOCS-ONLY HANDOFF DRAFTED`
Design: `architecture/16_CANONICAL_ONBOARDING_CONVERGENCE_DESIGN.md`
Implementation branch: `workbook-onboarding-test-20260804-1514`
Clean baseline commit for this session: `8bfd9c8ef2a5b3857c63b9977c811c8d199574ae`

## Goal

Freeze the current-state staffing convergence scope before runtime work resumes, so
later sessions do not rediscover hidden dependencies, replay invariants, or
unknown-data semantics during implementation.

## Authorized outcome

Batch A0 is complete only as documentation, analysis, and frozen slice planning.
It does **not** authorize runtime code changes, schema changes, reader migration,
freshness replacement, legacy deletion, or any continuation of the abandoned
runtime attempt.

## A0 artifact index

1. coverage/dependency matrix
2. missing-coverage register
3. invariant checklist
4. end-to-end state-machine matrix
5. product/semantic decision log
6. frozen slice plan for A1/A2/A3/A4
7. regression-scope map
8. slice self-review checklist

## 1. Frozen coverage/dependency matrix

| Dependency cluster | Current legacy authority | Facts / projections / side effects that matter | Dependent readers / regression surfaces | Frozen replacement owner | Compatibility / deletion rule |
| --- | --- | --- | --- | --- | --- |
| Mixed workbook import (`src/scripts/import_from_excel.py`) | Starts `import-resource-portal` sync run; wipes and rewrites `employees`, `employee_external_ids`, `staffing_placeholders`, `projects`, `assignments`, `monthly_allocations`, `placeholder_monthly_allocations`, `plan_versions`; resets invalid `project_snapshots.staffing_scenario_id`; derives current assignments from one current-month column | One script currently publishes both **plan-state** and **current-state** staffing; full-wipe semantics; placeholder handling; artifact/audit metadata in `sync_runs`; top-load summary printed from `v_member_load` | Workbook UAT findings; Dashboard `/api/summary`, `/api/projects`, `/api/employees`; `team-workload-overview`; `pm workload`; weekly report; resource recommendation reads; attention overload reads; demo characterization | **A1** defines a new canonical current-state staffing contract for the current-state portion only. Existing `workforce_planning_import` remains the plan-state owner. **A4** retires the script as a current-state product authority. | A1-A3 may use a **read-only derived compatibility projection** only. No writable dual-authority shim is allowed for onboarding publication replay. |
| Current member-load projection (`src/pm_agent/database/bootstrap.py` `v_member_load`) | `LEFT JOIN assignments` over active employees; derives `current_load` and `active_projects`; absent publication currently collapses to numeric zero | Hidden semantic risk: missing current-state publication can look like `current_load = 0`, `available`, or `avg_load = 0` instead of unknown/unavailable | `repository.get_all_members()`, `repository.get_member()`, `team_workload`, `team_capacity_context`, `weekly_report`, `resource_planning.recommend`, `operations.validate`, Dashboard `/api/summary` and `/api/employees`, attention overload inputs, `test_unified_use_case_contract.py`, `test_demo_characterization.py` | **A2** migrates readers off direct `v_member_load` authority. **A3** adds publication/freshness semantics to every migrated reader. **A4** deletes or demotes the view. | `v_member_load` may survive only as a read-only projection generated from the canonical publication and only until the last mapped reader is migrated. |
| Current project-team projection (`src/pm_agent/database/bootstrap.py` `v_project_team`) plus direct assignment joins | Active project/member pairing from `assignments` | Project team membership, per-project allocation detail, active project counts | `repository.get_project_team()`, `repository.get_member_projects()`, `team_workload.member_detail`, `pm project team`, Dashboard `/api/projects`, Dashboard `/api/employees` active project lists | **A2** migrates these reader paths to the canonical current-state read contract or a temporary read-only compatibility projection. **A4** closes the projection. | No module may keep ad hoc `assignments` joins once its A2 migration is accepted. |
| Script-name freshness coupling (`data_sources`, `sync_runs`, `repository.get_data_source_freshness()`) | Current readers map script IDs `import-resource-portal`, `import-skills-matrix`, `import-hiref-report` to `fresh/stale/partial/failed/never_synced/inactive/running` | Current-state freshness is coupled to legacy script names rather than capability publications; staffing proposals use these states for decision gating and override audit | `team_workload._workload_freshness()`, `staffing._source_states()`, attention source-freshness observations, `test_unified_use_case_contract.py`, `test_staffing_pipeline.py` | **A3** replaces current-state staffing freshness for A-scope readers with canonical publication freshness/evidence. Batch B keeps skills/HIREF source freshness as adjacent inputs until their own migration. | A3 may preserve legacy script freshness only as supplemental evidence text, never as the primary current-state staffing freshness authority. |
| Skills enrichment sidecar (`src/scripts/import_skills.py`) | Updates `employees.role`, `employees.level`, `employees.email`, `employees.skills`; records `import-skills-matrix` freshness | Highest-skill-wins merge, role/level normalization, missing-data leaves employee unchanged | `staffing` skill matching, `resource_planning` scoring context, Dashboard `/api/employees`, `team_workload` member detail/context | **Deferred to Batch B**. A-scope may consume these facts only as adjacent enrichment evidence. | A1-A4 must not absorb skills ownership. A3 must preserve explicit `unknown/unavailable` freshness semantics when enrichment evidence is missing. |
| HIREF / contract sidecar (`src/scripts/import_hiref.py`) | Updates `employees.resource_type`, `employees.current_hiref`, `employees.billing_end_date`, and `hiref`; marks unmatched active staff as `LTFTE`; may default missing start dates to import date | Contract coverage, STFTE/LTFTE classification, next-action context, import-time fallback notes | `staffing` hiref context, `contract_continuity`, Dashboard `/api/employees` and `/api/projects`, HIREF review/summarization | **Deferred to Batch B**. A-scope treats HIREF as adjacent evidence, not current-state staffing ownership. | A1-A4 must not rewrite HIREF ownership or source semantics. A3 preserves explicit freshness state for decision gating. |
| Legacy dashboard direct SQL routes (`src/pm_agent/dashboard/server.py`) | `/api/summary`, `/api/projects`, `/api/employees` query `employees`, `assignments`, `v_member_load` directly; `X-DM-Interface-Contract: legacy-direct-read` remains explicit | Current numeric summaries have no current-state publication-state guard; project/member lists silently assume `assignments` is authoritative | `test_unified_use_case_contract.py::test_legacy_dashboard_direct_sql_route_is_explicitly_marked`, `test_demo_characterization.py::test_demo_dashboard_summary_and_health_are_offline`, local dashboard UI | **A2** migrates these routes to the canonical current-state contract or a current-state compatibility reader. **A3** enforces unknown/unavailable semantics. | Temporary adapters must be read-only and must stop returning numeric availability summaries when publication state is not `fresh` or `stale`. |
| Legacy helper consumers (`team_workload`, `weekly_report`, `resource_planning`, `attention` overload inputs) | `get_all_members()`, `get_member_projects()`, `get_project_team()`, and direct `v_member_load`/`assignments` reads | Availability classification (`available` if `<0.8`, `overloaded` if `>=1.0`), overloaded counts, recommendation context, attention facts | `pm workload`, `/api/use-cases/team-workload-overview`, weekly report output, `pm allocate` recommendation path, attention resource overload | **A2** migrates read-side consumers named here. `resource_planning.confirm()` and any manual mutable assignment flow remain outside A-scope and are explicitly deferred. | Read-side migration may proceed; manual current-state mutation must not be silently folded into A2. If mutable legacy writes remain, A4 cannot claim full authority deletion. |
| Seed / demo / characterization fixtures | `scripts/seed.py`, `scripts/seed_demo_evidence.py`, demo characterization data, tests that expect `assignments`-backed reads | Synthetic demo data still mirrors the legacy `assignments` model and must not accidentally reassert it as canonical authority | `test_demo_characterization.py`, `test_synthetic_seed.py`, local demo flows | **A2/A3** update only the A-scope expectations. Broader fixture redesign is **deferred** unless directly required by migrated readers. | Keep synthetic fixtures, but make any remaining legacy mirror status explicit in comments/tests until A4 closure. |

## 2. Missing-coverage register

| Missing coverage item | Why it is currently missing | Blocks next slice? | Frozen owner | Frozen note |
| --- | --- | --- | --- | --- |
| No canonical current-state staffing package / publication / read contract exists | Workbook onboarding only publishes workforce planning and optional capacity packages; no current-state staffing domain package is emitted today | **Yes** | **A1** | A1 must create the minimal current-state staffing capability skeleton and publication identity model before any reader migration begins. |
| No canonical current-state reader contract exists for member load / project team semantics | Readers still consume `assignments`, `v_member_load`, or ad hoc joins | **Yes** | **A1** defines contract; **A2** migrates readers | A2 must not invent semantics; it consumes the A1 contract only. |
| No publication-backed freshness/evidence model for current-state staffing | A-scope readers use legacy script-name freshness instead of capability publication freshness | **No for A1**, **Yes for A3** | **A3** | A1 may leave legacy freshness untouched; A3 must replace it for A-scope readers. |
| No explicit degradation contract for missing current-state schema family or missing current publication | Current direct SQL surfaces can imply zero/available from empty joins | **No for A1**, **Yes for A2/A3** | **A2/A3** | The semantic rule is frozen now: missing current-state evidence must surface as `unknown`/`unavailable`, never numeric zero. |
| Skills enrichment remains a separate mutable owner | `import_skills.py` still updates `employees` directly and owns role/level/skills freshness | **No** | **Batch B** | A-scope may depend on it as adjacent evidence only; do not pull it into A1-A4. |
| HIREF / contract coverage remains a separate mutable owner | `import_hiref.py` still updates `employees` and `hiref` directly | **No** | **Batch B** | A-scope preserves explicit dependency and freshness semantics but does not migrate HIREF ownership. |
| Manual mutable assignment flow still exists outside onboarding convergence | `resource_planning.confirm()`, `repository.create_assignment()`, and `repository.end_assignment()` still write `assignments` directly | **No for A1**, **Potential blocker for late A4 deletion** | **Explicit defer after A4 unless separately authorized earlier** | A1-A4 may migrate read authority away from `assignments`, but they may not silently redesign manual mutable staffing flows. |
| Legacy direct SQL dashboard contract is still user-visible | `/api/summary`, `/api/projects`, `/api/employees` remain marked `legacy-direct-read` | **No for A1**, **Yes for A2** | **A2** | A2 owns migration or explicit compatibility projection for these routes. |

## 3. Invariant checklist

- [x] **Package identity vs payload identity** — `package_id` names the business replay identity; payload identity is a deterministic fingerprint over canonical preview/publication material. Same `package_id` plus different payload identity is a conflict, not idempotent replay.
- [x] **Preview reuse** — identical preview fingerprint may reuse the prior preview run and its planned package set. Reuse is allowed only when the prior run was not invalidated by profile/source change semantics.
- [x] **Confirmability** — only previewed, failed, or partially completed runs tied to the same frozen preview identity may be confirmed or retried. Rejected stale previews are not confirmable.
- [x] **Replay safety** — later confirm attempts after a completed publication must return the existing completion identity, not mint a second completed publication.
- [x] **Publication completion** — one current-state staffing run may produce at most one completed publication per capability. Partial publication may be resumed only against the same run identity and may not create duplicate completed links.
- [x] **Same `package_id`, different payload** — must fail closed as a replay/uniqueness conflict until the operator republishes under a new business identity or reuses the exact original payload.
- [x] **Missing-schema degradation** — if the required current-state staffing schema family is missing locally, readers return `unavailable` with an explicit reason; they do not invent zero or empty-known summaries.
- [x] **Missing-publication degradation** — if schema exists but no current-state publication exists for the requested scope, readers return `unknown` and suppress numeric availability/load summaries.
- [x] **Partial-data degradation** — `partial` means some required current-state evidence is missing or not covered. Row-level facts may remain visible only with explicit state, but team-level summary numbers that imply full coverage must be suppressed.
- [x] **Dashboard unknown-data semantics** — Dashboard and summary surfaces may emit numeric current-state availability/load aggregates only when the backing current-state publication state is `fresh` or `stale`. They must not emit "everyone available" or `0` as a substitute for missing evidence.
- [x] **Freshness-state semantics** — `fresh` and `stale` describe known published facts; `partial`, `unknown`, and `unavailable` describe incomplete or missing evidence and must remain explicit in reader results. Decision flows may override only non-fresh freshness through audited manager intent, never missing schema.
- [x] **Plan-state separation** — missing current-state staffing publication must not hide or rewrite workforce-planning publications. Planned staffing stays visible through its existing owner and must not masquerade as current-state staffing.
- [x] **Compatibility shims** — any A-scope shim must be read-only, generated from canonical current-state publication facts, named in this matrix, and assigned a deletion target. A writable legacy shim is forbidden.

## 4. End-to-end state-machine matrix

| Scenario | Frozen preview result | Frozen confirmability | Frozen publication result | Frozen next step / reader effect |
| --- | --- | --- | --- | --- |
| First preview, new package identity, new payload identity | `previewed` | Confirmable | None yet | Await explicit confirm. No reader may treat preview as published data. |
| Repeated preview with identical profile/source/payload fingerprint | Reuse prior preview identity | Confirmable | None yet | Return the same planned package identity set; do not create a second preview lineage for the same fingerprint. |
| Confirm after valid preview | `completed` | Confirm consumes the preview | Exactly one completed current-state publication link | Later confirm returns the same completed result idempotently. |
| Post-confirm preview with identical payload identity | `already_completed` / idempotent replay | No new confirm required | Existing completed publication reused | Do not create a second completed publication. |
| Already-completed replay from the same `package_id` and same payload identity | `already_completed` | Not a new publication attempt | Existing completed publication remains current | Safe idempotent response only. |
| Preview rejected because profile/source changed during or after preview | `rejected` with stale blocker | **Not confirmable** | None | Operator must preview again; later confirm on the stale run is forbidden. |
| Same `package_id` with different payload identity | `rejected` replay/uniqueness conflict | **Not confirmable** | None | Fail closed; require a new `package_id` or exact payload reuse. |
| Multiple confirm attempts after one completed publication | First confirm completes; later confirms are idempotent | Confirm remains safe only as replay of the completed run | No duplicate completed publication IDs | Duplicate completion is forbidden even if the caller retries later. |
| Partial publication followed by retry | `partially_completed` | Retry allowed only on the same run identity while invariants still match | Retry may complete the same logical publication; it may not create a second completed lineage | If profile/source identity changed, retry is blocked and the operator must preview again. |
| Non-confirmable preview followed by confirm request | Preview remains `rejected` | Confirm denied with not-confirmable failure | None | No side effects. |
| Required schema family missing at read time | No preview implication | N/A | N/A | Reader state is `unavailable`; no numeric current-state summaries or availability classifications. |
| Current-state publication missing but schema family exists | No preview implication | N/A | No current publication for scope | Reader state is `unknown`; planned staffing may still be shown separately. |
| Current-state publication is stale | Existing publication remains readable | N/A | Last known publication remains current but stale | Numeric current-state summaries may be shown only with explicit stale evidence/warnings. |
| Current-state publication is partial | Existing publication is incomplete | N/A | Publication exists but coverage incomplete | Reader state is `partial`; row-level facts may show state, but team-level availability/load aggregates are suppressed. |
| Planned staffing exists but current-state publication is missing | Existing plan publication unchanged | N/A | Only plan-state is known | Product must show "planned known / current unknown-or-unavailable", never treat plan data as current load. |

## 5. Product / semantic decision log

| ID | Frozen decision | Status |
| --- | --- | --- |
| D-01 | **Package identity and payload identity stay separate.** The replay key is the business `package_id`; the safety key is the deterministic payload fingerprint. Same `package_id` with a different payload is a hard conflict. | Frozen |
| D-02 | **Preview reuse is fingerprint-based.** Re-running preview with the same profile binding, source identity, and preview payload reuses the existing preview lineage instead of multiplying previews. | Frozen |
| D-03 | **Completed publication is idempotent.** Later confirm or replay requests must reuse the existing completed publication identity and must never publish a second completed record for the same logical run. | Frozen |
| D-04 | **Partial publication may resume only in-place.** A retry after partial completion may continue the same run identity, but only if profile/source invariants still match. | Frozen |
| D-05 | **Missing current-state publication is not zero.** Dashboard, summary, and workload surfaces must treat missing current-state publication as `unknown` or `unavailable`, never as numeric zero load or "everyone available". | Frozen |
| D-06 | **Numeric summary suppression rule.** A-scope readers may emit numeric current-state availability/load aggregates only when current-state publication state is `fresh` or `stale`; `partial`, `unknown`, and `unavailable` suppress those aggregates. | Frozen |
| D-07 | **Plan-state stays separate.** Workforce-planning publications remain authoritative for planned staffing even when current-state staffing is missing. No reader may substitute plan-state load for current-state load. | Frozen |
| D-08 | **Missing schema family is `unavailable`, not `unknown`.** `unknown` means the contract exists but has no current publication for the requested scope; `unavailable` means the schema/contract family is missing or unreadable. | Frozen |
| D-09 | **Legacy script freshness is transitional evidence only.** Current-state staffing freshness for A-scope readers must move to publication freshness in A3; script-name freshness may remain as adjacent source evidence only. | Frozen |
| D-10 | **Skills and HIREF stay adjacent during A-scope.** A1-A4 may depend on those facts and freshness states, but they may not claim ownership of those data families. | Frozen |
| D-11 | **Physical storage shape for the new current-state staffing capability is deferred.** A1 must choose the dedicated capability-owned schema/module shape, but it must preserve every invariant already frozen here. | Deferred to A1 |
| D-12 | **Exact dashboard copy and badge wording are deferred.** A0 freezes semantic states and suppression rules, not the final UI phrasing. | Deferred to A2/A3 |
| D-13 | **Manual mutable assignment convergence is deferred.** Legacy write paths such as `create_assignment()` and `end_assignment()` are outside A1-A4 unless later explicitly authorized. | Deferred after A4 |

## 6. Frozen slice plan

| Slice | Exact goal | Allowed modules / capabilities | Focused tests expected | Exact stop condition | Must not touch |
| --- | --- | --- | --- | --- | --- |
| **A1 — current-state staffing contract skeleton** | Create the minimal canonical current-state staffing capability boundary, preview/confirm/publication identity model, and public read-contract skeleton for onboarding-managed current-state staffing | New dedicated current-state staffing capability module family under `src/pm_agent/`; minimal `pm_agent.data_onboarding` wiring needed to plan/publish that capability; bootstrap **composition wiring only** for the new capability-owned schema module; focused new tests under `src/tests/` | New current-state staffing preview/confirm/publication tests; focused onboarding replay/idempotency tests; no reader contract tests yet | A dedicated current-state staffing publication/read contract exists and can be previewed/confirmed in isolation, but no existing product reader has been migrated yet | `dashboard/server.py`; `use_cases/team_workload.py`; `team_capacity_context.py`; `use_cases/staffing.py`; `import_skills.py`; `import_hiref.py`; any legacy deletion; Batch B/C/D |
| **A2 — reader migration** | Move A-scope current-load readers from raw `assignments` / `v_member_load` / `v_project_team` authority to the A1 contract or its temporary read-only compatibility projection | `pm_agent/database/repository.py` read helpers; `pm_agent/use_cases/team_workload.py`; `pm_agent/use_cases/team_capacity_context.py`; `pm_agent/dashboard/server.py` current-state routes; `pm_agent/use_cases/weekly_report.py`; `pm_agent/use_cases/resource_planning.py` **read side only**; `pm_agent/database/attention.py`; `pm_agent/attention/rules.py`; `pm_agent/cli/commands/operations.py` adapters; focused tests | `test_unified_use_case_contract.py`; `test_demo_characterization.py`; `test_allocation_and_weekly_report.py`; attention overload tests; any new current-state staffing reader tests | Named A-scope readers no longer read raw `v_member_load`, `v_project_team`, or ad hoc current-state `assignments` joins directly | `use_cases/staffing.py` freshness semantics; `import_skills.py`; `import_hiref.py`; manual mutable assignment writes; schema deletion; Batch B/C/D |
| **A3 — freshness and evidence migration** | Replace A-scope current-state freshness/evidence semantics so readers stop using legacy script-name freshness as the primary authority | Current-state staffing capability freshness/evidence read layer; `pm_agent/database/repository.py` freshness adapters as needed; `pm_agent/use_cases/team_workload.py`; `pm_agent/use_cases/team_capacity_context.py`; `pm_agent/use_cases/staffing.py`; `pm_agent/dashboard/server.py`; focused tests | `test_unified_use_case_contract.py` freshness cases; `test_staffing_pipeline.py`; new current-state publication-state tests | A-scope readers emit `fresh/stale/partial/unknown/unavailable` from capability publication semantics and honor the suppression rules frozen in A0 | Skills/HIREF ownership migration; reader expansion outside the named A-scope; compatibility deletion; Batch B/C/D |
| **A4 — compatibility closure for current-state staffing** | Remove or demote temporary A-scope compatibility projections and retire the legacy current-state product entry once A1-A3 are accepted | Current-state staffing capability module family; read-only compatibility projections; `import_from_excel.py` current-state authority path; docs/tests tied to A-scope migration | Focused regression for migrated readers plus compatibility-closure tests | No A-scope reader depends on `v_member_load`, `v_project_team`, or direct current-state `assignments` authority; every surviving compatibility artifact is either deleted or explicitly reclassified as a deferred blocker | Skills/HIREF migration; registry convergence; broad legacy cleanup outside A-scope; Batch B/C/D; silent redesign of manual mutable assignment writes |

## 7. Regression-scope map

| Surface / regression cluster | Why it belongs here | Frozen slice |
| --- | --- | --- |
| `src/tests/test_unified_use_case_contract.py` workload contract, workload freshness, dashboard workload endpoint | Exercises `team-workload-overview`, current-state member context, and freshness warnings | **A2** for reader contract migration; **A3** for freshness/unknown semantics |
| `src/tests/test_unified_use_case_contract.py::test_legacy_dashboard_direct_sql_route_is_explicitly_marked` and Dashboard `/api/summary` | Explicit proof that the old summary path is still legacy direct read | **A2** to migrate route authority; **A3** to enforce unknown-data semantics |
| `src/tests/test_demo_characterization.py::test_demo_dashboard_summary_and_health_are_offline` | Demo dashboard currently depends on current-state direct SQL | **A2/A3** |
| `src/tests/test_staffing_pipeline.py` freshness blockers, override audit, source-change invalidation | Decision flows must keep audited non-fresh override behavior while freshness authority moves | **A3** |
| `pm workload`, `team-workload-overview`, `team_capacity_context` | Direct workload UX and availability classifications rely on current-state load facts | **A2/A3** |
| Dashboard `/api/projects` and `/api/employees` | Direct project/member summaries still join `assignments` and `v_member_load` | **A2/A3** |
| `weekly_report.py`, attention overload inputs, `resource_planning.recommend()` read path | Legacy helper consumers of current-load facts; should migrate only after A1 contract exists | **A2** |
| `contract_continuity.py` and HIREF review/display | Coupled to HIREF ownership and active-assignment display | **Deferred to Batch B** unless a later owner narrows a separate bridge slice |
| Manual `resource_planning.confirm()`, `repository.create_assignment()`, `repository.end_assignment()` | Mutable legacy assignment writes are not onboarding replay/read migration work | **Deferred after A4** |

## 8. Slice self-review checklist

Every runtime slice must complete this checklist before requesting external
review:

1. Scope matches the frozen A0 slice boundary exactly; no opportunistic adjacent migration was folded in.
2. Every changed reader/write path maps to a row in the coverage matrix and keeps the assigned owner/deletion target.
3. Replay, confirmability, and duplicate-publication invariants remain true for every touched current-state staffing operation.
4. `unknown` / `unavailable` / `partial` semantics stay explicit; no numeric zero or "available" fallback was introduced for missing current-state evidence.
5. Focused tests for the slice were updated or added only where the frozen slice plan said they should be.
6. Any out-of-scope finding discovered during the slice was recorded back into the matrix/register instead of being silently fixed.
7. `PROGRESS.md` and the active IP-036 handoff text reflect the actual working tree, validation evidence, deferred items, and commit/push state.

## Validation plan for A0

Batch A0 remains documentation-only. Validation stays documentation-appropriate:

- `git diff --check` for the changed handoff documents;
- read-only review against the required failure classes, invariants, state-machine
  scenarios, and slice boundaries;
- `PROGRESS.md` continuity update naming the next session's single allowed target.

`make validate` and `make rehearse-release` remain explicitly out of scope for A0.

## Next gate after A0

The next session may do **only A1 — current-state staffing contract skeleton**.
It must not start A2/A3/A4, must not resume the abandoned runtime attempt, and
must not reinterpret the deferred Batch B items as A-scope work.
