# Delivery Intelligence Phase-Gated Evolution Plan

Status: `PHASE 1 PROMOTED — PHASE 2 DESIGN GATE NEXT`
Last updated: 2026-07-28

## Purpose

Evolve the existing local Delivery Manager runtime into a Delivery Intelligence
system through small, independently reviewable and reversible phases.

This plan does not authorize a broad redesign. It preserves the modular
monolith, the single Copilot agent interface, the local SQLite runtime, existing
connectors, deterministic rules, structured use-case contracts, and controlled
writes.

The exact `0.2.0rc1` commit
`a272890a7b51856c033df69b5148bc8c2fa928da` is the development baseline.
Feature work must use a separate `codex/` branch. Release tagging, isolated
operational-copy rehearsal, and controlled real-environment UAT are deferred
until the integrated candidate is assembled after the approved capability
iterations.

## Approval record

The owner approved this phase sequence and its delivery gates on 2026-07-27.
The approval covers the evolution order, standard phase batches, definitions of
ready and done, and session/branch strategy.

This approval does not authorize Phase 1 implementation, a Phase 1
implementation pack, a release tag, a merge into `main`, connector access,
active-database migration, or real-data operations. The owner separately
accepted the validated `a272890` commit as the development baseline on
2026-07-27 and deferred the current tag and UAT gates. Bounded Phase 1 design
approval was recorded on 2026-07-27; implementation remains limited to the
approved sequential batches.

The owner promoted Phase 1 on 2026-07-28 after IP-027 Batch D passed focused
regression, `make validate`, synthetic installed-package upgrade/rollback
rehearsal, portable-scope review, and schema review. This establishes the local
Phase 1 baseline but does not authorize a push, merge, tag, release,
deployment, real-data action, or Phase 2 implementation.

## Delivery loop

Every phase follows the same gated loop:

```text
Blueprint objective
    |
    v
Current architecture review
    |
    v
Phase-specific gap analysis
    |
    v
Design approval
    |
    v
Small implementation batches
    |
    v
Focused tests and full regression
    |
    v
Phase promotion decision
    |
    v
Next phase
```

No phase may absorb work from a later phase merely because adjacent code is
being edited.

## Invariants

- Deterministic code owns facts, filtering, calculations, validation,
  persistence, authorization, freshness, and execution evidence.
- Copilot owns intent interpretation, comparison, explanation, and uncertainty.
- Intelligence output separates facts, signals, and recommendations.
- Missing or non-fresh data remains visible and is never converted into zero,
  healthy, available, or safe.
- Existing tables and services are extended or adapted before a replacement is
  considered.
- Database changes are additive or backward compatible, rehearsed on synthetic
  data, and have a practical rollback.
- All business writes follow propose, preview, explicit confirmation, persist.
- Portable work uses synthetic data only. Operational configuration, data,
  identifiers, logs, and evidence remain inside the approved work environment.

## Standard phase batches

### Batch A — Design

No runtime code changes.

Required outputs:

- verified current call path and schema;
- business goal and decision being supported;
- stable input and output contracts;
- canonical context and evidence requirements;
- deterministic rules and configurable thresholds;
- model role and prohibited inferences;
- migration and rollback design;
- scenarios, acceptance criteria, and non-goals;
- explicit owner design approval.

### Batch B — Deterministic core

- backward-compatible migration or repository adapter, when required;
- typed domain result or rule implementation;
- unit, repository, integrity, and migration tests;
- no interface-specific business behavior.

### Batch C — Use-case integration

- shared executor registration or existing-use-case extension;
- evidence, freshness, assumptions, warnings, and execution metadata;
- thin CLI, Dashboard, and Copilot projections;
- contract tests, golden scenarios, and legacy compatibility coverage.

### Batch D — Regression and promotion

- focused tests for the phase;
- `make validate`;
- `make rehearse-release` when schema, packaging, migration, or installed
  behavior changes;
- rollback rehearsal;
- portable-scope review;
- implementation report and `PROGRESS.md` update;
- explicit decision to promote, revise, or stop.

## Definition of ready

A phase is ready for implementation only when:

- the previous phase is promoted;
- its current code, schema, call paths, and tests have been inspected;
- the design pack is approved;
- input, output, evidence, freshness, and failure behavior are defined;
- unknown company-specific details are marked `UNKNOWN`;
- migration, compatibility, and rollback effects are understood;
- synthetic scenarios and acceptance criteria exist;
- non-goals prevent work from expanding into later phases.

## Definition of done

A phase is complete only when:

