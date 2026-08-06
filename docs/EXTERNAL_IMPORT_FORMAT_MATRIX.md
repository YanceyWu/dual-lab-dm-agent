# 外部导入格式矩阵

本文档回答两个实际问题：

1. **外部导入是否必须遵守固定文件格式？**  
   **是。** 每个 importer 都有自己期待的输入边界，不能把任意 Excel / CSV /
   JSON 直接喂给脚本。
2. **仓库里现在每个 importer 是否都有对应 sample？**  
   **当前列出的主要 importer 基本都有对应 sample。** 但 sample 的用途是
   “说明格式”，不代表你可以直接把真实文件原样替换字段名以外的全部结构。

---

## 1. 怎么看这张表

### 1.1 “是否受控”是什么意思

- **是（preview/confirm）**
  - 这是更正式的版本化导入路径；
  - 通常要求 `--dry-run` 或 preview，然后 `--confirm`；
  - 更适合作为长期、可审计的数据导入入口。

- **部分（dry-run）**
  - 脚本支持 `--dry-run`，但不是完整 preview/confirm 事务式入口；
  - 更像受限导入工具，而不是提升后的正式导入合同。

- **否**
  - 没有 preview/confirm 受控边界；
  - 一般是早期脚本、辅助导入、或模板型数据回填工具。

### 1.2 推荐使用原则

1. **保留来源族统一优先走 `pm onboarding`；不再保留 source-specific standalone operator script。**
2. **能先把你们现有数据转换成 sample 对应格式的，不要先改产品。**
3. **Excel / CSV 导入比版本化 JSON 更依赖列名、sheet 名、模板结构。**
4. **真实数据接入时，先在批准副本上 rehearsal，不要先碰活动库。**

---

## 2. 外部导入格式矩阵

| 受支持入口 | 文件类型 | Sample 路径 | 是否受控 | 推荐使用场景 |
| --- | --- | --- | --- | --- |
| `pm onboarding` (`workforce-planning-json`) | JSON | `src/sample-data/json/workforce_planning_import.sample.json` | **是（preview/confirm）** | 导入 versioned JSON 形式的人员、项目、plan version、monthly allocation；这是该 JSON family 的受支持 operator-visible 入口。对应 standalone operator script 已在 D1 退役。 |
| `pm onboarding` (`resource-capacity-json`) | JSON | `src/sample-data/json/resource_capacity_import.sample.json` | **是（preview/confirm）** | 导入 capacity / commitment 相关输入；用于 Capacity Heatmap 和 capacity-aware 判断。对应 standalone operator script 已在 D1 退役。 |
| `pm onboarding` (`milestone-json`) | JSON | `src/sample-data/json/milestone_import.sample.json` | **是（preview/confirm）** | 导入 canonical milestones；用于 Delivery Execution、部分健康与 attention 规则。对应 standalone operator script 已在 D1 退役。 |
| `pm onboarding` (`project-health-reimport-json`) | JSON | `src/sample-data/json/project_health_reimport.sample.json` | **是（preview/confirm）** | 导入 Project Health re-import 包并触发七维评估；用于 Layered Health。对应 standalone operator script 已在 D1 退役。 |
| `pm onboarding` (`jira-board-registry-csv`) | CSV | `src/sample-data/csv/jira_board_configs.sample.csv` | **是（preview/confirm）** | 注册 board 与项目映射；Project Health / JIRA 相关页面需要这类基础映射。对应 standalone operator script 已在 D1 退役。 |
| `pm onboarding` (`confluence-page-registry-csv`) | CSV | `src/sample-data/csv/confluence_pages.sample.csv` | **是（preview/confirm）** | 导入 Confluence 页面注册表；用于 Confluence 状态来源映射。对应 standalone operator script 已在 D1 退役。 |
| `pm onboarding` (`servicenow-change-request-csv`) | CSV | `src/sample-data/csv/servicenow_change_requests.sample.csv` | **是（preview/confirm）** | 导入 ServiceNow change request CSV 导出。对应 standalone operator script 已在 D1 退役。 |
| **已退休：legacy HIREF Excel 入口** | Excel (`.xlsx`) | `src/sample-data/excel/hiref_status_sample.xlsx` | **否（retired）** | `import_hiref.py` 已退休，不再是受支持的产品入口；contract coverage 与现有 HIREF slot/result 所需数据改由 `pm onboarding` 的 workbook source 提供。需要保留 HIREF feature point 时，请在 workbook 中补充可选的 `HIREF Requests` sheet，并使用 `Members.next_hiref_id` 与 `Allocations.hiref_id` 表达续签和 open-demand。 |
| `pm onboarding` (`workbook`) | Excel (`.xlsx`) | `src/sample-data/excel/team_project_capacity_workbook_hiref_sample.xlsx` | **是（preview/confirm）** | 当前受支持的 workbook onboarding 正式入口。`templates/team_project_capacity_workbook_template.xlsx` 提供 review/template 结构，sample 文件展示 B4 简化后的 HIREF workbook 合同：基础 Members / Allocations sheet 扩展 + 可选 `HIREF Requests` sheet。对应 standalone operator script 已在 D1 退役。 |
| `pm onboarding` (`project-profile-workbook`) | Excel (`.xlsx`) | `src/sample-data/excel/project_profiles_sample.xlsx` | **是（preview/confirm）** | 从填写好的项目资料模板回写项目 profile。对应 standalone operator script 已在 D1 退役。 |
| **已退休：legacy Distribution Excel 入口** | Excel (`.xlsx`) | `src/sample-data/excel/resource_portal_team_sample.xlsx` | **否（retired）** | 早期 Distribution Excel 团队导入路径已在 D1 退役；sample 仅保留为不受支持的历史格式参考，不再提供 standalone operator script。要发布 authoritative workbook current-state，请使用 `pm onboarding` 的 workbook source。 |

