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
- the generated bundle `.github/agents/delivery-manager.agent.md` and
  `.github/copilot-instructions.md` only insofar as Slice 4 must keep their
  operator entry wording aligned with the new single-entry bundle story;
- the bounded demo-bundle adjustment needed to ship one **read-only** synthetic
  demo database file and copy it to a local writable location during install;
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

Slice 4 may rely on already-verified baseline `pm init` behavior that preserves
an existing `src/.env` by default; it must not redesign or broaden `pm init`
semantics beyond that existing contract.

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

Here, “one entry” means **one operator story** across the bundle, not one
literal script file. Each supported platform may keep its own install/open
wrapper while still presenting one logical install → open-in-VS-Code entry.

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

Chosen mechanism:

- the authoritative repository source for the shipped demo DB is a
  bundle-build-generated artifact assembled from the committed synthetic loader
  path in a temporary build workspace; Slice 4 must not depend on the
  pre-existing local `src/sample-data/demo/sample_pm.db` working-tree artifact;
- the bundle ships one read-only synthetic demo database file at
  `demo/sample_pm.db`;
- the generated install script copies that database to a local writable demo
  location at `src/.dm-demo/sample_pm.db` inside the installed bundle workspace;
- the demo path points the operator at that copied writable database, not at the
  immutable shipped bundle artifact;
- the runtime selector value written into `src/.env` is exactly
  `DATABASE_PATH=.dm-demo/sample_pm.db`, which runtime resolution converts to
  `src/.dm-demo/sample_pm.db` through `pm_agent.config.get_database_path()`;
- Slice 4 does **not** reintroduce full sample-data sources or the demo rebuild
  loader into the usage bundle.

Authoritative handoff after the landing section:

1. point the operator to the exact synthetic demo path that exists inside the
   installed local workspace;
2. show the minimum command or environment setup needed to use that copied demo
   safely;
3. hand off to the `Delivery Manager` agent with example business prompts.

Demo lifecycle/reset rule:

- the shipped bundle copy remains read-only reference content;
- the installed writable demo copy is allowed to change locally during trial
  usage;
- re-running install must **not** silently overwrite an existing writable demo
  copy;
- the documented demo reset step is the only allowed overwrite path for the
  writable demo copy: delete `src/.dm-demo/sample_pm.db`, then rerun the existing
  install script so it recreates the writable copy from `demo/sample_pm.db`;
- switching from demo to local data must not require deleting bundled sources or
  guessing which database is active;
- once the operator switches `DATABASE_PATH` away from demo and into local-data
  mode, Slice 4 treats that as a **one-way switch**; returning to demo mode is
  not a supported operator path in this slice.
- this one-way rule is enforced at the supported-flow contract level: the
  installer/helper must preserve any non-demo `DATABASE_PATH` and must never
  auto-switch the workspace back to demo mode; manual out-of-contract edits that
  restore demo mode are unsupported and outside Slice 4 acceptance/testing.

Demo reset scope rule:

- the documented demo reset flow is valid only while `src/.env` is still in
  demo mode (`DATABASE_PATH=.dm-demo/sample_pm.db`);
- after the operator switches to local data, reinstall may preserve the stale
  demo copy for reference, but Slice 4 does not support restoring the workspace
  to active demo mode.

Install-time copy error handling:

- if `demo/sample_pm.db` is missing or unreadable, install fails with an
  explicit message and does not pretend the demo path is available;
- if `src/.dm-demo/sample_pm.db` cannot be created or written, install fails
  with an explicit message;
- if `src/.dm-demo/sample_pm.db` already exists, install leaves it unchanged and
  reports that the writable demo copy was preserved.
- install failure must be fail-closed with no partial active-state switch:
  - existing `src/.env` content must remain unchanged on failure;
  - any preserved pre-existing writable demo DB must remain unchanged on failure;
  - any newly created temporary or incomplete demo-copy artifact must be cleaned
    up before exit;
  - install must not leave the workspace pointing at demo DB unless the copied
    writable demo DB is present and valid.

