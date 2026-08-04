# Dashboard 使用说明（侧边栏含义、关注条件、下一步动作）

本文档面向 Delivery Manager 日常使用，解释 Dashboard **左侧每个菜单项是什么意思**、**什么时候需要重点看**、以及**看到以后通常该做什么**。

适用范围：

- 当前本地 Dashboard；
- 以 `pm dashboard serve` 打开的界面；
- 合成演示库与未来本地工作副本都适用；
- **不覆盖真实 connector 探针、真实数据、或未批准写操作**。

---

## 1. 先记住这三件事

### 1.1 左侧菜单本身是固定显示的

左侧菜单项不是“有数据才出现”，而是**这个 Dashboard 构建里固定可访问的页面**。  
真正会变化的是：

- 页面里的 **KPI 数字**；
- **红 / 黄 / 蓝 / 绿** 状态；
- 是否出现 **warnings / freshness / empty state**；
- 某个页面是不是查到内容。

所以本文件里说的“出现条件”，主要指：

- **什么时候页面会出现重点信号**；
- **什么时候某类记录会非空**；
- **什么时候你需要立即处理，而不是只看一眼**。

### 1.2 颜色和状态不要误读

- **红色 / critical / failed / overdue / expired / high**  
  代表高优先级风险、失败、逾期，通常需要立即跟进。
- **黄色 / amber / partial / stale / never_synced / blocked**  
  代表数据不完整、快过期、已过 SLA、存在风险但未必已经失控。
- **绿色 / success / fresh / known / complete / ready**  
  代表当前记录正常或可用。
- **蓝色 / active / open / pending / info**  
  代表有工作项、说明项或当前活跃状态，**不是健康，也不是故障**。
- **unknown / unavailable / not_available**  
  代表**没有足够证据**或当前能力没有该维度的批准输入，**绝不能理解成“没问题”**。

### 1.3 推荐阅读顺序

每天或每周进入 Dashboard，建议按下面顺序看：

1. **Overview**：快速判断今天有没有明显风险。
2. **Attention**：看当前最需要管理动作的事项。
3. **Project Health / Layered Health / Delivery Execution**：判断项目为什么有风险。
4. **Team / HIREF / Monthly Plan / Capacity Heatmap**：看资源、排期、合同是否支撑当前计划。
5. **Weekly Brief v2**：整理对外/对上沟通口径。
6. **Connectors / Snapshots**：当你怀疑数据时效或需要历史基线时再看。

---

## 2. 左侧菜单总览

左侧分成两组：

- **Legacy views**：Overview、Projects、Team、HIREF、Monthly Plan、Project Health  
  这些是原来就有、偏“操作视图”的页面。
- **Delivery intelligence**：Attention、Weekly Brief v2、Capacity Heatmap、Delivery Execution、Layered Health、Connectors、Snapshots  
  这些是基于提升后的只读 use-case contract 展示的“决策视图”。

---

## 3. Dashboard 里的数据是怎么来的

先说结论：**Dashboard 不是自己生成业务数据**。  
它只是把**本地 SQLite 数据库**里已经存在的记录，用页面形式展示出来。

这批数据通常来自四类路径：

1. **初始化**
   - `pm init`
   - 作用：建立本地数据库结构与基础本地配置。

2. **导入**
   - 例如 workforce planning、resource capacity、milestones、project health clean re-import。
   - 作用：把结构化输入写入本地数据库。

3. **同步 / 种子**
   - 例如 board 注册、JIRA / Confluence 快照、合成演示证据种子。
   - 作用：把页面所需的来源事实放进本地库。

4. **派生 / 对账 / 快照**
   - 例如 Project Health 七维评估、Attention reconciliation、Weekly Brief v2 snapshot。
   - 作用：把原始事实加工成可读的管理结果。

### 3.1 两类页面，取数方式不同

#### A. Legacy views

- Overview
- Projects
- Team
- HIREF
- Monthly Plan
- Project Health

这些页面主要读取**本地表 / 视图**，属于“本地 SQL 直读型”页面。

#### B. Delivery intelligence

- Attention
- Weekly Brief v2
- Capacity Heatmap
- Delivery Execution
- Layered Health
- Connectors
- Snapshots

这些页面主要通过共享只读合同：

