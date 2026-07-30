# Delivery Intelligence Program Context for Copilot 5.4

This document is a compact orientation for a new Copilot Chat. It describes
the whole approved Delivery Intelligence program; it is not authority to start
any phase or batch. `AGENTS.md`, `PROGRESS.md`, and the currently approved
design or implementation pack win whenever they conflict with this summary.

## Product and operating model

This is a portable, local Delivery Management intelligence system: a modular
Python/SQLite monolith with one Copilot-facing agent interface. Copilot reasons
over deterministic use cases; it does not become the system of record.

- Deterministic code owns canonicalization, filtering, calculations,
  validation, freshness, evidence, persistence, and write safety.
- Copilot owns interpretation, comparison, explanation, and uncertainty.
- The stable path is Copilot -> Tool/agent contract -> `UseCaseExecutor` ->
  registered use case -> domain services and canonical repositories.
- Results distinguish facts, signals, and recommendations. Missing, partial,
  stale, or conflicting evidence must remain explicit, never inferred as zero,
  healthy, available, or safe.
- New writes use propose -> preview -> explicit confirmation -> persist. A
  proposed design does not itself authorize a public write path.
- Use stable anonymous synthetic data only. Never access or add real data,
  company identifiers, credentials, live connectors, or operational exports.

## Program history and roadmap

| Phase | Purpose | Current program status |
| --- | --- | --- |
| 0 | Freeze and prove the candidate baseline | Promoted as the development baseline; release/UAT deferred. |
| 1 | Compatible facts, signals, recommendations contract | Promoted locally. |
| 2 | Delivery Attention Center foundation | Promoted locally; unaccepted legacy mapping configuration remains unavailable. |
| 3 | Execution and canonical milestone/commitment facts | Promoted locally. |
| 4 | Seven-dimension Project Health | Promoted locally; legacy review remains in place. |
| 5 | Effective capacity and Resource Intelligence | Design review required; no implementation pack or implementation authority. |
| 6 | Weekly Brief v2 from promoted facts | Planned only. |
| 7 | Forecast v1 using milestone and health history | Planned only. |
| 8 | What-if Simulation v1 | Planned only. |
| 9 | Integrated release candidate and deferred UAT | Planned only; requires separately approved release/UAT work. |

Phases 6–9 are roadmap intent, not frozen implementation designs. Before work
on any of them, inspect the live repository, write and approve a bounded design
and implementation pack, then receive authorization for exactly one gate.

## Reuse and ownership decisions already made

- Preserve the existing usable base through strangler migration; do not replace
  a legacy capability simply because a newer capability exists.
- Sprint Execution, Release/Milestone Health, and seven-dimension Project
  Health are distinct. Phase 3 owns canonical milestone and commitment facts;
  Phase 4 consumes them for health; Phase 7 may reuse their promoted history.
- Project Health dimensions are Schedule, Delivery, Scope, Quality, Resource,
  Dependency, and Governance. A missing factor is `not_available`/unknown, not
  neutral or green.
- Phase 5 may introduce structured effective-capacity facts. It must not
  manufacture Resource health from narrative or planned allocation alone;
  placeholders express demand, not human capacity.
- Manager Attention is automatic only where a separately approved deterministic
  producer exists. Do not create a producer, enable
  `pending_decision_attention`, or alter Attention/legacy behavior without its
  own approved scope.
- Production readiness is empty bootstrap -> versioned structured full import
  -> canonical derivation -> assessment -> coverage/integrity report. Each new
  persisted capability needs preview/validation, idempotent replay, audit,
  partial-failure protection, rollback, and synthetic tests.

## Required reading order

1. `AGENTS.md` and `PROGRESS.md` for binding state and exact active gate.
2. `architecture/00_ARCHITECTURE_NORTH_STAR.md` through
   `architecture/05_DELIVERY_INTELLIGENCE_EVOLUTION_PLAN.md` for enduring
   architecture and the Phase 0–9 roadmap.
3. `architecture/06_PHASE_1_INTELLIGENCE_OUTPUT_CONTRACT_DESIGN.md` through
   `architecture/12_PHASE_5_RESOURCE_INTELLIGENCE_DESIGN.md` for completed
   decisions and the current proposed design.
4. `implementation-packs/INDEX.md`, then a cited pack only when its phase is
   active or needed for compatibility analysis.
5. Relevant current code, schema, call paths, and tests before any proposal or
   edit. Historical statements never substitute for inspection.

## Gate discipline and completion protocol

Only an explicit owner decision authorizes the named design review, one bounded
implementation slice, promotion, connector/real-data work, push, merge, tag,
release, or deployment. Passing tests never grants the next authorization.

After any authorized implementation, first validate and perform an independent
read-only self-review. Then report in Chinese: what and why; usable behavior
and use; module/data/compatibility impact; remaining scope and next gate;
tests/review; and commit/push state. Update `PROGRESS.md` to match the actual
working tree.
