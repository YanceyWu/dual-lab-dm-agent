# Phase 1 Legacy Dashboard Productization Design

Status: `OWNER-APPROVED 2026-08-07 — IMPLEMENT THROUGH A SEPARATE BOUNDED PACK ONLY`
Date: 2026-08-06
Current-state authority: `PROGRESS.md`.
Baseline branch: `phase1-legacy-dashboard`
Baseline commit: `a6d654a0d2ead6027c1da673fef6d2a2ebcd6e80`
Previous implemented baseline: `IP-037 combined pushed workbook branch state`

## Decision supported

Define a bounded **Phase 1 productization slice** for external Delivery Manager
trial use so the product can be distributed as a small, stable,
evidence-preserving **legacy Dashboard** offering while newer capabilities remain
available for internal development only.

The immediate objective is **not** to add features or rewrite the system. The
objective is to reduce operator-visible state, configuration branches, and
change blast radius until the first external trial becomes a controlled
experiment rather than a broad preview of everything in the repository.

## Review boundary

This document is design-only. It does not authorize runtime, schema, package,
bundle, connector, or UI changes. A separately approved implementation pack is
required before any refactor or visibility change begins.

## First-principles objective

The first external trial only needs to prove one proposition:

> a Delivery Manager can install the product, onboard approved local data, and
> use the legacy Dashboard to answer routine management questions with low
> support cost and explicit unknown-data semantics.

That proposition is satisfied only when the product exhibits all of the
following:

1. **one small supported operator surface** rather than multiple competing
   surfaces;
2. **truthful output semantics** where `unknown`, `partial`, `stale`, and
   `unavailable` remain explicit;
3. **one predictable installation and onboarding path** rather than multiple
   equally advertised setup variants;
4. **bounded change blast radius** so a legacy-page correction does not require
   editing mixed stable/experimental presentation code.

## Adversarial assumptions

This design assumes the trial environment behaves adversarially:

- users will click or ask about any surface they can see, not just what the
  documentation recommends;
- users will treat any visible page as an implicitly supported product promise;
- users will not distinguish configuration mistakes from product problems unless
  the default path is extremely narrow;
- users may interpret a missing fact as `0`, healthy, or clear if the UI does
  not make degraded state explicit;
- future maintainers will forget oral scope agreements unless the supported
  surface is declared in product-owned structure.

Therefore the Phase 1 problem is not primarily "too many lines of code". It is
"too many exposed states for a controlled trial".

## Current state that creates trial risk

The repository now contains a broader set of capabilities than the intended
first external trial:

- the legacy Dashboard pages are the required Phase 1 operator UI;
- additional newer read-only pages and capabilities exist for internal product
  evolution and local review;
- operator-facing behavior is described across dashboard navigation, bundle
  content, onboarding guidance, Copilot routing, and documentation;
- internal read paths still include a mix of canonical publications,
  compatibility projections, and older read artifacts.

That broader state is acceptable for development, but it is risky for an
external trial because it can create:

- false-positive feedback on surfaces that are not ready for support;
- false-negative feedback caused by setup/configuration complexity rather than
  the legacy Dashboard itself;
- unnecessary regression risk when stable and experimental presentation concerns
  are edited together.

## Phase 1 operator contract

Phase 1 should promise a deliberately narrow operator surface.

| Area | Phase 1 supported contract | Retained internally but outside the Phase 1 contract |
| --- | --- | --- |
| Dashboard UI | Legacy pages only: Overview, Projects, Team, HIREF, Monthly Plan, Project Health | Newer read-only pages may remain in the repository for development and internal review, but are not part of the external operator promise |
| Setup and onboarding | One documented install path, one documented dashboard launch path, one default approved onboarding path | Additional onboarding source families, presets, and developer-oriented helper flows may remain for internal evolution |
| Documentation and bundle guidance | Only the Phase 1 stable surface is promoted to trial users | Internal/reference documentation may continue to describe broader capability history and evolution |
| Copilot/operator guidance | Support the Phase 1 surface and its minimum troubleshooting path | Broader internal discovery and development use remains available in the development repository |

This contract does **not** require deleting newer capabilities from the codebase.
It requires making the external promise smaller and more explicit than the full
internal repository surface.

## Design goals

### 1. Reduce operator-visible state

The Phase 1 trial should expose one deliberate surface, not a loosely filtered
development surface.

### 2. Preserve truthful business semantics

The product must continue to show `unknown`, `partial`, `stale`, and
`unavailable` explicitly. Productization must not convert degraded evidence into
guessed values or healthy-looking placeholders.

### 3. Reduce support cost

A new Delivery Manager should have one obvious install/setup/onboarding path.
Support should focus on product value rather than feature discovery or setup
branch selection.

### 4. Reduce change blast radius

A change to one legacy page or one Phase 1 visibility decision should not force
edits across mixed experimental presentation paths.

### 5. Keep the long-term extensibility path

This is a **strangler productization step**, not a rewrite. Experimental and
later-phase capabilities may remain in the repository, but Phase 1 work should
introduce clearer seams so future promotion or replacement can happen
incrementally.

## Design decisions

### Decision A — declare one code-owned stable surface manifest

Phase 1 should have one product-owned declaration of the supported external
surface. That declaration should drive, or at minimum be checked against:

- dashboard page visibility/navigation;
- bundle/distribution content and instructions;
- operator-facing Copilot routing/guidance;
- supported onboarding path messaging;
- focused tests that prove hidden/promoted surfaces match the product contract.