```text
POST /api/tool/query/<use_case_id>
```

也就是说，它们不是随便拼页面，而是调用已经注册的 use case，把结果中的：

- `status`
- `warnings`
- `freshness`
- `facts / signals / recommendations`

按统一方式显示出来。

### 3.2 你看到“有数据 / 没数据”的本质是什么

Dashboard 某个页面有数据，通常表示：

- 这个页面依赖的数据已经进入本地数据库；
- 该能力需要的派生/对账已经做过；
- 当前查询条件（如 project、month、plan version）能命中记录。

某个页面没数据，通常表示以下三种之一：

1. **还没导入 / 还没同步 / 还没派生**
2. **当前查询前提不满足**
   - 例如 Capacity 需要 `plan_version_id`
3. **数据是 unknown / partial / not_available**
   - 说明证据不足，不是“没问题”

### 3.3 每个主要页面需要什么前提数据

| 页面 | 最低前提 | 数据通常来自哪里 |
| --- | --- | --- |
| Overview | staff / project / hiref / load / freshness 基础记录 | 本地 employees、projects、hiref、load view、sync/freshness 记录 |
| Projects | 项目、成员、里程碑、分配 | workforce/project/allocation 数据 |
| Team | 人员、当前项目、负载、HIREF | workforce 数据 + assignments/load + hiref |
| HIREF | 当前合同、next HIREF、slot、placeholder | HIREF/contract continuity 数据 |
| Monthly Plan | 月度 allocation | workforce planning 导入 |
| Project Health | board 映射、JIRA/Confluence 快照、freshness | board 注册 + health/status snapshots + sync 记录 |
| Attention | 项目健康、里程碑、超载、逾期 action、freshness 等已存在事实 | Attention reconciliation 之后的结果 |
| Weekly Brief v2 | health / attention / next actions / snapshot candidate | promoted use cases 的汇总结果 |
| Capacity Heatmap | year + month + plan version + capacity facts | resource capacity 导入 + allocation 数据 |
| Delivery Execution | sprint/release/milestone 事实 | milestone 导入 + execution facts |
| Layered Health | 七维评估结果 | project health re-import / assessment |
| Connectors | connector registry + local sync outcomes | 本地 connector 配置与 sync 结果记录 |
| Snapshots | 已保存的 project snapshots | snapshot list / stored snapshot records |

### 3.4 合成演示数据是怎么来的

如果你现在看到的是 demo 效果，这些数据不是手填到 Dashboard 的，而是通过一条演示流水线生成：

```bash
PYTHONPATH=src src/.venv/bin/python src/scripts/load_sample_data.py --force
```

这条命令会依次完成：

1. 建库（bootstrap）
2. workforce planning 导入
3. resource capacity 导入
4. board 注册
5. 合成证据种子
6. milestone 导入
7. Project Health re-import / 七维评估
8. Attention reconciliation
9. Weekly Brief v2 snapshot

所以你在 Dashboard 上看到的，不是一张静态 demo 页面，而是**本地库经过导入、派生、对账后形成的结果**。

---

## 4. 作为使用者，我怎样才能“有这些数据”

这个问题要分成两种场景。

### 4.1 如果你只是想先体验和理解 Dashboard

最简单的方法是使用**合成演示库**。

#### 第一步：安装本地运行环境

```bash
cd src
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -e .
```

#### 第二步：回到仓库根目录，构建演示库

```bash
cd ..
PYTHONPATH=src src/.venv/bin/python src/scripts/load_sample_data.py --force
```

#### 第三步：指向演示库并启动 Dashboard

```bash
export DATABASE_PATH="$PWD/src/sample-data/demo/sample_pm.db"
pm dashboard serve
```

然后打开：

```text
http://127.0.0.1:5001
```

如果只是重复刷新演示库而不想重建，可用：

```bash
PYTHONPATH=src src/.venv/bin/python src/scripts/load_sample_data.py --replay
```

### 4.2 如果你是实际使用者，想让自己的本地 Dashboard 有数据

你需要的不是“打开 Dashboard”，而是先把**本地数据库准备好**。

典型步骤是：

1. `pm init`
   - 初始化本地数据库与本地配置
2. `pm config validate`
   - 校验本地配置是否完整
3. `pm connector validate --portable`
   - 只做安全边界内的本地校验