Database selector/control point:

- on first install, if `src/.env` is absent, the install wrapper runs
  `pm init --skip-db` first so the standard starter `.env` is scaffolded
  without creating the default `src/data/pm.db` before any Slice 4
  `DATABASE_PATH` rewrite occurs;
- if that first-install `pm init --skip-db` step fails, install stops
  immediately, the helper is not invoked, and the workspace remains only in
  whatever starter-scaffold state `pm init --skip-db` left behind;
- after install, the default local runtime config points to the copied writable
  demo DB at `src/.dm-demo/sample_pm.db`;
- the concrete selector surface is the local generated `.env` file entry
  `DATABASE_PATH=.dm-demo/sample_pm.db`, scaffolded by `pm init` and finalized
  by the generated install script in `src/.env`;
- the `Use local data` path explicitly tells the operator to replace that local
  database-path setting with the approved local target before onboarding local
  data;
- the documented and supported local-data target in Slice 4 is
  `DATABASE_PATH=data/pm.db` under `src/`;
- on reinstall, if `src/.env` already exists and `DATABASE_PATH` no longer
  matches the canonical demo-mode value `.dm-demo/sample_pm.db`, install must
  preserve the existing local-data choice and must not silently reset it back to
  demo mode;
- if `.env` is unreadable or contains duplicate `DATABASE_PATH` keys, install
  fails with an explicit message rather than guessing how to mutate it;
- if `src/.env` exists but contains no `DATABASE_PATH` entry, install fails with
  an explicit message instead of guessing how to repair it, because `pm init`
  should already have scaffolded that key;
- demo-mode detection for reinstall/preserve decisions uses this canonical rule:
  take the one allowed `DATABASE_PATH` value from `src/.env`, trim whitespace,
  strip one matching pair of single or double quotes when present, resolve it
  relative to `src/`, and compare the resolved absolute path to the canonical
  demo DB path `src/.dm-demo/sample_pm.db`;
- the landing page and runtime reference must both name this config/database-path
  switch explicitly so the operator does not have to guess which database is
  active.
- on a brand-new workspace, if `pm init --skip-db` succeeds but the helper later
  fails, `src/.env` remains at its scaffolded pre-demo value, no active
  `DATABASE_PATH` switch to demo mode is considered complete, and any incomplete
  new demo-copy artifact is cleaned up.

Expected effect:

- a first-time DM can reach a working demo and ask one meaningful business
  question within a few minutes;
- the path does not require reading deep runtime docs before asking questions.

### Use local data path

The landing page gives the minimum bounded steps needed to initialize local
state and move into approved local data onboarding without pretending that demo
data is the only supported flow.

Authoritative handoff after the landing section:

1. preserve the existing install-script behavior as the only default local
   initialization step;
2. edit the local generated `.env`/runtime config so `DATABASE_PATH` no longer
   points to `.dm-demo/sample_pm.db` and instead points to the standard local
   data target `DATABASE_PATH=data/pm.db`;
3. run `pm init` once against that new `DATABASE_PATH` so the target database
   and parent directory exist if they were not created yet;
   - `pm init` in this branch must preserve the operator-edited `DATABASE_PATH`
     in `src/.env`; it is not allowed to reset the workspace back to demo mode;
   - this is a path-specific local-data step, not a competing default install
     path or second top-level entry story;
4. `pm config validate`
5. `pm connector validate --portable`
6. hand off to the retained runtime reference in the `Structured data
   onboarding` section of generated `src/README.md` for the exact approved
   `pm onboarding profile save → preview → confirm` flow.

Local-data failure handoff:

- if `pm init`, `pm config validate`, or `pm connector validate --portable`
  fails after the operator switches away from demo mode, the landing/runtime
  guidance must explicitly tell the operator to stop and resolve that failure
  before any onboarding command is run;
- Slice 4 must not imply a fallback back to demo mode when the local-data path
  fails.

Expected effect:

- a first-time DM can see the correct safe path for local configuration and
  onboarding immediately;
