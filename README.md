# Local Delivery Manager

This repository contains a portable, local-first Delivery Manager decision
support system. VS Code Copilot is the reasoning interface; deterministic Python
code owns data access, filtering, calculations, validation, freshness, and
persistence. SQLite and locally configured connectors provide operational
context.

The repository contains no company records, credentials, internal endpoints, or
company-specific configuration. Those values must remain only on the approved
work computer.

## What the product supports

- team workload and capacity review;
- staffing assessment and controlled staffing proposals;
- legacy project health, layered seven-dimension Project Health, delivery
  execution, and management-attention review;
- persisted Delivery Attention Center review;
- resource-capacity heatmap and project-capacity evidence publication;
- STFTE HIREF/charge-code continuity review;
- weekly Delivery Manager briefs (legacy v1 and opt-in v2) and action follow-up;
- connector status, sync-result, and project-snapshot review;
- controlled Project Health configuration preview/confirm and capacity-policy
  marker state/enable entry;
- a local Dashboard and structured CLI;
- evidence, freshness, warnings, execution traces, and deterministic validation.

## Start on the work computer

Use the independent `codex/ip-000-baseline-safety` branch or an explicitly
approved immutable release-candidate tag. Do not merge or rebase it into `main`.

### 1. Install locally

```bash
cd src
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -e .
pm version
```

### 2. Create local configuration

```bash
pm init
pm config validate
pm connector validate --portable
```

`pm init` creates generic starter configuration when needed. Add approved
database paths, endpoints, and credentials only to local ignored files. Never
commit or copy those values back to this repository.

Real-environment UAT is deferred during Delivery Intelligence capability
iteration. Do not point an iteration branch at an operational database. The
retained `docs/REAL_ENVIRONMENT_UAT_RUNBOOK.md` is safety reference and must be
revised and explicitly approved against the integrated candidate before use.

### 3. Use natural language in VS Code Copilot

Open the repository root in VS Code, open Copilot Chat, and select the workspace
agent named `Delivery Manager`. In customization diagnostics, confirm these are
loaded:

- `.github/agents/delivery-manager.agent.md`
- `.github/copilot-instructions.md`

You can then ask questions such as:

- “下个月哪些同事还有容量？”
- “项目 Atlas 当前有哪些需要管理层关注的问题？”
- “未来 90 天有哪些 STFTE 的 HIREF 需要处理？”
- “为这个项目评估 0.6 FTE 的人员安排。”
- “生成本周 DM brief。”

The agent maps the question to approved structured `pm` commands. Read-only
queries may run directly. Staffing writes follow
`assess → propose → preview → explicit confirmation → persist`; the agent must
not invent confirmation or override missing/freshness/HIREF decisions.

Keep terminal approval enabled during real-environment UAT. Do not use global
auto-approval or unrestricted Autopilot against operational data.

## Direct CLI

Useful structured commands include:

```bash
pm tool list
pm tool describe team-workload-overview
pm tool query team-workload-overview
pm tool query project-health-review
pm tool query layered-project-health-review
pm tool query delivery-execution-review --project <exact-project-id>
pm tool query management-attention --limit 10
pm tool query delivery-attention-center
pm tool query resource-capacity-heatmap --param year=<YYYY> --param month=<1-12> --param plan_version_id=<exact-plan-id>
pm tool query contract-continuity-review --days 180
pm tool query weekly-dm-brief
pm weekly-brief query
pm tool query action-followup
pm tool query connector-status-review
pm tool query connector-sync-results
pm tool query project-snapshot-list
pm project-health config show
pm staffing capacity-policy show
pm onboarding preset list
pm onboarding preset show --mapping-preset team-project-capacity-workbook-v1
pm onboarding profile save --profile-key fy26-q4 --source-type workbook --mapping-preset team-project-capacity-workbook-v1 --file /approved/path/team-project-capacity.xlsx
pm onboarding profile save --profile-key workforce-json --source-type workforce-planning-json --file /approved/path/workforce_planning.json
pm onboarding profile save --profile-key capacity-json --source-type resource-capacity-json --file /approved/path/resource_capacity.json
pm onboarding profile save --profile-key milestone-json --source-type milestone-json --file /approved/path/milestones.json
pm onboarding profile save --profile-key health-json --source-type project-health-reimport-json --file /approved/path/project_health_reimport.json
pm onboarding profile save --profile-key jira-registry --source-type jira-board-registry-csv --file /approved/path/jira_board_configs.csv
pm onboarding profile save --profile-key confluence-registry --source-type confluence-page-registry-csv --file /approved/path/confluence_pages.csv
pm onboarding preview --profile-key fy26-q4
pm onboarding confirm --run-id <onboarding-run-id>
pm onboarding run show --run-id <onboarding-run-id>
```

