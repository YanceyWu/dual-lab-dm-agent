# IP-000 — Baseline and Private-State Safety

## Status

READY FOR LOCAL REPOSITORY ASSESSMENT

## Business goal

Create a safe, reproducible baseline for evolving and distributing the local DM
product without exposing one DM's operational data or losing current working
behavior.

## Architecture intent

Before refactoring application boundaries, clearly separate:

- versioned product core;
- sanitized onboarding and test assets;
- DM-specific configuration;
- local private state.

Establish behavior evidence and isolated validation so later strangler migration
can detect unintended change.

## Verified current-state indicators

The current baseline contains:

- a local SQLite operational database path;
- a raw/import data-feed path;
- sanitized sample files and a demo database workflow;
- CLI, dashboard, connector, migration, and use-case code in one product tree;
- existing UAT documentation and focused automated tests;
- test fixtures that can redirect the database to a temporary path;
- documentation that intends operational data and data feeds to be ignored.

The local repository architect must verify the effective ignore rules and current
tracked/untracked state before implementation. Do not inspect, print, copy, or
summarize real data rows during this assessment.

## Required outcomes

1. Product-core, sample, configuration, and private-state boundaries are explicit.
2. Private-state paths cannot be staged through normal whole-repository add
   workflows.
3. A clean product-core checkout can create and use a sanitized demo database.
4. Automated tests and smoke checks use isolated or demo data and cannot write to
   the default operational database.
5. Existing supported behavior is captured before application refactoring.
6. The current architecture and known-defect baseline is documented internally.

## Required classification

### Versioned product core

- runtime source;
- migrations and bootstrap logic;
- connector and importer code;
- shared configuration templates;
- Copilot instructions and use-case playbooks;
- sanitized samples;
- tests and validation scripts;
- product documentation.

### DM-specific configuration

- enabled source definitions;
- team/project mappings;
- policy and scoring overrides;
- non-secret display preferences.

Whether DM-specific configuration is versioned must follow company policy. It
must contain no credentials, confidential identifiers, or operational records.

### Local private state

- operational database and its journal/temporary files;
- raw exports and source documents;
- credentials, environment files, and token caches;
- backups and migration copies;
- generated reports containing real records;
- execution logs that may contain operational context;
- screenshots and debug artifacts.

### Sanitized onboarding assets

- synthetic sample source files;
- synthetic demo database or deterministic demo-data builder;
- generic configuration examples;
- synthetic expected-output fixtures.

## Scope

### A. Repository boundary

- Inspect ignore rules from repository root to the runtime directory.
- Enumerate private-state path categories by name only; do not read contents.
- Add or correct scoped ignore rules where required.
- Add a lightweight repository preflight check that fails when known private-state
  artifacts are tracked or staged.
- Ensure the preflight distinguishes approved sanitized samples from live-state
  paths.
- Document the product-core/private-state boundary in onboarding guidance.

### B. Isolated demo workflow

- Verify a clean setup can create the demo database from sanitized assets.
- Ensure the demo database path cannot overwrite the default operational database.
- Ensure destructive importers require an explicit target and provide a clear
  warning when they rebuild data.
- Record the minimal commands and expected success conditions.

### C. Test safety harness

- Verify every database-writing automated test uses a temporary path or an
  explicitly selected demo copy.
- Add a guard that fails a test if it attempts to write to the default operational
  database.
- Disable external network calls in the default automated test run.
- Use sanitized fixtures for connector and importer tests.

### D. Behavior characterization

Capture deterministic, sanitized behavior for:

- Team Workload;
- Capacity by month;
- HIREF/contract summary;
- Project List;
- Weekly Report;
- use-case catalog;
- connector validation with disabled or synthetic connectors;
- dashboard summary and health endpoints.

Behavior snapshots should assert semantic fields and outcomes, not terminal color
codes, timestamps, or unstable whitespace.

### E. Current architecture baseline

Classify current components as:

- IF: interface;
- UC: user-facing use case;
- DS: deterministic domain service;
- PS: platform service;
- CN: connector/importer;
- LG: legacy path to contain.