---

## 3. 每类 importer 的使用建议

## 3.1 推荐优先使用的“正式入口”

这四个 retained JSON source type 最值得优先围绕其格式做数据映射：

1. `workforce-planning-json`
2. `resource-capacity-json`
3. `milestone-json`
4. `project-health-reimport-json`

原因：

- 输入是版本化 JSON；
- 有明确 sample；
- 有 `dry-run` / `confirm` 路径；
- 更接近当前产品的正式数据路径。

如果你们现在有自己的外部数据，**优先把数据转换成这四类 sample 对应的 JSON 格式**，而不是优先修改代码。

## 3.2 适合作为“映射桥接”的 importer

这些 retained source family 更适合在“你们已经有导出报表/模板”的前提下做本地桥接：

- `jira-board-registry-csv`
- `confluence-page-registry-csv`
- `servicenow-change-request-csv`
- `project-profile-workbook`
- legacy Distribution Excel sample / historical bridge format（unsupported reference only）

这些入口的特点是：

- 有 sample 可以对照；
- 对列名 / sheet / 字段结构更敏感；
- 更像“把既有导出转成本地产品可读格式”的工具。

---

## 4. 不是所有“有 sample”都代表格式很宽松

即使仓库里有 sample，也不表示脚本会自动适配任何类似文件。

### 4.1 JSON 导入

JSON 导入通常要求：

- 顶层结构正确；
- 关键字段齐全；
- 标识符、日期、版本、manifest 等字段满足导入服务校验。

也就是说，**不是“看起来像 JSON 就行”**。

### 4.2 CSV 导入

CSV 导入通常要求：

- 列名符合脚本预期，或能被脚本映射；
- 数据值可被脚本解析；
- 特定列必须存在。

其中 `servicenow-change-request-csv` 底层沿用的 retained CSV parser 相对宽松一些，因为它有列名映射表，会自动识别一批 ServiceNow 常见列名变体。
但“相对宽松”不等于“任意 CSV 都可以”。

### 4.3 Excel 导入

