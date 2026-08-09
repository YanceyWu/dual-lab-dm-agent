# IP-038 corrective design — lean Copilot-first distribution bundle

Status: `OWNER ACCEPTED — IMPLEMENTATION COMPLETE PENDING INDEPENDENT REVIEW`

## 1. Goal

Correct the current Slice 4 distribution path so another Delivery Manager can:

1. extract one small package;
2. open that folder directly in VS Code;
3. select the bundled `Delivery Manager` Copilot agent;
4. ask Copilot to install and initialize the runtime;
5. choose synthetic demo or approved local-data onboarding;
6. use Copilot as the primary query/update interface and the six-page Legacy
   Dashboard as a supporting visualization.

This is a packaging and first-run correction. It adds no business capability,
Dashboard page, connector, data model, or write authority.

## 2. Owner decisions fixed by this design

- The default package is lean and dependency-on-demand.
- Do not embed Python, a virtual environment, `wheelhouse/`, Playwright wheels,
  or the full dependency set.
- Users open the extracted folder themselves in VS Code. There is no
  user-facing open-in-VS-Code launcher.
- Copilot owns first-run guidance and invokes deterministic setup only after an
  explicit user request.
- Dashboard publishes only Overview, Projects, Team, HIREF, Monthly Plan, and
  Project Health.
- Copilot may expose newer read-only capabilities even when their Dashboard
  pages remain hidden.
- Existing writes retain explicit intent and propose/preview/confirm/persist.
- Interaction memory may shape answers and routing but is not business
  authority and cannot trigger writes.
- Python 3.12 is the one supported pilot runtime. Other versions are reported as
  unsupported instead of being guessed compatible for this distribution.

## 3. Problems corrected

### 3.1 Wrong database when launched from the bundle root

The installer writes `src/.env`, but runtime settings currently load `.env`
relative to the caller's current working directory. A Dashboard launched from
the bundle root therefore misses `src/.env`, falls back to `data/pm.db`, and may
create an empty SQLite database.

Required correction:

- runtime settings load the repository-scoped env file from the actual runtime
  project root, independent of caller cwd;
- environment variables still override file values through the existing
  settings precedence;
- `get_database_path()` continues to resolve relative database paths against
  the runtime project root;
- focused tests launch/configure from both bundle root and `src/` and prove they
  resolve the same selected database;
- a missing selected database must not be silently described as a successful
  initialized workspace.

### 3.2 Noisy and misleading package contents

The reviewed ZIP contained an unintended empty `src 2/`, ignored `.DS_Store`
files, two competing README files, redundant `artifacts/`, a large offline
`wheelhouse/`, and open-in-VS-Code wrappers that do not match the real user
journey.

Required correction:

- enforce an exact bundle-root allowlist;
- filter `.DS_Store`, AppleDouble metadata, caches, generated databases other
  than the approved demo DB, and unexpected duplicate directories at copy time;
- reject any unknown root entry before archiving;
- emit one root README only;
- remove `src/README.md`, `artifacts/`, `wheelhouse/`, and all open-in-VS-Code
  wrappers;
- leave development, test, release, sample-source, and real/local state outside
  the package.

### 3.3 Generated Copilot agent contradicts the approved surface

The current generated bundle agent explicitly rejects newer read-only use
cases and omits interaction-memory pre-read. That conflicts with the owner's
Copilot-first boundary.

Required correction:

- generated bundle instructions keep the six-page Legacy Dashboard UI boundary;
- generated Copilot routing includes the repository-approved newer read-only
  use cases;
- write-capable routes remain only the already-approved controlled flows;
- before installation, the agent enters setup guidance rather than trying to
  call an unavailable local `pm` executable or interaction memory;
- after installation, the agent performs the same bounded memory pre-read and
  fail-open behavior as the maintained Delivery Manager agent;
- the generated agent never treats package installation as authorization for a
  business-data write, connector call, or real-data access.

### 3.4 JIRA and Confluence onboarding is too technical

The retained deterministic path is two registry CSV source types under
`pm onboarding`, each using profile save -> preview -> confirm. The capability
exists, but the generated agent does not guide it conversationally.

Required correction:

- the agent recognizes an explicit request to onboard JIRA board-registry or
  Confluence page-registry CSV files;
- it asks only for the missing local file path and a stable anonymous profile
  key;
- it invokes the existing `pm onboarding profile save` and preview commands;
- it explains blockers, warnings, counts, coverage, and source identity without
  reading or summarizing raw CSV content itself;
- it asks for explicit confirmation of the exact preview before invoking the
  existing confirm command;
- no importer, connector sync, source schema, or reconciliation behavior is
  redesigned in this correction.

## 4. Selected package shape

Emit one platform-neutral lean ZIP because platform-specific wheels are no
longer included. The target root allowlist is:

```text
Delivery Manager/
├── README.md
├── bundle-manifest.json
├── .gitignore
├── .github/
│   ├── agents/delivery-manager.agent.md
│   ├── copilot-instructions.md
│   └── prompts/dm-workload.prompt.md
├── demo/
│   └── sample_pm.db
├── scripts/
│   ├── setup.py
│   └── install-helper.py
└── src/
    ├── .env.example
    ├── pyproject.toml
    ├── runtime-requirements.lock
    ├── configs/
    ├── pm_agent/
    └── scripts/
```

