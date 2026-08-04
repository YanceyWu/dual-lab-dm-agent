# IP-036 — Canonical Onboarding Convergence Batch A

Status: `OWNER-REQUESTED FOLLOW-ON IMPLEMENTATION HANDOFF`
Design: `architecture/16_CANONICAL_ONBOARDING_CONVERGENCE_DESIGN.md`
Implementation branch: `TBD IN FOLLOW-ON SESSION`
Baseline: `OWNER-SELECTED POST-IP-035 LOCAL BASELINE`

## Goal

Implement the first bounded slice of the canonical-onboarding convergence
program by replacing the legacy current-load authority path with a new
canonical current-state staffing publication and read contract under
`pm onboarding`.

This batch exists so the repository can preserve workload, staffing, Dashboard,
and load-based Attention behavior without preserving `import_from_excel.py`,
`assignments`, `v_member_load`, or script-name freshness as product authority.

## Why Batch A comes first

The workbook onboarding UAT exposed the most important fracture:

- plan-state workbook onboarding can already publish canonical planning facts;
- current-load readers still depend on a separate legacy path;
- `import_from_excel.py` is the clearest remaining operator entrypoint that both
  overlaps with the new onboarding model and blocks retirement of old current
  staffing semantics.

Until current-state staffing has a canonical owner, the repository cannot safely
delete or demote the legacy path.

## Proposed scope (Batch A only)

- Define a canonical current-state staffing import/publication/read contract.
- Add one approved current-state staffing source under `pm onboarding`.
- Migrate current-load readers to the new read contract, including:
  - workload and availability use cases;
  - Dashboard load summaries;
  - load-dependent Attention logic;
  - any helper flows that currently depend on active assignment storage
    shortcuts.
- Replace script-name freshness coupling with capability publication freshness.
- Keep plan-state staffing semantics unchanged.
- If a compatibility projection is temporarily required, make it strictly
  derived from the new canonical facts and mark it for later deletion.
- If this batch introduces temporary compatibility shims, record their exact
  deletion target so later cleanup can remove the code instead of preserving it
  as permanent fallback behavior.

## Explicit non-goals

- No migration of skills, HIREF, registry, project profile, or change request
  onboarding in this batch.
- No new UI or Dashboard onboarding surface.
- No connector acquisition, scheduling, or live-environment work.
- No broad schema purge outside the surfaces directly replaced by this batch.
- No change to plan-state workforce planning semantics.

## Proposed ownership boundary

- `pm onboarding`
  - remains the sole operator entrypoint, preview/confirm shell, and run audit.
- current-state staffing capability
  - owns current-staffing package validation, publication, freshness, and public
    read contract.
- existing plan-state workforce planning capability
  - remains owner of `plan_versions` and `monthly_allocations`.
- product use cases and projections
  - consume public read contracts only; they must not read legacy current-load
    storage as authority.

## Proposed operator contract

Batch A should produce a controlled workflow equivalent to:

```text
save or select current-staffing source profile
  -> preview onboarding run
  -> review coverage, blockers, warnings, and publish intent
  -> confirm onboarding run
  -> query workload / staffing / dashboard outputs from the new read contract
```

The operator must be able to answer:

- which source profile published the current staffing baseline;
- what coverage and freshness the current staffing publication has;
- whether workload-style capabilities are reading current-state staffing or
  plan-state staffing;
- whether the run replaced, replayed, or rejected a prior current-state
  publication.

## Acceptance criteria

Batch A is complete only when all of the following are true:

1. current-state staffing has one canonical publication path under
   `pm onboarding`;
2. no in-scope user-visible capability requires `import_from_excel.py`,
   `assignments`, or `v_member_load` as the authority path;
3. freshness shown by in-scope readers comes from capability publication state,
   not legacy script IDs;
4. plan-state staffing remains unchanged and explicitly separate;
5. any retained compatibility projection is derived-only and documented as
   temporary.
6. any new compatibility shim created in this batch has an explicit follow-on
   deletion target and is not treated as a new permanent public path.

## Validation plan

Focused validation should cover:

- current-state staffing preview/confirm publication behavior;
- idempotent replay and replacement behavior for current-state staffing runs;
- workload, availability, Dashboard, Attention, and staffing regression through
  the new read contract;
- explicit distinction between current-state and plan-state staffing reads;
- rejection or explicit reporting when current-state publication freshness is
  missing or stale.

Required broader evidence:

- `make validate`;
- `make rehearse-release`;
- independent read-only review;
- clean bootstrap / re-import confidence for the changed schema and import path.

## Rollback

Prefer a software-plus-clean-reimport rollback. Do not design this batch around
long-lived dual-write or complex backfill. If a temporary compatibility
projection exists, rollback must remain possible by reverting the software and
re-importing through the prior baseline.

## Risks and transitional debt to watch

- A current-staffing capability can drift into a second planning model if it
  starts absorbing future-state semantics.
- If any reader silently falls back from current-state to plan-state facts, the
  cleanup will recreate the ambiguity this batch is meant to remove.
- If a compatibility projection becomes writable or permanent, the repository
  will keep the same dual-authority problem under a new name.

## Recommended follow-on sequence after Batch A

1. Batch B — workforce enrichment and contract coverage convergence.
2. Batch C — registry and auxiliary onboarding convergence.
3. Batch D — redundancy deletion and final cleanup.

Each later batch remains separately gated. Do not widen Batch A to absorb them.

The final cleanup batch must remove deprecated code as well as deprecated
storage: replaced scripts, old repository helpers, compatibility facades, dead
branches, and obsolete tests/docs should be deleted once the new path is
accepted and fully wired.

## Next gate

In a separate session and branch, start only this Batch A scope from the exact
owner-selected baseline commit. Before requesting acceptance, complete focused
tests, `make validate`, `make rehearse-release`, and independent read-only
review.
