# DM Scenario Capability Map

日期：2026-08-11

状态：TPO 选择前的场景映射；不是实施 Roadmap，不授权代码、schema、页面、Agent、Service 或表变更。

## 1. 口径与边界

本文件以已完成的 Current Product Audit 为证据基线，不重新执行完整代码盘点。成熟度采用：

| 等级 | 定义 |
|---|---|
| L0 | 只有设计、文档或占位 |
| L1 | 存在代码，但没有进入真实用户流程 |
| L2 | 局部可用，用户需要人工拼接信息、判断或后续操作 |
| L3 | 用户可以完成一次端到端的业务判断或决策 |
| L4 | 包含主动发现、证据解释、DM 确认、执行和后续闭环 |

当前基线是：**没有已验证的 L3/L4 DM 决策工作流。** 初次数据导入是一条完整操作型工作流，但不是 Delivery Intelligence 决策能力。

Owner 证据只采用以下明确事实：

- `OWNER-USED`：Owner 个人构建并实际使用过现有系统，人员、项目、Monthly Plan 等基础能力有实际业务基础；
- `OWNER-REAL-DATA`：Jira / Confluence 同步曾在公司环境使用真实数据运行；本次未重新执行当前快照的 live verification；
- `OWNER-REPEATED`：IP-027～IP-032 尚未成为 Owner 固定使用的工作流；
- `OWNER-MEANING`：Project Health 尚不足以代表完整项目健康判断；
- 当前没有稳定的项目全景、规划、风险判断和跟进闭环。

超出这些事实的 Owner 结论均为 `OWNER CONFIRMATION REQUIRED`。

### 1.1 改造规模标签

| 标签 | 含义 |
|---|---|
| `REUSE` | 现有资产可以直接作为场景的一部分 |
| `CONNECT` | 能力已存在，主要缺少入口、调用顺序或结果衔接 |
| `SMALL CHANGE` | 需要收紧合同、补字段覆盖、修复选择规则或增加有限场景行为 |
| `MISSING` | 当前没有足以支撑该步骤的业务语义或能力 |
| `OUT` | 不属于该场景最小路径；不表示应删除 |

### 1.2 问题类型

| 标签 | 含义 |
|---|---|
| `PV` | Product Value：业务问题、判断规则、输出和行动本身尚未成立 |
| `PH` | Productization / Handover：入口、配置、文档、追踪、测试、发布或维护问题 |
| `BOTH` | 产品语义和产品化问题同时存在 |

## 2. 跨场景可复用资产

| 层 | 现有资产 | 复用价值 |
|---|---|---|
| UI | Overview、Projects、Team、HIREF、Monthly Plan、Project Health；7 个隐藏实验 tab | 核心页是已用入口；隐藏页只作为可复用 renderer，不默认成为新产品入口 |
| API | 18 个 Dashboard routes；generic use-case query；Attention / Weekly Brief operation APIs | 可连接已有 reader 与受控写入，不必先新增 API family |
| Application | `UseCaseExecutor`、onboarding、staffing、attention、weekly brief、connector sync | 提供统一查询合同、导入、候选评估和局部操作 |
| Domain | Project、Person、Plan / Allocation、HIREF、Execution、Attention、Health、Capacity、Action、Decision | 已覆盖多数名词，但 Risk、Demand、Action closure 和 cross-plan impact 仍不统一 |
| Agent | 15 个 registered use cases、direct routes、propose / preview / confirm 指令 | 可作为自然语言入口；当前是被动路由器，不是主动闭环 |
| Data | core tables、Jira / Confluence、publication / freshness、execution evidence、audit / trace | 能支持 evidence 和可追踪操作；多套 authority / fallback 需先收束 |
| Test / release | 56 个测试文件、合成 demo、validation / rehearsal、usage bundle | 是交接基础；目前主要证明组件，不证明四个 DM 场景 |

## 3. 场景一：项目证据汇总与决策准备

### 3.1 真实 DM 决策

DM 需要回答：

> 对这个项目，本周是否有足够、一致且新鲜的证据支持继续按当前计划；如果不能，具体缺什么、冲突在哪里、哪些事项需要 DM 确认或介入？

这是“决策准备”场景。达到 L3 的结果不是多展示几张卡片，而是 DM 能基于可追溯证据确认“继续 / 介入 / 暂时无法判断”之一，并形成可执行结果。

### 3.2 步骤映射