Notes:

- `src/` remains the one runtime root in this corrective batch. Moving it under
  another hidden hierarchy would widen path and packaging risk without solving
  a business problem.
- There is no `src 2/`, `src/README.md`, `artifacts/`, `wheelhouse/`, `.venv/`,
  embedded Python, or user-facing install/open launcher.
- `scripts/setup.py` is an internal deterministic helper invoked by Copilot;
  the root README does not ask users to run it directly as the primary path.
- The manifest records source identity, product version, Python requirement,
  demo provenance, dependency mode `online_locked`, and hashes for every file.

## 5. Copilot-first setup contract

### 5.1 Preflight before any setup mutation

When the workspace-local `pm` executable is absent, the generated agent does
not attempt interaction-memory pre-read. It first performs read-only checks:

- platform and architecture;
- Python executable discovery;
- exact Python major/minor version 3.12;
- ability to create files under the extracted workspace;
- existing `.venv`, `src/.env`, demo DB, and setup-state markers;
- whether setup is fresh, complete, partial, or inconsistent.

The preflight must not inspect package-index credentials, connector
configuration, raw source files, SQLite contents, or real data.

Preflight states:

- `python_missing` — explain that Python 3.12 must be installed; do not mutate;
- `python_unsupported` — report detected version and required 3.12; do not
  mutate;
- `ready_to_install` — required executable and workspace checks passed;
- `already_installed` — verified runtime and setup marker agree;
- `partial_install` — incomplete state detected; provide the bounded repair
  action and do not call it success;
- `failed` — sanitized failure code plus exact next action.

### 5.2 Explicit user request

Copilot may invoke setup only after a clear request such as “安装并初始化”. It
must show:

- detected Python executable/version;
- that dependencies will be downloaded through pip's existing configured
  package index;
- the target workspace-local `.venv` and local config locations;
- that no connector or real-data access will occur;
- whether the next initialization target is demo or local data.

System Python installation is guidance-only. Copilot must not invoke a package
manager, use administrator privileges, or modify machine-wide Python state.

### 5.3 Dependency installation

The deterministic setup helper:

1. validates Python 3.12 again;
2. detects and rejects an inconsistent partial environment;
3. creates a workspace-local virtual environment;
4. installs the complete tested runtime dependency set from
   `src/runtime-requirements.lock` through the user's existing pip/index
   configuration;
5. installs the local project from `src/` without resolving a second drifting
   dependency graph;
6. runs `pm version` and an import/bootstrap smoke check;
7. records a local ignored setup-state marker only after every install check
   succeeds.

The lock contains exact versions for the supported Python 3.12 pilot runtime.
It contains no index URL, credentials, local path, or company value. Package
index/network failures return a stable sanitized category; raw credentialed
URLs must not be echoed.

Setup must be retry-safe:

- a complete verified environment returns `already_installed` without
  reinstalling;
- a failed first install is marked partial and never reported complete;
- repair/removal of a partial environment requires a separate explicit user
  request surfaced by Copilot;
- an existing verified environment is never silently overwritten.

### 5.4 Initialization modes

After runtime installation, Copilot asks the user to choose:

- `Try demo` — use the shipped read-only synthetic DB as source, copy it to the
  existing writable demo location, write the canonical demo selector, and run
  read-only smoke queries;
- `Use local data` — scaffold local configuration and empty database only, then
  guide approved structured onboarding. It does not access connectors or real
  files automatically.

The existing demo copy/preserve and non-demo selector-preservation rules remain
in force. The helper receives the absolute bundle root and never depends on
caller cwd.

## 6. Runtime dependency contract

- Default distribution supports Python 3.12 only.
- `runtime-requirements.lock` is repository-controlled, synthetic/portable, and
  fully pinned for the tested runtime set.
- Development-only tools are excluded.
- The current required runtime behavior remains installable; this correction
  does not silently remove connector capability to reduce download size.
- Future optional dependency groups, including browser automation, require a
  separate owner decision and are not part of this corrective batch.
- Validation must install from the lock against a clean temporary Python 3.12
  environment and prove the package starts without relying on the developer
  checkout's existing `.venv`.

## 7. Owning modules and allowed dependencies

### Primary packaging owner

`tools/build_usage_bundle.py`

Allowed responsibilities:

- platform-neutral lean tree staging;
- exact root allowlist and metadata filtering;
- generated root README, Copilot instructions, setup helper, and manifest;
- generation/copy of the synthetic demo DB from the committed loader path;
- archive validation.

Allowed dependencies:

- release/package metadata helpers already used by the builder;
- Dashboard surface manifest for the six visible Legacy pages;
- committed synthetic loader for builder-controlled demo generation;
- Python standard library.

It must not absorb business rules, onboarding importer logic, connector logic,
Dashboard provider logic, or persistence behavior.

### Runtime configuration owner

`pm_agent.config`

