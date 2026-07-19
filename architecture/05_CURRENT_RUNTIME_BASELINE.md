# Current Runtime Baseline

Status: verified against the local `src/` checkout on 2026-07-19
Scope: structural and behavioral baseline only; no real database or export content was inspected

## 1. Product shape

The current product is a local Delivery Manager toolkit backed by SQLite and
operated through Copilot Agent instructions, a Typer CLI, and a Flask dashboard.
It is not an embedded LLM runtime. Copilot is the reasoning interface; Python
owns data access, deterministic calculations, validation, and persistence.

The source already contains a useful modular-monolith foundation. The evolution
should preserve this base and introduce clearer contracts by strangler migration.

## 2. Verified execution model

```text
DM
  -> Copilot Agent instructions or direct CLI/dashboard interaction
  -> CLI command or dashboard route
  -> use-case service, repository, sync workflow, or direct query
  -> deterministic rules and local SQLite/connectors
  -> structured service result or rendered UI response
```

IP-001 has introduced a single application execution contract for one
low-risk, read-only reference slice: `team-workload-overview`. Both the CLI
workload overview and the Dashboard JSON endpoint invoke the same registered
implementation. Other CLI and dashboard paths still call services,
repositories, SQL, or integration workflows directly and remain unmigrated.

## 3. Current component classification

### User use cases

- Resource planning and staffing recommendation
- Team workload and capacity views
- Weekly delivery reporting
- Contractor/HIREF governance
- Action-item management
- Project, release, health, and source-freshness views

### Domain services and deterministic rules

- Candidate scoring and option construction
- Allocation-request and member validation
- Contractor/HIREF rules
- Identity and normalization helpers
- Weekly aggregation and workload calculations

### Platform services

- SQLite bootstrap and migrations
- Repository/data-access functions
- Decision logging
- Backup and repository bootstrap
- Source registry, sync-run history, and use-case catalog

### Connectors and sync workflows

- JIRA
- Confluence
- Service-management/browser workflow
- File/CSV/Excel import paths

This classification describes current responsibilities. The package layout does
not yet enforce all of these boundaries consistently.

## 4. Contracts that already exist

The current use-case package provides:

- `ServiceRequest`
- `ServiceResponse`
- `BaseService`
- a central `SERVICES` registry
- service-specific request models
- deterministic scoring and validation results
- `UseCaseRequest` and `UseCaseResult` version `1.0`
- a `UseCaseExecutor` with explicit registration

The executor adds a generated execution ID and records use-case ID, actor,
requested output, contract version, read-only status, timing, and outcome. The
reference result also reports bounded local SQLite evidence, source freshness,
assumptions, warnings, alternatives, and no proposed writes. A local trace
summary is retrievable by execution ID without retaining business result rows or
connector configuration. Existing `ServiceRequest` and `ServiceResponse` remain
in place behind the migrated slice so the migration does not change its workload
semantics.

These are the correct seams to evolve. They should not be replaced wholesale.
The current `ServiceResponse` is still too small to be a stable Copilot tool
contract: it does not consistently expose evidence, freshness, warnings,
assumptions, alternatives, proposed writes, or execution metadata.

## 5. Canonical model status

The local database already represents part of the required management language:

- Person: explicit
- Project: explicit, with profile extensions
- Assignment: explicit, with both current and monthly allocation shapes
- Contract/HIREF: explicit
- Action: explicit
- Decision: explicit
- Data provenance and freshness: partial through source and sync metadata
- Risk: partial and source-shaped
- Dependency: partial or implicit
- Capacity: derived from people and allocation data
- Snapshot: multiple operational representations

The next architecture phase should clarify ownership and contracts before any
large schema migration. A canonical model is a semantic boundary, not a request
to create one universal table.

## 6. Staffing reference-path findings

The staffing use case is the strongest candidate for a later vertical reference
migration because it already combines request validation, repository reads,
deterministic scoring, alternatives, confirmation, assignment writes, and a
decision log.

Verified current constraints:

- The request expresses project, role, skills, task type, and headcount.
- It does not yet express an allocation period, effort, or required capacity.
- Candidate evaluation reads all members, their current projects, and prior
  decision outcomes.
- Confirmation persists a fixed allocation value rather than a value derived
  from the request or selected option.
- Assignment writes and decision-log writes are separate operations rather than
  one explicit atomic transaction.
- The service returns alternatives and scores, but evidence/freshness semantics
  are not standardized.

These are baseline facts, not authorization to change staffing behavior in
IP-000.

## 7. Portability and privacy baseline

The checkout contains private runtime locations for a live local database and
source exports. Their contents were not read. They are ignored by Git and are
covered by an automated repository-boundary preflight.

Portable assets may include source-independent product code, contracts, domain
models, tests, and reviewed synthetic sample data. Before the whole `src/` tree
can be published, a separate sanitization review is still required because the
checkout contains at least:

- a company-specific endpoint default;
- company/project-specific aliases in deterministic rules;
- real-looking people or project identifiers in fixtures or documents;
- company configuration profiles whose portability has not been approved.

No such values should be transferred merely because the paths are source code or
documentation. Until reviewed, `src/` remains quarantined from public staging.

## 8. Current validation evidence

- The repository has six pytest modules and an isolated temporary-database
  fixture.
- Prior static validation covered 74 Python files successfully.
- Historical UAT documents exist, but they are evidence leads rather than proof
  of the current checkout.
- The current isolated suite passes 20 tests under Python 3.12.
- One time-dependent dashboard test used a fixed 2026-07-13 timestamp and failed
  after its 24-hour freshness window. The fixture now derives its fresh timestamp
  from the test execution time; production freshness behavior was not changed.

## 9. IP-000 preservation list

IP-000 must not change:

- current user-facing use-case behavior;
- database schema or migrations;
- connector behavior;
- scoring weights or eligibility rules;
- CLI or dashboard routing;
- write semantics;
- Copilot operating instructions inside `src/AGENTS.md`.

IP-000 may add only safety automation, baseline evidence, isolated developer
tooling, and focused tests for those additions.

## 10. Gate G0 exit checklist

- [x] Private runtime directories are ignored.
- [x] Database files are private by default.
- [x] Synthetic databases are distinguishable from private databases, while the
  current sample tree remains transfer-quarantined pending review.
- [x] A path-only repository-boundary preflight exists.
- [x] The preflight has focused unit tests.
- [x] Current test dependencies are installed in an ignored local environment.
- [x] Current pytest suite result is recorded: 20 passed.
- [x] A source portability/sanitization manifest exists and keeps `src/`
  quarantined pending unit-by-unit approval.
- [x] A minimal synthetic behavior characterization set covers workload,
  capacity, contracts, weekly report, project list, use-case catalog, dashboard
  summary, and project health.
- [x] Offline connector contract validation is available without reading or
  displaying runtime configuration.
- [x] The owner approved the reconstructed synthetic sample organization for
  public transfer on 2026-07-19.
- [ ] Runtime source units have passed portability review.
- [x] Known module-level cached database paths were replaced with call-time
  resolution and covered by explicit isolation tests.

G0 is not complete until every unchecked item is resolved or explicitly accepted
as a documented exception.