| 步骤 | 需要完成的工作 | 当前 UI / API / Service / Domain / Agent / Data 资产 | 当前能做到什么 | 断点、改造规模与类型 | IP-027～IP-032 价值 |
|---|---|---|---|---|---|
| S1. 选择项目并识别来源 | 确定项目及 Excel、PPT、Minutes、Confluence、Jira、Monthly Plan 的覆盖 | UI：Projects；API：`/api/projects`；Service：onboarding、Jira board / Confluence page registry；Domain：Project、Project Profile、source identity；Agent：project / connector routes；Data：`projects`, `project_profiles`, registry 和 source identity tables | 可识别本地项目、Jira board、Confluence page、plan 数据；项目 profile 可保存 objective、milestones 和 key risks | PPT 和 Meeting Minutes 没有受支持的结构化 source；没有明确 scope 字段；跨来源 coverage 没有统一用户视图。`CONNECT` + `MISSING`，`BOTH` | IP-027 可统一 coverage 输出；IP-029 可复用 source identity / evidence |
| S2. 获取并刷新证据 | 导入或同步各来源并保留时间和来源 | UI：Project Health sync；API：`/api/project-health/sync`, sync-runs, freshness；Service：data onboarding、Jira / Confluence sync；Domain：sync run、source evidence；Agent：connector / onboarding route；Data：Jira、Confluence、onboarding run / publication tables | Excel / JSON / CSV 可 preview / confirm；Jira / Confluence 曾在真实环境运行；可记录 sync 和部分 freshness | 当前快照未 live verify；刷新主要靠显式触发；PPT / Minutes 缺失；不同 source 没有共同 as-of 规则。`REUSE` + `SMALL CHANGE` + `MISSING`，`BOTH` | IP-029 提供 evidence publication；IP-027 提供 freshness / evidence contract |
| S3. 形成当前状态 | 汇总目标、scope、计划、实际进展、风险、决定、人员和行动 | UI：Projects、Team、Monthly Plan、Project Health；API：projects、employees、allocations、health；Service：project health、execution review、action follow-up；Domain：Project Profile、Execution、Plan、Action、Decision；Agent：project-health-review、delivery-execution-review、action-followup；Data：core、Jira / Confluence、execution / action / decision tables | 可分别查看项目、人员、计划、sprint / milestone、部分 risk 和 action | 没有一个结果同时覆盖全部维度；Risk / Decision / Action 来自不同表示；“实际进展”与“目标 / scope”没有共同判断合同。`CONNECT` + `MISSING`，`PV` | IP-029 贡献 execution；IP-030 贡献 dimension / evidence；IP-032 可作为 composer；IP-027 统一结果 |
| S4. 识别本周变化 | 对比上周和本周的计划、进展、风险、人员和行动变化 | UI：Weekly Brief v2 / Snapshots 默认隐藏；API：weekly operation、project snapshots；Service：Weekly Brief composer、snapshot；Domain：execution observations、brief baseline；Agent：weekly-dm-brief-v2；Data：snapshot / observation / operation tables | 可保存部分 snapshot，Execution 有 observation；Weekly Brief 可输出部分 achievements / changes | 没有覆盖所有来源和字段的统一 baseline；snapshot-day、缺失 publication 会产生 partial；核心页面不自然进入此路径。`CONNECT` + `SMALL CHANGE`，`BOTH` | IP-032 是主要组合资产；IP-029 提供时间化 evidence；IP-028 可提供 attention state change |
| S5. 检查证据质量 | 标识来源、过期、缺失、冲突和无法判断 | UI：freshness / connector / advanced outputs 分散；API：freshness、generic use-case result；Service：UseCaseExecutor、public readers；Domain：known / unknown / unavailable / conflicting；Agent：解释 warnings / evidence；Data：sync runs、publications、evidence refs | typed intelligence 已能表达 value state、freshness、evidence 和 warning | legacy 核心页面没有一致呈现；缺少“每个决策字段需要哪些 source”的覆盖规则；冲突通常停留在 capability 内。`CONNECT` + `SMALL CHANGE`，`BOTH` | IP-027 是核心；IP-029 提供 evidence；IP-030 的 missing / conflicting 语义可复用 |
| S6. 生成决策准备结果 | 说明当前状态、本周变化、不确定性和待确认事项 | UI：Overview / Project Health、隐藏 Brief / Attention；API：generic query；Service：Weekly Brief、Attention、Health；Domain：facts、signals、recommendations；Agent：自然语言解释；Data：execution trace / snapshot | 可以分别返回 facts、signals、recommendations 和 partial sections | 没有以单个项目决策为边界的统一输出；现有 brief 依赖面过宽；没有明确“继续 / 介入 / 无法判断”的确认合同。`CONNECT` + `SMALL CHANGE`，`PV` | IP-027、IP-028、IP-029、IP-030、IP-032 均可复用；IP-031 只提供资源维度 |
| S7. DM 确认并形成可执行结果 | DM 确认判断、待补证据或介入事项，并交给 Action / Decision | UI：没有统一入口；API：capability-specific operations；Service：Attention confirm、Weekly snapshot、Action / Decision legacy operations；Domain：Attention、Action、Decision；Agent：局部 preview / confirm；Data：operation / action / decision tables | 可以确认 attention state、保存 brief snapshot、手工添加 action 或 decision | 决策准备结果不能直接形成一组带 evidence 的确认事项；Action 与 Decision 不统一；是否支持真实判断为 `OWNER CONFIRMATION REQUIRED`。`CONNECT` + `MISSING`，`PV` | IP-028 可管理 attention state；IP-032 可保留 snapshot；IP-027 可引用 evidence |