4. 执行已批准的导入 / 同步 / 派生流程
   - 让数据真正进入本地库
5. `pm dashboard serve`
   - 最后才是启动页面

换句话说：

> **Dashboard 是最后一层“看结果”的界面，不是第一步的数据准备工具。**

### 4.3 如果页面是空的，我应该先补哪类数据

可以按下面理解：

- **Team / Projects / Monthly Plan 空**
  - 先看 workforce / allocation 是否导入
- **HIREF 空**
  - 先看合同 / slot / continuity 数据是否存在
- **Project Health 空**
  - 先看 board 映射和 JIRA / Confluence 快照
- **Capacity 空**
  - 先看 plan version、month、capacity import 是否到位
- **Delivery Execution 空**
  - 先看 milestone / execution 事实是否导入
- **Layered Health 空**
  - 先看七维评估是否跑过
- **Attention 空**
  - 先看 reconciliation 是否做过
- **Weekly Brief v2 空**
  - 先看 health / attention / next actions 是否已有结果
- **Connectors 空**
  - 先看本地 connector registry 和 sync results
- **Snapshots 空**
  - 先看是否有保存过 snapshot

### 4.4 初始化之后，平时怎么更新这些数据

大多数情况下，**首次把数据接进来**还是要靠：

- 结构化导入；
- 批准的本地同步；
- 派生 / 对账 / 快照流程。

但在这之后，日常使用更自然的方式通常是：

> **通过 Copilot 对话，让系统帮你查询、解释、预览、再确认少量受控更新。**

适合通过对话做的，通常是：

- 问当前 workload / capacity / health / attention；
- 发起 staffing proposal；
- 对 Attention 做 acknowledge / snooze / reconcile；
- 生成或确认 Weekly Brief v2 snapshot；
- 查看受控配置并执行已批准的 preview / confirm。

不适合直接靠口述改的，通常是：

- 大批量成员 / 项目 / allocation 变更；
- capacity 全量刷新；
- milestone 批量导入；
- project health re-import 包；
- connector 同步结果重建。

也就是说：

> **Dashboard 主要负责看结果；Copilot 主要负责驱动查询和受控动作；基础事实的大批量刷新仍然回到 importer / sync 路径。**

对 Delivery Manager 来说，真正可用的长期体验应该是：

- 首次把来源关系配置好；
- 后续只做“刷新范围选择 → preview → confirm → 看结果”；
- 不需要长期自己记住 importer 名字和依赖链。

---

## 5. 作为使用者，建议怎么开始

### 路线 A：先学会看页面（推荐第一次）

1. 用合成演示库启动 Dashboard
2. 先看 `docs/DASHBOARD_USAGE_GUIDE.md`
3. 按顺序点：
   - Overview
   - Attention
   - Project Health / Layered Health / Delivery Execution
   - Team / HIREF / Monthly Plan / Capacity
   - Weekly Brief v2
   - Connectors / Snapshots
4. 对照 `docs/SYNTHETIC_DEMO_WALKTHROUGH.md` 里的已知演示状态理解每个页面为什么有内容

这是“理解系统”的最安全起点。

### 路线 B：开始准备你自己的本地数据

1. 在批准的本地工作环境中安装并初始化
2. 用本地忽略配置填入允许的数据库路径 / endpoint / credential
3. 先跑配置校验，不要先跑 live probe
4. 先从**只读查询**开始
5. 确认本地库里已经有事实后，再开 Dashboard

建议顺序：

```bash
pm init
pm config validate
pm connector validate --portable
pm tool list
pm tool query team-workload-overview
pm dashboard serve
```

如果初始化已经完成，之后的日常节奏通常会变成：

1. 先通过 Copilot 问“现在有什么风险 / 谁有容量 / 哪些项目异常”；
2. 需要受控动作时，让 Copilot 帮你走 preview / confirm；
3. 只有在基础事实层发生大批量变化时，才回到导入或同步。

### 路线 C：如果你是 owner / reviewer，只想确认“现在有没有准备好”

先回答三个问题：

1. 本地数据库是不是已经建好？
2. 关键导入 / 派生是不是跑过？
3. 当前页面里的 `stale / partial / unknown` 我是不是理解其含义？

