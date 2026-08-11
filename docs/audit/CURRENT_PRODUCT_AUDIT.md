# Current Product Audit

审计日期：2026-08-11

审计对象：收到的 release source snapshot（ZIP SHA-256：`0b870296fd1212de0f160d2e812c0ec9e6bacc6a07380fcad35fdecffb8eba40`）

审计性质：只读产品审计；未连接真实 Jira / Confluence，未修改业务代码、数据库设计或 Agent 指令

该 transport snapshot 不包含可验证的 Git 历史，因此本审计能确认“快照内代码是什么”，不能独立确认它对应哪个远端 commit。快照内文档的 branch / status 声明只按 `DOC` 证据处理。

## 0. 审计背景与演进边界

本次审计不是 Greenfield 设计，也不以推翻现有系统为目标。后续方向是保留已经验证有价值的代码、数据模型、连接器和安全写入机制，找出它们为什么没有连接成真正可用的 Delivery Manager 工作流，再通过增量连接、修复、简化和补齐关键断点形成产品。

产品负责人的角色将逐步从个人开发者转为 TPO：负责业务场景、产品能力、优先级、验收标准、Roadmap 和产品决策；实现细节、模块维护、测试和交付证据应能由其他开发人员接手。

因此，本审计采用以下边界：

1. 先判断现有资产能否复用，不用“架构不够整洁”作为重写理由；
2. 只有当模块边界直接阻碍 Golden Path 修改、测试或交接时，才记录为重构候选；
3. 优先寻找已有能力之间的断点，而不是继续增加页面、Service、Agent 或表；
4. 把“产品可用性不足”和“代码没有实现”分开；
5. 本文件只提供 Roadmap 输入，不生成大而全的实施 Roadmap。

## 1. 结论先行

如果只看实际代码和本次可复现行为，而不采用规划文档中的完成声明，当前产品是：

> 一个面向 Delivery Manager 的本地数据看板与结构化查询工具。它已经能够集中查看项目、人员、HIREF 和 Monthly Plan，并能显示有限的 Jira / Confluence 项目状态；同时包含一批可以通过 CLI、Dashboard API 或 Copilot 调用的分析引擎，但这些引擎大多仍是被动查询或受控操作，尚未组合成 DM 日常判断、确认、执行和跟进的完整闭环。

产品目前真正稳定解决的是“把几类 DM 核心数据集中到一个本地界面中查看”。它尚未被证据证明能够稳定解决“主动发现问题、解释证据、辅助决策、执行决定并跟踪结果”这一更高层问题。

核心事实：

- 默认 Dashboard 只开放 6 个页面：Overview、Projects、Team、HIREF、Monthly Plan、Project Health。
- Owner 已实际使用前 5 个页面，人员、项目和 Monthly Plan 等能力具有真实业务基础；这只证明进入过实际使用，不证明页面足以支持一次 DM 判断或决策。Project Health 的业务含义仍存在争议。
- 代码中另有 7 个实验页面，但默认隐藏；存在页面代码不等于进入真实工作流。
- 注册了 15 个结构化 Use Case；多数需要用户知道能力名称并主动调用。
- 干净数据库初始化会创建 110 张应用表和 2 个视图；数据和维护成本显著高于当前 6 个可见页面所体现的产品面。
- 没有发现通用的项目、人员、HIREF 或 allocation 单条增量更新入口。核心数据日常修改仍主要依赖重新导入或专用操作命令。
- “导出当前完整业务数据为可继续维护的标准 Excel”尚未形成可复现的通用闭环。
- 当前没有已验证的 L3/L4 DM 决策工作流；也没有发现面向用户的定时调度、主动通知或自动执行闭环。

## 2. 证据规则与成熟度

### 2.1 证据标签

| 标签 | 含义 |
|---|---|
| `CODE` | 在实际源代码中找到入口、调用链、数据结构或持久化实现 |
| `RUNTIME` | 本次在隔离的合成数据库副本上实际执行并获得结果 |
| `TEST` | 对应自动化测试在本次审计中通过；只证明测试覆盖的行为 |
| `DOC` | 文档或进度文件中的声明；不自动视为已实现或可用 |
| `OWNER-USED` | Owner 明确实际使用过系统或能力；不自动代表真实数据、重复工作流或决策有效 |
| `OWNER-REAL-DATA` | Owner 明确该能力在公司环境使用真实数据运行过；本次审计未重新执行 live verification |
| `OWNER-MEANING` | Owner 明确认可或否定输出的业务含义 |
| `OWNER-REPEATED` | Owner 明确该能力已进入固定、重复的工作流程 |
| `OWNER-DECISION` | Owner 明确该能力足以支持一次实际判断或决策 |
| `OWNER CONFIRMATION REQUIRED` | 超出当前明确反馈，不能从使用过、返回结果或测试通过自行推断 |
| `INFERENCE` | 根据代码和行为做出的合理推断 |
| `UNVERIFIED` | 需要真实连接器、真实用户操作或实际部署环境，本次未验证 |

本次可采用的 Owner 背景事实仅限：

- Owner 个人构建并实际使用过现有系统；
- Jira 和 Confluence 同步已在公司环境使用真实数据运行过；
- 人员、项目、Monthly Plan 等基础页面和能力具有实际业务基础；
- IP-027～IP-032 尚未成为 Owner 固定使用的工作流；
- Project Health 尚不足以代表完整项目健康判断；
- 当前没有形成稳定的项目全景、规划、风险判断和跟进闭环。

除上述事实外，对“业务含义正确”“重复采用”或“足以决策”的判断均标记为 `OWNER CONFIRMATION REQUIRED`。

### 2.2 成熟度

| 等级 | 判定标准 |
|---|---|
| L0 | 只有设计、文档或占位 |
| L1 | 存在代码，但没有进入真实用户流程 |
| L2 | 局部可用，用户需要人工拼接信息、判断或后续操作 |
| L3 | 用户可以完成一次端到端的业务判断或决策 |
| L4 | 包含主动发现、证据解释、DM 确认、执行和后续闭环 |

成熟度按用户可完成的工作流评定，不按代码量、页面存在、接口返回 200 或单元测试数量评定。

## 3. 当前产品的用户与入口

### 3.1 主要用户

主要业务用户是单个 Delivery Manager。代码中的交互方式同时假设该用户具备一定操作能力：

1. 通过本地 Dashboard 浏览数据；
2. 通过 VS Code Copilot / Agent 用自然语言触发结构化命令；
3. 必要时通过 `pm` CLI 完成导入、同步、预览和确认；
4. 在首次使用或迁移时准备标准 Excel / JSON / CSV 数据源。

因此，当前实际用户模型并不是“只会使用一个产品界面的 DM”，而是“能够在 Dashboard、Copilot 和 CLI 之间切换的 DM / 本地操作员”。这是产品使用成本的一部分。

证据：

- `CODE`：`.github/agents/delivery-manager.agent.md` 定义 Copilot 路由。
- `CODE`：`src/pm_agent/cli/app.py` 注册 onboarding、staffing、attention、weekly-brief、project-health、connector 等命令组。
- `CODE`：`src/pm_agent/dashboard/server.py` 提供 Dashboard 与 API。
- `OWNER-USED`：Owner 个人构建并实际使用过现有系统。是否通过 Copilot 完成过特定决策为 `OWNER CONFIRMATION REQUIRED`。