### 3.3 可以直接复用、需要连接和确实缺失

- `REUSE`：Projects、Monthly Plan、Project Health、Jira / Confluence sync、project profiles、execution evidence、UseCaseResult、freshness、Weekly Brief composer、Attention、Action / Decision 基础表。
- `CONNECT / SMALL CHANGE`：项目级 source coverage；跨 reader 的同一 as-of；本周变化；在现有入口中呈现 missing / stale / conflict；从 decision-prep result 到 confirm / action。
- `MISSING`：PPT / Meeting Minutes 的受支持输入合同；覆盖全部维度的项目决策准备合同；统一的“继续 / 介入 / 无法判断”确认结果。

### 3.4 与最小路径无关的现有能力

Staffing capacity policy、完整 HIREF 方案比较、backup / release engineering、interaction memory 不属于本场景的最小决策路径。资源事实可以被读取，但不应把资源决策引擎整体塞入项目证据汇总。

### 3.5 从当前 L2 到一次 L3 的最小补齐

1. 选择一个项目和固定周界面，不追求全 portfolio；
2. 复用现有 Projects / Project Health / Monthly Plan、Jira / Confluence、execution、action 数据；
3. 定义有限且明确的项目决策字段及其 source / freshness / missing / conflict 规则；
4. 生成一个可追溯的“继续 / 介入 / 无法判断”decision-prep result；
5. 让 DM 明确确认结果，并使用现有 snapshot、Action 或 Decision 机制形成可执行后续；
6. 用一个 end-to-end acceptance scenario 证明从刷新证据到确认结果可完成。

`PV` 核心是字段、判断和确认结果；`PH` 核心是入口、调用链、测试、release artifact 和开发者可复现性。

## 4. 场景二：Monthly Plan 兑现检查

### 4.1 真实 DM 决策

DM 需要回答：

> 当前人员释放和实际投入是否使未来 Monthly Plan 不再可信；如果存在偏差，哪些后续项目会受影响，DM 现在应介入什么？

### 4.2 步骤映射

