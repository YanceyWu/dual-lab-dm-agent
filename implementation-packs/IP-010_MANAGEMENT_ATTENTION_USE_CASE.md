# IP-010 — Management Attention Use Case

## Goal

Rank the locally observed issues that most need Delivery Manager attention.

## Scope and rules

- Read latest local project-health observations, overdue action items, and the
  freshness state of health sources directly through repositories.
- Return deterministic severity, reason code, evidence, freshness, and bounded
  `ManagementAttentionContext`; never create an action or infer a future risk.
- RED health is `critical`; AMBER health and stale/failed sources are `high`;
  overdue actions are `high` only when their recorded priority is high.

## Acceptance

Synthetic RED project health, an overdue action, and a non-fresh source each
produce a separate evidence-backed attention item. The JSON tool query does not
change project, action, contract, or staffing data.