Record direct database access, direct connector invocation, write paths, and
current automated coverage. Do not prescribe module restructuring in this pack.

## Explicit non-goals

- no business-rule changes;
- no use-case contract implementation;
- no database schema redesign;
- no repository module split;
- no connector migration;
- no Copilot skill or custom-agent redesign;
- no dashboard redesign;
- no staffing correctness changes;
- no live connector execution;
- no real-data migration.

## Local discovery procedure

Before editing:

1. Report the repository roots and effective ignore files.
2. Report private-state path categories by generic purpose and tracked status.
3. Identify demo-data creation and default database selection paths.
4. Identify all tests that initialize or write a database.
5. Identify commands and endpoints selected for behavior characterization.
6. Identify current dependency-install and validation instructions.
7. Identify conflicts between documentation and effective repository behavior.
8. Report assumptions and UNKNOWN areas.

Do not output real data, credentials, internal URLs, names, project identifiers,
or raw source content.

## Mandatory constraints

- Preserve current application behavior.
- Do not delete private-state files; ignore and boundary changes do not authorize
  data deletion.
- Do not inspect database rows or raw export content.
- Do not stage or commit the local runtime source as part of the assessment.
- Do not call external enterprise systems.
- Do not add a new test framework.
- Reuse the existing temporary-database fixture and sample-data builder where
  practical.
- A private-state preflight must operate on paths and repository metadata, not
  file contents.
- Avoid broad recursive ignore patterns that would hide source, migrations,
  sanitized samples, or tests.

## Acceptance criteria

### Repository safety

1. Known operational database, export, credential, token-cache, backup, log, and
   generated-real-output paths are ignored.
2. Sanitized sample assets remain visible to version control.
3. The preflight fails on a deliberately staged synthetic file placed in each
   private-state category.
4. The preflight passes for approved sanitized sample paths.
5. No existing private file is deleted or uploaded.

### Demo reproducibility

6. A clean isolated working copy builds a demo database from sanitized assets.
7. Demo commands use the demo database and leave the default operational database
   unchanged.
8. Re-running demo setup is deterministic or explicitly idempotent.

### Test isolation

9. The default automated suite performs no live connector request.
10. Database-writing tests use temporary databases.
11. A guard test proves that the default operational database cannot be selected
    accidentally during automated tests.

### Behavior evidence

12. Focused smoke or characterization tests cover every workflow listed in scope.
13. Snapshots assert stable business semantics rather than presentation noise.
14. Known defects remain visible and are not converted into expected behavior
    without explicit approval.

### Documentation

15. The internal baseline records component classification, entry points, write
    paths, data boundaries, test coverage, and UNKNOWN areas.
16. Onboarding clearly distinguishes product core, configuration, sanitized
    samples, and local private state.

## Validation procedure

The independent reviewer must:

1. inspect repository status without staging files;
2. verify ignore behavior using synthetic filenames in a temporary test area;
3. build the sanitized demo database in an isolated directory;
4. run focused tests and the default automated suite;
5. verify no test or demo command changed the operational database metadata;
6. verify network-dependent tests were mocked, skipped, or explicitly isolated;
7. compare characterization results with the pre-pack behavior baseline;
8. confirm no business logic, schema, or Copilot behavior changed.

## Rollback

Rollback consists of reverting only the boundary rules, preflight, tests,
characterization fixtures, and documentation introduced by this pack.

Because the pack must not modify or delete operational data, database restoration
must not be required. If validation finds that any operational file was changed,
the pack fails and must not be promoted.

## Required implementation report

- assessed repository roots and ignore boundaries;
- private-state categories protected;
- sanitized paths intentionally retained;
- files/modules changed;
- tests and smoke checks added;
- validation commands and results;
- behavior differences, if any;
- private files encountered by category only;
- assumptions and UNKNOWN areas;
- deviations from this pack;
- rollback verification;
- recommendation on whether G0 is passed;
- readiness or blockers for IP-001.