| 步骤 | 需要完成的工作 | 当前 UI / API / Service / Domain / Agent / Data 资产 | 当前能做到什么 | 断点、改造规模与类型 | IP-027～IP-032 价值 |
|---|---|---|---|---|---|
| S1. 确认正式计划基线 | 选择有效 plan version 和未来月份 allocation | UI：Monthly Plan；API：`/api/allocations`, project plans；Service：repository / workforce planning import；Domain：Plan Version、Monthly Allocation；Agent：team / planning routes；Data：`plan_versions`, `monthly_allocations`, coverage | 能展示按月人员与项目安排，基础数据有真实业务基础 | 默认 plan 选择隐式，随包 demo 选到空 plan；baseline / scenario / active 的产品语义未成为显式合同。`SMALL CHANGE`，`BOTH` | IP-031 复用 planning publication / coverage；IP-027 可表达 baseline evidence |
| S2. 获取实际投入和当前可用性 | 对比计划与人员当前实际投入 | UI：Team；API：employees、team workload；Service：current-state staffing reader、workload；Domain：Assignment、Member Load；Agent：team-workload-overview；Data：assignments、current-state staffing publications | 能显示 current load、项目成员和部分 staffing facts | 没有明确的“实际投入”权威定义、观测周期或历史序列；Jira 活动不能直接等同 FTE 投入。`MISSING` + `SMALL CHANGE`，`PV` | IP-031 提供 current-state / capacity reader；IP-027 可表达 observed / unknown |
| S3. 判断当前项目能否按期释放 | 把项目进展 / milestone 与计划释放月份关联 | UI：Projects、Project Health、Delivery Execution；API：health / generic query；Service：execution review、health；Domain：Milestone、Release、Sprint、Allocation；Agent：delivery-execution-review；Data：execution facts、Jira health、allocations | 能看到 sprint、release、milestone 与未来 allocation | 没有确定性规则把交付证据转换为“人员可否按某月释放”；缺少项目完成 / release 与 allocation end 的关系。`MISSING`，`PV` | IP-029 提供 schedule / milestone evidence；IP-030 可提供 delivery state，但不能自行证明 release |
| S4. 计算 Leave / BAU / 离职 / HIREF 影响 | 识别个人可用量和 contract / demand 变化 | UI：Team、HIREF、Capacity；API：employees、hiref、generic capacity；Service：resource capacity、contract continuity；Domain：Capacity、HIREF、Member；Agent：capacity heatmap、contract continuity；Data：capacity observations、employees、hiref、coverage publications | 可计算 leave / BAU / non-project capacity；可查看 HIREF 和 contract continuity | 数据来自不同 import / publication；离职的时间化影响和 HIREF delay 对月份的传播没有统一场景输出。`CONNECT` + `SMALL CHANGE`，`BOTH` | IP-031 是核心；IP-027 表达 freshness；IP-028 可将严重偏差变为 attention |
| S5. 识别计划偏差 | 判断持续超配、低配或与 baseline 的偏离 | UI：Monthly Plan / Team / Capacity；API：allocations、workload、capacity；Service：staffing facts、capacity heatmap；Domain：Allocation、Capacity；Agent：resource-capacity-heatmap；Data：plan / current-state / capacity tables | 能分别提供计划 allocation、current load、effective capacity 和 overload signals | 没有跨周期的 plan-vs-actual variance 合同，也没有“持续偏离”的时间窗口规则。`MISSING`，`PV` | IP-031 可复用计算输入；IP-027 提供 fact / signal contract |
| S6. 传播到后续项目 | 显示人员不能释放会影响哪些未来项目和角色 | UI：Monthly Plan；API：allocations；Service：staffing read model；Domain：future allocation、project priority；Agent：staffing assess；Data：monthly allocations / project | 可查同一人员的未来分配和候选项目 | 没有从 source project delay 到 downstream project 的月度 cascade / impact result；项目 priority 和替代人员影响需人工拼接。`MISSING`，`PV` | IP-031 提供候选和 capacity；IP-029 提供 delay evidence；IP-028 可承载影响 signal |
| S7. DM 确认介入决定 | 确认保持计划、补证据、调整人员 / 日期或创建 action | UI：没有统一入口；API：staffing / attention operations 分散；Service：staffing proposal、attention、action / decision；Domain：Proposal、Action、Decision；Agent：局部 preview / confirm；Data：proposal / operation / action tables | 可对单一 staffing proposal preview / confirm，可手工记录 action / decision | 没有 Monthly Plan exception 的 decision package；确认后如何影响 baseline、source project 和 downstream project不统一。`CONNECT` + `MISSING`，`PV` | IP-028 提供 attention lifecycle；IP-031 提供 staffing proposal；IP-027 提供证据结果 |

### 4.3 可以直接复用、需要连接和确实缺失

- `REUSE`：Monthly Plan、Team、HIREF、plan / allocation、current-state staffing、capacity、contract continuity、execution milestone、staffing proposal。
- `CONNECT / SMALL CHANGE`：明确 baseline 选择；将 leave / BAU / HIREF / contract facts 对齐到同一月份；把 exception 连接到现有 Attention / Action / Decision。
- `MISSING`：受信任的 actual投入时序；release forecast；持续偏差规则；source project → person → downstream project 的 impact result。

### 4.4 与最小路径无关的现有能力

Project profile 的长文本、Confluence action content、interaction memory、Weekly Brief 的非资源 sections 和 Project Health 的 quality / governance 配置不属于 Monthly Plan 兑现检查的最小路径。

### 4.5 从当前 L2 到一次 L3 的最小补齐

1. 固定一个正式 plan version 和一个检查月份窗口；
2. 明确“计划投入”“实际投入”“effective capacity”和“预计释放”的来源与缺失语义；
3. 只实现一条可解释的偏差链：当前项目不能按月释放 → 指定人员 / 角色 → 后续项目受影响；
4. 输出 evidence、freshness、assumptions 和无法判断项；
5. 让 DM 确认一个介入决定，并用现有 proposal、Action 或 Decision 形成可执行结果；
6. 用跨两个月、两个项目和一个共享人员的 scenario test 验证。

`PV` 核心是 actual、release 和 downstream impact 的业务定义；`PH` 核心是 baseline 选择、数据准备、入口、测试和可重复发布。

## 5. 场景三：需求变化后的资源决策

### 5.1 真实 DM 决策

DM 需要回答：

> 当 scope、工作量、日期或技能需求变化时，在内部吸收、调 scope、调日期、临时增援、跨项目调人和 New Hire / HIREF 之间，应选择哪个方案；它对目标项目、来源项目和未来 Monthly Plan 有什么影响？

### 5.2 步骤映射

