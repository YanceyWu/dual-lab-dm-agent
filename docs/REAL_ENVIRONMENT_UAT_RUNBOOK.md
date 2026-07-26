# Real-Environment UAT Runbook

## Boundary

Use `codex/ip-000-baseline-safety` only. Do not merge or rebase it into `main`.
All credentials, endpoints, databases, exports, logs, screenshots, raw payloads,
and real records remain in the approved local environment.

## Setup

From `src/`, create an isolated environment and install the product:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -e .
```

Create a local `.env` from `.env.example`; set approved database and connector
values locally only. Run `pm init` to initialize the local product database.

Open the repository root in VS Code, open Copilot Chat, and select the workspace
`Delivery Manager` agent from the agent picker. Keep terminal approvals enabled;
do not use global auto-approval or Autopilot for real-environment UAT. In Chat
customization diagnostics, verify that
`.github/agents/delivery-manager.agent.md` and
`.github/copilot-instructions.md` are loaded.

## Recovery point

Before any import, migration, or write-capable workflow:

```bash
pm backup create --label before-real-uat
```

Keep the tag and manifest in approved local records. If validation fails, stop
writes and follow `LOCAL_PRODUCT_UPGRADE_LIFECYCLE.md`.

## Validate before connector access

```bash
pm config validate
pm connector validate --portable
pm tool list
pm sync status
```

Use `pm connector probe <connector-name>` for an explicit safe runtime check of
an approved connector. Atlassian OAuth token refresh is automatic; the result
reports whether it occurred without exposing token or endpoint details. The
legacy `pm connector validate` command is local diagnostic output and must not
be exported without manual sanitization.

## Read-only UAT

```bash
pm tool query project-health-review
pm tool query management-attention
pm tool query weekly-dm-brief
pm tool query contract-continuity-review --days 180
pm tool query action-followup
pm tool query connector-status-review
pm tool query connector-sync-results
```

For every response, verify evidence/freshness are present, non-fresh states are
visible, and no credential, endpoint, raw error, or source payload appears.

## Controlled connector UAT

Sync one approved connector and narrow scope at a time. Afterwards inspect only
locally:

```bash
pm connector probe <connector-name>
pm sync status
pm tool query connector-status-review --connector <connector-name>
pm tool query connector-sync-results --connector <connector-name>
```

Confirm source, target tables, rows observed/changed, freshness, and retry
indication are expected. Stop on unexpected source, target table, or data volume.

## Staffing UAT

Start with the reversible stages only:

```bash
pm staffing assess ...
pm staffing propose ...
pm staffing preview <proposal-id>
pm staffing cancel <proposal-id> --reason "UAT verification"
```

Use `confirm` only after an authorized manager approves that exact proposal and
local token. Verify cancellation/rejection/expiry/changed facts produce no
assignment or allocation write.

## Dashboard UAT

Run locally with `pm dashboard serve`. Confirm project-snapshot filtering works
and the Dashboard stays inside the approved network boundary.

## Stop conditions

Stop and do not write if data scope is unexpected; an output exposes a
credential, URL, raw error, or payload; freshness is inadequate for a decision;
proposal facts change before confirmation; or migration/config validation fails.

## Sanitized feedback

Return only: candidate commit, test category, pass/fail/blocked/partial,
generic error category or counts/ranges, impact level, and sanitized requested
change. Never return real names, IDs, URLs, record content, credentials,
screenshots, or raw logs.