### 3.2 当前可见产品入口

| 入口 | 实际作用 | 可见性 | 证据 |
|---|---|---:|---|
| Dashboard `/` | 浏览 Overview、Projects、Team、HIREF、Monthly Plan、Project Health | 默认可见 | `CODE`、`RUNTIME`、`OWNER-USED`；决策有效性待确认 |
| Copilot Agent | 把自然语言路由为一个结构化查询或专用操作 | 已配置，但依赖 Agent 文件和 CLI | `CODE`；真实 Agent 会话覆盖 `UNVERIFIED` |
| `pm onboarding` | 首次数据导入、预览、确认和部分导出 | CLI | `CODE`、`TEST`、部分 `RUNTIME` |
| `pm health` / Project Health API | 同步 Jira / Confluence 状态并展示健康信息 | CLI + Dashboard | `CODE`、`OWNER-REAL-DATA`；当前快照 live verification 未执行 |
| `pm staffing` | 评估和受控确认人员安排 | CLI / Agent | `CODE`、`TEST`、部分 `RUNTIME` |
| Attention / Weekly Brief / advanced reviews | 结构化分析与有限状态操作 | API / CLI / Agent；Dashboard 默认隐藏 | `CODE`、`TEST`、`RUNTIME`；`OWNER-REPEATED` 为否 |

## 4. 已形成的用户工作流

### 4.1 工作流 A：初次导入后查看核心业务数据

**路径**：准备标准 Excel → onboarding profile / preview → confirm import → 打开 Dashboard → 查看 Overview / Projects / Team / HIREF / Monthly Plan。

- 业务问题：把分散的项目、人员、月度安排和招聘需求集中到本地系统。
- 输入：标准 workbook，包含 Setup、Members、Projects、Allocations、Capacity，可选 HIREF Requests。
- 输出：本地数据库中的项目、员工、plan version、monthly allocations、capacity 和 HIREF 数据，以及 5 个核心页面。
- 上游：Excel schema、onboarding profile、校验、确认导入。
- 下游：Dashboard、team workload、staffing、capacity、weekly brief。
- 证据：`CODE`、`TEST`、`OWNER-USED`。
- 操作完整度：workbook preview → confirm → 数据落库是一条完整的操作型工作流；它建立数据基础，不构成 Delivery Intelligence 判断或决策。
- Delivery Intelligence 成熟度：**L2**。导入后仍需用户自行查看、拼接和判断；随包 demo 的默认 plan 选择还会使 Monthly Plan 返回空结果。

### 4.2 工作流 B：通过 Dashboard 进行日常查看

**路径**：启动 Dashboard → 选择 6 个可见 tab → 查看聚合信息。

- Overview、Projects、Team、HIREF、Monthly Plan 已被 Owner 实际使用，具有真实业务基础；业务含义是否足以支持具体判断或决策为 `OWNER CONFIRMATION REQUIRED`。
- Project Health 能同步 sprint / Jira 状态，但缺少稳定的 progress、risk、blocker 等共同判定维度，当前输出不能被等同于“项目整体是否健康”。
- 这是读流程，不包含发现后的确认、执行和后续跟踪。
- 成熟度：6 个页面均为 **L2**。前 5 页主要支持信息查看；Project Health 还存在健康语义不足。

### 4.3 工作流 C：Jira / Confluence 同步后查看状态

**路径**：配置项目和 board / page registry → 执行 sync → 写入 sync runs / Jira / Confluence 数据 → Dashboard Project Health 或结构化 Use Case 读取。

- 业务问题：集中查看迭代、release、变更请求和 Confluence 状态信息。
- 输入：Jira board 配置、Confluence page registry、连接器凭据和远端数据。
- 输出：Jira issues / sprints / health snapshots、Confluence pages / status、同步记录。
- 证据：`CODE`、`TEST`、`OWNER-REAL-DATA`。
- 真实环境结果：Owner 确认 Jira / Confluence 同步曾在公司环境使用真实数据运行；本次审计没有重新连接或验证当前快照的 live behavior。
- 成熟度：**L2**。同步与读取存在，但没有证据证明已经形成稳定的日常判断闭环。

### 4.4 工作流 D：Copilot 结构化查询

**路径**：用户提问 → Agent 预读 interaction memory → 选择一个 Use Case → CLI / API 执行确定性查询 → Agent 解释 facts / signals / recommendations。

- 业务问题：让 DM 用自然语言调用既有确定性查询。
- 输入：自然语言、当前本地数据库、Use Case 参数。
- 输出：结构化 facts、signals、recommendations、warnings 和 evidence。
- 证据：`CODE`、`TEST`；本次直接执行多个 Use Case 的 runtime，而非完整 Copilot UI 会话。
- 局限：Agent 是路由器，不是持续监控器；没有通用核心数据增量更新命令；不同工作仍需用户知道正确入口。
- 成熟度：**L2**。

### 4.5 工作流 E：受控 Staffing 决策

**路径**：assess demand → propose → preview → confirm / reject / cancel → 写入 proposal / assignment / allocation 相关状态。

- 业务问题：在人员负荷和 capacity 约束下评估并确认人员安排。
- 输入：项目、时间范围、角色、effort、最小 allocation、现有 staffing / capacity publications。
- 输出：候选人、可行性、安全阻断、proposal 和确认结果。
- 证据：`CODE`、`TEST`；合成 demo 上 assess 能返回候选，但 `decision_ready=false`，因为必要 publication / freshness 不完整。
- 真实用户采用：尚未成为 Owner 固定工作流；是否曾完成单次真实 staffing decision 为 `OWNER CONFIRMATION REQUIRED`。
- 成熟度：**L2**。受控写入链存在，但本次没有证据证明可直接完成一次真实决策。

### 4.6 工作流 F：Attention / Execution / Layered Health / Capacity / Weekly Brief

这些能力都能在代码层被调用，部分在合成 demo 上返回非空 facts / signals / recommendations；但默认 Dashboard 隐藏，IP-027～IP-032 尚未成为 Owner 固定工作流，并且不同能力依赖不同 publication、derivation、freshness 和 snapshot。

- 入口：通用 `/api/tool/query/<use_case_id>`、CLI、Copilot Agent；部分有专用 operation API。
- 用户需要人工决定先同步、导入、derive、reconcile 或 snapshot，再查询结果。
- 没有主动通知，没有自动执行决定，没有对 action 的统一闭环。
- 成熟度：整体 **L2**；部分基础设施仅 **L1**。

### 4.7 工作流 G：导出完整数据用于继续维护和升级

期望路径是：当前数据库 → 导出完整标准 Excel → 用户继续维护或导入新版。

实际状态：

- `pm onboarding export-workbook` 存在，并声明导出当前 planning state。
- `pm onboarding export-source` 只支持 project profile workbook、Jira board registry CSV、Confluence page registry CSV。
- 在随包合成数据库副本上，未 bootstrap upgrade 时 export-workbook 因缺少 onboarding 表直接失败；upgrade 后因缺少 workbook horizon 上下文返回 `WORKBOOK_EXPORT_HORIZON_UNAVAILABLE`。
- 同一环境中的 source export 能运行，但 project profile 和 Confluence registry 均可能为空；它也不是一个覆盖全部业务对象的统一 Excel。