| 步骤 | 需要完成的工作 | 当前 UI / API / Service / Domain / Agent / Data 资产 | 当前能做到什么 | 断点、改造规模与类型 | IP-027～IP-032 价值 |
|---|---|---|---|---|---|
| S1. 描述需求变化 | 记录目标项目、变化类型、effort、日期、角色 / skill | UI：无统一 change form；API：无通用 demand API；Service：staffing assess 接受 demand；Domain：`StaffingDemand`、Project Profile、Decision / CR；Agent：staffing route；Data：proposal request JSON、project / CR tables | Staffing 可以接收 project、period、role、effort、allocation 等请求 | Scope / date / skill change 没有共同业务对象；ServiceNow CR 不等于资源需求；请求未成为可复用的 decision case。`SMALL CHANGE` + `MISSING`，`PV` | IP-031 的 staffing demand 可复用；IP-027 可定义输入 / 输出合同 |
| S2. 建立当前团队和计划基线 | 获取目标项目团队、全局负荷、capacity 和未来 allocations | UI：Projects、Team、Monthly Plan、HIREF；API：projects、employees、allocations、hiref；Service：staffing read model、capacity、contract continuity；Domain：Member、Allocation、Capacity、HIREF；Data：core + publications | 可列出候选、当前负荷、future allocation、capacity 和部分 contract 信息 | authority / freshness 可能不完整；demo assess 非 decision-ready；计划与实际仍需人工判断。`REUSE` + `SMALL CHANGE`，`BOTH` | IP-031 是主要基础；IP-027 表达证据与 blocker |
| S3. 形成候选方案 | 生成内部吸收、scope、date、增援、跨项目调人、HIREF 方案 | UI：无统一 comparison；API：无 options endpoint；Service：staffing candidate / proposal、HIREF review；Domain：Proposal、Placeholder、HIREF；Agent：staffing / HIREF routes；Data：staffing proposals、hiref、allocations | 能评估内部候选并生成一个 staffing proposal；能显示 open HIREF / placeholder | 调 scope / 调日期不是 staffing engine 的正式 alternative；临时增援与跨项目调人没有独立语义；不能保证六类方案可比较。`MISSING`，`PV` | IP-031 只覆盖人员 / capacity 选项；IP-029 可提供 schedule evidence；IP-030 可说明风险但不生成方案 |
| S4. 评估目标项目影响 | 比较每个方案对交付、capacity、skill 和 risk 的效果 | UI：advanced views 分散；API：generic query；Service：staffing feasibility、execution / health readers；Domain：Capacity、Execution、Health；Agent：多个 use cases；Data：facts / signals | 可计算候选 availability / capacity blockers，并读取进度与健康 facts | 没有统一 option impact contract；skill fit、scope / date trade-off 和项目结果需人工解释。`CONNECT` + `MISSING`，`PV` | IP-027 统一 result；IP-029 / IP-030 / IP-031 提供不同影响维度 |
| S5. 评估来源项目和未来 Monthly Plan | 显示调人造成的 source project 与后续月份影响 | UI：Monthly Plan、Projects；API：allocations / projects；Service：staffing read model；Domain：Assignment、Allocation、Project Priority；Agent：staffing；Data：monthly allocations | 可查候选人的当前 / 未来项目和 allocation | 没有 option-specific before / after plan delta；来源项目 release risk 和替代资源未形成确定性结果。`MISSING`，`PV` | IP-031 提供 capacity / candidate；IP-029 可提供来源项目 delivery evidence；IP-028 可标记风险 |
| S6. 并列比较方案和不确定性 | 用共同尺度展示收益、代价、风险、缺失证据 | UI：无统一 view；API：无统一 comparison result；Service：UseCaseResult 可表达 facts / signals / alternatives；Domain：Recommendation / Alternative；Agent：可解释；Data：execution trace | 结果合同已有 `alternatives`、warnings、assumptions 等容器 | 现有 staffing output 没有覆盖全部方案的共同 impact；业务权重和不可比较项未定义。`CONNECT` + `MISSING`，`PV` | IP-027 是主要合同资产；IP-032 的 composer 思路可参考但不应直接复用全部 brief |
| S7. DM 选择并执行 | 确认方案、写入 allocation / plan 或形成 HIREF / scope / date action | UI：无统一入口；API：局部 operations；Service：staffing propose / preview / confirm、Action / Decision；Domain：Proposal、Allocation、HIREF、Decision；Agent：controlled write route；Data：proposal / allocation / decision / action | 单一 staffing proposal 可受控确认；其他方案可手工记录 action / decision | 不能确认一个跨六类方案的 decision package；非人员方案没有确定性执行路径；后续 plan 影响未一并确认。`REUSE` + `MISSING`，`PV` | IP-031 提供受控 staffing 写；IP-028 可创建 attention；IP-027 保留 evidence |

### 5.3 可以直接复用、需要连接和确实缺失

- `REUSE`：staffing demand / feasibility / proposal、Team、Projects、Monthly Plan、capacity、HIREF、execution / health evidence、controlled write。
- `CONNECT / SMALL CHANGE`：把需求变化输入保存在一次 decision case 中；让候选结果引用目标 / 来源项目和未来 allocations；复用统一 evidence / assumption / alternative contract。
- `MISSING`：六类方案的共同语义；scope / date alternative；option-specific cross-project plan delta；一个覆盖选择与执行的 decision package。