- the path points to deeper runtime docs only after the landing page has already
  explained the operator sequence.

## Design decisions

### 1. One landing page owns the trial story

The generated bundle root `README.md` becomes the single authoritative landing
page for the external trial package.

It must contain these required sections in this order:

1. `Delivery Manager Trial Bundle`
2. `Before first use`
3. `Install locally`
4. `Open in VS Code`
5. `Choose your first run path`
6. `Try demo`
7. `Use local data`
8. `Boundary`

Within those sections it should contain:

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

For Slice 4 completion, the root README must also satisfy these concrete checks:

- both `Try demo` and `Use local data` appear as same-level headings;
- both paths appear before any long-form runtime reference section;
- the only top-level launch sequence is install then open in VS Code;
- `pm dashboard serve` may appear inside a path, but not as a competing global
  “main way to start”.

### 2. Runtime README becomes secondary

The generated bundle `src/README.md` remains more detailed, but its role changes
to “runtime reference after entry”, not “primary first-run guide”.

It may still contain:

- command families;
- dashboard startup reference;
- onboarding/reference details;
- validation/reference sections already needed inside the trimmed runtime.

Required integration point:

- generated `src/README.md` must contain the heading `Structured data
  onboarding`, because the Slice 4 landing page hands off to that exact section;
- that section must include the approved onboarding sequence
  `pm onboarding profile save → preview → confirm` in usable operator guidance,
  not just a heading stub.

But it should no longer compete with the bundle root as the main trial story.

### 3. Preserve one default VS Code entry

No second launcher is added. The existing install/open scripts remain the only
default top-level actions. The simplification happens in guidance and generated
content, not by multiplying scripts.

### 4. Keep demo and local-data paths visually equal

The landing page must not bury one path under the other.

Allowed:

- two same-level sections under one shared `Choose your first run path` parent
  section;
- two same-weight callouts/cards/blocks;
- the same internal structure for both paths:
  - one short purpose sentence;
  - one primary command block or step block;
  - one short “what to do next” handoff;
- a short neutral sentence explaining when to choose each path.

Not allowed:

- “demo first” with local data hidden in an appendix;
- “local data first” with demo hidden as a footnote;
- equal wording in theory but clear hierarchy in the generated layout.

For acceptance and regression, “visually equal” means at minimum:

- same markdown heading level;
- adjacent placement under the same parent section;
- the same subsection structure count;
- neither path placed in an appendix or secondary reference section.

## Planned file boundaries

### Primary owner

- `tools/build_usage_bundle.py`
  - owns the generated bundle trial story;
  - owns root/runtime README generation;
  - owns any bundle-facing wording reshaping required for the new landing page;
  - owns any needed alignment of the generated `.github` bundle instruction files
    with the single-entry trial story;
  - owns generation of the bundle install scripts with the bounded demo-copy
    step and its documented failure policy;
  - owns the build-time helper that generates the shipped `demo/sample_pm.db` in
    a temporary build workspace from the committed synthetic loader path;
  - owns emission of bundle manifest provenance metadata with the exact field
    `demo_db_source` and exact value `generated_from_synthetic_loader`.

Repository-side source-of-truth seam:

- the emitted install helper content is owned in repository source by a
  dedicated generator function inside `tools/build_usage_bundle.py`
  (for example `build_install_helper(...)`);
- that generator function, not the emitted bundle file, is the reviewable source
  of truth for Slice 4 install-policy logic.

Build-time failure policy:

- if build-time demo DB generation fails, the bundle build fails immediately;
- if manifest provenance recording fails or the required field/value is missing,
  the bundle build fails immediately;
- the build-time demo DB helper operates only inside a builder-controlled
  temporary workspace under the bundle output artifact cache, not from an
  arbitrary pre-existing local sample DB path;
- Slice 4 must not emit a partial “successful” bundle that lacks either the demo
  DB or the required provenance metadata.

Build-time synthetic-loader contract:

- the builder invokes the committed synthetic loader path as a local Python
  entrypoint against a requested output DB path inside the builder-controlled
  temporary workspace;
- expected success output is one valid SQLite demo DB written to that requested
  path;
- any non-zero process exit, missing output DB, or invalid output DB causes the
  bundle build to fail immediately.

### Shared install helper

- `scripts/install-helper.py` (generated into the bundle)

This generated Python helper is the single owner of:

- `src/.env` parsing;
- canonical demo-mode detection;
- `DATABASE_PATH` mutation/preservation rules;
- copy/preserve/fail decisions for `src/.dm-demo/sample_pm.db`.

Helper interface contract:

- the helper is invoked by both platform install wrappers after dependency
  install and after `pm init --skip-db` has produced `src/.env` when needed;
- the helper receives the absolute bundle root path from the wrapper and must
  not depend on the caller's current working directory;
- exit code `0` means the demo-copy and `.env` update/preserve flow completed
  successfully;
- any non-zero exit code means installation must stop immediately;
- on failure, the helper emits a human-readable deterministic error message that
  explains whether the failure came from demo DB copy, `src/.env` parsing,
  duplicate/missing `DATABASE_PATH`, or config write failure.

### Install-surface ownership

- `scripts/install.command`
- `scripts/install.cmd`

These generated install surfaces own:

- invoking `scripts/install-helper.py` and surfacing its deterministic
  success/failure result;
- failing fast if the helper reports demo-copy, `.env`, or `DATABASE_PATH`
  mutation errors;
- remaining thin cross-platform wrappers instead of duplicating stateful policy.

### Open-in-VS-Code wrapper ownership

- `scripts/open-in-vscode.command`
- `scripts/open-in-vscode.cmd`

These generated wrappers remain owned by `tools/build_usage_bundle.py` and are
**frozen by default** in Slice 4. They may receive only the minimum wording or
invocation adjustment needed to keep the single logical install → open-in-VS-Code
entry story coherent; they must not gain a second launch mode or a separate demo
vs local-data branch.

### Frozen or minimally aligned generated bundle instruction surfaces

- `.github/agents/delivery-manager.agent.md`
- `.github/copilot-instructions.md`

Slice 4 must make an explicit choice for these generated surfaces:

- if their current wording already fits the new entry story, leave them
  unchanged and record that they are intentionally frozen in this slice;
- if they currently contradict the new landing page, make the smallest wording
  change needed to remove the contradiction.

Slice 4 must not redesign their behavior, routing, or capability boundary.
The implementation report and `PROGRESS.md` entry for Slice 4 must record which
of those two outcomes was taken so review can verify it quickly.

Required integration check:

- the generated bundle must still ship both
  `.github/agents/delivery-manager.agent.md` and
  `.github/copilot-instructions.md`;
- their emitted wording must remain coherent with the single logical install →
  open-in-VS-Code → Delivery Manager agent operator entry.

### Focused tests

- `tools/tests/test_build_usage_bundle.py`
  - asserts the generated bundle still has one default VS Code entry;
  - asserts the root README includes both `Try demo` and `Use local data`;
  - asserts those two paths are emitted as same-level sections in the root
    landing page;
  - asserts those two paths are adjacent and share the same internal subsection
    structure markers;
  - asserts the root README keeps install → open in VS Code as the only default
    launch sequence;
  - asserts `bundle-manifest.json` includes only the approved demo-bundle
    asset(s) added for this slice and does not reopen full sample-data content;
  - asserts the bundle story does not regress to a broad developer-facing entry.
  - owns direct tests for the generated install-helper behavior contract:
    `.env` parsing, demo-mode detection, demo-copy/preserve behavior, and
    partial-failure rollback semantics.
  - asserts the generated `src/README.md` `Structured data onboarding` section
    includes the approved onboarding handoff sequence;
  - asserts the bundled `.github` agent/instruction entry surfaces are present
    and coherent with the single entry path.

### Optional minimal source-repo alignment only if needed

- repository root `README.md`
- repository source `src/README.md`