因此，“导出当前完整业务数据为 DM 可继续维护的标准 Excel”当前评级为 **L1**：存在局部实现，但没有形成通用、可复现、版本升级可依赖的工作流。

## 5. UI 页面盘点

`src/pm_agent/dashboard/surface_manifest.py` 定义 13 个 tab。默认 surface 仅把 legacy tab 标为 visible。

| 页面 | 业务问题 | 主要输入 | 输出 | 工作流状态 | 成熟度 |
|---|---|---|---|---|---:|
| Overview | 快速查看整体项目、人员、HIREF、计划摘要 | projects、employees、hiref、allocations、snapshots | 聚合 KPI 与摘要 | `OWNER-USED`；API 可运行；决策有效性待确认 | L2 |
| Projects | 查看项目列表及其属性 | projects、project profiles、Jira 映射 | 项目列表与详情 | `OWNER-USED`；API 可运行；决策有效性待确认 | L2 |
| Team | 查看团队成员、状态与负荷 | employees、assignments、allocations | 团队列表与 workload | `OWNER-USED`；API 可运行；决策有效性待确认 | L2 |
| HIREF | 查看当前与后续短期资源 / 招聘需求 | hiref、成员 HIREF 关联、open demand | HIREF 摘要和明细 | `OWNER-USED`；API 可运行；决策有效性待确认 | L2 |
| Monthly Plan | 查看按月项目分配 | plan_versions、monthly_allocations | 月度 allocation 表 | `OWNER-USED`；随包 demo 默认 plan 返回空 | L2 |
| Project Health | 查看 Jira / Confluence 状态 | Jira sprint / issue / health snapshot、Confluence status | 状态与有限 health 指标 | `OWNER-USED`、`OWNER-MEANING` 否定完整健康含义 | L2 |
| Attention | 集中查看需关注事项并 ack / snooze | attention signals / rules / reconciliation | attention items / recommendations | 默认隐藏；可通过 API / Agent 调用 | L2 |
| Weekly Brief v2 | 汇总多个能力的周报 | health、execution、capacity、attention、actions 等 | 分节 brief | 默认隐藏；部分 section 缺失 | L2 |
| Capacity Heatmap | 查看人员可用 capacity | resource capacity publication | capacity rows / signals | 默认隐藏；合成数据可运行 | L2 |
| Delivery Execution | 查看 milestone / release / dependency 状态 | canonical execution evidence | facts / signals | 默认隐藏；无真实 connector 验证 | L2 |
| Layered Health | 七维 Project Health assessment | project health assessment run | dimension / factor 结果 | 默认隐藏；常见维度 `not_available` | L2 |
| Connectors | 查看 connector 状态和最近 sync 结果 | data sources、sync runs | connector status | 默认隐藏 | L2 |
| Snapshots | 查看项目 snapshot | project_snapshots | snapshot 列表 | 默认隐藏；demo 为 0 行 | L1 |

页面运行、真实使用或 API 成功只证明入口和信息可达，不证明完成 L3 判断或决策。

## 6. API 盘点

Dashboard server 中有 18 个明确 HTTP route：

| API | 作用 | 输入 / 输出 | 实际入口状态 |
|---|---|---|---|
| `GET /` | Dashboard shell | HTML | 默认入口 |
| `GET /dashboard-config.js` | 返回可见 / 隐藏 tab 配置 | JS config | 默认入口 |
| `GET /api/summary` | Overview 聚合 | DB → summary | 200，runtime 已验证 |
| `GET /api/projects` | 项目列表 / 详情模型 | DB → projects | 200，2 行合成数据 |
| `GET /api/employees` | 团队列表 | DB → employees | 200，3 行合成数据 |
| `GET /api/hiref` | HIREF 摘要 | DB → HIREF payload | 200，runtime 已验证 |
| `GET /api/allocations` | Monthly Plan | plan version → allocations | 200，但随包 demo 为 0 行 |
| `GET /api/project-health` | Legacy Project Health | Jira / Confluence snapshots | 200，2 个项目 |
| `POST /api/project-health/sync` | 触发 health sync | sync request → result | 代码 / 测试存在；`OWNER-REAL-DATA`，但当前快照 live verification 未执行 |
| `GET /api/use-cases` | Use Case catalog | registry → metadata | 200 |
| `POST /api/tool/query/<use_case_id>` | 通用结构化查询 | request → UseCaseResult | advanced 能力主要 API 入口 |
| `GET /api/use-cases/team-workload-overview` | team workload 专用读取 | DB → workload | 与通用 query 存在入口重叠 |
| `POST /api/attention/operations` | attention preview / confirm | operation request → state | 默认隐藏页面使用 |
| `POST /api/weekly-brief/operations` | brief snapshot preview / confirm | operation request → snapshot | 默认隐藏页面使用 |
| `GET /api/sync-runs` | 同步历史 | DB → runs | runtime 为空列表 |
| `GET /api/freshness` | 数据新鲜度 | publications / runs → status | runtime 已验证 |
| `GET /api/project-snapshots`、`GET /api/project-plans` | snapshot / plan 读取 | DB → rows | 页面能力有限或隐藏 |

API 层的主要重叠是：同一能力可能同时有 legacy 专用 API、通用 Use Case API、CLI 和生成后的 Agent 指令。调用面增加不代表新增用户价值，却会增加合同同步成本。

## 7. Application Service / Domain Service 盘点

| 能力族 | 代表模块 | 业务作用 | 上下游与状态 |
|---|---|---|---|
| Use Case runtime | `use_cases/service.py`、`use_cases/__init__.py` | 注册、校验并执行结构化查询 | 下接多个 domain reader；上接 API / CLI / Agent。基础设施 L1，具体 use case 分别评级 |
| Data onboarding | `data_onboarding/service.py`、`workbook_onboarding/` | profile、preview、confirm、publication、replay、audit | 上游 Excel / JSON / CSV；下游 canonical tables。初次导入操作链完整但不属于 L3 DM 决策；完整导出 L1 |
| Legacy planning repository | `database/repository.py` | 项目、人员、plan、allocation 等查询和部分写入 | 多页面共用；与后续 publication 模型并存，维护重叠明显 |
| Staffing | `use_cases/staffing.py` | demand feasibility、proposal、preview / confirm | 依赖 projects、employees、allocations、current-state staffing、capacity freshness；L2 |
| Attention | `attention/`、attention use cases | 规则、reconcile、ack、snooze、recommendations | 依赖 execution / health 等 producer；L2 |
| Execution / milestone | `execution/`、`milestone_import/`、delivery execution use case | 将 Jira / release / milestone evidence 标准化并 derive | 上游 evidence import；下游 attention、health、brief；L2 |
| Project Health assessment | `project_health/`、layered health use case | 按维度和 factor 评估项目 | 与 legacy `/api/project-health` 并存；输入不完整时大量 unavailable；L2 |
| Resource capacity | `resource_capacity/`、capacity heatmap | 导入 / 发布 capacity 并计算可用量 | 下游 staffing、health、brief；L2 |
| Weekly Brief | `weekly_brief/`、weekly use cases | 组合多个 public reader 成周报 | 依赖最多，容易传播 partial / stale / unavailable；L2 |
| Interaction memory | `interaction_memory/` | 保存与预读对话事实 | demo 返回 unavailable / disabled；L1 |
| Connectors | `connectors/jira/`、`connectors/confluence/` | 同步远端证据 | `OWNER-REAL-DATA`；当前快照 live verification 未执行；L2 |