### 5.4 与最小路径无关的现有能力

Weekly Brief snapshot、connector status、interaction memory、Project Health config 和通用 onboarding export 不属于方案比较的最小计算路径。Action closure 属于选择后的下游场景，不应先与比较引擎混为一体。

### 5.5 从当前 L2 到一次 L3 的最小补齐

1. 只选择一种高频需求变化，并定义明确输入；
2. 以现有 staffing / capacity / Monthly Plan 为基线，不重新建设资源模型；
3. 至少提供内部吸收、跨项目调人、HIREF 和一个非人员方案的共同 impact 表达；
4. 对目标项目、来源项目和未来 plan 给出 before / after、evidence、assumption 和 unknown；
5. 让 DM 选择一个方案并通过既有 controlled-write / Action / Decision 形成执行结果；
6. 用一个包含 source project、target project 和 downstream month 的 acceptance scenario 验证。

该场景的 `PV` 缺口最大，尤其是 option semantics 和 cross-project impact。`PH` 不是主要阻碍；在业务合同明确前，不应先重构或扩页面。

## 6. 场景四：风险与行动闭环

### 6.1 真实 DM 决策

DM 需要回答：

> 对一个已发现的风险或资源问题，谁在何时前完成什么动作、依据什么证据判断完成；逾期如何升级，后续证据是否证明问题真正关闭？

### 6.2 步骤映射

| 步骤 | 需要完成的工作 | 当前 UI / API / Service / Domain / Agent / Data 资产 | 当前能做到什么 | 断点、改造规模与类型 | IP-027～IP-032 价值 |
|---|---|---|---|---|---|
| S1. 发现并解释风险 | 从 project、execution、capacity 或人工输入识别问题和 evidence | UI：Project Health、Attention / Capacity / Execution 隐藏页；API：health / generic query；Service：health、attention、execution、capacity；Domain：Fact、Signal、Risk text；Agent：多个 review use cases；Data：health / evidence / attention tables | 可产生部分 facts、signals、recommendations 和 evidence refs；也可人工记录 risk | 没有统一 Risk lifecycle；legacy health、profile risk 和 attention signal 语义不同。`CONNECT` + `MISSING`，`PV` | IP-027 统一 evidence；IP-028 管理 signal；IP-029 / 030 / 031 提供不同 producer |
| S2. 转为 Action | 从风险提出一个具体行动 | UI：无默认统一 action入口；API：无 risk-to-action operation；Service：legacy ActionItemsService / CLI、Confluence actions；Domain：Action Item、Action Tracker、Recommendation；Agent：action route；Data：`action_items`, `action_tracker` | 可手工 add / list / done action，Confluence action 可同步 | risk / signal 不能直接生成带来源证据的 action proposal；两套 action 表示并存。`CONNECT` + `SMALL CHANGE`，`PV` | IP-028 recommendation 可作为 proposed action；IP-027 提供 evidence refs |
| S3. 完整定义 Action | 保存 Owner、Due Date、Evidence、Closure Condition | UI / API：无统一 contract；Service：action add；Domain：Action、Attention operation；Agent：可收集部分参数；Data：action tables、attention history | Action 有 owner / due date 等基础字段，Attention 有 subject / history | Closure Condition 和 evidence linkage 不完整；字段在两套 Action 中不一致；谁是 authoritative owner 不明确。`SMALL CHANGE` + `MISSING`，`BOTH` | IP-027 可复用 evidence / subject；IP-028 可复用 lifecycle identity |
| S4. DM 确认行动 | 预览并确认责任、期限和关闭条件 | UI：无统一入口；API：Attention 有 preview / confirm，Action 没有同等合同；Service：capability-specific controlled operations；Domain：Operation / Action；Agent：propose / preview / confirm pattern；Data：operation tables | Attention state 可受控确认；Action 可直接 CLI 写入 | Action 创建没有统一 propose / preview / confirm；确认的 risk 与 action 之间缺少稳定关联。`CONNECT` + `SMALL CHANGE`，`PV` | IP-028 的 operation pattern 可复用；IP-027 可校验引用 |
| S5. Reminder / Escalation | 在到期前提醒、逾期后升级 | UI：Overview / brief / attention 可被动查看；API：action follow-up / attention query；Service：action follow-up、attention rules；Domain：Due Date、Overdue、Attention；Agent：按需 query；Data：`v_overdue_actions`, attention tables | 可查询 overdue action，Weekly Brief / Attention 可显示部分事项 | 没有 scheduler、主动通知或统一 escalation rule；用户必须主动查询。`MISSING`，`PV`（主动价值）+ `PH`（运行机制） | IP-028 是主要 lifecycle 资产；IP-032 可在周回顾中呈现，但不是主动提醒 |
| S6. 更新结果并声明完成 | 记录完成状态和结果证据 | UI：无统一入口；API：无统一 action result；Service：action done、Attention ack / resolve；Domain：Action status、Attention history；Agent：局部 route；Data：action / history | 可把 action 标为 done，attention 可改变状态 | 完成动作不要求结果 evidence；ack / resolve 与 action done 不是同一闭环。`CONNECT` + `MISSING`，`PV` | IP-028 提供 history；IP-027 可引用 completion evidence |
| S7. 验证 Closure Condition | 用后续 evidence 验证问题确实关闭，否则重开 / 升级 | UI / API：无统一验证入口；Service：producer 可重新计算 signal，Attention reconcile 可更新 state；Domain：Signal evaluation / Action closure；Data：new evidence、attention history | 某些 signal 可在新 evidence 后重新 reconcile | 没有 action closure condition evaluator，也没有 signal ↔ action ↔ closure result 的稳定关联。`MISSING`，`PV` | IP-028 reconciliation 最接近；IP-029 / 030 / 031 可提供后续 evidence；IP-032 可回顾状态 |

