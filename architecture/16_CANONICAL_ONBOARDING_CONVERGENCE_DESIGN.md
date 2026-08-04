# Canonical Onboarding Convergence Design

Status: `OWNER-REQUESTED FOLLOW-ON DESIGN HANDOFF`
Date: 2026-08-04
Current-state authority: `PROGRESS.md`.
Baseline branch: `TBD IN FOLLOW-ON SESSION`
Baseline commit: `OWNER-SELECTED AFTER THE CURRENT LOCAL ONBOARDING GATE`
Previous local baseline: `IP-035 Structured Data Onboarding Workbook Presets (current local candidate)`

## Decision supported

Rebuild the pre-production onboarding foundation so that:

- every operator-visible import or onboarding action enters through
  `pm onboarding`;
- every business fact family has one canonical writer and one public read
  contract;
- redundant tables, views, functions, freshness IDs, and standalone import
  entrypoints can be removed;
- deprecated scripts, compatibility shims, legacy helpers, and dead code paths
  can be removed once the new canonical path fully replaces them;
- existing user-visible capabilities remain available through the new internals.

This is a pre-production cleanup decision. The repository should preserve
functional behavior and output contracts, not legacy table authority, script
entrypoints, or migration baggage.

## Design-only review boundary

This document defines the target architecture and the recommended execution
sequence only. Runtime, schema, CLI, Dashboard, connector, and real-data changes
still require a separately opened implementation session and a bounded batch.

The current local IP-035 gate remains in force until the owner selects the exact
baseline commit for the new branch.

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

### Clean re-import is the migration strategy

The cleanup path should assume an empty local database plus a versioned,
supported, structured full re-import. The target architecture must not depend on
historical backfill, dual-write, or long-lived compatibility storage.

### No dual authority paths

At end state:

- one operator entrypoint exists (`pm onboarding`);
- one canonical writer exists for each fact family;
- one public read contract exists for each user-visible capability;
- any temporary compatibility projection is one-way derived, clearly bounded,
  and scheduled for removal.

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

## Operator-entry convergence map

| Current operator entry | Current shape | Target onboarding source family | Retained canonical owner | Retirement outcome |
| --- | --- | --- | --- | --- |
| `import_workforce_planning.py` | Structured JSON preview/confirm | Workforce planning source under `pm onboarding` | Workforce planning import capability | Remove separate operator path; keep domain importer |
| `import_resource_capacity.py` | Structured JSON preview/confirm | Resource capacity source under `pm onboarding` | Resource intelligence import capability | Remove separate operator path; keep domain importer |
| `import_milestones.py` | Structured JSON preview/confirm | Milestone source under `pm onboarding` | Execution / milestone import capability | Remove separate operator path; keep domain importer |
| `import_project_health.py` | Structured JSON preview/confirm | Project Health re-import source under `pm onboarding` | Project Health re-import capability | Remove separate operator path; keep domain importer |
| Workbook planning source | Workbook profile already under `pm onboarding` | Keep workbook planning source | Workforce planning import capability | Retain as canonical planning path |
| `import_from_excel.py` | Mixed roster + current-load + plan-state workbook path | Split into explicit onboarding-managed planning and current-state staffing sources | Workforce planning plus a new canonical current-state staffing capability | Retire script as product entrypoint |
| `import_skills.py` | Team/skills enrichment JSON | Workforce profile enrichment source under `pm onboarding` | Workforce profile enrichment capability | Retire script as product entrypoint |
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
| Workforce profile enrichment | What are role/level/email/skills facts? | Workforce profile enrichment capability | Move away from generic multi-writer `employees` mutation |
| Contract coverage | What HIREF / contract / resource-type facts are in force? | Contract coverage capability | Move away from direct employee-field mutation as the authority path |
| Execution source registry | Which JIRA sources are configured and current? | Execution source registry capability | Keep canonical registry facts; remove standalone CSV operator path |
| Status source registry | Which Confluence sources are configured and current? | Status source registry capability | Keep canonical registry facts; remove standalone CSV operator path |
| Project profile facts | What project-specific static context is published? | Project profile capability | Keep canonical profile facts; remove standalone workbook operator path |
| Change request facts | What change request facts are imported? | Change request import capability | Keep canonical change facts; remove standalone CSV operator path |
| Onboarding audit and freshness | What ran, what published, and how fresh is it? | `pm_agent.data_onboarding` plus capability publication freshness | Keep onboarding run/publication audit as operator authority; demote `sync_runs` and script-name source IDs to low-level internal evidence only where still useful |

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

## Recommended batch sequence

### Batch A — Current-state staffing convergence

Create the new canonical current-state staffing capability and move all
current-load readers to it.

Scope:

- define the canonical current-staffing import/publication/read contract;
- expose one approved current-staffing source under `pm onboarding`;
- replace reader dependency on `assignments`, `v_member_load`, and script-name
  freshness IDs;
- keep plan-state staffing semantics unchanged;
- keep any transitional compatibility projection derived-only and temporary.

### Batch B — Workforce enrichment and contract coverage convergence

Split or strictly bound the mutable workforce facts now mixed into `employees`.

Scope:

- move role/level/email/skills to a capability-owned publication or explicitly
  owned extension surface;
- move HIREF/resource-type/billing coverage facts to a contract-coverage
  publication;
- migrate skills and HIREF operator entrypoints under `pm onboarding`;
- remove overlapping multi-writer field ownership.

### Batch C — Registry and auxiliary onboarding convergence

Converge the remaining onboarding-capable sources.

Scope:

- move structured JSON importers behind `pm onboarding` while keeping their
  domain importers as canonical owners;
- move JIRA board registry, Confluence registry, project profile, and change
  request onboarding behind `pm onboarding`;
- standardize audit, publication links, and freshness semantics.

### Batch D — Redundancy deletion and final cleanup

Delete the old operator and storage baggage once all readers and writers have
converged.

Scope:

- remove standalone operator entrypoints;
- remove script-name freshness assumptions from use cases;
- remove redundant tables, views, functions, and helper paths that no longer
  carry distinct semantics;
- remove deprecated scripts, repository helpers, compatibility facades, dead
  branches, and obsolete tests/docs that existed only to support the replaced
  legacy paths;
- update documentation and synthetic demo paths so they describe only the new
  authority model.

## Acceptance expectations

Each bounded batch should prove all of the following before acceptance:

- output parity for the affected user-visible capabilities;
- focused regression for the capability owners and the onboarding wrapper;
- `make validate`;
- `make rehearse-release`;
- independent read-only review;
- explicit clean bootstrap / re-import confidence for any changed import or
  schema boundary.

The final converged state should satisfy:

- one operator entrypoint;
- one canonical writer per fact family;
- one public read contract per capability;
- no remaining dual-authority path;
- no deprecated runtime code path kept solely for historical compatibility.

## Risks to keep explicit

- Current-state staffing convergence can become a hidden second planning system
  if current versus planned semantics are not kept distinct.
- Over-aggressive cleanup of `employees` can blur identity facts with enrichment
  facts instead of separating them.
- Registry-source migration must preserve source-specific deletion/full-sync
  semantics without reintroducing direct table mutation outside capability
  owners.
- `sync_runs` and `data_sources` may still be useful as low-level execution
  telemetry; the cleanup target is operator-facing authority and script-coupled
  semantics, not indiscriminate table deletion.

## Next gate

Open a separate implementation session and branch from the exact owner-selected
post-IP-035 baseline and implement only Batch A first. Do not start Batch B or
later cleanup until Batch A is implemented, validated, rehearsed, reviewed, and
accepted.