## 8. Agent / LLM 能力盘点

### 8.1 Agent 实际职责

Agent 主要负责：

- 识别用户意图并选择一个结构化 Use Case 或专用 CLI；
- 把确定性查询结果解释成自然语言；
- 对 staffing、attention、weekly brief snapshot 等写操作遵循 propose / preview / confirm；
- 在每轮前读取 interaction memory context。

确定性代码负责过滤、计算、校验和持久化；LLM 没有直接写数据库。这一边界在代码中基本成立。

### 8.2 目前没有形成的智能能力

- 未发现定时调度或主动通知 DM 的用户路径。
- 未发现系统自动将发现的问题转为统一 action、获得确认、执行并持续跟踪结果的完整链。
- Agent 没有通用的单条 project / employee / HIREF / allocation 增量更新命令。
- 用户仍需知道什么时候应 import、sync、derive、reconcile、query 或 snapshot。
- 同一仓库存在“维护中的 Agent 文件”和“usage bundle 生成时重写 / 拼接的 Agent 文件”，开发入口和发行入口可能漂移。

因此，当前 Agent 的产品成熟度为 **L2**：它是一个自然语言命令路由与解释层，不是主动决策助理。

### 8.3 Job / 后台自动化盘点

本次在 Python、配置和工具代码中未找到 APScheduler、Celery、cron 或其他面向用户的后台 scheduler / job runner。所谓“automatic producer”是在相应 import、derive 或 reconcile 流程被执行时自动产生 signal，不等同于系统在后台定期发现并通知 DM。

- `CODE`：没有注册后台 job 的运行入口。
- `INFERENCE`：能力主要由用户、Agent、CLI 或 API 请求触发。
- `UNVERIFIED`：仓库之外是否存在外部调度配置，本次 snapshot 无法证明。

## 9. 数据来源盘点

代码注册 9 类 onboarding source：

| 数据来源 | 主要对象 | 导入方式 | 真实流程状态 |
|---|---|---|---|
| `workbook` | Members、Projects、Allocations、Capacity、HIREF | profile → preview → confirm | 初始导入已形成；日常增量更新缺失 |
| `project-profile-workbook` | 项目 profile、风险等 | onboarding / export-source | 局部可用 |
| `jira-board-registry-csv` | project ↔ Jira board 映射 | registry import / export-source | 代码与测试存在；真实同步未验证 |
| `confluence-page-registry-csv` | project ↔ Confluence page 映射 | registry import / export-source | 代码与测试存在；真实同步未验证 |
| `servicenow-change-request-csv` | change requests | CSV import | 孤立于核心页面，主要供查询 |
| `milestone-json` | milestones / release links | JSON preview / confirm | advanced execution 链；L2 |
| `project-health-reimport-json` | Project Health observations | JSON re-import / assessment | advanced health 链；L2 |
| `resource-capacity-json` | capacity observations / publication | JSON import | capacity 链；L2 |
| `workforce-planning-json` | staffing / planning publication | JSON import | staffing / capacity 链；L2 |

另有直接 connector 同步 Jira 与 Confluence。Excel / CSV / JSON onboarding 和实时 connector 是两套并存的数据获取机制；不同能力读取 legacy tables 或 publication tables，用户需要理解数据来自哪条链。

## 10. 领域对象盘点

| 领域对象 | 当前表示 | 主要使用者 | 判断 |
|---|---|---|---|
| Project | `projects`、`project_profiles`、source identities | Projects UI、health、execution、staffing | 有核心对象，但 profile / connector / execution 身份并存 |
| Person / Team | `employees`、external IDs、current-state staffing members | Team、Monthly Plan、staffing、capacity | 核心可用；legacy 与 publication reader 并存 |
| Monthly Plan | `plan_versions`、`monthly_allocations`、coverage | Monthly Plan、workload、staffing | 核心可用，但默认 plan 选择与完整导出存在缺口 |
| HIREF | `hiref`、成员关联、staffing placeholders、open-demand allocation | HIREF UI、contract continuity、staffing | 同一业务概念有多种表示，存在重叠 |
| Demand | `StaffingDemand` 请求模型、HIREF placeholder、open-demand allocation | staffing、HIREF | 没有单一持久化 canonical Demand aggregate |
| Risk | project profile JSON / text、Jira health、signals、decision log | Project Health、brief、planning | 没有单一 canonical Risk 对象或统一 lifecycle |
| Blocker | Jira / health signal、导入校验 blocker、文本风险 | health、attention、brief | “blocker”同时表示业务阻塞与技术校验严重性；无统一业务对象 |
| Action | `action_items`、Confluence `action_tracker`、attention operation | action follow-up、brief、Confluence | 至少两套 action 表示，闭环不统一 |
| Decision | `decision_log`、staffing proposal / confirmation、config operations | planning、staffing、health | 多个 capability 各自记录决定，没有统一 DM decision journey |
| Change Request | `change_requests` | CR 查询、brief | 有结构化对象，但不在默认 Dashboard 主流程 |
| Milestone / Release / Sprint / Work Item | execution 和 Jira families | execution、attention、health、brief | advanced 分析基础；数据链复杂 |

## 11. 数据库与维护成本

### 11.1 规模

本次从空数据库运行实际 bootstrap 后得到：

- 110 张应用表；
- 2 个视图：`project_plan_snapshots`、`v_overdue_actions`；
- 多个 capability 同时保留 source stage、attempt、run、session、publication、observation、operation 和 audit 表。

这些表并不都代表独立产品能力。大量表用于安全导入、幂等、审计和 derivation，本身合理，但当上层用户流程未形成时，会造成维护成本先于用户价值增长。

### 11.2 按能力族分组的完整表清单

