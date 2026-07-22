# IP-014 — Connector Contract Reference Migration

## First slice

Add `connector-status-review`: a structured, credential-free read-only view of
connector readiness, active/stale source counts, latest local run, and source
freshness. It does not invoke a connector, read endpoint configuration, or
expose authentication material.

## Acceptance

`pm tool query connector-status-review [--connector jira]` returns JSON with
evidence, freshness, warnings, calculation version, and execution metadata.
