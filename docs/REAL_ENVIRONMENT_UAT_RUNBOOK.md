# Real-Environment UAT Runbook

Status: `APPROVED 2026-08-02 — PROCESS BASIS ONLY; EXECUTION REQUIRES SEPARATE AUTHORIZATION`

This revision (usability R6) aligns the deferred real-environment UAT flow
with the current integrated Delivery Intelligence candidate. The owner
approved it on 2026-08-02 (recorded in `PROGRESS.md` as `UAT RUNBOOK
APPROVED`). The approval makes this the valid **process basis** only: it is
not authorization to execute UAT. Real-environment execution still requires
a separate explicit authorization for an approved integrated release
candidate, and each connector/real-data action remains individually gated.

## Boundary

Use `codex/ip-000-baseline-safety` or an explicitly approved immutable
release-candidate tag only. Do not merge or rebase it into `main`. All
credentials, endpoints, databases, exports, logs, screenshots, raw payloads,
and real records remain in the approved local environment. Never copy
operational data into the repository or portable artifacts.

## Setup

From `src/`, create an isolated environment and install the product:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -e .
```

For the approved candidate, verify the checked-out commit and version and
record only the commit hash plus version:

```bash
git rev-parse HEAD
pm version
```

Do not begin real-environment UAT from an uncommitted working tree or a commit
whose `make validate` and `make rehearse-release` have not passed. Create a
local `.env` from `.env.example` with approved database and connector values
locally only, then run `pm init`.

Open the repository root in VS Code, open Copilot Chat, and select the
workspace `Delivery Manager` agent. Keep terminal approvals enabled; do not
use global auto-approval or Autopilot for real-environment UAT. In
customization diagnostics, verify that `.github/agents/delivery-manager.agent.md`
and `.github/copilot-instructions.md` are loaded.

## Recovery point

Before any import, migration, or write-capable workflow:

```bash
pm backup create --label before-real-uat
```

Keep the tag and manifest in approved local records. If validation fails, stop
writes and follow `docs/LOCAL_PRODUCT_UPGRADE_LIFECYCLE.md`.

## Clean re-import and upgrade rehearsal

The production data path is a **clean database followed by the versioned
structured full re-import**; it must not depend on migration, backfill, or
preservation of current records. Rehearse on isolated copies only:

```bash
cp /approved/path/from-backup-manifest.db /approved/temp/dm-uat-rehearsal.db
DATABASE_PATH=/approved/temp/dm-uat-rehearsal.db pm init
DATABASE_PATH=/approved/temp/dm-uat-rehearsal.db \
  python3 -m pm_agent.cli.app onboarding profile save \
  --profile-key workforce-uat \
  --source-type workforce-planning-json \
  --file src/sample-data/json/workforce_planning_import.sample.json
DATABASE_PATH=/approved/temp/dm-uat-rehearsal.db \
  python3 -m pm_agent.cli.app onboarding preview --profile-key workforce-uat
DATABASE_PATH=/approved/temp/dm-uat-rehearsal.db \
  python3 -m pm_agent.cli.app onboarding confirm --run-id <onboarding-run-id-from-preview>
