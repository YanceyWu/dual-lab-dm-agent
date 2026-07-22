# PM Toolkit Starter Repo

This repo is a practical **local-first Delivery Manager toolkit baseline** that
each DM can clone, configure, run, and extend on their own workstation.

## What this starter repo already does

- Resource allocation and capacity planning
- Weekly project status reporting
- HIREF / staffing tracking
- Project snapshot and planning artifact management
- JIRA release tracking and project health scoring
- Use case registry and sync freshness tracking

## Quick start

### 1. Install

Use Python 3.10+.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -e .
```

After the editable install, the primary CLI is available as:

```bash
pm --help
```

If you do not want an editable install yet, you can still run commands with:

```bash
python3 -m pm_agent.cli.app --help
```

### 2. Bootstrap the local starter repo

```bash
pm init
```

This will:

- scaffold `.env` from `.env.example` if needed
- ensure starter config files exist under `configs/`
- initialize the SQLite database safely

### 2.5 Load the committed demo data (recommended for first-time review)

```bash
python3 scripts/load_sample_data.py --force
```

This creates a separate demo DB under `sample-data/demo/sample_pm.db` so you can review the toolkit without touching your live `data/pm.db`.

Use it like this:

```bash
DATABASE_PATH=sample-data/demo/sample_pm.db pm workload
DATABASE_PATH=sample-data/demo/sample_pm.db pm hiref summary
DATABASE_PATH=sample-data/demo/sample_pm.db pm report
DATABASE_PATH=sample-data/demo/sample_pm.db python3 -m pm_agent.dashboard
```

For the full source-file map and DB cleanup notes, see:

- `docs/README.md`
- `docs/current/PM_AGENT_DB_REVIEW_AND_ONBOARDING.md`

### 3. Update local settings

- Fill in local connector endpoints and credentials in `.env`; no company
  endpoint is pre-filled.
- Keep company configuration local and outside the portable repository.
- Copy and adapt:
  - `configs/teams/example-team.yaml`
  - `configs/projects/example-project.yaml`

### 4. Validate

```bash
pm config validate
pm connector validate
pm validate
```

### 5. Launch the local dashboard

```bash
pm dashboard serve
```

You can also start it directly with:

```bash
python3 -m pm_agent.dashboard
```

## Config model

Practical v1 uses four layers:

1. generic code defaults
2. optional local company baseline
3. local team and project configuration
4. local `.env` secrets and runtime overrides

Useful commands:

```bash
pm config show
pm config effective
pm config validate
pm connector list
pm connector validate
pm connector status
```

## Common commands

```bash
pm workload
pm tool list
pm tool describe team-workload-overview
pm tool query team-workload-overview
pm tool query project-health-review --project project-atlas-990001
pm tool query management-attention --limit 10
pm tool query contract-continuity-review --days 180
pm tool query weekly-dm-brief
pm tool query action-followup
pm tool query connector-status-review --connector jira
pm staffing assess --project project-atlas-990001 --start 2026-08 --end 2026-08 --effort 0.6 --skills python --maximum-people 2
pm capacity --month aug
pm hiref summary
pm project list
pm report
pm usecase list
pm sync status
pm planning list
pm backup create --label before-change
```

## Repository layout

```text
pm_agent/            Canonical runtime package
  use_cases/         PM-facing features such as allocate, workload, report, action items
  rules/             Shared business logic: scoring, validation, identifier cleanup
  database/          Database bootstrap plus all SQLite reads and writes
  repo_tools/        Local repo setup, effective config, and backup helpers
  cli/               Typer CLI wiring and command modules
  connectors/        Per-system entrypoints and self-checks
  dashboard/         Packaged Flask dashboard API + web assets
  sync/              Low-level sync/import implementations for JIRA and ServiceNow
scripts/             Thin wrappers plus import/migration/admin entry points
configs/             Shared company/team/project starter config
docs/                Current docs, share packs, history, and diagrams
  current/           Authoritative starter-repo docs and current schema
  share/             PM sharing artifacts and Confluence-ready material
  history/           Older reference packs kept for migration/redesign context
  diagrams/          Draw.io and markdown diagram sources
data/                Local SQLite database (ignored by git)
data-feed/           Imported raw files (ignored by git)
sample-data/         Committed onboarding samples and demo DB workspace
```

## Optional runtime tools

Some connector workflows require extra local setup beyond the core package:

- Playwright for browser-assisted ServiceNow sync flows
- Local Atlassian OAuth or API-token credentials for JIRA / Confluence
- Repo-local Atlassian token cache under `.auth/atlassian/` (with compatibility fallback from older skill folders)

The core PM workflows remain local-first and SQLite-backed.

## Contributor validation

If you are modifying the starter repo itself, install a repo-local venv and run the regression checks:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e . pytest ruff
.venv/bin/python -m pytest -q
python3 -m py_compile $(find pm_agent scripts tests -name '*.py')

# Optional incremental lint for the files you touched
.venv/bin/python -m ruff check <files-you-touched>
```

## Documentation map

If you want to understand or reuse this starter repo, start here:

- `docs/README.md`
- `docs/current/PM_AGENT_DB_REVIEW_AND_ONBOARDING.md`
- `docs/current/PM_AGENT_CURRENT_SCHEMA.sql`
- `docs/current/PM_AGENT_UAT_RESULTS_2026-07-13.md`
- `docs/current/PM_AGENT_UAT_RETEST_2026-07-13_ALLOCATE_WEEKLY.md`
- `docs/share/PM_AGENT_CONFLUENCE_ONE_PAGER.txt`
- `docs/history/v17/PM_AGENT_V17_TABLE_FUNCTION_REFERENCE.md`
