# 合成集成演练手册（从零到每周简报）

本文档是 R2 的交付物：用仓库内已提交的合成数据，从干净数据库完整走一遍
Delivery Manager 典型周工作流。所有数据均为 `SYNTHETIC_DATASET_V1`
标记的合成组织（`member-synthetic-001/002`、`project-synthetic-atlas`、
`plan-synthetic-baseline-001`）；不接触真实数据、凭据、connector 或任何外部环境。

本手册与 `src/sample-data/README.md` 配套：前者讲"怎么做"，后者讲"数据是什么"。
当前状态以 `PROGRESS.md` 为准。

## 0. 前置条件

- 当前 checkout：`codex/usability-r1-r2`（R1 已合并到该分支的本地提交）。
- Python 3.10 或 3.12；仓库 `src/.venv` 已按 `README.md` 安装。
- 所有命令在仓库根目录执行；用 `$REPO` 表示仓库根路径。

```bash
cd "$REPO"
git status --short --branch          # 预期：在 codex/usability-r1-r2
python3 --version
src/.venv/bin/python --version
```

## 1. 一键构建演示库

```bash
PYTHONPATH=src src/.venv/bin/python src/scripts/load_sample_data.py --force
```

该命令从**空库**依次执行（每步都是既有导入/派生入口，无新增业务能力）：

1. `bootstrap`（`scripts/init_db.py`）——建全部表；
2. workforce planning 版本化导入
   （`scripts/import_workforce_planning.py --confirm`）——预期输出
   `"status": "completed"`，`employees: 2, projects: 1, monthly_allocations: 2`；
3. resource capacity 版本化导入
   （`scripts/import_resource_capacity.py --confirm`）——预期
   `"derivations": 2, "observations": 6`，`derivation_states.known: 2`；
4. board 注册（`scripts/import_jira_boards.py`）——`Loaded 1 JIRA board rows`，
   board `atlas-board` 映射到 `project-synthetic-atlas`（IP-033 入口的数据前提）；
5. Project Health re-import（`scripts/import_project_health.py --confirm`，
   IP-033 入口）——预期 `"assessment_state": "completed"`，
   `assessments[0].project_id == "project-synthetic-atlas"`；
6. Milestone 版本化导入（`scripts/import_milestones.py --confirm`）——预期
   `"milestone_count": 4`；
7. 派生重放（既有 `execution.derive_board` API，指纹幂等）——预期
   `Derivation replay: atlas-board -> derived ... facts 4`，把 Milestone 事实
   暴露给执行评审与 Attention 规则（IP-033 评估本身按交接顺序在 Milestone 之前，
   因此 schedule 维度为 `unknown`，见"已知限制"）；
8. Attention 对账（preview → confirm）——预期
   `Attention reconciliation confirmed: success`；
9. Weekly Brief v2 快照（compose → preview → confirm）——预期
   `Weekly Brief v2 snapshot: confirmed`。

结尾输出 `Demo DB ready: .../src/sample-data/demo/sample_pm.db` 即成功。

### 排查提示

- `Demo DB already exists`：改用 `--force`（重建）或 `--replay`（幂等重跑）；
- 任何一步失败都会在 `Running: ...` 行后带出 traceback，且命令以非零码退出；
  先修复输入文件或环境（尤其 `PYTHONPATH=src`、`DATABASE_PATH`）再重跑；
- 若 `load_sample_data.py` 找不到模块：确认在仓库根目录执行且带
  `PYTHONPATH=src`；
- 若希望把库建到别处：`--db /path/to/demo.db`（R1 之后所有子步骤都尊重该路径）。

## 2. 验证五种已提升能力（R1 验收命令）

先导出环境变量：

```bash
export DATABASE_PATH="$REPO/src/sample-data/demo/sample_pm.db"
export PYTHONPATH="$REPO/src"
PY=src/.venv/bin/python
```

### 2.1 七维 Project Health

```bash
$PY -m pm_agent.cli.app tool query layered-project-health-review --project project-synthetic-atlas
```

预期：`status: success`；`data.assessments` 非空，且
`assessments[0]` 含 7 个维度
（schedule/delivery/scope/quality/resource/dependency/governance；
本演示中 schedule/dependency/scope 为 `unknown`，其余为 `not_available`）。
整体 `state: unknown` 是诚实的不确定状态，不是缺失数据。

### 2.2 执行评审（Milestone）

```bash
$PY -m pm_agent.cli.app tool query delivery-execution-review --project project-synthetic-atlas
```

预期：`status: success`；`data.release_milestone` 有 4 条 Milestone 事实
（`milestone-atlas-001` 为 `overdue`，`milestone-atlas-002/004` 为
`on_track`，`milestone-atlas-003` 为 `achieved_on_time`）；`signals` 含
`milestone_schedule_exception`。

### 2.3 Delivery Attention Center

```bash
$PY -m pm_agent.cli.app tool query delivery-attention-center
```

预期：`status: success`；`data.items` 非空（2 条
`source_freshness_attention`：`confluence-status-batch` 与
`jira-health-atlas-board` 因无同步记录而 `unknown`）；
`data.reconciliation_coverage.status` 为 `partial`（演示数据没有权威来源，
`partial` 不代表健康）。

### 2.4 Resource Capacity 热图

```bash
$PY -m pm_agent.cli.app tool query resource-capacity-heatmap \
  --param year=2026 --param month=8 \
  --param plan_version_id=plan-synthetic-baseline-001
```

