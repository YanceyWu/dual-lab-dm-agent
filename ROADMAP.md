# DM Agent Evolution Roadmap

## Purpose

This roadmap turns the current local PM toolkit into a reusable, Copilot-driven
Delivery Manager intelligence product without rewriting the working base.

It is designed for execution by repository-aware implementation models that may
have weaker architecture capability. Each change must therefore be delivered as
a bounded implementation pack with explicit discovery, contracts, constraints,
acceptance tests, and rollback instructions.

The detailed target architecture is defined in
`architecture/04_COPILOT_LOCAL_AGENT_ARCHITECTURE.md`.

## Operating rules

1. Preserve working behavior through strangler migration.
2. Migrate one vertical slice at a time.
3. Separate repository assessment, implementation, and validation runs.
4. Do not combine framework change, schema redesign, and new business behavior in
   one pack.
5. Use existing components before adding a framework or parallel implementation.
6. A pack is complete only when tests, evidence, rollback, and documentation are
   complete.
7. A later wave must not begin until the required quality gate is passed.
8. Product-core artifacts and local private state remain separate.
9. Portable source-independent code may be developed externally with synthetic
   data; company adapters and real-environment validation remain internal.

## Delivery tracks

### Product track

Delivers stable DM workflows, local onboarding, Copilot experience, evidence,
safe writes, and upgrade usability.

### Architecture track

Reduces extension cost through shared execution contracts, canonical context,
domain services, repositories, connector boundaries, and evaluation.

Both tracks progress together. Product delivery does not wait for architectural
perfection, and architecture work must prove value through a real use case.

## Quality gates

| Gate | Outcome | Required before |
| --- | --- | --- |
| G0 Safe Baseline | Reproducible, data-safe current product with behavior evidence | Any refactor |
| G1 Shared Runtime | One executor and versioned result envelope used by two interfaces | Agent tools |
| G2 Copilot Tooling | Copilot consumes structured results with evidence and freshness | High-value reasoning |
| G3 Staffing Reference | Time/effort/contract-aware proposals and atomic confirmation | Write-capable expansion |
| G4 DM V1 | Core read-only use cases are stable and evaluated | Broad DM adoption |
| G5 Distributable Product | Clean install, local configuration/state separation, tested upgrades | Multi-DM rollout |

## Wave 0 — Safe baseline and behavior characterization

### Goal

Create a trustworthy starting point before changing architecture.

### Scope

- Define the distributable product core and local private-state boundary.
- Ensure operational databases, exports, credentials, token caches, backups, and
  real-data reports cannot enter the distributable repository.
- Capture current CLI and dashboard behavior for supported demo-data workflows.
- Establish a current component and capability classification: Interface, UC,
  DS, PS, CN, Legacy.
- Record known behavioral defects separately from intended legacy behavior.
- Make current installation and sample-data setup reproducible.
- Establish a temporary-database test harness and smoke tests for supported entry
  points.

### Preserve

- current SQLite schema and migration behavior;
- current CLI and dashboard output;
- current sample-data workflow;
- current use-case classes and repositories.

### Do not do

- do not restructure modules;
- do not redesign the database;
- do not add Copilot workflows yet;
- do not fix unrelated historical lint or formatting.

### Exit criteria: G0

- a clean clone can build an isolated demo database;
- local private-state paths are excluded and verified by an automated check;
- current supported smoke tests pass without accessing real sources;
- behavior snapshots exist for Team Workload, Capacity, HIREF Summary, Weekly
  Report, Project List, and Dashboard health;
- the known issue register distinguishes defects from migration constraints;
- rollback is a clean return to the pre-refactor product core.

## Wave 1 — Shared use-case execution runtime

### Goal

Create one stable application boundary without changing business behavior.

### Reference slice

Use a low-risk, read-only workflow. Preferred order:

1. Team Capacity/Workload; or
2. HIREF Summary if it provides better existing automated coverage.

The internal repository architect selects one after comparing interface reuse and
test coverage. Writes remain out of scope.

### Scope

- Version the shared UseCaseRequest and UseCaseResult envelopes.
- Introduce one shared executor and executable use-case registration.
- Add execution ID, use-case ID, status, warnings, and execution metadata.
- Adapt one existing use-case service rather than replacing it.
- Route the existing CLI and one dashboard/API path through the same executor.
- Preserve human-formatted output through a renderer outside the use case.
- Add structured output for automation and Copilot consumption.

### Do not do

- do not migrate every command;
- do not add an LLM or semantic router;
- do not split the repository module;
- do not add write confirmation;
- do not change the underlying database.

### Exit criteria: G1

- two interfaces call the same reference use-case implementation;
- the structured result is validated against a versioned schema;
- existing human output remains semantically equivalent;
- a new read-only use case can be registered without adding business logic to
  each interface;
- execution and failure status can be traced by execution ID;
- focused contract, service, renderer, and interface tests pass;
- removal of the new route cleanly restores the legacy route.

## Wave 2 — Copilot Agent Tool protocol and context evidence

### Goal