- approved behavior is implemented without unapproved redesign;
- facts, signals, and recommendations remain distinguishable;
- failure, partial, stale, conflicting, and missing-data behavior is tested;
- focused tests and full regression pass;
- migration and rollback evidence exists when applicable;
- the portable boundary check passes;
- unresolved risks have an owner or explicit next action;
- documentation and `PROGRESS.md` match the actual working tree;
- commit, push, CI, and promotion state are recorded;
- the owner approves entry into the next phase.

## Phase sequence

### Phase 0 — Freeze and prove the current baseline

Goal: establish the exact `0.2.0rc1` source and schema as the trusted starting
point.

Required outcomes:

- final GitHub Actions result for the exact candidate HEAD;
- local full regression for the exact source plus approved planning changes;
- explicit owner decision accepting or rejecting the source as the development
  baseline.

Deferred release outcomes:

- immutable candidate tag;
- isolated operational-database-copy upgrade and rollback rehearsal;
- controlled configuration, read-only use-case, connector, staffing, and
  Dashboard UAT;
- sanitized defect categories and final operational candidate decision.

These outcomes move to Phase 9 and require a refreshed UAT runbook that covers
the capabilities actually promoted through the iteration sequence.

Non-goals:

- no Delivery Intelligence feature implementation;
- no active-database-first migration;
- no merge into `main`;
- no automatic tag or publication.

Promotion decision: passed for development evolution on 2026-07-27. Exact
remote HEAD `a272890` passed GitHub Actions on Python 3.10 and 3.12, and the
owner accepted it as the baseline with tag and real-environment UAT explicitly
deferred. This is not production or operational approval.

### Phase 1 — Intelligence output contract

Goal: define a backward-compatible fact, signal, and recommendation structure
inside the existing `UseCaseResult`.

Initial contract concepts:

- `facts[]`: observed value, subject, observed time, freshness, evidence refs;
- `signals[]`: type, severity, state, rule version, fact refs, reason codes;
- `recommendations[]`: action, rationale, signal refs, confirmation behavior.

Reuse:

- `UseCaseRequest` and `UseCaseResult`;
- `UseCaseExecutor`;
- evidence, freshness, assumptions, warnings, and execution traces.

Non-goals:

- no Attention rules;
- no database migration unless the approved design proves it necessary;
- no new agent or model runtime;
- no Staffing write-path change.

Promotion gate: at least one existing read-only use case emits the new compatible
shape while all existing consumers and registered-use-case regression tests
continue to pass.

Promotion decision: passed on 2026-07-28. Management Attention is the single
production reference mapping, and all approved local validation and rehearsal
checks passed. The next phase-boundary action is a new Phase 2 design task.

### Phase 2 — Delivery Attention Center foundation

Goal: make high-confidence attention signals explainable, deduplicated, and
historical.

Initial signals:

- project health red or amber;
- overdue action;
- pending decision;
- resource overload from existing allocation facts;
- stale or missing source.

Expected storage, subject to design approval:

- attention rules;
- current attention signals;
- attention history.

Non-goals:

- no Jira issue-history acquisition;
- no aging-blocker, scope-growth, or forecast signals;
- no automatic action creation or project-status write.

Promotion gate: every attention item exposes its facts, evidence, freshness,
rule version, state change, and bounded recommendation.

### Phase 3 — Delivery execution signal enrichment

Goal: provide the source facts required for aging blockers, scope growth,
sprint risk, release risk, and dependency observations.

Expected additions, subject to design approval:

- incremental Jira issue-history cache;
- Jira issue-link cache;
- deterministic duration and scope-delta calculations;
- additional Attention signal producers.

Non-goals:

- no Forecast engine;
- no replacement of the current Jira issue snapshot;
- no management judgment inside connector code.

Promotion gate: sync is bounded, incremental, idempotent, observable, and
partial-state aware; every new signal traces to source history.

### Phase 4 — Seven-dimension Project Health

Goal: create explainable project health across Schedule, Delivery, Scope,
Quality, Resource, Dependency, and Governance.

Reuse:

- current project-health review;
- Jira and Confluence observations;
- Attention signals;
- resource, action, decision, and project-snapshot facts.

Expected additions, subject to design approval:

- health score definitions;
- project health snapshots;
- health factors with evidence, freshness, and rule versions.

Non-goals:

- no silent project-status update;
- no conversion of missing dimensions into healthy scores;
- no concealment of source conflicts.

Promotion gate: green, amber, red, unknown, stale, missing, and conflicting
scenarios are independently explainable and regression tested.