### 6.3 可以直接复用、需要连接和确实缺失

- `REUSE`：facts / signals / recommendations、Attention identity / history / reconcile、Action add / list / done、due date / overdue view、Weekly Brief、controlled-operation pattern。
- `CONNECT / SMALL CHANGE`：signal → proposed action；统一一个 Action authority；补 evidence link 和 closure condition；让 action 使用 preview / confirm；完成时记录结果 evidence。
- `MISSING`：主动 reminder / escalation runtime；closure condition 验证；signal、action 和 closure result 的稳定端到端关联。

### 6.4 与最小路径无关的现有能力

完整 onboarding / export、staffing capacity policy、Project Health configuration、connector setup 和 interaction memory 不属于 Action closure 的最小路径。它们可以提供上游 evidence，但不应成为完成 Action workflow 的前置要求。

### 6.5 从当前 L2 到一次 L3 的最小补齐

1. 选择一种现有可靠 signal 或人工确认 risk；
2. 复用现有 Action 和 controlled-write pattern，形成包含 owner、due date、evidence、closure condition 的 proposal；
3. DM preview / confirm 后持久化并可在现有入口查看；
4. 完成时要求提交 result evidence；
5. 用 closure condition 验证成功或保持 open；
6. 用“发现 → 确认 action → 完成 → evidence 验证”的 scenario test 证明 L3。

主动 reminder / escalation 是从 L3 继续走向 L4 的关键缺口，不应被悄悄算入本次最小 L3。

## 7. 四个场景的 Product Value 与 Productization / Handover 分界

| 问题 | 类型 | 原因 |
|---|---|---|
| 项目全景需要哪些字段、怎样判断继续 / 介入 / 无法判断 | PV | 决定产品是否帮助 DM 判断 |
| actual投入、release forecast、持续偏差和 downstream impact 定义 | PV | 是 Monthly Plan 决策的核心业务语义 |
| 六类资源方案的共同 option / impact contract | PV | 决定方案是否真正可比较 |
| Risk → Action → Closure Condition → result verification | PV | 决定是否形成业务闭环 |
| legacy / publication authority、default plan、fallback | BOTH | 同时影响业务结果正确性和维护安全 |
| existing capability 连接到一个默认用户入口 | BOTH | 影响用户完成工作，也影响调用链可追踪性 |
| source freshness / missing / conflict 的统一呈现 | BOTH | 既是决策安全要求，也是实现合同 |
| README、setup、demo、配置和数据准备可复现 | PH | 影响新开发者和 operator 能否独立运行 |
| UI → API → Service → Domain → Data owner map | PH | 影响安全修改和交接，不直接定义业务价值 |
| acceptance scenario → tests → commit / release artifact | PH | 影响验收和发布证据 |
| source Agent 与 generated Agent 一致性 | PH | 影响发行行为可预测和可维护 |

## 8. Golden Path 候选

以下候选都以达到一次 L3 DM 判断 / 决策为目标，不默认创建新页面、Agent、Service 或表。实际是否需要新增持久化字段，必须在 TPO 选择后通过有界 discovery 确认。

### GP-1：单项目周度证据与介入决策

**支持的真实 DM 决策**

对一个项目确认“继续按计划 / 需要介入 / 当前无法可靠判断”，并明确需要确认或跟进的事项。

**复用的现有资产**

Projects、Project Health、Monthly Plan、Jira / Confluence sync、project profiles、execution evidence、freshness、UseCaseResult、Weekly Brief composer、Attention / Action / Decision。

