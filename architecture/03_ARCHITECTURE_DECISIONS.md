# Architecture Decisions

## ADR-001 — External architecture control plane

External assets define architecture intent, contracts, migration order, quality
gates, and portable reference implementations. Company-specific source code and
all real company data remain exclusively inside the company environment.

## ADR-002 — One-way transfer model

Approved portable code, models, tests, synthetic samples, and architecture
artifacts flow from this repository into the company environment through GitHub.
Return feedback is optional, manually reviewed, sanitized, and policy-dependent.

## ADR-003 — Modular monolith and single agent

Keep a single deployable system and one agent interface through early versions.
Split only when a capability requires independent state, lifecycle, permissions,
or scaling.

## ADR-004 — Strangler migration

Keep legacy paths working while new use-case contracts surround and incrementally
replace them. No broad rewrite is authorized by the target architecture.

## ADR-005 — Canonical model between sources and intelligence

Source-specific records map into canonical delivery concepts before use by new
domain services. Raw evidence remains available for traceability.

## ADR-006 — Deterministic core, model-assisted reasoning

Rules, filtering, allocation math, constraints, persistence, and authorization
belong in deterministic code. The model interprets requests, compares computed
options, surfaces uncertainty, and explains evidence.

## ADR-007 — Human-controlled writes

State changes use propose, preview, confirm, persist. Read-only analysis is the
default.

## ADR-008 — Copilot is the primary reasoning host

GitHub Copilot Agent provides the natural-language interaction and model
reasoning layer for the local DM product. The Python runtime remains model-host
independent and owns authoritative data, calculations, validation, and
persistence. A second embedded agent framework is not introduced without a
measured requirement that the Copilot host cannot satisfy.

## ADR-009 — Tool contracts are transport independent

Copilot, CLI, dashboard, and automation call the same versioned use-case
contracts. Structured CLI is an acceptable initial transport. HTTP or MCP may be
added later without changing the application contract or domain behavior.

## ADR-010 — Product core and local state are separate

Versioned runtime, migrations, instructions, sanitized samples, and tests form
the distributable product core. DM-specific configuration is separately managed.
Credentials, token caches, operational databases, source exports, backups, and
real-data outputs remain local private state and are never distributed.

## ADR-011 — Delivery Intelligence evolution is phase gated

Evolve the product through one independently reviewable and reversible vertical
slice at a time. Every phase requires current-state inspection, a bounded gap
analysis, design approval, small implementation batches, focused tests, full
regression, and an explicit promotion decision before the next phase begins.
Future-phase work must not be pulled into an active phase merely because
adjacent code is being changed.

## ADR-012 — Current UAT is deferred to the integrated candidate

Accept exact commit `a272890` as the validated development evolution baseline,
not as an operationally approved release. Defer the `0.2.0rc1` tag, isolated
operational-copy rehearsal, and real-environment UAT until the approved
Delivery Intelligence capability phases have been integrated. Before that UAT,
revise and approve the runbook against the final promoted capability set.