Excel 导入通常要求：

- 文件是指定模板或同结构导出；
- sheet 名固定；
- 关键列位置固定；
- 单元格文本格式符合脚本预期。

因此 Excel 类型最应该先拿 sample 对照，再做字段映射。

---

## 5. 如果你们已经有现成数据，推荐怎么接

建议流程：

1. 先确定你们现有数据最接近哪一种 importer；
2. 打开对应 sample；
3. 做一份**字段映射表**：
   - 你们当前字段
   - sample 需要的字段
   - 是否能直接映射
   - 是否需要转换
4. 先在批准副本上 `dry-run`
5. 通过后再 `confirm` 或再继续后续导入

### 最推荐的映射目标

如果你们准备做长期接入，优先朝这几类格式收敛：

- `workforce_planning_import.sample.json`
- `resource_capacity_import.sample.json`
- `milestone_import.sample.json`
- `project_health_reimport.sample.json`

因为这些更接近现在的受控主路径。

### 一个关键现实：这张表不应该成为 DM 的日常操作菜单

这张矩阵**很适合实施者、owner、或接入设计阶段参考**，但它不应该长期成为
Delivery Manager 日常要手动记忆的操作菜单。

如果一个 DM 需要自己长期判断：

- 今天该跑哪个 importer；
- 先跑 workforce 还是先跑 milestone；
- 哪个 sample 对应哪个来源；
- 这次刷新会影响哪些 Dashboard 页面；

那么使用门槛会过高。

更合理的产品形态应该是：

1. 先把这些 importer 背后的来源关系固化成一个本地 **source profile**
2. 刷新时由系统按既定顺序自动编排
3. DM 只看 preview / confirm / refresh summary

所以这张表更适合拿来做：

- 首次接入规划；
- 字段映射；
- source profile 设计；
- 刷新失败时的问题定位；

而不是让 DM 每周都手动照表逐条执行。

---

## 6. 一个实用判断：我该先看哪个 sample

| 如果你想导入… | 先看哪个 sample |
| --- | --- |
| 人员、项目、月度分配 | `src/sample-data/json/workforce_planning_import.sample.json` |
| 容量、承诺、可用度 | `src/sample-data/json/resource_capacity_import.sample.json` |
| 里程碑 | `src/sample-data/json/milestone_import.sample.json` |
| 项目健康重导入包 | `src/sample-data/json/project_health_reimport.sample.json` |
| JIRA board 映射 | `src/sample-data/csv/jira_board_configs.sample.csv` |
| Confluence 页面注册 | `src/sample-data/csv/confluence_pages.sample.csv` |
| ServiceNow 变更单 CSV 导出 | `src/sample-data/csv/servicenow_change_requests.sample.csv` |
| Team/Project + Capacity workbook template | `templates/team_project_capacity_workbook_template.xlsx` |
| Team/Project + Capacity workbook sample（含 B4 simplified HIREF contract） | `src/sample-data/excel/team_project_capacity_workbook_hiref_sample.xlsx` |
| HIREF 状态报表 | `src/sample-data/excel/hiref_status_sample.xlsx` |
| 项目 profile 模板 | `src/sample-data/excel/project_profiles_sample.xlsx` |
| 资源门户团队 Excel | `src/sample-data/excel/resource_portal_team_sample.xlsx` |

---

## 7. 结论

可以把这件事总结成三句话：

1. **外部导入必须遵守固定格式。**
2. **当前主要 importer 基本都有 sample。**
3. **最佳实践不是先改 importer，而是先把现有数据映射到 sample 对应格式。**

---

## 8. 相关文档

- `docs/LOCAL_DATA_ONBOARDING_GUIDE.md`
- `docs/DASHBOARD_USAGE_GUIDE.md`
- `docs/REAL_ENVIRONMENT_UAT_RUNBOOK.md`
- `src/sample-data/README.md`
- `docs/SYNTHETIC_DEMO_WALKTHROUGH.md`
