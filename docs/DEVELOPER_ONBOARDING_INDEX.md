# Developer Onboarding Index

适用对象：任何接手本仓库开发/测试的新模型或新会话（模型无关）。
This index is model-agnostic: any capable coding model can use it to take over
development and testing quickly. It points to the authoritative files instead
of duplicating their content. When anything conflicts, `PROGRESS.md` wins.

## 5-minute start order

1. `AGENTS.md` — repository rules, boundaries, module guardrails, completion
   report format.
2. `PROGRESS.md` — the single current-state authority: branch, HEAD, gate,
   validation evidence, decisions in force, exact next action.
3. `implementation-packs/INDEX.md` — historical pack index (statuses point to
   `PROGRESS.md`).
4. `docs/USABILITY_REQUIREMENTS_HANDOFF_2026-08-02.md` — completed R1–R7
   requirements and acceptance criteria.
5. `docs/COPILOT_5_4_PROGRAM_CONTEXT.md` + `docs/COPILOT_5_4_CONTINUATION_KIT.md`
   — whole-program orientation (written for Copilot 5.4, model-agnostic in
   content).
6. `docs/SYNTHETIC_DEMO_WALKTHROUGH.md` — the executable demo workflow.
7. This file — repository map, commands, data paths, gates, conventions,
   boundaries, and the first-session checklist.

## Current state snapshot (always re-verify from PROGRESS.md)

- Branch `codex/usability-r1-r2`; local HEAD includes the accepted
  rehearse-release remediation commit `3cb4d33` plus the current unpushed Batch
  3 slice (exact new hash is reported in the task handoff after commit).
- `origin/codex/usability-r1-r2` remains at `998ed37`; later local commits and
  working-tree records are not pushed.
- Usability R1–R7: implemented, validated, owner-confirmed, and pushed.
- IP-033 (Phase 4 assessment entry): owner-accepted 2026-08-02 as a local
  development-baseline fix.
- UAT runbook: owner-approved 2026-08-02 as process basis only; execution still
  requires a separate explicit authorization for an integrated release
  candidate.
- Latest owner-approved repository-convergence batch: **Batch 2 — module
  boundary hardening design**.
- Batch 2 slice 1 (**Phase 3 schema extraction from `database/bootstrap.py`**)
  is treated as owner-accepted.
- Batch 2 slice 2 (**`database/execution.py` owner split**) is also now treated
  as owner-accepted.
- `make rehearse-release` blocker remediation is owner-accepted and committed
  locally as `3cb4d33` (`Restore release rehearsal flow`).
- Active follow-on: **Batch 3 — promoted-capability closure**. Slice 1 wires
  explicit Project Health `capacity_scope` through the promoted IP-033 re-
  import entry so the resource dimension can use the promoted capacity-coverage
  reader instead of always publishing `not_available`.
- The next gate is owner review / acceptance of this Batch 3 slice. The
  remaining recommended `dashboard/server.py` split and Phase 7 still need
  separate authorization after that gate.

## Repository map (module ownership)

| Area | Owner / role | Key files |
| --- | --- | --- |
| Read-only use cases + intelligence contract | `src/pm_agent/use_cases/` | `__init__.py` (registry), `execution.py` (executor + contract validation), `service.py` (UseCaseResult) |
| Presentation (CLI) | `src/pm_agent/cli/` | `app.py` (wiring), `commands/*` (JSON preview/confirm groups) |
| Bootstrap / composition boundary | `src/pm_agent/database/bootstrap.py` | composes dedicated schema modules; do NOT add tables here |
| Phase 3 canonical schema | `src/pm_agent/database/execution_schema.py` | owns canonical Phase 3 DDL only; imported by bootstrap |
| Phase 3 execution facts | `src/pm_agent/database/execution.py`, `execution_derivation.py`, `execution_milestones.py`, `execution_common.py`, `execution_review.py` | facade + dedicated owners for derivation, milestone operations, and shared helpers |
| Attention | `src/pm_agent/attention/` + `database/attention.py` | rules, service, preview/confirm operations |
| Project Health | `src/pm_agent/project_health/` | catalog, configuration (preview/confirm), evaluation, service (IP-033 re-import) |
| Resource Intelligence | `src/pm_agent/resource_intelligence/` | capacity import, read model (heatmap, coverage) |
| Workforce planning import | `src/pm_agent/workforce_planning_import/` | versioned clean import |
| Weekly Brief v2 | `src/pm_agent/weekly_brief/` | composer, snapshots, operations |
| Staffing + capacity marker | `src/pm_agent/use_cases/staffing.py`, `database/staffing_capacity.py` | feasibility/proposals; one-way enable policy |
| Import/demo scripts | `src/scripts/` | `load_sample_data.py` (orchestrator), `seed_demo_evidence.py`, `import_*.py` |
| Validation tooling | `tools/` | `validate_release.py`, `rehearse_release.py`, `check_synthetic_samples.py`, `check_documented_use_cases.py` |
| Tests | `src/tests/` | focused suites per capability; `conftest.py` isolates DB/network |

Dependency rule: a module may depend inward on a capability contract, never
sideways into another capability's storage internals.

## Command cheat-sheet