Make the shared runtime safe and predictable for Copilot Agent.

### Scope

- Add transport-neutral operations: list, describe, query, propose, preview,
  confirm, reject, and get-result. Implement only list, describe, and query for
  the reference slice in this wave.
- Add evidence, freshness, assumptions, warnings, and alternatives to the result
  envelope.
- Create the first context recipe and bounded Context Package.
- Distinguish success, partial, invalid, unavailable, and failed.
- Ensure connector failure is not represented as empty business data.
- Add a concise repository-wide Copilot policy and one bounded use-case playbook
  or skill for the reference use case.
- Validate that Copilot operating mode uses the tool contract rather than direct
  database inspection or formatted CLI parsing.

### Copilot customization stance

Copilot currently supports repository instructions, repository-level custom
agents, and project skills. These are delivery mechanisms, not domain contracts.
The use-case and tool schemas must remain valid if the Copilot file mechanism or
host changes.

Official references reviewed for this plan:

- [Repository custom instructions and AGENTS.md](https://docs.github.com/en/copilot/how-tos/configure-custom-instructions-in-your-ide/add-repository-instructions-in-your-ide)
- [Repository-level custom agents](https://docs.github.com/en/copilot/concepts/agents/copilot-cli/about-custom-agents)
- [Project agent skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills)

### Do not do

- do not encode capacity or staffing calculations in prompts;
- do not expose raw database rows as the tool contract;
- do not make MCP mandatory;
- do not add write-capable tools;
- do not create multiple business agents.

### Exit criteria: G2

- Copilot can answer one reference management question from structured tool
  output;
- the answer states evidence, freshness, warnings, and assumptions;
- an unavailable source produces an explicit unavailable or partial result;
- the same tool result can be rendered by CLI without Copilot;
- the playbook has synthetic happy, missing-data, stale-data, and tool-failure
  scenarios;
- no authoritative fact is calculated only in Copilot instructions.

## Wave 3 — Staffing as the write-capable reference slice

### Goal

Deliver a real DM decision workflow for new demand and staffing that proves the
target architecture end to end.

### Step 3A — Canonical staffing read model

- Define canonical contracts for Person, Skill, Project, Demand, Assignment,
  Capacity, Contract, and SourceState.
- Implement repository adapters over current employees, projects, assignments,
  monthly allocations, plan versions, staffing placeholders, and contract data.
- Do not rename or bulk-migrate existing tables.
- Add identity, time-period, unit, nullability, and source-of-truth rules.

#### Exit criteria

- staffing domain services use canonical contracts rather than raw source rows;
- current and planned allocations are distinguishable;
- capacity specifies period and plan version;
- contract coverage can be checked for a requested period;
- missing and conflicting facts remain visible.

### Step 3B — Demand and deterministic feasibility

- Add demand effort, start/end period, duration, roles, skills, minimum
  allocation, maximum people, splitability, priority, constraints, and
  preferences.
- Correct load boundary, skill-threshold, role-match, project-count, and
  over-allocation behavior.
- Check monthly capacity and contract coverage.
- Generate combinations that satisfy total effort rather than only headcount.
- Calculate impact on existing assignments.
- Version rule sets and scoring configuration.

#### Exit criteria

- a fully loaded or contract-ineligible person cannot pass hard eligibility;
- total recommended allocation satisfies effort and period constraints;
- role and required-skill behavior matches the documented contract;
- results expose accepted, rejected, and unknown reasons;
- deterministic tests cover all boundary conditions.

### Step 3C — Proposal, confirmation, and persistence

- Create immutable staffing proposals with expiry and evidence snapshot.
- Add preview with intended before/after assignment changes.
- Revalidate decision-critical facts at confirmation time.
- Commit all assignment and decision records in one transaction.
- Make confirmation idempotent and reject reused or expired tokens.
- Retain a manager-readable decision record and rule version.

#### Exit criteria: G3

- no write occurs during query or proposal creation;
- every write has an explicit confirmed proposal;
- failure cannot leave partial assignments without the decision record;
- repeated confirmation cannot duplicate the decision;
- cancellation and rejection leave domain state unchanged;
- legacy staffing behavior is preserved where intended or the approved behavior
  difference is documented;
- at least 20 synthetic staffing scenarios pass, including time, effort, skill,
  contract, overload, split-demand, stale-data, and concurrent-change cases.

## Wave 4 — Core DM V1 use cases

### Goal

Expand the proven architecture to the smallest shareable DM product.

### Migration order

1. Project Health Review
2. Management Attention Review
3. Weekly DM Brief
4. Contract Continuity Review
5. Action Follow-up

Each use case is a separate implementation pack and follows the same sequence:

1. current behavior and source mapping;
2. contract and context recipe;
3. deterministic domain analysis;
4. shared executor integration;
5. Copilot playbook and grounded explanation;
6. golden scenarios and interface regression;
7. independent validation and rollback report.

### Cross-use-case rules

- use cases may share domain services and context components;
- one user-facing use case must not invoke another user-facing use case;
- Management Attention and Weekly Brief may compose domain results through
  application-level orchestration, not by parsing another interface response;
- every result distinguishes fact, derived signal, model inference, and unknown;
- stale or failed sources are always visible.

### Exit criteria: G4

- all V1 use cases use the shared executor and result envelope;
- Copilot can select the correct use case for agreed example requests;
- every result has evidence and freshness coverage;
- management reasoning golden scenarios meet defined factuality and usefulness
  rubrics;
- no core V1 workflow requires direct interface SQL;
- one use case can fail without causing unrelated use cases to return false empty
  data;
- pilot DM feedback is recorded against use-case IDs and scenario categories.

## Wave 5 — Connector and data-lineage hardening

### Goal

Make source integration extensible without destabilizing business use cases.

### Scope

- Introduce the shared connector acquisition/mapping/result contract.
- Migrate one connector at a time, starting with the connector that has the best
  existing test fixtures and highest V1 use-case value.
- Standardize source ID, sync ID, raw evidence reference, observed time, parser
  version, mapping errors, freshness, retry, and partial-failure status.
- Add sanitized connector contract fixtures.
- Separate source parsing from domain interpretation.
- Add lineage from canonical and derived facts to source observations.

### Do not do

- do not migrate all connectors in one pack;
- do not change source authentication and domain mapping together unless required;
- do not delete source cache tables until all read paths are proven migrated;
- do not let connector retry hide persistent failure.

### Exit criteria

- a connector can be added without changing unrelated use cases;
- connector failure, no records, and stale records are distinguishable;
- sync is idempotent for the same observation;
- partial success is visible to context packages;
- canonical facts retain traceable source evidence;
- connector contracts have sanitized fixtures and deterministic tests.

## Wave 6 — Multi-DM distribution and upgrade lifecycle

### Goal

Turn the architecture into a product that multiple DMs can install, configure,
upgrade, and trust locally.

### Scope

- Package versioned product core separately from local configuration and private
  state.
- Provide a first-run setup and validation workflow.
- Provide sanitized demo data and scenario walkthroughs.
- Validate local connector readiness without printing credentials.
- Add database version checks, pre-upgrade backup, migration, verification, and
  recovery guidance.
- Establish supported-version policy and release notes.
- Add local-only default network binding and explicit opt-in for broader access.
- Create a DM onboarding checklist and first-week acceptance flow.

### Exit criteria: G5

- a new DM can install and run the demo without access to another DM's data;
- live data and credentials cannot be committed through normal repository use;
- configuration errors are actionable and do not corrupt the database;
- upgrade from the previous supported version is tested on an isolated copy;
- failed migration has a verified recovery path;
- the five core V1 use cases pass smoke and golden evaluation after upgrade;
- each DM can retain local state while updating the product core.

## Implementation-pack execution protocol

Every roadmap item is converted into a bounded implementation pack.

### Required pack sections

- business goal and user impact;
- architecture intent;
- verified current-state indicators;
- required contracts;
- in-scope and explicit non-goals;
- repository discovery steps;
- compatibility and migration constraints;
- acceptance scenarios and focused tests;
- observability expectations;
- rollback or recovery approach;
- required implementation report;
- independent validation checklist.

### Required execution sequence

1. Repository architect assesses and maps the pack without edits.
2. Human reviews conflicts and scope.
3. Implementation engineer performs only the approved pack.
4. Focused tests and regression checks run on isolated data.
5. Independent reviewer validates architecture intent and behavior.
6. Human promotes, corrects, or rolls back.

The implementing model must use `UNKNOWN` for unresolved repository facts and
must not silently redesign the pack.

## Release and prioritization rules

Priority is determined in this order:

1. data exposure, corruption, or irreversible-write risk;
2. factual correctness of management decisions;
3. shared contract and regression safety;
4. high-frequency DM user value;
5. extension cost and internal maintainability;
6. presentation or theoretical elegance.

A release may include product and architecture work, but it must not cross more
than one major quality gate at a time.

## Architecture fitness metrics

Track these per release:

- percentage of supported interfaces routed through the shared executor;
- percentage of migrated use cases returning evidence and freshness;
- number of interface modules changed to add a use case;
- number of business use cases changed to add a connector;
- number of decision rules existing only in prompt instructions;
- number of write paths without proposal and atomic confirmation;
- golden-scenario pass rate by use case and failure category;
- upgrade and rollback validation status;
- unresolved source-of-truth conflicts;
- pilot feedback categorized by use case, context, rule, reasoning, or interface.

Targets are tightened at each gate. A metric must not be optimized by hiding
unsupported behavior or silently dropping failed sources.

## Stop conditions

Stop an implementation pack and return to assessment when:

- the required behavior conflicts with an unknown production dependency;
- the proposed change requires a database rewrite outside the pack;
- a current interface cannot be preserved and the behavior change is unapproved;
- a connector or migration would touch real data without isolated validation;
- the model cannot explain the transaction or rollback boundary;
- acceptance tests cannot distinguish success from partial or unavailable data;
- implementation requires company-specific data to leave the local environment.