The purpose is to replace scope-by-memory with scope-by-contract.

### Decision B — treat the legacy Dashboard as the only guaranteed Phase 1 UI

The legacy Dashboard is the Phase 1 operator experience. Newer dashboard
surfaces may remain implemented, but they are not part of the first external
trial contract and should not be promoted or exposed by default in the trial
experience.

This avoids blending two product stories:

1. "the stable legacy Dashboard we want external DMs to evaluate now"; and
2. "the broader evolving internal dashboard surface that may become promotable
   later".

### Decision C — split stable and experimental presentation assembly

The dashboard presentation boundary should separate:

- the stable Phase 1 legacy-page assembly; and
- the retained experimental or later-phase page assembly.

The purpose is not aesthetic cleanup. The purpose is to reduce regression risk
and make visibility decisions local rather than cross-cutting.

This split should preserve current behavior for retained internal surfaces while
making the Phase 1 assembly independently understandable and testable.

### Decision D — add page-level legacy providers/facades

Each legacy page should read through a small page-level provider/facade that
owns the page contract and degraded-state semantics for that page.

These providers/facades should:

- adapt canonical publications and retained compatibility artifacts into the
  page contract;
- preserve explicit `unknown` / `partial` / `unavailable` semantics;
- keep formatting and view-model assembly close to the page boundary;
- avoid growing into a second domain-logic layer.

This is a bounded refactor for the Phase 1 legacy pages only. It is **not** a
repository-wide rewrite of every read path.

### Decision E — flatten the Phase 1 configuration and distribution path

The external trial should have one obvious path for:

- local installation;
- minimum configuration validation;
- default onboarding;
- dashboard launch;
- first-use instructions.

Advanced options, alternative onboarding paths, and broader internal workflows
may remain in the development repository, but they should not compete with the
Phase 1 default path in the trial distribution.

## Ordered implementation slices

If this design is approved, the work should proceed in four ordered slices.

### Slice 1 — stable surface declaration and visibility gating

Scope:

- define the Phase 1 stable surface explicitly;
- gate dashboard/navigation/distribution/operator guidance against that surface;
- prove that non-Phase-1 surfaces are not accidentally promoted in the trial
  default path.

Acceptance expectation:

- the Phase 1 surface can be named from one product-owned declaration;
- dashboard, bundle, and guidance reflect that same declaration;
- focused tests fail if a hidden surface is accidentally re-promoted.

### Slice 2 — stable/experimental dashboard assembly split

Scope:

- separate stable legacy-page assembly from retained experimental assembly;
- keep app startup and routing behavior understandable without editing one large
  mixed presentation surface.

Acceptance expectation:

- a legacy-page visibility or wiring change is localized to the stable assembly;
- experimental surfaces can remain implemented without being part of the Phase 1
  operator contract.

### Slice 3 — legacy page-provider extraction

Scope:

- introduce page-level providers/facades for the legacy pages;
- move page-contract adaptation and degraded-state handling to those boundaries;
- avoid a broader read-model redesign.

Acceptance expectation:

- the most important legacy pages can evolve without direct mixed read-path
  changes in their view layer;
- legacy pages continue to preserve explicit degraded-state semantics.

### Slice 4 — Phase 1 config/bundle flattening

Scope:

- narrow the external distribution path to the supported install, onboarding,
  launch, and operator guidance flow;
- remove competing trial-facing guidance for non-Phase-1 surfaces.

Acceptance expectation:

- a new external DM receives one documented default path;
- support/trial feedback can focus on legacy Dashboard usefulness rather than
  surface discovery.

## Success measures

The Phase 1 productization slice is successful when:

1. the trial bundle and operator instructions present only the intended legacy
   Dashboard product story;
2. a user can describe the supported trial surface without referring to hidden
   tribal knowledge;
3. a degraded legacy metric appears as explicitly degraded, never as an invented
   zero or false clear state;
4. a bounded legacy-page fix does not require editing mixed stable/experimental
   presentation code;
5. trial feedback is mainly about the usefulness and trustworthiness of the
   legacy Dashboard itself, not about which surface should have been used.

## Explicit non-goals

- No new business capability, new operator workflow, or expanded Dashboard page
  set.
- No deletion of later-phase capabilities merely to reduce file count.
- No repository-wide repository/facade rewrite outside the legacy-page boundary.
- No bootstrap/schema redesign in the same productization batch.
- No connector/UAT/real-data/release action.
- No conversion of evidence-limited states into synthetic certainty.

## Validation and acceptance expectation

An approved implementation pack should require:

- focused visibility/navigation regression for the Phase 1 surface;
- focused legacy-page regression for degraded-state rendering and page contracts;
- bundle/documentation checks proving the same supported story is presented
  externally;
- `make validate`;
- `make rehearse-release` when package/distribution changes affect the shipped
  operator bundle or installed behavior;
- independent read-only review after each slice and again before final
  acceptance.

## Risks and guardrails

- Do not create a second source of truth where the stable surface manifest and
  the docs can drift silently.
- Do not let legacy page providers absorb unrelated domain rules or persistence
  ownership.
- Do not hide degraded states merely to make the UI look cleaner.
- Do not widen the productization slice into a full dashboard rewrite or a full
  repository cleanup campaign.

## Next gate

Owner-review this design only. If accepted, authorize a separate bounded
implementation pack for the ordered Phase 1 productization slices. Do not start
the refactor from this document alone.