| 能力族 | 表 |
|---|---|
| Core project / people / planning | `projects`, `project_profiles`, `employees`, `employee_external_ids`, `assignments`, `plan_versions`, `monthly_allocations`, `monthly_project_allocation_coverage`, `placeholder_monthly_allocations`, `project_snapshots`, `hiref`, `staffing_placeholders` |
| Actions / decisions / CR | `action_items`, `action_tracker`, `decision_log`, `change_requests` |
| Generic source / sync / use cases | `data_sources`, `sync_runs`, `use_cases`, `execution_traces` |
| Onboarding orchestration | `onboarding_profiles`, `data_onboarding_runs`, `data_onboarding_run_attempts`, `data_onboarding_plan_reservations`, `data_onboarding_publication_links` |
| Workforce planning publication | `workforce_planning_import_sessions`, `workforce_planning_import_attempts`, `workforce_planning_import_runs`, `workforce_planning_publications`, `workforce_member_period_coverage` |
| Current-state staffing publication | `current_state_staffing_import_sessions`, `current_state_staffing_import_attempts`, `current_state_staffing_import_runs`, `current_state_staffing_publications`, `current_state_staffing_members`, `current_state_staffing_member_loads`, `current_state_staffing_projects`, `current_state_staffing_assignments` |
| Contract coverage publication | `contract_coverage_import_sessions`, `contract_coverage_import_attempts`, `contract_coverage_import_runs`, `contract_coverage_publications`, `contract_coverage_members` |
| Staffing decisions / capacity policy | `staffing_proposals`, `staffing_capacity_policy`, `staffing_capacity_operations` |
| Resource capacity | `resource_capacity_import_sessions`, `resource_capacity_import_attempts`, `resource_capacity_import_runs`, `resource_capacity_publications`, `resource_capacity_observations`, `resource_capacity_manifest_coverage`, `resource_capacity_derivations` |
| Jira / Confluence | `jira_board_configs`, `jira_issues`, `jira_sprints`, `jira_health_snapshots`, `jira_stream_versions`, `confluence_pages`, `confluence_status_snapshots` |
| Source evidence staging / publication | `source_evidence_runs`, `source_evidence_manifest_stage`, `source_evidence_published_items`, `source_evidence_cursors`, `jira_issue_event_stage`, `jira_issue_events`, `jira_issue_link_stage`, `jira_issue_links` |
| Canonical execution | `execution_work_items`, `execution_source_identities`, `execution_work_item_observations`, `execution_sprints`, `execution_release_commitments`, `execution_release_observations`, `execution_scope_memberships`, `execution_milestones`, `execution_milestone_observations`, `execution_milestone_release_links`, `execution_dependencies`, `execution_dependency_observations`, `execution_derivation_runs`, `execution_derivation_inputs`, `execution_facts` |
| Milestone operations | `milestone_import_operations` |
| Attention | `attention_rules`, `attention_signals`, `attention_history`, `attention_reconciliations`, `attention_operations`, `attention_configuration_operations` |
| Project Health assessment | `project_health_assessment_runs`, `project_health_assessment_details`, `project_health_dimension_results`, `project_health_factor_catalog`, `project_health_factor_results`, `project_health_input_observations`, `project_health_default_conditions`, `project_health_configuration_versions`, `project_health_configuration_changes`, `project_health_configuration_operations`, `project_health_reimport_sessions`, `project_health_reimport_attempts`, `project_health_reimport_runs`, `project_health_reimport_assessments` |
| Weekly brief / Dashboard operations | `weekly_brief_snapshot_operations`, `dashboard_operations` |
| Interaction memory | `interaction_memory_scopes`, `interaction_memory_entries`, `interaction_memory_audit`, `memory_facts` |

## 12. 文档声明、测试与实际代码的差异

| 声明或表象 | 实际证据 | 结论 |
|---|---|---|
| 13 个 Dashboard tab 都有 HTML / JS | 默认 config 仅显示 6 个 legacy tab | 7 个页面不能计为真实默认产品入口 |
| 页面或 API 存在且测试通过 | 多数 advanced 能力尚未成为 Owner 固定工作流；需要 CLI / publication 前置步骤 | 不能据此判定端到端完成 |
| Demo 已准备好 allocations / contract continuity 等非空结果 | `/api/allocations` 在随包 demo 返回 0 行；contract continuity 返回 0 contracts 和 unavailable warning | 文档与随包可复现状态不一致 |
| Project Health 已实现 | 可见页面主要使用 Jira / Confluence sprint/status；七维 assessment 是另一条默认隐藏链，且多维可 unavailable | 不能把现有输出直接称为可靠的整体项目健康判断 |
| Workbook export 是 complete current planning state | 随包 demo 无法直接导出；source export 仅覆盖 3 类 source | 尚未满足“完整业务数据、可继续维护、可用于升级”的用户要求 |
| Agent 支持完整使用方式 | checked-in Agent 与 usage bundle 生成时拼接的 Agent 指令不完全相同 | 发行行为和开发行为存在漂移风险 |
| IP-027～IP-032 已完成 / promoted | 代码、测试和局部 runtime 存在；Owner 未实际采用，默认 UI 隐藏，缺少主动闭环 | 应理解为“实现候选能力”，不是“已验证产品能力” |

## 13. 本次 Runtime 与测试证据

### 13.1 隔离合成数据库 Runtime

实际执行结果摘要：

- Dashboard：summary、projects、employees、hiref、project-health、use-cases、freshness 均返回成功；allocations 返回空；sync-runs 为空。
- Use Cases：team workload、legacy project health、management attention、delivery attention、delivery execution、layered health、capacity heatmap、weekly brief v1/v2、action follow-up、connector status / results 均可执行。
- contract continuity：命令状态 success，但返回 0 contracts，并带 publication unavailable warning。
- project snapshots：0 行。
- interaction memory：wrapper success，但 capability unavailable / disabled。
- staffing assess：可返回候选，但 `decision_ready=false`，存在 freshness / publication 阻断。
- export-workbook：随包 demo 未 upgrade 时 schema error；隔离 upgrade 后仍因 horizon unavailable 不能生成完整 workbook。

这些结果证明“引擎可运行”，不等于“真实用户流程已完成”。

### 13.2 本次聚焦测试

- Dashboard / rendering / health / demo：35 passed。
- CLI / Agent / unified contract / usability integration：52 passed。
- IP-027 / Attention / Execution / Layered Health：47 passed。
- Capacity / Staffing / Weekly Brief / Onboarding / Export：122 passed。

测试总计 256 passed。测试没有捕获随包 demo 默认 plan 导致 allocations 为空这一实际组合问题，也不能替代真实 Jira / Confluence 和 Owner 工作流验证。

## 14. 产品成熟度总评

| 产品层 | 成熟度 | 理由 |
|---|---:|---|
| 核心信息查看：Overview / Projects / Team / HIREF | L2 | `OWNER-USED`，但仍需 DM 自行拼接信息和形成判断 |
| Monthly Plan | L2 | 有真实业务基础，但只提供计划信息，且随包快照无法独立复现非空默认结果 |
| Legacy Project Health | L2 | 有同步与展示，缺少足够维度支撑整体 health 判断 |
| 初次数据导入 | 操作型 E2E | 有 schema、preview、confirm 和 audit；它是完整操作链，不纳入 Delivery Intelligence 的 L3 决策评级 |
| 核心数据日常增量维护 | L1 | 没有通用单记录操作入口；实际仍会被引导重新导入 |
| 完整业务 Excel 导出 / 升级后路 | L1 | 只有局部实现，随包 demo 无法完成完整导出 |
| Jira / Confluence 同步 | L2 | 代码、CLI、测试和读路径存在；Owner 确认曾在公司环境使用真实数据运行，但尚未形成稳定决策闭环 |
| Copilot Agent | L2 | 可路由和解释结构化命令，未形成主动判断与闭环 |
| IP-027～IP-032 | L1～L2 | 代码和测试较完整，但默认隐藏、依赖复杂、Owner 未采用 |
| 整体产品 | **L2** | 用户可以使用若干局部流程，但必须人工拼接入口、数据和判断 |

**总评：当前没有已验证的 L3/L4 DM 决策工作流。** 初次数据导入是一条完整操作型工作流，但它不等同于 Delivery Intelligence 判断或决策。

## 15. 审计边界与尚未验证

本次没有执行以下行为，因此不能做相应完成声明：

- 当前代码快照的真实 Jira / Confluence / ServiceNow live verification；其中 Jira / Confluence 仅有 Owner 确认的历史真实运行事实；
- 真实 Copilot UI 中的每条自然语言路由；
- 使用真实业务 workbook 的 clean import、日常更新和完整 export round-trip；
- Staffing、Attention、Weekly Brief snapshot 在真实 DM 决策中的连续使用；
- 定时任务、主动通知、跨周跟踪和执行结果闭环；
- 发布版安装器在另一台机器上的完整迁移升级。