### Phase 5 — Resource Intelligence

Goal: evolve allocation views into effective-capacity and resource-risk views.

Reuse:

- employees, assignments, monthly allocations, plan versions, skills,
  placeholders, HIREF, and the controlled Staffing workflow.

Expected additions, subject to design approval:

- capacity calendar;
- explicit leave, BAU, and non-project commitments;
- read-only resource heatmap;
- resource-overload and skill-dependency signals;
- effective-capacity input to Staffing assessment.

Non-goals:

- no automatic personnel assignment;
- no personnel-performance scoring;
- no portable storage of operational HR data;
- no change to confirmation authority.

Promotion gate: Heatmap and Staffing use the same explainable capacity formula,
and all existing Staffing safety and concurrency tests remain green.

### Phase 6 — Weekly Brief v2

Goal: produce a management-ready brief from verified facts and promoted
intelligence capabilities.

Required sections:

- overall health;
- changes since the previous snapshot;
- highest attention signals;
- achievements;
- risks and dependencies;
- decisions required;
- resource concerns;
- next actions;
- freshness and limitations.

Non-goals:

- no automatic publication, email, action creation, or decision creation;
- no user-facing use-case chaining when shared domain facts can be composed.

Promotion gate: every material statement is traceable, new and continuing
issues are distinguished, and the model cannot add facts absent from tool
results.

### Phase 7 — Forecast v1

Goal: implement a transparent deterministic Sprint and Release forecast.

Prerequisites:

- sufficient execution history from Phase 3;
- promoted health and effective-capacity models;
- normalized milestone or release-commitment inputs.

Expected additions, subject to design approval:

- velocity snapshots;
- release forecasts;
- forecast assumptions, evidence windows, confidence, and error history.

Non-goals:

- no black-box ML;
- no cross-team story-point comparison without normalization evidence;
- no forecast presented as a commitment;
- no precise forecast when facts are insufficient.

Promotion gate: repeatable backtesting exposes error and confidence, and
insufficient data produces unavailable or low-confidence results.

### Phase 8 — What-if Simulation v1

Goal: compare one constrained planning scenario with an approved baseline.

The first scenario should change only one material parameter. Recommended first
slice: reduce scope and calculate the forecast delta. Additional scenarios such
as adding resources or moving a dependency require separate approved slices.

Reuse:

- plan versions;
- Forecast;
- effective capacity;
- project snapshots.

Non-goals:

- no mutation of the baseline;
- no causal guarantee;
- no conversion of a simulation into an approved plan without a separate
  proposal and confirmation.

Promotion gate: baseline and scenario remain isolated, assumptions and
sensitivity are visible, unsupported parameters fail safely, and forecast
uncertainty propagates into the result.

### Phase 9 — Integrated release candidate

Goal: promote the completed set of approved phases as a new independently
validated Delivery Intelligence candidate.

Required validation:

- structured use cases and legacy compatibility;
- Staffing write safety;
- Attention lifecycle;
- Health history;
- Resource capacity;
- Weekly Brief;
- Forecast and Simulation, if promoted;
- connector partial and failure behavior;
- all migrations and rollback;
- package build and temporary installation;
- synthetic legacy-database upgrade;
- isolated operational-copy rehearsal and controlled UAT.

Before Phase 9 UAT begins, revise and approve
`docs/REAL_ENVIRONMENT_UAT_RUNBOOK.md` against the final promoted capability
set. The deferred `0.2.0rc1` runbook is reference material, not a current
promotion gate.

Non-goals:

- no automatic merge, tag, publication, deployment, or active-database
  migration.

## Session and branch strategy

- Keep one Codex task for the design and implementation batches of a phase.
- Start a new task at the next phase boundary after the previous gate is
  recorded.
- Each new task begins by reading `AGENTS.md`, `PROGRESS.md`, this plan, the
  approved phase design, and current Git state.
- Use a separate `codex/` branch for each implementation phase, based on the
  exact promoted HEAD of the previous phase.
- Do not open a new implementation branch merely to draft a future design.
- Do not register a new implementation pack until Phase 0 and the applicable
  design approval are complete.

## Immediate next action

Start a new Codex task for Phase 2 Batch A design. Read `AGENTS.md`,
`PROGRESS.md`, this plan, the promoted Phase 1 design/report, and current Git
state. Inspect the existing Management Attention implementation and database
schema before drafting the bounded Delivery Attention Center design. Do not
register a Phase 2 implementation pack or change runtime/schema until that
design is explicitly approved.