如果这三个问题里有一个答案是否定的，就先不要把 Dashboard 的结果当最终结论。

---

## 6. 每个菜单项怎么理解

## Overview

**它是什么**

- 这是首页总览，帮助你在 30 秒内知道团队和项目今天是不是有明显异常。
- 它聚合了团队人数、项目数、平均负载、HIREF 告警、空闲 HIREF、重点 alert strip 等摘要。

**什么时候需要重点看**

- 页面顶部出现红/黄 alert；
- `HIREF Alerts` > 0；
- `Avg Team Load` 很高，或 overloaded 人数 > 0；
- `stale_sources_count` 偏高，说明部分判断可能基于过期数据。

**你接下来该做什么**

- 如果是人力问题，转到 **Team / Monthly Plan / Capacity Heatmap**；
- 如果是合同问题，转到 **HIREF**；
- 如果是项目健康问题，转到 **Project Health / Layered Health / Delivery Execution**；
- 如果一开始就看到很多 stale/failed 信号，先去 **Connectors** 判断数据可信度。

---

## Projects

**它是什么**

- 活动项目卡片视图。
- 用来快速看每个项目的成员、阶段、优先级、里程碑，以及 legacy health 摘要。

**什么时候需要重点看**

- 某个项目出现 health 相关红/黄标记；
- 项目被标成重点，但成员/计划明显不足；
- 项目成员里出现临期 HIREF 或 planned assignment 过多。

**你接下来该做什么**

- 判断是否需要调人或调整优先级；
- 与项目负责人确认里程碑、风险、实际投入是否一致；
- 如果要看更严格的证据，去 **Delivery Execution** 和 **Layered Health**。

---

## Team

**它是什么**

- 以人员为中心查看当前负载、在做项目、下一个 assignment，以及 HIREF 情况。

**什么时候需要重点看**

- `Load > 100%`；
- STFTE 人员没有当前 HIREF，或 HIREF 临近到期；
- 有人当前项目很多，但后续 assignment 不清晰；
- 搜索/过滤后发现关键技能只有单点人员。

**你接下来该做什么**

- 对超载人员做工作再平衡；
- 提前安排下一个月/下一个阶段的 assignment；
- 对合同人员与 HIREF 状态做交叉检查；
- 如果要看未来月份是否还能接新工作，去 **Monthly Plan** 或 **Capacity Heatmap**。

---

## HIREF

**它是什么**

- 合同与 HIREF 连续性管理页，重点面向 STFTE。
- 展示当前合同、即将到期人员、是否已有 next HIREF、是否存在 free slot、是否项目对不上。

**什么时候需要重点看**

- `Critical <60d` 或 `High <90d` 不为 0；
- `Mismatch` > 0，说明 HIREF 项目与实际项目不一致；
- 出现 `No HIREF`、`reserved_for_next`、`free slot` 等信号。

**你接下来该做什么**

- 临期无续期：尽快推动续期或替代安排；
- 有 free slot：判断是否可用于补位；
- 项目不一致：核对人员实际上在支持哪个项目；
- 对长期资源缺口，再结合 **Team / Monthly Plan / Capacity Heatmap** 看是否需要重新分配。

---

## Monthly Plan

**它是什么**

- 月度分配视图，按人或按项目看未来月份 allocation。
- 偏“排班/规划”视图。

**什么时候需要重点看**

- 某人某月超过 100%；
- 某项目某月投入明显不足；
- 你在做下月或下季度排班；
- 当前项目健康有风险，想确认是不是资源排法导致。

**你接下来该做什么**

- 调整未来月份 allocation；
- 提前发现即将超载的人员或即将缺人的项目；
- 结合 **Capacity Heatmap** 判断“计划上排了”是否等于“容量上真的可行”。

---

## Project Health

**它是什么**

- 这是 **legacy** 的项目健康视图，主要把 JIRA health、Confluence status、freshness、sync action 放在一页上。
- 适合先看“项目哪里不对劲”，也适合做 source-level 的快速核对。

**什么时候需要重点看**

- `Needs Attention` > 0；
- `Need Sync` > 0；
- `Signal Gaps` > 0，说明 Confluence 和 JIRA 结论不一致；
- `No Board Link` > 0，说明项目没有板子映射；
- 某个项目显示 stale / failed / missing。

