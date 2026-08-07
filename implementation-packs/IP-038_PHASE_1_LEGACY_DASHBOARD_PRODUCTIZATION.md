# IP-038 — Phase 1 Legacy Dashboard Productization

Status: `OWNER-APPROVED 2026-08-07 — CURRENT WORKING TREE LIMITED TO SLICE 1`
Design: `architecture/17_PHASE_1_LEGACY_DASHBOARD_PRODUCTIZATION_DESIGN.md`
Implementation branch: `phase1-legacy-dashboard`
Baseline: `a6d654a0d2ead6027c1da673fef6d2a2ebcd6e80`

## Goal

Implement a bounded productization program so the external Delivery Manager
trial is presented as a small, stable, evidence-preserving **legacy Dashboard**
offering rather than a broad preview of every newer internal dashboard surface.

This pack is about **surface reduction and safer seams**, not about adding new
business capabilities or rewriting the product.

## Authorized outcome

The owner approved the direction on 2026-08-07. Work may proceed only in the
ordered slices recorded below, with an owner review gate after each slice.

The current working tree is authorized to implement **Slice 1 only** unless a
later review explicitly advances to Slice 2 or beyond.

## Current local state before Slice 1

- the repository now contains both the required legacy Dashboard pages and newer
  later-phase read-only pages in the same shipped shell;
- the external usage-bundle path and dashboard shell do not yet declare one
  code-owned stable trial surface;
- the new Phase 1 design was reviewed and approved as the productization
  direction, but no runtime or bundle gating had begun on this branch when the
  pack was created.

## Ordered slice plan

### Slice 1 — Stable surface declaration and visibility gating

Authorized scope:

- define one code-owned Phase 1 stable surface declaration for the Dashboard
  trial shell;
- gate default dashboard navigation/section visibility to the legacy pages only:
  Overview, Projects, Team, HIREF, Monthly Plan, and Project Health;
- align the usage-bundle trial guidance to the same Phase 1 legacy-dashboard
  story;
- add focused regression proving the default shell does not promote experimental
  tabs by accident.

Acceptance criteria:

- one code-owned declaration names the Phase 1 visible legacy tabs;
- the default dashboard shell hides the experimental tabs from the operator UI;
- default navigation rejects hidden tabs instead of loading them interactively;
- bundle guidance describes the same legacy-dashboard trial surface.

### Slice 2 — Stable and experimental dashboard assembly split

Authorized scope:

- separate stable legacy-page assembly from retained experimental page assembly
  without changing business semantics;
- localize stable-surface wiring so future visibility changes do not require
  mixed-shell edits.

Acceptance criteria:

- stable-page wiring is understandable without reading the experimental
  assembly;
- experimental surfaces may remain implemented internally without being part of
  the default Phase 1 operator surface.

### Slice 3 — Legacy page-provider extraction

Authorized scope:

- add bounded page-level providers or facades for the legacy pages only;
- move page-contract adaptation and degraded-state handling to those page
  boundaries without creating a second domain-logic layer.

Acceptance criteria:

- legacy page contracts no longer depend on mixed view-layer adaptation;
- degraded-state semantics remain explicit and behavior-preserving.

### Slice 4 — Phase 1 config and bundle flattening

Authorized scope:

- narrow the external distribution path to one clear install, launch, and
  default onboarding story suitable for the trial;
- remove competing trial-facing guidance for non-Phase-1 surfaces.

Acceptance criteria:

- a new trial user receives one obvious default path;
- bundle/operator guidance no longer reads like a broad internal development
  surface.

## Explicit non-goals

- No new business capability, query, connector flow, or Dashboard page.
- No deletion of experimental/later-phase capability code merely to reduce file
  count.
- No bootstrap/schema redesign in this productization program.
- No repository-wide repository/facade rewrite outside the bounded legacy-page
  slices.
- No connector/UAT/real-data/release action.
- No conversion of degraded evidence into guessed certainty.

## Proposed ownership boundaries

- `pm_agent.dashboard.surface_manifest`
  - owns the code-level declaration of the Phase 1 stable Dashboard surface.
- `pm_agent.dashboard.web`
  - owns client-side visibility gating and stable-shell presentation behavior.
- `tools/build_usage_bundle.py`
  - owns the generated external bundle guidance for the Phase 1 trial story.
- later Slice 2/3 work
  - must keep stable presentation assembly and legacy page adapters inside the
    Dashboard boundary rather than leaking new logic into bootstrap or unrelated
    capability storage.

## Validation plan

Slice 1 must complete focused evidence before any later slice begins:

- dashboard shell regression covering default visible tabs and hidden-tab
  navigation rejection;
- bundle guidance regression proving the same Phase 1 trial story is emitted in
  the generated bundle workspace;
- relevant dashboard front-end regression for the stable surface behavior;
- `make validate`;
- independent read-only review before acceptance.

Use `make rehearse-release` only when a later slice changes shipped installed
behavior in a way that affects release rehearsal scope beyond the bounded UI or
bundle-story edits.

## Rollback

Prefer a software-only rollback. The productization slices should be reversible
by reverting the bounded surface-manifest, dashboard-shell, and bundle-guidance
changes without requiring data migration or persistent state repair.

## Risks and guardrails

- Do not let the stable surface declaration become a second drifting source of
  truth detached from the actual shell or bundle.
- Do not widen Slice 1 into a dashboard rewrite, API gating program, or legacy
  page data-model redesign.
- Do not hide experimental tabs by deleting their code paths in the same slice;
  keep the behavior reversible.
- Do not convert hidden experimental tabs into implied deprecation of the
  underlying capabilities without a separate decision.

## Next gate

Implement Slice 1 only. After Slice 1 validation and independent review, stop
for owner review before entering Slice 2.
