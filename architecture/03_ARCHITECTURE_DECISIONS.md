# Architecture Decisions

## ADR-001 — External architecture control plane

External assets define architecture intent, contracts, migration order, and
quality gates. Company source code remains exclusively inside the company
environment.

## ADR-002 — One-way transfer model

Artifacts flow from this repository into the company environment. Return feedback
is optional, manually reviewed, sanitized, and policy-dependent.

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