**你接下来该做什么**

- **不要把 stale / partial 当成健康**；
- 如有需要，使用页面里现有的 sync 动作先刷新 JIRA health；
- 如果 Confluence 与 JIRA 不一致，先确认状态口径，再做汇报；
- 如果要看提升后的七维结果，去 **Layered Health**；
- 如果要看里程碑/发布层面的事实，去 **Delivery Execution**。

---

## Attention

**它是什么**

- 把三类信息放在一起：
  - `management-attention`
  - `delivery-attention-center`
  - `action-followup`
- 这是“今天我最该盯什么”的优先级入口。

**什么时候需要重点看**

- `critical_count`、`returned_count`、`overdue_count` 大于 0；
- 某个 rule 一直反复出现；
- Weekly Brief 或 Layered Health 告诉你总体有问题，但你想先看最值得行动的清单。

**你接下来该做什么**

- 先按 critical / high 排序做管理跟进；
- 区分是**项目风险**、**资源超载**、**逾期动作**，还是**来源数据 freshness** 问题；
- 对于 overdue follow-up，推动 owner 明确下一步；
- 对于 source freshness 类 attention，先去 **Connectors** 判断基础数据是否可靠。

> 注意：Attention 是**决策支持页**，不是“系统已经替你解决问题”。  
> 看到 item 后，真正的动作通常发生在项目/团队管理流程里。

---

## Weekly Brief v2

**它是什么**

- 周报合成视图，把当前项目状态、attention、next actions 汇总成一个管理口径。
- 适合做周会前准备、向上汇报前预览。

**什么时候需要重点看**

- `overall_state` 是 red / amber；
- `highest_attention_signals` 非空；
- `next_actions` 非空；
- 某些 section 是 `partial` / `not_available`，说明本周口径还不完整。

**你接下来该做什么**

- 把它当作“本周汇报底稿”而不是最终真相；
- 对红色和 partial 区域回查原始页面（Attention、Project Health、Layered Health、Execution）；
- 把 next actions 转成真实 follow-up；
- 对外汇报前，确认 unknown / partial 部分的解释口径。

---

## Capacity Heatmap

**它是什么**

- 基于已发布计划窗口的 **effective capacity / commitment / overload** 视图。
- 偏“容量事实”而不是“排班表”。

**什么时候需要重点看**

- 某些 row 的 `overload_state` 是 red；
- `available_capacity` 很低或为负；
- 你在判断某个人/某个月还能不能接活；
- Monthly Plan 看起来排得下，但你想确认容量上是否真的可行。

**你接下来该做什么**

- 对 red 行优先减载或换人；
- 把它和 **Monthly Plan** 一起看：一个是“怎么排”，一个是“排完是否超容量”；
- 做 staffing 决策前，先确认当前选中的 year / month / plan version 是你真正要看的窗口。

> 如果这个页面为空，通常不是“没有风险”，而是当前数据库没有可用于该窗口的
> `plan_version_id` + allocation 组合。

---

## Delivery Execution

**它是什么**

- 提升后的执行评审页，展示 Sprint Execution 与 Release / Milestone 事实。
- 用来回答：“项目为什么红？到底是 Sprint、Release 还是 Milestone 出问题？”

**什么时候需要重点看**

- 里程碑出现 `overdue`；
- release / milestone signal 非空；
- 你想把“健康差”拆成可执行的计划问题；
- Layered Health 告诉你 schedule/scope 有问题，但你想看到更具体的事实。

**你接下来该做什么**

- 先按 `active`、`overdue`、`high` 的事实或 signal 排查；
- 对逾期 milestone 明确恢复计划；
- 对 unavailable / unknown 项，不要硬解释成正常，而要承认当前证据不足；
- 需要跨项目比较时，再回到 **Attention** 或 **Weekly Brief v2** 看整体排序。

---

## Layered Health

**它是什么**

- 提升后的 **七维 Project Health** 视图。
- 这是对项目整体状态更正式的评估页，和 legacy Project Health 并存。

**什么时候需要重点看**

- 某项目 overall state 是 `red`；
- 某些维度是 `amber` / `red`；
- 某些维度是 `unknown` / `not_available`；
- 你要做项目级判断，但不想只靠单一来源（例如只有 JIRA）。