## 16. 当前审计结论

当前产品不是没有价值。它已经形成了一个可用的本地 DM 数据查看基础，尤其是 Overview、Projects、Team、HIREF 和 Monthly Plan。问题在于，后续能力更多地以页面、Use Case、CLI、API、publication 和表的形式累积，尚未收束为少数可重复、可解释、可维护的 DM 工作流。

因此，在本次审计边界内应将当前状态理解为：

1. **已形成的产品核心**：初次导入 + 5 个核心查看页面；
2. **有争议的产品能力**：Legacy Project Health；
3. **局部可用但需人工拼接的工具能力**：Jira / Confluence、Staffing、Attention、Execution、Layered Health、Capacity、Weekly Brief；
4. **尚未形成的关键产品能力**：核心数据便捷增量维护、完整标准 Excel 导出、主动发现与决策执行闭环；
5. **当前没有已验证的 L3/L4 DM 决策工作流**。

本文件只记录当前事实与成熟度，不授权新增功能、删除表、重构模块或重新设计数据库。

## 17. 现有资产复用判断

### 17.1 应作为演进基础保留的资产

| 资产 | 为什么重要 | 实际证据 | 复用判断 |
|---|---|---|---|
| 5 个核心 Dashboard 页面 | 已由 Owner 实际使用，直接承载当前产品价值 | `surface_manifest.py` 默认可见；Dashboard API runtime 成功 | **保留并作为 Golden Path 起点** |
| Core project / people / plan / HIREF 数据 | 支撑所有当前可用页面，也是后续分析的事实基础 | 核心表、repository、workbook import 和 Owner 数据 | **保留；先明确权威来源和选择规则，不重建** |
| Workbook onboarding preview / confirm | 已形成安全、版本化、可审计的首次导入路径 | onboarding service、source registry、run / attempt / publication 表、focused tests | **保留；在此基础上补数据连续性** |
| Jira / Confluence connector 与 sync audit | 真实项目状态的重要来源，已有 registry、sync run 和 freshness 机制 | connector modules、CLI、sync tables、tests | **保留；先验证真实调用链和失败处理，不重写 connector** |
| `UseCaseRequest` / `UseCaseResult` 与 executor | 提供 renderer-neutral 契约、输入校验、evidence 和 execution trace | `use_cases/service.py`、`use_cases/execution.py`、registry | **保留为 UI / Agent 共用连接点** |
| propose / preview / confirm / persist | 已在 staffing、attention、config、snapshot 等写入中形成安全模式 | capability services、operation tables、tests | **保留并复用，不建立另一套写入机制** |
| Execution evidence、Attention、Capacity、Layered Health readers | 方向与“帮助 DM 判断”一致，已有确定性事实和缺失状态表达 | IP-028～IP-031 modules、runtime、tests | **保留为候选能力；先连接场景，不继续横向扩张** |
| Weekly Brief v2 composer | 已证明可以组合多类 public reader，并能暴露 partial / unavailable | weekly brief modules、runtime、tests | **保留为工作流连接候选，不立刻新增更多 section** |
| 合成 demo 与 release validation 工具 | 可为新开发人员提供安全、可重复的学习和回归环境 | `src/scripts/load_sample_data.py`、56 个 test files、Makefile / release tools | **保留并修正可复现漂移** |
| 导入、operation、execution 的审计表 | 支撑幂等、失败恢复、证据和受控写入，不是纯粹冗余 | run / attempt / session / publication / operation / trace 链 | **不因表多而直接删除；应先映射 owner 和消费者** |

### 17.2 方向正确但没有接成完整工作流的能力

| 能力 | 已有正确部分 | 当前缺少的连接 | 小改造形成价值的可能性 |
|---|---|---|---|
| Project Health | 已有 Jira / Confluence 状态和 advanced assessment evidence | 默认页面与 layered assessment 分离；业务维度和结论语义未统一 | **中**：先收束显示含义和证据，不要求重写评估引擎 |
| Attention | 已有 rule、signal、history、ack / snooze | 没有自然进入 DM 每日 / 每周流程，也无主动交付 | **中高**：可先连接现有核心页面或 brief，而不是新增页面 |
| Delivery Execution | 已有 canonical evidence 和 review | 数据准备步骤与默认项目查看割裂 | **中**：已有 reader 可复用，关键是选择一个真实场景接入 |
| Resource Capacity / Staffing | 已有 heatmap、feasibility 和安全阻断 | publication 前置复杂，Owner 没有稳定准备路径 | **中低**：引擎可保留，但需先解决数据权威和准备流程 |
| Weekly Brief v2 | 已有 composer、partial / unavailable 表达和 snapshot | 上游缺失会放大；未进入固定周工作流 | **中高**：作为既有能力的汇总入口比新增独立功能更接近产品价值 |
| Action follow-up | 已有查询和 action 数据 | 两套 action 表示，未与 attention / brief /执行结果统一 | **中**：先选择一个真实 follow-up 场景，不需要新建第三套 Action |
| 完整 Excel export | 已有 export-workbook 和部分 source export | 无法覆盖任意当前数据库状态并稳定 round-trip | **高价值**：已有基础代码，但实际改造规模需先做字段覆盖审计 |

“小改造可能性”是 Roadmap 调研输入，不代表已经授权实现，也不保证改动量一定小。

### 17.3 不应为架构整洁而重写的区域

- 已有 workbook parser / validator / preview / confirm / audit 链；
- Jira / Confluence 连接器的认证边界、registry 和 sync run 记录；
- typed intelligence contract 和执行 trace；
- capability-specific controlled write operation；
- 已通过的合成测试、migration / replay / rollback 保护；
- legacy 5-page Dashboard 的现有用户行为和响应 shape；
- 缺失证据返回 unknown / unavailable，而不是猜测为健康或零值的规则。

这些区域可以在实际 Golden Path 需要时进行行为保持的边界整理，但不应先被替换为新框架。

## 18. 开发交接与可维护性审计

### 18.1 已存在的交接资产

代码快照并非没有文档和测试：

- README 提供环境、connector、onboarding、validation 和 demo 命令；
- `docs/DEVELOPER_ONBOARDING_INDEX.md` 提供模块地图、数据路径、命令和 first-session checklist；
- `docs/` 下有 13 份主要说明文档；
- implementation pack / report 共 26 份；
- `src/tests/` 有 56 个测试文件；
- `.env.example`、Makefile、合成 demo loader 和 release tooling 均存在。

这些是重要资产。交接问题不是“没有材料”，而是材料主要按技术阶段、批次和操作门禁组织，缺少按当前产品场景组织的单一事实视图。

### 18.2 高知识单点区域

下表中的“原作者知识风险”不是断言别人无法阅读代码，而是指新开发人员仅靠当前入口和文档，很难安全推断正确行为。