**最小新增或改造范围**

- 定义有限项目 decision fields 和 source coverage；
- 连接现有 readers，统一 as-of、missing、stale、conflict；
- 在现有页面或 Agent 路由中提供一个 decision-prep result；
- 复用 snapshot / Action / Decision 完成 DM 确认，不先新增页面。

**端到端用户路径**

选择项目 → 刷新 / 读取已有 evidence → 查看 current state + weekly change + evidence quality → DM 确认继续 / 介入 / 无法判断 → 保存决定并形成必要 Action。

**主要数据缺口**

目标 / scope / plan / progress / risk / decision / action 的统一字段覆盖；PPT / Meeting Minutes 输入；跨来源 baseline 和 conflict 规则。

**产品验收方式**

使用一个包含 fresh、stale、missing 和 conflicting evidence 的项目 scenario，DM 无需手工打开多个隐藏能力即可完成三选一判断；每个结论引用来源，无法判断不被包装成健康；确认结果和 Action 可追踪。

**对开发交接的影响**

建立第一条 Business Scenario → UI / Agent → Use Case → Data → Test → Release 的完整链，并迫使 Project Health 两套语义、source authority 和 generated Agent 行为得到说明。

### GP-2：Monthly Plan 释放与下游影响决策

**支持的真实 DM 决策**

确认某人员 / 角色能否按计划从当前项目释放；若不能，决定是否介入并识别受影响的后续项目。

**复用的现有资产**

Monthly Plan、Team、Projects、HIREF、plan / allocation、current-state staffing、capacity、contract continuity、execution milestone、staffing feasibility / proposal、Attention。

**最小新增或改造范围**

- 显式固定 plan baseline 和月份窗口；
- 定义一个可信 actual投入来源和一个 release 判断规则；
- 连接人员未来 allocations，生成一层 downstream impact；
- 复用 proposal / Action / Decision 完成介入确认。

**端到端用户路径**

选择 plan / 月份 → 查看计划与 actual / capacity → 识别不能按期释放的人或角色 → 查看受影响的后续项目 → DM 确认保持、补证据或介入 → 保存可执行结果。

**主要数据缺口**

actual投入时序、release forecast、持续偏差窗口、人员离开 source project 与 downstream project 的影响规则。

**产品验收方式**

一个包含两个项目、一个共享人员、两个月份及 leave / BAU 或 HIREF 约束的 scenario；系统正确指出 source delay、downstream impact、证据与假设，DM 能确认一个介入结果。

**对开发交接的影响**

必须明确 default plan、legacy / publication authority、capacity prerequisites 和 plan-vs-actual 规则，从而降低目前最严重的数据选择知识单点。

### GP-3：风险到 Action 的可验证关闭

**支持的真实 DM 决策**

对一个已确认风险决定具体行动、负责人、期限和关闭条件，并确认后续 evidence 是否证明风险关闭。

**复用的现有资产**

UseCase facts / signals / evidence、Attention identity / history / reconcile、Action add / list / done、due date / overdue view、controlled write、Weekly Brief。

**最小新增或改造范围**

- 选择一个现有 signal 或人工 risk 作为起点；
- 将其连接到一个 authoritative Action；
- 补 evidence、closure condition 和 preview / confirm；
- 完成时记录 result evidence，并复用 producer / reconcile 验证 closure。

**端到端用户路径**

发现并解释风险 → 生成 Action proposal → DM 确认 owner / due / closure → 执行并记录结果 → 系统依据后续 evidence 验证关闭或保持 open。

**主要数据缺口**

Action authority、risk / signal 到 Action 的引用、closure condition、result evidence；主动 reminder / escalation 仍是 L4 后续缺口。

**产品验收方式**

一个 signal 在初始 evidence 下 active；DM 确认 Action；完成时提交 result evidence；后续 evaluation 只有在 closure condition 满足时关闭，否则保持 open 并解释原因。

**对开发交接的影响**

把 Attention、Action、evidence 和 controlled write 从四条分散实现连接成一条可测试链；同时明确 lifecycle owner，降低 `attention/service.py` 和双 Action 模型的知识风险。

## 9. TPO 选择提示

- GP-1 复用面最广，最贴近“项目全景和决策准备”，但需要先严格限制字段和来源范围；
- GP-2 最贴近 Monthly Plan 的独特产品价值，也最依赖尚未明确的 actual / release 业务定义；
- GP-3 边界最容易控制，最接近形成可验证闭环，并可为其他场景提供统一 follow-up 出口；
- 场景三的完整六方案比较存在较大的 `PV` 缺口，不建议在没有 TPO 先限定高频变化类型前作为第一个 Golden Path。

本文件完成后停止。下一步仅由 TPO 选择一个 Golden Path 或要求进一步收紧候选，不自动进入设计或实现。