```

Repeat the same `profile save → preview → confirm` pattern for resource
capacity (`resource-capacity-json`), Project Health re-import
(`project-health-reimport-json`), and canonical Milestone import
(`milestone-json`), then verify:

```bash
sqlite3 "$DM_UAT_DATABASE_PATH" "PRAGMA integrity_check;"
sqlite3 "$DM_UAT_DATABASE_PATH" "PRAGMA foreign_key_check;"
```

Expected: `integrity_check=ok`, no `foreign_key_check` rows, every import
reports `completed` with an authoritative complete manifest, and replay of the
same package reports `already_completed`/`no_op`. Stop if any import reports
`rejected`, a non-authoritative manifest, changed aggregate counts, or a
failed integrity/foreign-key check. Keep the active database untouched until
the rehearsal passes and the operator explicitly approves the live `pm init`.

For upgrade-compatibility checks on the existing local database, follow the
same isolated-copy rules (copy from the backup manifest, run `pm init` on the
copy, check views `v_member_load`/`v_project_team`, operation tables, token
columns, and aggregate counts before/after).

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

The current structured read-only use cases (see `pm tool list` for the
authoritative set):

```bash
pm tool query team-workload-overview
pm tool query project-health-review
pm tool query management-attention
pm tool query layered-project-health-review
pm tool query delivery-execution-review --project <exact-project-id>
pm tool query delivery-attention-center
pm tool query resource-capacity-heatmap --param year=<YYYY> --param month=<1-12> --param plan_version_id=<exact-plan-id>
pm tool query contract-continuity-review --days 180
pm tool query action-followup
pm tool query connector-status-review
pm tool query connector-sync-results
pm tool query project-snapshot-list --param health=amber --param artifact_kind=plan
pm weekly-brief query
```

For every response, verify evidence/freshness are present, non-fresh and
unavailable states are visible, and no credential, endpoint, raw error, or
source payload appears. Also verify executor enforcement with a deliberately
invalid read-only request:

```bash
pm tool query contract-continuity-review --days 9999
```

It must exit non-zero with `PARAMETER_OUT_OF_RANGE`, without invoking a
connector or returning a raw exception.

## Controlled configuration UAT

Health-condition configuration is a controlled preview/confirm write
(R4 (a)); rehearsal on the isolated copy first:

```bash
pm project-health config show [--project <exact-project-id>]
pm project-health config preview --tolerance-days <0-90> --scope-green-minimum <0-100> [--project <exact-project-id>]
pm project-health config confirm --operation-id <id> --token <token>
```

Verify `show` returns the fixed catalog plus the effective configuration,
`preview` returns prior/proposed/effective and a one-time token (or `no_op`
when unchanged), and `confirm` changes only subsequent assessments and records
the new configuration version. Stop if confirmation succeeds without a token,
rejects a legitimate stale operation, or exposes an unaccepted Attention RAG
configuration path.

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
indication are expected. Stop on unexpected source, target table, or data
volume.

## Staffing UAT

Start with the reversible stages only:

```bash
pm staffing assess --project <id> --start <YYYY-MM> --end <YYYY-MM> --effort <0-1>
pm staffing propose ...
pm staffing preview <proposal-id>
pm staffing cancel <proposal-id> --reason "UAT verification"
```

Use `pm staffing confirm` only after an authorized manager approves that exact
proposal and the runtime token. Verify cancellation/rejection/expiry/changed
facts produce no assignment or allocation write. If UAT must exercise
capacity-aware behavior, check the marker first and enable it on the isolated
copy only:

```bash
pm staffing capacity-policy show
pm staffing capacity-policy enable-preview
pm staffing capacity-policy enable-confirm --operation-id <id> --token <token>
```

The marker installs disabled and is a one-way enable; there is no product
disable command in this candidate. After enabling, proposals/confirmation
become fail-closed against effective capacity, and missing or stale capacity
blocks confirmation. Record the enable decision and audit result.

## Dashboard UAT

Run locally with `pm dashboard serve` (loopback default; non-loopback binding
requires the explicit `--allow-remote` operator option for an approved network
scope). Confirm generic `/api/tool/query/<use-case-id>` responses retain the
full structured contract, and legacy endpoints carry their
interface-classification headers.

For controlled writes through the Dashboard, verify preview performs no
connector call and displays the exact scope, then confirm and verify a replay
of the one-time token is rejected:

- `/api/attention/operations` — attention preview/confirm;
- `/api/weekly-brief/operations` — Weekly Brief v2 snapshot preview/confirm;
- `/api/project-health/sync` — legacy Project Health sync preview/confirm.

Do not use a real sync target merely to test error handling. Browser output
must contain no raw connector error. Project Health configuration and the
capacity-policy marker are CLI-only controlled writes in this candidate.

## Stop conditions

Stop and do not write if data scope is unexpected; an output exposes a
credential, URL, raw error, or payload; freshness is inadequate for a decision;
proposal facts change before confirmation; a controlled preview/confirm token
is reused or rejected unexpectedly; migration/config validation fails; or the
clean re-import is not reproducible with `already_completed`/`no_op` replay.

## Sanitized feedback

Return only: candidate commit, test category, pass/fail/blocked/partial,
generic error category or counts/ranges, impact level, and sanitized requested
change. Never return real names, IDs, URLs, record content, credentials,
screenshots, or raw logs.

## Approval gate

The owner approved this revised runbook on 2026-08-02 (`UAT RUNBOOK APPROVED`
recorded in `PROGRESS.md`). It is the valid process basis; executing UAT
requires a separate explicit owner authorization for the integrated release
candidate before any real-environment action begins.