| 区域 | 实际证据 | 为什么形成知识单点 | 风险 |
|---|---|---|---:|
| 默认 plan 与 Monthly Plan 数据选择 | `repository.get_default_plan_version()` 选择最新 active baseline；随包 demo 中更新的空 plan 覆盖了有 allocation 的 plan | 用户语义“哪个 plan 应显示”没有成为显式产品合同；测试未捕获组合结果 | 高 |
| Legacy 与 publication fallback | `dashboard/server.py` 对 staffing、contract coverage 等按 freshness 决定 legacy fallback | 必须理解多套表、publication state 和 fallback 条件才能解释同一页面的数据 | 高 |
| 两套 Project Health | 可见 legacy `/api/project-health` 与隐藏 layered assessment 并存 | 名称相同但证据、维度、入口和成熟度不同，Owner 和开发者容易误认 | 高 |
| Advanced capability 前置顺序 | demo loader 依次 bootstrap、多个 imports、publications、derive、reconcile、brief | 少一步就可能变成 partial / unavailable，但入口没有引导用户完成 prerequisite | 高 |
| Source Agent 与发行 Agent | `tools/build_usage_bundle.py` 读取维护中的 Agent，再替换 pre-read、追加 setup / onboarding / export 指令并重写 bundle Agent | 开发 checkout 中看到的 Agent 不是最终发行行为的完整来源 | 高 |
| Read-only query 的隐式写入 | `UseCaseExecutor._finalize()` 保存 execution trace；Developer Onboarding 特别要求复制 demo DB | “read-only”指业务状态不变，不代表数据库完全不写；容易污染验证基线 | 中高 |
| 数据 authority 与多种对象表示 | employee / assignment / allocation 与 current-state staffing / workforce publication 并存；HIREF / placeholder / demand 并存 | 同一用户问题可能有多个 reader 和权威来源，选择规则分散在代码中 | 高 |
| 发布快照身份 | transport package 没有 Git 历史，只能依赖文档声明和 ZIP hash | 新开发者无法把代码、测试结果和远端 commit 建立可靠对应 | 高 |

### 18.3 模块职责与边界风险

| 模块 | 规模与职责证据 | 风险判断 | 重构边界 |
|---|---|---|---|
| `database/bootstrap.py` | 2,984 行；组合 schema，同时包含多版 migration、compat view、identity rewrite 和 seed | schema 修改影响面大，新开发者难判断历史迁移与 clean bootstrap 的边界 | **需要受控拆分，但不重写 schema**；只在相关 schema change 前做行为保持提取 |
| `database/repository.py` | 2,836 行；覆盖 people、HIREF、sources、sync、projects、health、plans、staffing、snapshots、actions、decisions | 多领域共享 repository，依赖方向和 owner 不清 | **按触及的 capability 渐进拆分**；保留 public facade 和兼容行为 |
| `dashboard/server.py` | 1,931 行；HTTP、projection、direct SQL、fallback、freshness、sync trigger 和 operation API 混合 | UI → data 调用链难追踪；页面行为依赖 storage 细节 | **Golden Path 修改时优先提取 read model / service seam**；不重写 Dashboard |
| `attention/service.py` | 1,139 行；preview、confirm、reconciliation、lifecycle、history 和失败 audit | 单能力内部状态机复杂，安全修改依赖大量隐含 invariants | 先补 lifecycle 文档 / scenario tests；仅在真实 workflow 接入时拆分 |
| `cli/commands/integrations.py` | 1,130 行；CR、release、Jira health、Confluence、auth config 混合 | presentation layer 横跨多个 connector domain | 触及某 connector 时渐进迁移，不进行一次性 CLI 重写 |
| `cli/commands/operations.py` | 846 行；action、project、decision、HIREF 命令混合 | 旧式操作入口与新 use-case executor 并存 | 先建立命令到 capability 的 owner map，再按场景整理 |
| `tools/build_usage_bundle.py` | 超过 900 行；生成 README、Agent、setup helper、模板和 archive | 发布行为由生成逻辑决定，review 源码时难直接看到最终产品合同 | 应把生成结果纳入可追踪测试；不需重写打包器 |

行数不是独立重构理由；上述判断来自“规模 + 多职责 + 实际调用 / fallback / 生成行为”的组合证据。

### 18.4 UI、API、Service、Agent 与数据库调用链

当前存在两类明显不同的调用链：

1. **较可追踪的 structured chain**：Agent / `pm tool query` / generic API → `UseCaseExecutor` → descriptor / handler → capability read model → `UseCaseResult` → execution trace。
2. **较难追踪的 legacy Dashboard chain**：JavaScript loader → 专用 route → `dashboard/server.py` 内 projection + direct SQL + repository / publication fallback → response shape。

第一类已有统一 ID 和结果合同，是可复用资产；第二类承载最真实的产品价值，却更依赖 storage 细节和 fallback。这正是后续应增量连接而非另建新界面的区域。

### 18.5 重复实现与隐式依赖

已确认的重复或重叠包括：

- legacy Project Health 与 Layered Project Health；
- `action_items` 与 Confluence `action_tracker`；
- legacy `assignments` / `monthly_allocations` 与 current-state staffing / workforce planning publications；
- HIREF contract、staffing placeholder、open-demand allocation 和 `StaffingDemand`；
- legacy weekly brief / report 与 Weekly Brief v2；
- legacy service classes / `SERVICES` 与新的 registered `UseCaseExecutor`；
- source Agent 与 usage bundle 生成 Agent；
- 专用 Dashboard API 与 generic use-case API。

隐式依赖包括：

- 全局 `settings.database_path` 被大量 repository、sync、CLI 和 Dashboard 直接读取；
- 多个模块直接创建 SQLite connection，事务和 bootstrap 前置不由一个 application boundary 统一表达；
- advanced reader 依赖特定 publication、freshness 和 coverage state；
- Dashboard fallback 依赖表是否存在以及 publication 是否 fresh / stale；
- “read-only” use-case 会持久化 execution trace；
- release bundle setup 和 Agent 行为由生成脚本决定，而非只由 checked-in Agent 文件决定。

### 18.6 测试保护与安全修改风险

正面证据：

- 56 个测试文件按 onboarding、Dashboard、Agent、Attention、Execution、Health、Capacity、Staffing、Weekly Brief、connector 等能力分布；
- 本次 256 个聚焦测试通过；
- implementation packs 通常记录 focused suite 和 acceptance criteria；
- schema / import / release 工具已有 replay、integrity 和 rollback 保护。

风险证据：

- 未找到 repository-wide coverage threshold 或覆盖率报告，因此不能量化哪些分支没有保护；
- 随包 demo 的 default-plan / allocations 组合问题在相关测试通过时仍然存在；
- 测试多按 capability / batch 编排，较少以“DM 从初始数据到页面、判断、更新、导出”的产品旅程命名；
- 真实 connector、真实 Copilot routing、安装后完整迁移和 Owner workflow 仍未验证；
- 生成后的 usage bundle Agent 和 setup surface 是关键产品行为，源码级 unit tests 不能替代最终 bundle 的场景验收。

最难安全修改的区域依次是：跨多 publication 的 Dashboard projection、完整导入 / 导出 round-trip、Project Health 两套模型的连接、Attention lifecycle、release bundle 生成行为，以及 `bootstrap.py` 中历史 migration 与当前 schema composition 的交界。

### 18.7 配置、启动与数据准备