**你接下来该做什么**

- 先看 overall，再看具体红/黄维度；
- 对 `unknown` / `not_available`，补的是**证据解释**，不是“拍脑袋改绿”；
- 如果问题落在 schedule / scope，继续看 **Delivery Execution**；
- 如果问题落在 resource，继续看 **Team / Monthly Plan / Capacity Heatmap**；
- 如果问题需要管理层关注，继续看 **Attention**。

> **Project Health** 和 **Layered Health** 不同：  
> 前者偏来源观察和 sync，后者偏提升后的综合评估。

---

## Connectors

**它是什么**

- 查看 connector 的**离线状态**与**最近同步结果**。
- 不会主动做 runtime probe，也不会隐式访问真实系统。

**什么时候需要重点看**

- 其他页面大量出现 stale / never_synced / failed；
- 你怀疑当前 Dashboard 的判断依赖了老数据；
- 你要解释“为什么页面没有内容 / 内容不可信”。

**你接下来该做什么**

- 如果是 `never_synced` / `failed` / `stale`，先降低对相关页面结论的信心；
- 需要 live probe 或真实同步时，按受控流程单独执行，不要在这里直接假定连通；
- 报告风险时，区分“业务风险”与“数据来源时效风险”。

> 这个页面回答的是“本地记录怎么看”，不是“远端系统现在一定正常”。

---

## Snapshots

**它是什么**

- 查看已存储的项目快照清单。
- 适合做历史对比、审计、复盘、Weekly Brief 或项目状态的基线参考。

**什么时候需要重点看**

- 你想看某项目之前记录过什么；
- 你需要 draft / active 快照的盘点；
- 你想核对当前判断是否与上次快照一致；
- Weekly Brief 或项目复盘需要历史锚点。

**你接下来该做什么**

- 用它做“横向看现在、纵向看历史”；
- 如果没有 snapshot，不要自动理解成“项目没问题”，只表示当前没有存储记录；
- 如果状态或健康过滤后结果为空，先确认是不是筛选条件太窄。

---

## 7. 常见困惑

### 为什么很多页面会显示 warning / freshness / partial？

因为提升后的页面是按共享 contract 展示的，系统会把：

- warning；
- freshness；
- partial；
- unknown / not_available

都诚实显示出来。  
这比“看起来很干净但其实证据不够”更安全。

### 为什么有两个 health 页？

- **Project Health**：legacy 观察页，偏 JIRA / Confluence / freshness / sync；
- **Layered Health**：提升后的七维评估页，偏综合判断。

### 为什么 Monthly Plan 和 Capacity Heatmap 都在？

- **Monthly Plan**：你怎么排；
- **Capacity Heatmap**：排完以后是否超容量。

两者要结合看，不能互相替代。

### 为什么有些页面空白？

常见原因有三类：

1. 当前数据库确实没有该类记录；
2. 页面需要特定前提（例如 capacity 需要 plan version + allocation）；
3. 数据源 freshness / sync 状态不足，导致结果为空或 limited。

空白不等于健康，也不等于错误；要看页面上的 empty state、warnings、freshness 一起判断。

---

## 8. 一张最短的“怎么用”清单

如果你只记一页，请记下面这张：

1. **Overview**：今天有无明显异常。  
2. **Attention**：今天先处理什么。  
3. **Project Health / Layered Health / Delivery Execution**：为什么出问题。  
4. **Team / HIREF / Monthly Plan / Capacity Heatmap**：人和合同能不能支撑。  
5. **Weekly Brief v2**：怎么对外讲。  
6. **Connectors / Snapshots**：数据是否可信、历史如何对照。  

---

## 9. 相关文档

- `docs/SYNTHETIC_DEMO_WALKTHROUGH.md`：从零构建合成演示库并逐步查询；
- `src/sample-data/README.md`：演示数据具体包含哪些状态；
- `docs/LOCAL_DATA_ONBOARDING_GUIDE.md`：如果你已经有本地现有数据，怎样安全准备并接入；
- `PROGRESS.md`：当前工作树与能力状态的唯一权威；
- `src/README.md`：本地运行、Dashboard 启动、验证命令。
- `docs/REAL_ENVIRONMENT_UAT_RUNBOOK.md`：未来在批准前提下如何准备真实环境 UAT。