预期：`status: success`；`data.rows` 有 2 行（member-synthetic-001/002），
每行 `state: known`，`effective_capacity` 分别为 0.7 与 0.9
（002 为显式零分配，仍产生已知事实）。

### 2.5 Weekly Brief v2 查询

```bash
$PY -m pm_agent.cli.app weekly-brief query
```

预期：`status: success`；`data.summary.project_count == 1`；
`data.sections.overall_health.availability` 为 `partial`；
`highest_attention_signals.items` 非空；输出含
`snapshot.capture_candidate`（下一步快照用）。

## 3. Weekly Brief v2 快照 preview/confirm（手动演示）

流水线已在构建时自动确认一张快照。下面用手动流程演示同一受控写入边界：

```bash
$PY -m pm_agent.cli.app weekly-brief query \
  > /tmp/demo-brief.json
$PY - <<'EOF'
import json
with open('/tmp/demo-brief.json', encoding='utf-8') as handle:
    payload = json.load(handle)
print(json.dumps(payload["data"]["snapshot"]["capture_candidate"], ensure_ascii=False))
EOF
```

将上一步输出的 JSON 原样作为 `--candidate-json` 传入：

```bash
CANDIDATE=$(python3 -c "import json;print(json.dumps(json.load(open('/tmp/demo-brief.json'))['data']['snapshot']['capture_candidate']))")
$PY -m pm_agent.cli.app weekly-brief snapshot-preview \
  --candidate-json "$CANDIDATE" \
  --idempotency-key demo-brief-manual-001
```

预期：`{"status": "previewed", "confirmation_token": "...", ...}`。把返回的
`operation_id` 与 `confirmation_token` 填入：

```bash
$PY -m pm_agent.cli.app weekly-brief snapshot-confirm \
  --operation-id "<operation_id>" \
  --confirmation-token "<confirmation_token>"
```

预期：`status: confirmed` 且返回 `confirmed_snapshot_id`。用同一
idempotency key 再 preview 一次，预期 `already_confirmed`（幂等）。

### 排查提示

- `WEEKLY_BRIEF_CAPTURE_CONFLICT`：同一 key 已用于不同候选内容。要么换新 key
  （新快照），要么在未变数据上使用原 key；
- `WEEKLY_BRIEF_CAPTURE_CANDIDATE_INVALID`：`--candidate-json` 不是 query
  输出的原样 `capture_candidate`（例如被 shell 转义/截断）；
- 候选 JSON 很大时不要手动复制粘贴，用上面的文件+变量方式。

## 4. Dashboard 与其余 CLI 读取

### 4.1 Dashboard（本地只读）

```bash
$PY -m pm_agent.cli.app dashboard serve --host 127.0.0.1 --port 5001
```

另开终端验证：

```bash
curl -s http://127.0.0.1:5001/api/summary
curl -s http://127.0.0.1:5001/api/project-health
```

预期：`/api/summary` 含 `total_staff: 2`、`active_projects: 1`；
`/api/project-health` 为数组且含 `atlas-board` 的本地投影
（`confluence` 为空是预期，因为未配置真实连接器）。

### 4.2 传统视图的诚实预期

```bash
$PY -m pm_agent.cli.app workload
$PY -m pm_agent.cli.app report
```

预期：`workload` 显示 2 名成员、0% 负载（传统分配表在结构化组织下为空）；
`report` 是未随结构化组织更新的传统周报，整体状态为空。这些是"保留的旧视图"，
不代表结构化能力缺失；结构化能力请使用 2.1–2.5 的命令。

## 5. 幂等重放

```bash
PYTHONPATH=src src/.venv/bin/python src/scripts/load_sample_data.py --replay
```

预期输出依次为：workforce/capacity/health 的 `already_completed`、
Milestone 的 `{"changes": [], "status": "no_op"}`、
`Derivation replay ... idempotent`、`Attention reconciliation: no changes`、
`Weekly Brief v2 snapshot: already_confirmed`。评估、Attention 项、派生 run、
Milestone、快照的行数均不增加；每次重放只新增一条会过期的 Attention preview
审计行（产品 preview/confirm 审计设计，非新业务对象）。

## 6. UNKNOWN 区域（显式清单）

以下内容**不**在本手册覆盖范围内，状态为 UNKNOWN/未授权，不得由此手册推断为
可用或健康：

- 真实 connector（Jira/Confluence/ServiceNow 等）的同步、探针与凭据；
- 真实数据、真实项目/人员/客户记录及任何公司内部信息；
- 真实环境 UAT（见 `docs/REAL_ENVIRONMENT_UAT_RUNBOOK.md`，修订后须经 owner
  批准才有效）；
- 任何推送、合并、tag、发布、部署或外部分支操作；
- Phase 7 Forecast、Phase 4 配置 preview/confirm 的命令行入口（R4 决策未定）、
  Phase 5 capacity-aware Staffing 开关的公开命令（R4 决策未定）；
- IP-033 的 owner 验收决策（R3 仍在 `codex/phase-4-assessment-entry` 等待）；
- 评估重算入口：本演示中 Milestone 在评估之后导入，schedule 维度保持
  `unknown`；需要一个被单独授权的重评估入口才会刷新；
- 传统 `workload`/`report` 视图对结构化组织的语义（保留的旧视图，未升级）。

## 7. 与 R1 的关系

本手册依赖 R1 的合成流水线与重新生成的 `sample_pm.db`。R1 的验收命令
（第 2 节）与重放命令（第 5 节）即本手册的主干；R5 将把第 1、2 节的核心链条
固化为自动化集成测试。