| 项目 | 已有资产 | 交接风险 |
|---|---|---|
| Python / dependency setup | README、Makefile、bundle setup helper | 开发 checkout 与 operator bundle 的启动方式不同 |
| Environment | `src/.env.example`、Pydantic Settings | `DATABASE_PATH` 是全局关键开关；不同命令可能直接读取全局 settings |
| Database bootstrap | `init_db.py`、package bootstrap、release rehearsal | 随包 demo schema 可落后于代码；新开发者需知道何时先 upgrade |
| Demo data | `load_sample_data.py --force / --replay` | advanced capability 依赖固定编排顺序；structured query 会写 trace |
| Local business data | onboarding profiles、preview / confirm | 9 类 source 需要分别理解；没有一条完整日常维护与导出路径 |
| Connectors | auth bootstrap、registry、sync commands | 真实配置和 UAT 受单独门禁，本次未验证 |
| Release bundle | builder、manifest、setup gate、generated Agent | 最终行为不是开发文件的直接复制，需对生成物做产品级验证 |

## 19. 产品与实现的可追踪性

目标追踪链是：

> 业务场景 → Product Capability → 用户工作流 → User Story / Acceptance Criteria → UI / API / Service / Domain / Data → Test Evidence → Release Result

### 19.1 当前可以追踪的链路

| 链路 | 当前证据 | 完整度 |
|---|---|---:|
| use-case ID → descriptor → handler → typed result → execution trace | `use_cases/__init__.py`、`execution.py`、`service.py` | 高 |
| onboarding run → attempt → validation → confirm → publication → audit | onboarding service / repository 和表族 | 高 |
| capability operation → preview token → confirm → operation / history | staffing、attention、health config、weekly snapshot | 高 |
| IP / batch → implementation pack → focused tests → historical validation record | implementation packs / reports、PROGRESS | 中高；历史状态需重新验证 |
| Dashboard tab → route | surface manifest、legacy / experimental JS、server route | 中 |

### 19.2 已断裂或不完整的链路

| 断点 | 现状 | 影响 |
|---|---|---|
| 业务场景 → Product Capability | 没有当前统一场景目录；主要按 IP、phase、CLI 或页面组织 | TPO 难以判断能力为何存在和是否值得保留 |
| Capability → 用户工作流 | 多数 advanced capability 有 engine / route，但默认隐藏或需手工准备前置数据 | “实现完成”无法推导“用户可用” |
| Workflow → User Story / Acceptance Criteria | pack 中有技术 acceptance criteria，但缺少 Owner 日常场景的产品级 AC | 测试绿不能直接支持产品验收 |
| UI → API → Service | legacy Dashboard 大量 route 内 direct SQL / fallback；并非统一走 use-case contract | 修改 UI 时难确定所有业务规则和数据 owner |
| Service / Domain → Data owner | 同一概念分布在 legacy tables、publication tables 和 fallback | 新开发者难选择正确写入 / 读取边界 |
| Test Evidence → Release Result | 测试记录多为历史批次；transport snapshot 无 commit provenance | 无法严格证明当前发布包对应哪次验证 |
| Source Agent → Released Agent | bundle 构建时动态改写 Agent 和 setup 指令 | review checked-in Agent 不能完整预测用户行为 |
| Product adoption → Status document | promoted / implemented 不记录 Owner 是否实际使用 | Roadmap 状态会高估产品成熟度 |

### 19.3 后续追踪最小要求（非实施设计）

后续每个进入 Roadmap 的 slice 至少应能回答：

1. 哪个 DM 业务场景和决策被支持；
2. 用户从哪个现有入口开始、在哪里结束；
3. 复用了哪些现有 capability / data，新增了什么最小连接；
4. 哪些缺失或冲突状态必须显式展示；
5. 哪个 acceptance scenario 证明用户完成了工作，而不只是接口成功；
6. 哪些 focused tests 和一次产品级 journey test 提供证据；
7. 哪个 release artifact / commit 实际包含并验证了它。

这是交接所需的最小追踪合同，不是要求先建设一个新的管理平台。

## 20. Roadmap 输入（不是实施 Roadmap）

### 20.1 最可能快速接入真实工作流的现有能力

| 候选 | 复用资产 | 为什么接近真实价值 | 审计前置 |
|---|---|---|---|
| 核心页面上的 evidence / attention 连接 | 5 个已用页面、现有 signals / UseCaseResult | 不要求用户寻找隐藏页面或记住 use-case ID | 先选择一个具体 DM 判断场景和 AC |
| Weekly Brief v2 的受限真实场景 | 已有 composer、partial 状态和 snapshot | 能把多个孤立 reader 汇合为固定周工作流 | 先限定只使用已可靠的数据，不扩 section |
| Project Health 语义收束 | legacy status、layered evidence、freshness | 直接修复 Owner 已使用但有争议的页面 | 先定义“状态事实”与“健康判断”的边界 |
| 当前完整业务数据导出 | export-workbook、source export、onboarding schema | 直接解决维护、迁移和版本升级后路 | 先完成字段 / source / post-write coverage audit |
| 核心数据增量维护 | existing controlled-write pattern、core repositories | 直接修复 Copilot 要求整表重导的断点 | 先限定最常见的一类记录和 source-of-truth 规则 |
| Jira / Confluence 到核心判断的验证链 | connector、sync run、freshness、legacy health | 已有基础能力，缺的是产品 journey 证据 | 需要另行授权的合成 / 真实 UAT gate |

### 20.2 必须优先偿还的交接和维护风险

1. 明确 legacy / publication 的数据 authority、fallback 和 default-plan 规则；
2. 让 source Agent、生成 Agent、setup guide 和实际 release artifact 可对照；
3. 为核心 5-page Golden Path 建立 UI → API → rule / query → table → test 的 owner map；
4. 把“implemented / promoted”与“Owner-used / journey-validated”分开记录；
5. 让 demo / upgrade / export 在发布快照中可重复，而不依赖作者知道隐藏步骤；
6. 对 `dashboard/server.py`、`database/repository.py`、`database/bootstrap.py` 设定触及式拆分边界，防止继续吸收职责；
7. 为最关键业务规则补 scenario-level 文档和测试，而不是只增加 module-level unit tests。

### 20.3 影响 Golden Path 的关键技术缺口

| 缺口 | 影响的 Golden Path | 当前证据 |
|---|---|---|
| 核心记录没有便捷增量更新合同 | 导入后日常维护 | Agent / CLI 缺少通用 project / member / HIREF / allocation record update；Owner 实际受阻 |
| 完整 Excel round-trip 不成立 | 数据迁移、升级、继续维护 | 随包 demo export-workbook 无法完成；source export 不覆盖全部业务对象 |
| default plan / fallback 规则隐式 | Monthly Plan、Team、HIREF | runtime 与 Owner / README 预期冲突；选择逻辑分散 |
| Project Health 两套模型未收束 | 项目判断 | 默认页面与 layered assessment 分离，维度和入口不同 |
| advanced capability prerequisite 复杂 | Attention、Execution、Capacity、Brief | publication / freshness / derive 缺失传播为 partial / unavailable |
| 没有统一的发现 → action → result follow-up | DM 决策闭环 | signals、attention、actions、decisions 各自存在但没有单一 journey |
| release artifact 与验证记录不可严格对应 | 交接和发布信心 | transport snapshot 无 Git provenance；Agent / setup 又在 build 时生成 |

以上只作为后续 TPO 排序和有界 discovery slice 的输入。没有授权立即实施、重构或新增表。