```bash
# full portable validation (tests, Ruff, compile, boundary, synthetic, build)
make validate

# release rehearsal (install wheel, isolated upgrade/rollback) — required when
# schema/import/packaging changes
make rehearse-release

# focused tests
PYTHONPATH=src src/.venv/bin/python -m pytest src/tests/test_<suite>.py -q

# synthetic sample checker
python3 tools/check_synthetic_samples.py

# demo database: build / idempotent replay
PYTHONPATH=src src/.venv/bin/python src/scripts/load_sample_data.py --force
PYTHONPATH=src src/.venv/bin/python src/scripts/load_sample_data.py --replay

# five capability verification commands (demo DB; run on a copy to avoid
# writing execution traces into the committed database)
export DATABASE_PATH=/tmp/demo-copy.db PYTHONPATH="$PWD/src"
src/.venv/bin/python -m pm_agent.cli.app tool query layered-project-health-review --project project-synthetic-atlas
src/.venv/bin/python -m pm_agent.cli.app tool query delivery-execution-review --project project-synthetic-atlas
src/.venv/bin/python -m pm_agent.cli.app tool query delivery-attention-center
src/.venv/bin/python -m pm_agent.cli.app tool query resource-capacity-heatmap --param year=2026 --param month=8 --param plan_version_id=plan-synthetic-baseline-001
src/.venv/bin/python -m pm_agent.cli.app weekly-brief query

# controlled writes (R4)
src/.venv/bin/python -m pm_agent.cli.app project-health config show|preview|confirm
src/.venv/bin/python -m pm_agent.cli.app staffing capacity-policy show|enable-preview|enable-confirm
```

Important: read-only `tool query` / `weekly-brief query` calls write execution
traces into the database. For verification of the committed demo DB, copy it
first (`cp src/sample-data/demo/sample_pm.db /tmp/demo-copy.db`) and point
`DATABASE_PATH` at the copy.

## Data-path map

Production clean re-import (empty database):

`bootstrap` → workforce planning import → resource capacity import → board
registration → synthetic evidence seed → canonical Milestone import →
Project Health re-import (IP-033: derive + seven-dimension assessment) →
Delivery Attention reconciliation → Weekly Brief v2 snapshot.

`src/scripts/load_sample_data.py` orchestrates exactly this chain (`--force`
rebuild, `--replay` idempotent). The demo uses the versioned structured
organization (`member-synthetic-001/002/003`, `project-synthetic-atlas` /
`-beacon`, `plan-synthetic-baseline-001`), not the legacy Excel organization.
Legacy `assignments` mirror canonical allocations so the legacy load view and
canonical capacity agree. HIREF demo states live in `employees`
(`resource_type`/`current_hiref`/`next_hiref`) + `hiref` +
`staffing_placeholders`.

## Gates and decisions in force (summary; PROGRESS.md is authoritative)

- No push/merge/tag/release without explicit owner authorization; use
  independent `codex/` branches; never merge into `main`.
- All writes follow propose → preview → confirm → persist.
- After every batch: focused tests + `make validate` (+ `make rehearse-release`
  when schema/import/packaging changes) + independent read-only review +
  `PROGRESS.md` update + local commit; stop for owner review.
- Synthetic-only, stable anonymous IDs, `SYNTHETIC_DATASET_V1`; never real
  data, credentials, connectors, or internal identifiers.
- Missing/conflicting evidence is `UNKNOWN`, never zero/healthy.
- The unaccepted Attention RAG mapping configuration surface must never be
  exposed or invoked.
- Capacity-aware Staffing marker installs disabled and is one-way (no product
  disable command).
- UAT runbook approved as process basis; real-environment execution requires
  a separate future authorization.

## Known boundaries and UNKNOWN areas

- Quality/Governance structured inputs: reserved, no producer → dimensions
  stay `not_available`.
- Delivery dimension: no `sprint_completion`/`sprint_carry_over` producer →
  `not_available`.
- Resource dimension via the IP-033 entry is only available when the re-import
  package carries an explicit `capacity_scope`; otherwise it intentionally
  remains `not_available`.
- Dependency factor: proves an active link only → `unknown` semantics.
- `schedule_target_change` can be `unknown` or `amber`, never `green`.
- Weekly Brief achievements appear only for events after the baseline
  snapshot date; snapshot-day queries show empty achievements.
- Re-previewing a pre-snapshot brief candidate after the first snapshot is
  rejected as stale (recomposition includes the new baseline).
- Each `--replay` creates one expiring Attention preview audit row.
- Remote CI status on the pushed branch is UNKNOWN until observed.
- Real connectors, real data, live migration, and UAT execution: excluded;
  separately gated.

## First-session checklist

1. `git status --short --branch` and `git log --oneline -5`; note HEAD.
2. Read `AGENTS.md`, then `PROGRESS.md` (top + recent change log + decisions).
3. Run `make validate` once to confirm the checkout is green.
4. Build a demo copy and run the five verification commands (see cheat-sheet).
5. Read `docs/SYNTHETIC_DEMO_WALKTHROUGH.md` end-to-end.
6. Identify the current gate and the owner's named next batch; do not start a
   batch without a named authorization.
7. If a task is ambiguous, ask the owner; never assume authorization from
   roadmap context.

## Copy-ready first-session prompt

```text
你是本仓库（/Users/yanceywu/Documents/AI DM Workspace）的开发与测试接手者。
先读 AGENTS.md、PROGRESS.md、docs/DEVELOPER_ONBOARDING_INDEX.md、
docs/USABILITY_REQUIREMENTS_HANDOFF_2026-08-02.md，并检查 Git 状态
（分支/HEAD/工作区）。然后运行 make validate 确认基线绿色，并用副本构建
演示库、跑通五条能力验证命令。

任务：在不再新增业务功能、不接触真实数据/connector、不推送/合入 main/
不打 tag 的前提下，按 owner 明确授权的有界批次推进开发与测试。每批开始前
复述需求与验收指标；只做该批次；完成后跑聚焦测试与 make validate（涉及
schema/导入/打包时加 make rehearse-release），做独立只读复核，更新
PROGRESS.md（变更、验证证据、未解决风险、确切下一步、提交状态），本地
提交，停止等待 owner 审查。任何写入遵循 propose → preview → confirm →
persist。最终汇报按 AGENTS.md 的强制完成报告格式。
```