These source-repo files may receive **small** wording adjustments only when the
bundle-generated story would otherwise contradict them. Slice 4 must not turn
into a repo-wide documentation rewrite.

## Acceptance criteria

Slice 4 is acceptable when all of the following are true:

1. the generated bundle still has one install script and one open-in-VS-Code
   script per supported platform, while still presenting one logical default
   install → open-in-VS-Code entry path;
2. the bundle root `README.md` clearly presents `Try demo` and `Use local data`
   as equal first-run paths;
3. the `Try demo` path is real through one read-only shipped demo DB plus one
   installed writable copied demo DB;
4. the `Use local data` path does not require a contradictory second default
   initialization step after install;
5. generated bundle `.github` instruction files are either intentionally frozen
   unchanged or minimally aligned without behavior/routing redesign;
6. install deterministically fails if the shipped demo DB cannot be copied into
   the writable demo location, and normal reinstall does not silently overwrite
   an existing writable demo copy;
7. the shipped demo DB provenance is proven to come from the temporary
   bundle-build generation path rather than copying the local
   `src/sample-data/demo/sample_pm.db` working-tree artifact;
8. bundle manifest metadata contains `demo_db_source` with the exact value
   `generated_from_synthetic_loader`;
9. the landing page no longer reads like a broad internal development package;
10. `src/README.md` supports the runtime without acting as a second competing
   landing page, contains the heading `Structured data onboarding`, and includes
   the approved `pm onboarding profile save → preview → confirm` handoff flow;
11. install fails explicitly when `src/.env` is unreadable, contains duplicate
    `DATABASE_PATH` keys, or contains no `DATABASE_PATH` key after scaffold;
12. bundled `.github/agents/delivery-manager.agent.md` and
    `.github/copilot-instructions.md` are shipped and remain coherent with the
    install → open-in-VS-Code → Delivery Manager agent entry path;
13. focused bundle regression proves the new story;
14. `make validate` passes;
15. `make rehearse-release` passes.

## Validation plan

Minimum validation:

- focused `tools/tests/test_build_usage_bundle.py`;
- one bundle-build smoke check proving the approved demo asset is staged into
  the bundle and the generated landing/runtime docs point to the copied writable
  demo path coherently;
- one provenance check proving the builder generated `demo/sample_pm.db` from
  the temporary synthetic loader path rather than copying the local
  `src/sample-data/demo/sample_pm.db` working-tree artifact;
  - the bundle manifest must record that provenance in the observable field
    `demo_db_source=generated_from_synthetic_loader`;
- exact observable bundle inventory checks via `bundle-manifest.json`:
  - `files` must include `demo/sample_pm.db`;
  - `files` must include `scripts/install-helper.py`;
  - `files` must not include `src/sample-data/` or excluded synthetic loader
    scripts;
- explicit stateful checks for:
  - first install starting without `src/.env`;
  - first install;
  - reinstall with preserved writable demo DB;
  - reinstall after `.env` has been switched from demo DB to local-data DB;
  - the documented demo reset flow while still in demo mode;
  - existing `src/.env` with no `DATABASE_PATH` entry;
  - unreadable `.env` / duplicate `DATABASE_PATH` failure handling;
  - partial-failure rollback behavior where copy and `.env` mutation do not both
    complete successfully;
- installer parity checks for both generated `scripts/install.command` and
  `scripts/install.cmd`, covering demo-copy, `DATABASE_PATH` defaulting, and
  local-data preserve behavior;
  - Slice 4 validation does not require executing Windows scripts on Windows;
    instead it requires:
    1. pure-Python tests for the required shared helper
       `scripts/install-helper.py` that owns the `.env` / demo-copy logic;
    2. static assertions over the emitted macOS and Windows installer content to
       prove both invoke that helper and carry the same behavior contract;
- any directly related dashboard/bundle regression only if bundle wording or
  asset expectations require it;
- `make validate`;
- `make rehearse-release`, because Slice 4 changes shipped bundle/install
  semantics.

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
