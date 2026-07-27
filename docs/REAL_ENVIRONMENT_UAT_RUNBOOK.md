# Real-Environment UAT Runbook

Status: `DEFERRED — REVISE BEFORE INTEGRATED RELEASE UAT`

This runbook describes the deferred `0.2.0rc1` candidate flow. It is retained as
safety reference but is not a current gate for Delivery Intelligence feature
iteration. Do not execute it as the final integrated UAT procedure.

After the approved capability phases are complete, revise its installation,
schema, use-case, connector, write-safety, Dashboard, rollback, and sanitized
feedback coverage against the integrated candidate. Obtain explicit owner
approval before real-environment use.

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

For the `0.2.0rc1` candidate, first verify that the checked-out commit matches
the approved `v0.2.0-rc.1` tag and record only the commit hash plus version:

```bash
git rev-parse HEAD
pm version
```

Do not begin real-environment UAT from an uncommitted working tree or a commit
whose GitHub Actions validation has not passed.

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

## IP-024 isolated migration rehearsal

Do not first run the new bootstrap against the active operational database.
Use the database snapshot path printed by `pm backup create`, copy that snapshot
to an approved temporary location outside the repository, and point only the
rehearsal process at the copy:

```bash
cp /approved/path/from-backup-manifest.db /approved/temp/dm-uat-upgrade.db
DM_UAT_DATABASE_PATH=/approved/temp/dm-uat-upgrade.db
DATABASE_PATH="$DM_UAT_DATABASE_PATH" pm init
```

Before and after `pm init`, record only aggregate counts for the required core
tables. Do not export rows, names, identifiers, or database files. After the
upgrade, verify the copied database:

```bash
sqlite3 "$DM_UAT_DATABASE_PATH" "PRAGMA integrity_check;"
sqlite3 "$DM_UAT_DATABASE_PATH" "PRAGMA foreign_key_check;"
sqlite3 "$DM_UAT_DATABASE_PATH" \
  "SELECT name, type FROM sqlite_master WHERE name IN ('v_member_load','v_project_team','staffing_proposals','dashboard_operations') ORDER BY name;"
sqlite3 "$DM_UAT_DATABASE_PATH" "SELECT COUNT(*) FROM v_member_load;"
sqlite3 "$DM_UAT_DATABASE_PATH" "SELECT COUNT(*) FROM v_project_team;"
sqlite3 "$DM_UAT_DATABASE_PATH" \
  "SELECT name FROM pragma_table_info('staffing_proposals') WHERE name LIKE 'confirmation_token%';"
```

Expected results are `integrity_check=ok`, no rows from `foreign_key_check`,
both views and both new operation tables present, both views queryable, and
only `confirmation_token_hash` returned for the token-column check. Confirm
that employee, project, assignment, monthly-allocation, and decision aggregate
counts match their pre-upgrade values.

Stop if bootstrap reports invalid months, invalid allocation values, duplicate
employee/project/month/plan-version rows, a failed view query, an integrity or
foreign-key error, or a changed aggregate count. Keep the active database
untouched until this rehearsal passes and the operator explicitly approves the
live `pm init`.

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
pm tool query project-snapshot-list --param health=amber --param artifact_kind=plan
```

For every response, verify evidence/freshness are present, non-fresh states are
visible, and no credential, endpoint, raw error, or source payload appears.
Also verify executor enforcement with a deliberately invalid read-only request:

```bash
pm tool query contract-continuity-review --days 9999
```

It must exit non-zero with `PARAMETER_OUT_OF_RANGE`, without invoking a
connector or returning a raw exception.

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

Run locally with `pm dashboard serve`. Confirm project-snapshot filtering works,
generic `/api/tool/query/<use-case-id>` responses retain the full structured
contract, and legacy endpoints carry their interface-classification headers.

For project-health sync, verify preview performs no connector call and displays
the exact board scope. Confirm only that preview, then verify a replay of its
one-time token is rejected and browser output contains no raw connector error.
Do not use a real sync target merely to test error handling.

The Dashboard must bind to loopback by default. Non-loopback binding is allowed
only for an approved network scope and requires the explicit `--allow-remote`
operator option.

## Stop conditions

Stop and do not write if data scope is unexpected; an output exposes a
credential, URL, raw error, or payload; freshness is inadequate for a decision;
proposal facts change before confirmation; or migration/config validation fails.

## Sanitized feedback

Return only: candidate commit, test category, pass/fail/blocked/partial,
generic error category or counts/ranges, impact level, and sanitized requested
change. Never return real names, IDs, URLs, record content, credentials,
screenshots, or raw logs.
