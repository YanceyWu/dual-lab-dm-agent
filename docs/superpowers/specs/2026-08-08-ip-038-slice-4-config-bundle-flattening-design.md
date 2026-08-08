# IP-038 Slice 4 — Phase 1 config and bundle flattening design

Status: `DRAFTED 2026-08-08 AFTER OWNER ACCEPTED SLICE 3 AND AUTHORIZED SLICE 4`

## Goal

Narrow the external Phase 1 trial story to one obvious default operator entry:
**open the usage bundle in VS Code and use the `Delivery Manager` workspace
agent**. Within that one entry, the bundle landing page must present **two
equal first-run paths**:

1. `Try demo`
2. `Use local data`

This slice is about **bundle and guidance flattening only**. It must not add new
runtime capability or redesign the dashboard.

## Why this slice exists

After Slice 3, the legacy dashboard surface is stable enough for trial use, but
the external distribution path still reads like a developer/deployment package
instead of a narrow Delivery Manager trial experience.

The owner approved these Slice 4 product constraints during design:

- the only default entry should be **VS Code + Delivery Manager agent**;
- the landing page must show **demo** and **local-data onboarding** as equal
  first-run paths;
- the bundle should stay **single-bundle, single-entry**, not split into demo vs
  local-data distributions;
- the change must remain bounded to bundle/config/guidance surfaces.

## In scope

- generated usage-bundle landing guidance from `tools/build_usage_bundle.py`;
- the generated bundle root `README.md`;
- the generated bundle runtime `src/README.md`;
- any minimal bundle-facing open/install guidance text needed to keep the
  landing story coherent;
- focused bundle regression coverage proving the new trial story is emitted.

## Out of scope

- dashboard page behavior or page contracts;
- `pm` command semantics or CLI feature additions;
- connector/UAT scope changes;
- repository-wide README/doc cleanup beyond the minimum needed to keep the
  bundle story consistent;
- interaction-memory, personalization, or other unaccepted local batches;
- multi-bundle distribution variants.

## Selected approach

Use **one bundle** and **one default open path**:

- install from the bundle root;
- open the bundle in VS Code;
- use the `Delivery Manager` agent;
- make the bundle landing page the one authoritative first-run story;
- present two equal next steps on that landing page:
  - `Try demo`
  - `Use local data`

`src/README.md` remains available, but only as runtime/reference guidance rather
than the primary trial landing page.

## Target operator experience

### First minute

The operator sees one short top-level story:

1. run the install script;
2. run the open-in-VS-Code script;
3. choose either:
   - `Try demo`
   - `Use local data`

### Try demo path

The landing page gives the minimum commands and prompts required to get a useful
answer from synthetic data quickly. It should emphasize fast value discovery,
not technical setup detail.

Expected effect:

- a first-time DM can reach a working demo and ask one meaningful business
  question within a few minutes;
- the path does not require reading deep runtime docs before asking questions.

### Use local data path

The landing page gives the minimum bounded steps needed to initialize local
state and move into approved local data onboarding without pretending that demo
data is the only supported flow.

Expected effect:

- a first-time DM can see the correct safe path for local configuration and
  onboarding immediately;
- the path points to deeper runtime docs only after the landing page has already
  explained the operator sequence.

## Design decisions

### 1. One landing page owns the trial story

The generated bundle root `README.md` becomes the single authoritative landing
page for the external trial package.

It should contain:

- a short statement that this is the Delivery Manager local trial bundle;
- the single default entry: install, then open in VS Code;
- two equal first-run sections/cards/blocks for `Try demo` and `Use local data`;
- a short note that the legacy dashboard trial surface remains the supported
  Phase 1 dashboard UI;
- a boundary section reminding users not to treat the bundle as a development
  workspace.

It should not contain:

- broad capability inventories that read like internal product documentation;
- full CLI catalogs on the landing page;
- multiple competing “main ways to start”;
- developer/release engineering workflows.

### 2. Runtime README becomes secondary

The generated bundle `src/README.md` remains more detailed, but its role changes
to “runtime reference after entry”, not “primary first-run guide”.

It may still contain:

- command families;
- dashboard startup reference;
- onboarding/reference details;
- validation/reference sections already needed inside the trimmed runtime.

But it should no longer compete with the bundle root as the main trial story.

### 3. Preserve one default VS Code entry

No second launcher is added. The existing install/open scripts remain the only
default top-level actions. The simplification happens in guidance and generated
content, not by multiplying scripts.

### 4. Keep demo and local-data paths visually equal

The landing page must not bury one path under the other.

Allowed:

- two same-level sections;
- two same-weight callouts/cards/blocks;
- a short neutral sentence explaining when to choose each path.

Not allowed:

- “demo first” with local data hidden in an appendix;
- “local data first” with demo hidden as a footnote;
- equal wording in theory but clear hierarchy in the generated layout.

## Planned file boundaries

### Primary owner

- `tools/build_usage_bundle.py`
  - owns the generated bundle trial story;
  - owns root/runtime README generation;
  - owns any bundle-facing wording reshaping required for the new landing page.

### Focused tests

- `tools/tests/test_build_usage_bundle.py`
  - asserts the generated bundle still has one default VS Code entry;
  - asserts the root README includes both `Try demo` and `Use local data`;
  - asserts the bundle story does not regress to a broad developer-facing entry.

### Optional minimal alignment only if needed

- `README.md`
- `src/README.md`

These repository files may receive **small** wording adjustments only when the
bundle-generated story would otherwise contradict them. Slice 4 must not turn
into a repo-wide documentation rewrite.

## Acceptance criteria

Slice 4 is acceptable when all of the following are true:

1. the generated bundle still has one install script and one open-in-VS-Code
   script as the only default entry path;
2. the bundle root `README.md` clearly presents `Try demo` and `Use local data`
   as equal first-run paths;
3. the landing page no longer reads like a broad internal development package;
4. `src/README.md` supports the runtime without acting as a second competing
   landing page;
5. focused bundle regression proves the new story;
6. `make validate` passes.

## Validation plan

Minimum validation:

- focused `tools/tests/test_build_usage_bundle.py`;
- any directly related dashboard/bundle regression only if bundle wording or
  asset expectations require it;
- `make validate`.

Run `make rehearse-release` only if the implementation changes release-artifact
semantics beyond the bounded README/script/guidance scope.

## Risks

- **Competing trial stories remain**: if the root README, runtime README, and
  scripts all introduce their own operator narratives, Slice 4 fails even if the
  wording individually looks reasonable.
- **False equality**: demo/local-data sections may both exist, but one may still
  dominate by placement or wording.
- **Scope creep**: it will be tempting to clean all repo docs at once. Slice 4
  must stay bounded to bundle/config/trial-entry clarity.
- **Developer leakage**: bundle docs must not read like contributor/developer
  onboarding.

## Rollback

Rollback is software-only: revert the bounded bundle-generation and guidance
changes. No data migration or persistent runtime repair is involved.

## Exact next step

Write the Slice 4 implementation plan against this spec, then implement only
the bounded bundle/config flattening surfaces.