Run `pm staffing assess --help` before a staffing assessment. Use
`pm connector probe <connector-name>` only for an explicitly requested live
connector check. `pm onboarding` is now the supported profile-based entrypoint
for the retained workbook plus workforce-planning, resource-capacity,
milestone, Project Health re-import, JIRA board registry CSV, and Confluence
page registry CSV file sources. The legacy source-specific import scripts
remain available only as transitional compatibility / fallback entrypoints
while later convergence slices close the remaining operator-path gaps.

The complete package command and configuration guide is in `src/README.md`.

## Release and validation

From the repository root:

```bash
make validate
make rehearse-release
```

The first command runs portable source, tests, Ruff, compilation, repository
boundary, synthetic-data, and package checks. The second installs the built
wheel into a temporary target and rehearses database upgrade and rollback using
synthetic data.

To assemble **end-user DM usage bundles** for offline local distribution, run:

```bash
python3 -m pip install -r tools/validation-requirements.txt
make build-usage-bundles
```

That command generates separate **macOS** and **Windows** usage bundles under
`dist/dm-usage-bundles/`. The build requires the pinned release-tool
dependencies above, and each generated bundle is target-specific to its
configured Python/architecture. Each bundle contains:

- a trimmed workspace with `.github/agents/delivery-manager.agent.md` and
  `.github/copilot-instructions.md`;
- `src/` runtime sources and starter config templates only;
- a platform-specific offline `wheelhouse/`;
- one-click install/open scripts for VS Code + Copilot entry.

The generated bundles are local artifacts for distribution and must not be
committed back to the repository.

## Demo data

The committed `src/sample-data/demo/sample_pm.db` is rebuilt by one command from
a clean database and exercises every promoted capability (Project Health
seven-dimension assessment, Execution/Milestone review, Delivery Attention
Center, Resource Capacity heatmap, Weekly Brief v2):

```bash
PYTHONPATH=src src/.venv/bin/python src/scripts/load_sample_data.py --force
PYTHONPATH=src src/.venv/bin/python src/scripts/load_sample_data.py --replay  # idempotent re-run
```

See `src/sample-data/README.md` for the full command sequence and the five
verification commands with expected non-empty results.

Read:

- `PROGRESS.md` for the exact current state and next action;
- `docs/DEVELOPER_ONBOARDING_INDEX.md` to take over development quickly with a
  new model or a new session;
- `docs/REAL_ENVIRONMENT_UAT_RUNBOOK.md` before real-data validation;
- `docs/RELEASE_ENGINEERING.md` before tagging or promotion;
- `docs/DUAL_LAB_OPERATING_MODEL.md` for the information boundary;
- `architecture/04_COPILOT_LOCAL_AGENT_ARCHITECTURE.md` for the product design;
- `architecture/05_DELIVERY_INTELLIGENCE_EVOLUTION_PLAN.md` for the approved
  phase sequence, gates, and cross-session continuation model;
- `architecture/06_PHASE_1_INTELLIGENCE_OUTPUT_CONTRACT_DESIGN.md` for the
  approved Phase 1 implementation boundary and batch sequence;
- `architecture/07_PHASE_2_DELIVERY_ATTENTION_CENTER_DESIGN.md` for the
  promoted Attention Center contract;
- `architecture/08_LAYERED_PROJECT_HEALTH_AND_MILESTONE_EVOLUTION.md` for the
  approved layered health, milestone, and bounded DM configuration direction;
- `architecture/09_PHASE_3_EXECUTION_AND_MILESTONE_FOUNDATION_DESIGN.md` for
  the approved Phase 3 current-state findings and implementation boundary.
- `architecture/11_PHASE_4_SEVEN_DIMENSION_PROJECT_HEALTH_DESIGN.md` for the
  approved Phase 4 bounded Project Health design and later decision records
  (current state still lives in `PROGRESS.md`).

## Safety boundary

Never commit company source, real records, employee or project names, internal
IDs, endpoints, credentials, database copies, exports, logs, screenshots, or raw
connector payloads. Use synthetic data and stable anonymous identifiers in
portable tests and documentation. Any feedback leaving the work environment
must be manually sanitized and permitted by company policy.
