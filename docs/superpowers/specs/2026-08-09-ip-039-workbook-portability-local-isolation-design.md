# IP-039 Workbook portability and local-data isolation design

Status: owner-authorized design for implementation and review.

## Problem statement

Release-candidate testing exposed four connected usability failures:

1. the lean bundle carries an empty `src/configs/` directory and an optional
   workload Prompt File whose relationship to the primary Copilot agent is not
   clear;
2. the supported Team/Project + Capacity workbook template, synthetic example,
   and operator guidance exist in the repository but are absent from the usage
   bundle;
3. the runtime cannot export its current supported planning state back into the
   same workbook contract; and
4. selecting local data after trying the demo can leave `DATABASE_PATH` pointed
   at the writable demo database, so a subsequent import contaminates demo state
   instead of creating the local `pm.db`.

This slice corrects those boundaries without adding a connector, changing the
workbook import schema, expanding Dashboard pages, or accessing real data.

## Surface decisions

### Copilot files and empty configuration directory

- Keep `.github/agents/delivery-manager.agent.md`; it is the primary user-facing
  Copilot custom agent.
- Keep `.github/copilot-instructions.md`; it supplies workspace-wide operating
  and safety instructions.
- Remove `.github/prompts/dm-workload.prompt.md` from the lean usage bundle. It
  is an optional manually invoked Prompt File, is not called automatically by
  the custom agent, and duplicates a route already owned by the agent.
- Remove the empty `src/configs/` directory from the lean usage bundle. Runtime
  configuration remains `src/.env` plus the typed runtime settings module.

Repository copies outside the generated usage bundle are not removed by this
slice.

### Workbook kit in the bundle

Add one top-level `workbook/` directory to the bundle allowlist containing:

- `team_project_capacity_workbook_template.xlsx`: header-only preparation
  template;
- `team_project_capacity_workbook_sample.xlsx`: synthetic valid example; and
- `WORKBOOK_GUIDE.md`: concise, bundle-relative instructions for preparing,
  validating, previewing, confirming, and exporting a workbook.

The guide must name every sheet, required/optional field, stable-identifier
rule, percentage/fraction convention, supported status value, date/month
format, and the Copilot-first command sequence. It must direct users to the
template/sample by relative path and must not contain real identifiers.

### User-maintained source export

The export boundary is user-maintained source facts, not database backup and
not round-trip of system-derived publications. A user may edit the exported
source through Copilot or regenerate a supported source file and import it
again. After import, the runtime recomputes staffing, coverage, health,
freshness, snapshots, publication evidence, and audit state.

The release-visible source export set is:

- Team/Project + Capacity workbook: members, project master facts, plan
  metadata, monthly allocations, leave/BAU/non-project capacity facts, current
  and next HIREF facts, HIREF requests, and open-demand allocations;
- Project Profile workbook: user-maintained project phase, priority/focus,
  objective, milestone, stakeholder, and risk fields already accepted by the
  supported project-profile source contract; and
- JIRA Board Registry and Confluence Page Registry CSVs: user-maintained local
  connector mappings/configuration already accepted by their supported source
  contracts.

The owning source capability exposes each read-only export through onboarding
CLI/Copilot using its existing import format. Export never mutates SQLite.

Contract:

- input: explicit output path and optional explicit plan-version ID;
- selection: use the requested plan, or the sole active plan; fail closed when
  selection is ambiguous;
- facts: read only the current authoritative user-maintained source facts named
  above; a derived projection may be used as a storage compatibility detail but
  must not become an export precondition;
- output: the existing `team-project-capacity-workbook-v1` sheet/header contract;
- safety: never overwrite an existing path unless the user explicitly supplies
  an overwrite flag; use a same-directory temporary file and atomic replace;
- result: structured JSON containing status, output path, SHA-256, selected plan
  where applicable, row counts, warnings, and source identity metadata;
- privacy: Copilot may execute the export and report metadata, but must not open
  or quote raw workbook contents;
- completeness: missing, ambiguous, or internally incomplete source facts fail
  closed instead of inventing values or silently omitting data;
- re-import: an exported workbook must parse and preview successfully through
  its existing workbook preset, and exported registry CSVs must preview through
  their existing source handlers, without changing any import contract.

The export must not serialize or restore current-state staffing,
contract-coverage publications, Project Health snapshots, project snapshots,
freshness rows, sync runs, publication histories, derivations, execution traces,
or generic audit history. These are system-derived and must be regenerated
after source import. The latest completed `pm onboarding` source receipt is the
authoritative source envelope for facts not represented in canonical planning
tables, including the original Setup horizon and whether the accepted workbook
contained Capacity rows. Requiring that one current source receipt is not a
derived-publication coherence gate; older receipts must never be used as
fallback when the newest receipt is corrupt or incomplete. Internal direct
service calls that bypass the supported onboarding entry do not establish an
exportable source receipt. Derived publication generation/as-of agreement is
never a precondition for exporting otherwise valid source facts.

### Demo to local transition

The generated setup helper owns the transition contract:

1. an explicit local-mode request must compare the requested mode with the
   setup marker and resolved selector; a healthy demo install must not short
   circuit the mode change;
2. local mode atomically rewrites the single `DATABASE_PATH` entry to
   `data/pm.db`, preserving unrelated `.env` keys;
3. it then initializes `src/data/pm.db`, validates SQLite integrity and required
   bootstrap tables, and validates that runtime configuration resolves that
   exact file;
4. it updates the setup marker to `local` only after local config and smoke
   checks pass;
5. it preserves the writable demo database byte-for-byte and never imports or
   copies demo rows into the local database;
6. failure leaves the prior selector and marker coherent or reports a repairable
   partial state; it must not report local readiness while still selecting demo;
7. returning from local to demo remains unsupported unless separately designed.

The generated Copilot agent must route an explicit “switch to local data” request
through this deterministic transition before any onboarding preview or confirm.

## Module and dependency boundaries

- Each export belongs to the capability that owns the matching source contract.
  Workbook onboarding may compose the Team/Project + Capacity source facts and
  HIREF supplement; project-profile and connector-registry owners expose their
  own existing-format exports. No exporter may depend sideways on another
  capability's derived publication or private audit tables.
- Onboarding CLI remains a thin presentation layer.
- Bundle composition and demo/local setup remain owned by the usage-bundle
  builder and generated helpers.
- No schema, migration, connector, Dashboard provider, import semantics, or
  controlled business write is changed.

## Validation and acceptance

Focused evidence must cover:

1. bundle contains exactly the three workbook-kit files and excludes the empty
   configs directory and optional workload Prompt File;
2. template and sample both parse under the packaged default preset;
3. Team/Project + Capacity export success, ambiguous/no plan, incomplete source
   facts, existing output, explicit overwrite, atomic failure cleanup, JSON
   metadata, and export-to-preview round-trip, without requiring derived
   staffing/contract/health/publication state;
4. Project Profile, JIRA Board Registry, and Confluence Page Registry exports
   preview successfully through their existing supported source handlers and
   contain no derived snapshot, sync, or audit rows;
5. demo install followed by explicit local switch creates a distinct non-empty
   `src/data/pm.db`, rewrites the selector, changes the marker only after smoke,
   and preserves the demo DB hash;
6. a workbook import after the switch changes only the local database;
7. bundle-root and `src/` cwd resolve the same local database; and
8. Copilot routes, README, source templates/guides, manifest, and exact bundle
   tree agree.

Then run full validation, release rehearsal, a real isolated bundle smoke, and
an independent Sol read-only review. Passing tests does not authorize commit,
push, release, connector access, or real-data UAT.
