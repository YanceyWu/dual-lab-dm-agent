# Local Delivery Manager Runtime

`ai-pm-agent` is a local-first Delivery Manager toolkit. It exposes deterministic
SQLite-backed management use cases through the `pm` CLI and a loopback Dashboard.
VS Code Copilot provides natural-language interpretation through the repository's
`Delivery Manager` custom agent.

## Install

Python 3.10 or newer is required.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -e .
pm version
```

When the package has not been installed, commands can be inspected from this
directory with:

```bash
PYTHONPATH=. python3 -m pm_agent.cli.app --help
```

## Initialize local state

```bash
pm init
pm config validate
pm connector validate --portable
```

`pm init` initializes the configured SQLite database and creates generic starter
configuration when needed. Add operational paths, endpoints, credentials, and
company-specific mappings only to ignored local files.
For a user-oriented guide to safely connect an approved local data copy or
structured local data inputs, see `docs/LOCAL_DATA_ONBOARDING_GUIDE.md`.

For a synthetic first run:

```bash
python3 scripts/load_sample_data.py --force
DATABASE_PATH=sample-data/demo/sample_pm.db pm tool list
DATABASE_PATH=sample-data/demo/sample_pm.db pm tool query team-workload-overview
```

The demo database and fixtures use fictional names, `.invalid` domains, and
reserved synthetic identifiers.

## Structured data onboarding

Use saved source profiles plus preview/confirm when onboarding approved local
structured data sources:

```bash
pm onboarding profile save --profile-key fy26-q4 --source-type workbook --file /approved/path/team-project-capacity.xlsx
pm onboarding profile show --profile-key fy26-q4
pm onboarding preview --profile-key fy26-q4
pm onboarding confirm --run-id <onboarding-run-id>
pm onboarding run show --run-id <onboarding-run-id>
```

Batch A registers Team/Project + Capacity workbook onboarding as the first
shared source type. The existing source-specific workbook script remains
available as a transitional fallback while other sources converge on the same
framework.

## Structured read-only interface

These commands are the authoritative interface for Copilot and other automated
consumers:

```bash
pm tool list
pm tool describe <use-case-id>
pm tool query <use-case-id>
```

Registered use cases cover:

- `resource-capacity-heatmap`
- `layered-project-health-review`
- `delivery-execution-review`
- `team-workload-overview`
- `project-health-review`
- `management-attention`
- `delivery-attention-center`
- `contract-continuity-review`
- `weekly-dm-brief`
- `weekly-dm-brief-v2`
- `action-followup`
- `connector-status-review`
- `connector-sync-results`
- `project-snapshot-list`

This list mirrors the shared use-case registry in
`src/pm_agent/use_cases/__init__.py`. `weekly-dm-brief-v2` remains available
through that registry, but operators normally access it through
`pm weekly-brief query` so the snapshot preview/confirm flow stays in one
command family.

`pm tool query` returns structured JSON with evidence, freshness, warnings,
assumptions, execution metadata, and stable error codes. Missing or stale data
must not be interpreted as zero, healthy, available, or safe.

## Staffing workflow

Start with deterministic read-only assessment:

```bash
pm staffing assess \
  --project <project-id> \
  --start <YYYY-MM> \
  --end <YYYY-MM> \
  --effort <0-1> \
  --maximum-people <count>
```

Role is optional reference context rather than a hard eligibility constraint.
For STFTE staff, a recorded HIREF number indicates usable charge-code coverage
only for its recorded project and date interval.

Writes use:

```text
assess → propose → preview → explicit manager confirmation → persist
```

Never confirm without reviewing the exact proposal and runtime-issued one-time
token. Do not invent freshness overrides or HIREF acknowledgements. `cancel` and
`reject` close unconfirmed proposals without changing assignments.

## Controlled configuration and marker entry

```bash
pm project-health config show
pm project-health config preview --tolerance-days <0-90> --scope-green-minimum <0-100>
pm project-health config confirm --operation-id <id> --token <token>

pm staffing capacity-policy show
pm staffing capacity-policy enable-preview
pm staffing capacity-policy enable-confirm --operation-id <id> --token <token>
```

Project Health configuration and the capacity-policy marker use explicit
preview/confirm flows with one-time tokens and audit records. The staffing
capacity-policy entry is intentionally one-way in this candidate: it installs
disabled and exposes no product disable command.

## Connector boundary

Offline inspection:

```bash
pm connector validate --portable
pm sync status
pm tool query connector-status-review
pm tool query connector-sync-results
```

Use `pm connector probe <jira|confluence|servicenow>` only for an explicitly
requested live check with approved local configuration. OAuth refresh is
automatic; safe results may report that refresh occurred but never expose
tokens, endpoints, local paths, cloud IDs, or raw errors.

## Dashboard

```bash
pm dashboard serve
```

The Dashboard binds to loopback by default. Remote binding requires the explicit
operator option and an approved network scope. Write-capable routes use preview,
explicit confirmation, one-time tokens, idempotency, and audit records.
For a human-oriented walkthrough of each left navigation item, where the
Dashboard data comes from, how to prepare data, and the usual Delivery Manager
next step, see
`docs/DASHBOARD_USAGE_GUIDE.md`.

## Existing operational database

Do not run a new candidate against the active database first.

1. Create a local recovery point with `pm backup create`.
2. Copy the snapshot to an approved temporary location outside the repository.
3. Point `DATABASE_PATH` at the copy and run `pm init`.
4. Verify integrity, foreign keys, dependent views, token schema, and aggregate
   counts.
5. Approve the active-database migration only after the rehearsal passes.

The source checkout's `docs/REAL_ENVIRONMENT_UAT_RUNBOOK.md` contains the exact
commands and stop conditions.

## Contributor validation

From the repository root:

```bash
python3 -m venv src/.venv
src/.venv/bin/python -m pip install --upgrade pip
src/.venv/bin/python -m pip install -r tools/validation-requirements.txt
src/.venv/bin/python -m pip install -e src
make validate
make rehearse-release
```

`make validate` runs isolated tests, repository checks, Ruff, compilation, and
package inspection. `make rehearse-release` builds and installs the wheel in a
temporary target, rehearses a synthetic legacy-database upgrade, and proves
rollback.

## Package layout

```text
pm_agent/
  cli/          CLI composition and command modules
  use_cases/    Structured execution contracts and management capabilities
  rules/        Deterministic staffing, HIREF, identity, and validation rules
  database/     SQLite bootstrap, migration, repositories, and decision log
  connectors/   Generic connector contracts and locally configured adapters
  sync/         Connector synchronization workflows
  dashboard/    Local API, controlled writes, and packaged web assets
  repo_tools/   Bootstrap, configuration, and backup helpers
scripts/        Import, sample-data, report, bootstrap, and optional sync entrypoints
sample-data/    Synthetic onboarding fixtures and demo database
tests/          Isolated portable regression suite
```

## Information boundary

Never add real records, employee or project names, internal identifiers,
endpoints, credentials, database copies, raw exports, logs, screenshots, or
connector payloads to the portable repository. Keep company adaptations and
real-environment evidence inside the approved work environment.
