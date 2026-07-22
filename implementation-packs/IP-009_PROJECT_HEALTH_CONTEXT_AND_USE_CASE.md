# IP-009 — Project Health Context and Use Case

## Goal

Expose the latest locally stored project-health observations through the stable
read-only use-case contract, so Copilot can answer “what is the current health
and why?” with evidence and freshness rather than querying dashboard internals.

## Scope

- Register `project-health-review` in the shared executor and structured tool
  transport.
- Adapt existing active projects, JIRA board mappings, latest JIRA health
  snapshots, latest Confluence status snapshots, and source freshness behind a
  repository facade.
- Return a bounded `ProjectHealthContext` with grades, component scores,
  snapshot dates, evidence, freshness, warnings, and rule version.
- Support an optional exact `project_id` filter.

## Safety rules

- Query only: no sync, connector call, score recalculation, proposal, or write
  to project/staffing domain tables.
- The executor may persist its bounded execution trace only; it must not retain
  result payloads or source configuration.
- Do not invent a health grade when no local snapshot exists. Return `unknown`
  and a warning instead.
- JIRA grade takes precedence over a Confluence RAG label; conflicting records
  remain visible as evidence.

## Acceptance scenarios

1. A project with a latest RED JIRA snapshot returns `red`, its component
   scores, snapshot date, and source freshness.
2. A project with no JIRA snapshot but an AMBER status snapshot returns
   `amber` without fabricating scores.
3. A project with no health evidence returns `unknown` and a missing-snapshot
   warning.
4. An exact unknown/inactive project returns `unavailable`.
5. Structured CLI query is JSON-only and no domain data changes.

## Rollback

Unregister `project-health-review` and remove its adapter/context. Existing
Dashboard and legacy `pm health` views remain available because they are not
modified by this pack.