Allowed correction:

- resolve the repository-scoped env file from the runtime project root rather
  than caller cwd;
- preserve existing settings/env precedence and database-path normalization.

No schema, bootstrap, domain service, or connector change is allowed here.

### Generated setup helper

`scripts/setup.py` in the emitted bundle, with its reviewable generator in the
bundle builder.

Allowed responsibilities:

- preflight state calculation;
- local venv/dependency/project installation;
- install-state verification and sanitized results;
- invoking the existing generated install helper for demo/local initialization.

It must not implement business onboarding, inspect raw files, call connectors,
or bypass existing write controls.

### Generated Copilot surfaces

- `.github/agents/delivery-manager.agent.md`
- `.github/copilot-instructions.md`

They own setup routing, existing query/update routing, interaction-memory
pre-read after installation, and conversational use of existing onboarding
commands. They do not own deterministic install or import semantics.

## 8. Planned repository change boundary

Expected implementation files:

- `tools/build_usage_bundle.py`
- `tools/tests/test_build_usage_bundle.py`
- `src/pm_agent/config.py`
- `src/tests/test_database_path_resolution.py`
- `src/runtime-requirements.lock` or the reviewed equivalent selected during
  implementation without widening scope
- focused Delivery Manager agent contract tests if the generated prompt shares
  or reuses maintained routing text
- root release/bundle guidance only where required to remove the old offline
  wheelhouse/open-script claims
- this design, IP-038 pack continuity, implementation report, and `PROGRESS.md`

No database schema, migration, bootstrap DDL, Dashboard provider/page, domain
service, connector, real-data, or source-import contract file is in scope.

## 9. Acceptance scenarios

### Bundle tree

- one platform-neutral ZIP is produced without network access at build time;
- root contents exactly match the allowlist;
- unknown roots such as `src 2/` fail the build;
- `.DS_Store`, AppleDouble, caches, `.venv`, tests, sample source data,
  development docs, `artifacts`, and `wheelhouse` are absent;
- one root README is present and no secondary README competes with it;
- ZIP size and checksum are reported.

### Copilot/setup

- Python missing and unsupported-version paths are read-only and actionable;
- Python 3.12 preflight returns `ready_to_install`;
- setup begins only after explicit user intent;
- clean online install succeeds from the locked dependency set;
- package-index failure is sanitized, partial, retry-safe, and not success;
- completed setup is idempotent;
- partial setup is detected and requires explicit repair;
- before install, memory and business queries fail over to setup guidance;
- after install, memory fail-open and all approved read-only routes are
  available;
- controlled writes retain existing explicit preview/confirm behavior.

### Database/config

- launching from bundle root and `src/` resolves the same `src/.env` and DB;
- demo initialization produces a non-empty supported DB and successful workload
  and Project Health smoke queries;
- local-data initialization creates only the approved empty local state and does
  not call a connector;
- reinstall preserves an existing non-demo `DATABASE_PATH`;
- failed initialization does not leave a false complete marker.

### Onboarding guidance

- JIRA and Confluence registry paths use existing source types and
  profile-save/preview/confirm semantics;
- raw CSV is not inspected by the agent;
- preview blockers/warnings/counts are shown before confirmation;
- no sync or live connector call occurs implicitly.

## 10. Validation and independent review

Implementation cannot be presented as complete until all of the following pass:

- focused bundle-builder/setup/config/agent/onboarding-routing tests;
- a real lean bundle build with no build-time dependency download;
- isolated Python 3.12 online installation using only the emitted package and
  the configured public/test package index;
- demo initialization and root-cwd Dashboard/query smoke tests;
- `make validate`;
- `make rehearse-release` because packaging and runtime configuration change;
- independent Sol read-only review of the full design-to-implementation diff;
- correction of every accepted P0-P2 finding and repeated relevant validation;
- final package tree, manifest, size, checksum, commit, and push state recorded
  in `PROGRESS.md`.

No real-environment UAT, connector access, real data, push, tag, promotion, or
release is authorized by passing these checks.

## 11. Rollback

- Revert the bounded builder, config, lock, tests, and guidance changes.
- Existing databases require no migration or rollback because no schema or
  persisted business contract changes.
- Generated test bundles are disposable local artifacts and are not committed.
- A failed user setup can remove only its local ignored partial environment and
  setup marker after explicit repair approval; shipped demo/reference files are
  unchanged.

## 12. Deferred scope

- embedded/self-contained Python runtime;
- offline wheelhouse distribution;
- optional browser/Playwright dependency split;
- signing, notarization, enterprise package hosting, or auto-update;
- new onboarding importer/schema behavior;
- new Dashboard pages or redesign;
- connector execution or real-data validation;
- memory promotion/acceptance decision beyond preserving its current bounded
  non-authoritative behavior.

## 13. Owner review gate

This design authorizes no code implementation by itself. The owner must accept,
revise, or reject it. Only an explicit acceptance/implementation authorization
may start one bounded implementation batch using Luna-high or, when Luna is
unavailable, the already-authorized Terra-medium fallback. Sol remains limited
to design and independent read-only review.
