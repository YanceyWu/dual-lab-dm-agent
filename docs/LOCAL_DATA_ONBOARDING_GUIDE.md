# 本地数据接入指南（给使用者把现有数据接到本地产品）

本文档面向**实际使用者**，目标是回答一个问题：

> 我已经有本地可访问的数据或批准的数据副本，怎样把它安全地接入这个产品，让 Dashboard 和 `pm` 查询能看到内容？

这是一份**上手指南**，强调“怎么开始”和“怎样安全接入”。  
如果你需要的是正式真实环境 UAT 过程、审批边界、停止条件，请同时阅读：

- `docs/REAL_ENVIRONMENT_UAT_RUNBOOK.md`
- `docs/DASHBOARD_USAGE_GUIDE.md`

---

## 1. 先理解：产品吃的不是“页面输入”，而是“本地数据库 + 受控导入/同步结果”

这个产品不是在 Dashboard 上手工录入数据的。

它的典型数据路径是：

1. 建立本地 SQLite 数据库
2. 写入本地配置
3. 导入结构化数据 / 运行批准的同步
4. 执行派生、评估、对账、快照
5. 用 `pm` CLI 或 Dashboard 查看结果

所以接入现有数据时，重点不在“打开页面”，而在：

- 你的本地数据库准备好了没有；
- 数据是不是通过批准路径导入/同步进去；
- 派生/评估是不是跑过；
- freshness / warnings 是否足够支持判断。

### 1.1 首次接入靠文件，日常维护更适合通过 Copilot 对话驱动

你这次理解得对：

- **首次接入 / 建基线**，更适合走文件导入、结构化 re-import、或批准的同步；
- **初始化完成后**，日常很多操作更适合通过和 Copilot 对话来完成。

但这里要区分两类“更新”。

#### A. 适合通过对话驱动的更新

这类通常不是“大批量底层事实重建”，而是**围绕已有事实做判断、提案、受控动作**。例如：

- 查询 workload / capacity / health / attention / HIREF / weekly brief；
- 发起 staffing proposal，并按 preview → confirm 完成受控持久化；
- 对 Attention 做 acknowledge / snooze / reconcile；
- 对 Weekly Brief v2 做 snapshot preview / confirm；
- 查看或调整已批准的受控配置入口。

它的典型模式是：

> **你用自然语言表达意图 → Copilot 路由到批准的 `pm` 命令 → 返回结构化 preview / warnings / token → 你明确确认 → 系统持久化**

#### B. 仍然应该回到结构化导入的更新

这类通常是**基础事实层的大范围刷新**，不适合靠自由口述逐条改：

- workforce planning 全量或大批量变更；
- resource capacity 月度/版本化重载；
- canonical milestone 批量导入；
- project health re-import 包；
- board / page registry 批量维护；
- connector 同步产物刷新。

这些能力依赖：

- authoritative manifest；
- 幂等 replay；
- 结构校验；
- 依赖顺序；
- 覆盖率与完整性检查。

所以它们更适合继续走**文件导入 / 同步 / 受控脚本**，而不是“聊天直接改库”。

#### C. 最实用的使用方式

可以把它理解成：

1. **第一次**：用文件把基础事实接进来；
2. **平时**：主要通过 Copilot 对话来查询、解释、提案、确认受控动作；
3. **月度/批量刷新**：再回到结构化导入路径。

---

## 2. 你应该选哪条路径

### 路径 A：只是想先体验

如果你现在只是想先看效果、理解页面、学习操作：

- 不要接真实数据；
- 直接用合成演示库。

看：

- `src/sample-data/README.md`
- `docs/SYNTHETIC_DEMO_WALKTHROUGH.md`

### 路径 B：要接入你们现在已有的本地数据

如果你已经有：

- 已批准的本地数据库副本；或
- 已批准的本地 connector 配置；或
- 已批准的结构化导入包

那就走本文档这条路径。

> **不要直接把迭代分支指向活动生产数据库。**  
> 先用批准的本地副本或隔离拷贝做接入和验证。

---

## 3. 最小前提

开始前，你至少需要这几样东西：

### 3.1 本地安装好的产品

从仓库 `src/` 目录：

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -e .
pm version
```

### 3.2 一份批准的本地数据来源

可以是以下之一：

1. **批准的本地数据库副本**
2. **批准的结构化导入文件**
   - workforce planning
   - resource capacity
   - milestone
   - project health re-import package
3. **批准的本地 connector 配置**
   - 仅限本地使用，不提交到仓库

### 3.3 本地忽略配置

把以下内容只放在本地忽略文件里：

- 数据库路径
- endpoint
- credential
- connector mapping

**不要提交回仓库。**

---

## 4. 推荐接入顺序

这是最推荐的“使用者第一次接数据”的顺序：

1. 安装产品
2. 创建本地配置
3. 对现有数据库做 recovery point / 本地副本
4. 在副本上初始化和验证
5. 先跑只读查询
6. 再打开 Dashboard

换句话说：

> **先验证数据，再看页面。**

---

## 5. 是否需要统一规划和一致性

**需要，而且这是接入成败的关键。**

如果没有统一规划，最容易出现的不是“导不进去”，而是：

- 导进去了，但不同页面互相打架；
- Team/Monthly Plan 看起来正常，Capacity 却不对；
- Project Health 有项目，Execution 没有里程碑；
- Attention 一直报风险，但你找不到对应基础事实；
- Weekly Brief 能跑，但结论来自不一致的数据窗口。

所以在真正导入前，建议先统一下面这些内容。

### 5.1 要统一的不是“文件名”，而是业务语义

最少要统一这几件事：

1. **统一标识符**
   - 人员 ID
   - 项目 ID
   - plan version ID
   - board ID
   - milestone ID

2. **统一时间窗口**
   - 月度 allocation 用哪个年月
   - capacity 用哪个计划窗口
   - project health / snapshot / sync 看哪个时间点

3. **统一来源归属**
   - 哪个系统/文件是 workforce 的权威来源
   - 哪个是 capacity 的权威来源
   - 哪个是 milestone 的权威来源
   - 哪个是 health evidence 的权威来源

4. **统一含义**
   - “0 allocation” 是真实 0，还是缺失
   - “unknown / not_available” 是无证据，不是健康
   - 里程碑日期是承诺日期还是来源页面里的参考日期

### 5.2 你至少要保证这几种一致性

| 一致性项 | 要求 |
| --- | --- |
| 人员一致性 | 同一个人不要在不同导入里用不同 ID / 名称格式 |
| 项目一致性 | Team、Milestone、Health、Board mapping 里的项目必须能对上同一个 project ID |
| 时间一致性 | allocation、capacity、brief、snapshot 要知道自己基于哪个年月/窗口 |
| 来源一致性 | 同一类事实最好只有一个主来源，不要多个文件同时争夺“真相” |
| 重放一致性 | 同一包重复导入时要得到 `already_completed` / `no_op` 或等价幂等结果 |
| 解释一致性 | partial / stale / unknown 要在所有页面里按同一种含义理解 |

### 5.3 一个很实用的规划方法

在导入前先做一张本地映射表，至少列出：

- 你们当前来源文件/系统
- 对应哪个 importer
- 谁是这类数据的权威来源
- 对应 sample 路径
- 目标标识符是什么
- 目标时间窗口是什么
- 先导什么、后导什么

如果这张表做不出来，说明此时还不适合直接导入。

---

## 6. 推荐全量导入顺序（完整链路）

如果你的目标是让大多数页面都能稳定出现内容，推荐按下面顺序做：

1. **bootstrap / `pm init`**
2. **workforce planning import**
3. **resource capacity import**
4. **board / page registry**
   - JIRA board configs
   - Confluence page registry
5. **来源事实 / 补充导入**
   - 例如 change requests、HIREF、project profiles
6. **canonical milestone import**
7. **project health re-import / seven-dimension assessment**
8. **attention reconciliation**
9. **weekly brief v2 snapshot / query**
10. **Dashboard 查看**

### 为什么这个顺序合理

- **workforce planning** 先导，因为很多页面都依赖人员、项目、allocation 基础事实；
- **resource capacity** 要在 health / staffing 之前具备，否则容量相关判断会失真或为空；
- **board/page registry** 要先于 health 观察页存在，否则来源页面找不到映射；
- **milestone** 要在 execution / 部分 health 之前导入，否则 schedule 事实不完整；
- **project health re-import** 要在 attention / weekly brief 之前完成，因为后两者会消费这些结果；
- **attention / weekly brief** 是更高层的聚合结果，应该排在后面。

---

## 7. 页面驱动的最小导入顺序

如果你不是要一次把所有能力接齐，而是想先点亮某几页，可以按页面倒推。

| 如果你先想看… | 最小顺序 |
| --- | --- |
| Team / Projects / Monthly Plan | `pm init` → workforce planning |
| Capacity Heatmap | `pm init` → workforce planning → resource capacity |
| Project Health | `pm init` → workforce planning（项目基础）→ board configs → confluence/jira 相关来源记录 |
| Delivery Execution | `pm init` → workforce planning（项目基础）→ milestone import |
| Layered Health | `pm init` → workforce planning → milestone / health evidence → project health re-import |
| Attention | `pm init` → 基础事实齐备 → attention reconciliation |
| Weekly Brief v2 | `pm init` → health / execution / attention 基础齐备 → weekly brief query / snapshot |
| HIREF / Contract Continuity | `pm init` → Team/Project + Capacity workbook onboarding（发布 contract coverage；需要保留现有 HIREF slot/result feature points 时，在同一 workbook 中补充可选的 `HIREF Requests` sheet，并使用 `Members.next_hiref_id` 与 `Allocations.hiref_id` 表达续签和 open-demand） |

当前 workbook onboarding 的 review/template 文件位于：

- `templates/team_project_capacity_workbook_template.xlsx`
- `src/sample-data/excel/team_project_capacity_workbook_hiref_sample.xlsx`

也就是说：

> **先决定你要看哪类页面，再倒推最小数据链。**

---

## 8. 导入规则（使用者必须遵守）

### 8.1 规则一：优先空库 + 版本化全量导入

对正式的受控 JSON 导入路径，仓库的方向是：

> **空数据库 → versioned structured full import → derivation / assessment**

而不是：

- 在旧库上随意补丁式混写；
- 依赖不可解释的历史残留；
- 先导一半、手改一半。

### 8.2 规则二：先 dry-run，再 confirm

只要 importer 支持 `--dry-run` / `--confirm`，就不要跳过 dry-run。

你至少要在 dry-run 看这些：

- 状态是不是 `rejected`
- manifest 是否 authoritative / complete
- 目标记录数是否合理
- 标识符映射是否明显异常

### 8.3 规则三：不要让两个来源争夺同一事实

例如：

- workforce planning 不要同时有两份互相打架的项目/分配主文件；
- milestone 不要一部分来自 A 文件、一部分来自不兼容的 B 文件，却没有统一 ID；
- health 判断不要混入无法解释来源优先级的手工补丁。

最稳妥的做法是：

- 每类事实只指定一个主来源；
- 其他来源只做补充，不做“平行真相”。

### 8.4 规则四：缺失不是 0，unknown 不是 green

导入后看到：

- `unknown`
- `not_available`
- `partial`
- `stale`

要理解成：

- 证据不足；
- 来源不完整；
- 数据已过时；

而不是：

- 没有风险；
- 可以忽略。

### 8.5 规则五：重复导入必须可解释

对受控导入，重复同一包时应该能得到：

- `already_completed`
- `no_op`
- 或其他清晰可解释的幂等结果

如果重复导入反而造成：

- 重复记录；
- aggregate count 异常变化；
- 关联断裂；

就说明你的输入规划或导入路径有问题。

### 8.6 规则六：先看 CLI，再看 Dashboard

导入后不要立刻用页面当唯一验证手段。

推荐先看：

```bash
pm tool list
pm tool query team-workload-overview
pm tool query project-health-review
pm tool query management-attention
```

CLI 结果正确后，再看 Dashboard。

### 8.7 规则七：把“基础事实刷新”和“运营动作更新”分开

日常使用时，最容易混淆的是这两件事：

1. **基础事实刷新**
   - 例如成员、项目、allocation、capacity、milestone、health evidence 的大批量更新
   - 这类更新应优先走结构化导入 / 同步

2. **运营动作更新**
   - 例如 staffing proposal、Attention acknowledge/snooze、Weekly Brief snapshot、受控配置确认
   - 这类更新适合通过 Copilot 对话驱动批准命令完成

简单判断标准是：

- 如果你改的是**一整批源数据**，用 importer；
- 如果你改的是**基于现有事实的受控动作**，用 Copilot 对话；
- 如果当前能力没有公开 preview/confirm 写入口，就不要把聊天当成隐式写入通道。

### 8.8 对 DM 来说，必须足够简单才可用

如果一个 Delivery Manager 需要长期自己记住下面这些链路：

- `workforce → capacity → registry → milestone → project health re-import`
- 哪个 importer 先跑
- 哪个 sample 对哪个来源
- 哪一步还要再做 reconciliation / snapshot

那么这个产品即使能力完整，也会因为**操作复杂度过高**而难以真正落地。

所以更合理的目标不是“让 DM 学会所有 importer”，而是：

> **把复杂导入链隐藏在系统里，让 DM 只做选源、预览、确认、刷新。**

### 8.9 推荐的 DM 友好自动化目标形态

下面这个分工更适合长期使用：

| 阶段 | DM 负责什么 | 系统负责什么 |
| --- | --- | --- |
| 首次接入 | 选择数据来源、完成一次字段映射、保存本地 source profile | 记录映射、记住依赖顺序、校验最小前提 |
| 日常刷新 | 说“刷新本周数据”或点一次 refresh | 自动判断范围、按顺序跑 import / derive / reconcile |
| 预览确认 | 看本次会更新哪些项目/月份/页面 | 汇总 changed / unchanged / blocked / warnings |
| 异常处理 | 只处理失败项或补映射 | 指出是哪个来源、哪个 importer、哪种字段或依赖失败 |

换句话说，DM 日常更应该看到的是：

1. **source profile**
   - 你们的 workforce 从哪里来
   - capacity 从哪里来
   - milestone 从哪里来
   - board/page registry 从哪里来
2. **refresh scope**
   - 刷新本周
   - 刷新本月
   - 只刷新某个项目
3. **preview summary**
   - 会更新哪些数据族
   - 哪些页面会因此变动
   - 哪些来源缺失或过期
4. **confirm / run**
   - 明确确认后执行
5. **post-refresh summary**
   - 成功了什么
   - 跳过了什么
   - 失败了什么
   - 接下来应该先看哪个页面

### 8.10 当前产品现状与推荐理解

当前仓库已经具备很多**底层可组合能力**：

- 版本化导入；
- `dry-run` / `confirm`；
- 幂等 replay；
- assessment / reconciliation / snapshot；
- Dashboard 与 `pm tool query` 的读取能力。

但它**还没有完全收敛成一个 DM 级的一键编排入口**。

所以目前最准确的理解是：

- **当前现状**：已有可组合的 importer / sync / derivation 能力；
- **推荐方向**：把这些能力包装成 source profile + orchestrated refresh；
- **DM 体验目标**：不用长期直接面对 importer 名字和链路细节。

### 8.11 现在就可以按这个思路运转

在没有完全产品化之前，最实用的落地方式是：

1. **首次接入时**
   - 做好字段映射与来源归属
   - 明确每类事实的权威来源
   - 固化导入顺序
2. **把这套关系当作“本地 source profile”**
   - 即使现在还是人工约定，也尽量固定下来
3. **周期性刷新时**
   - workforce / capacity 按月或版本刷新
   - milestone / health evidence 按周刷新
   - registry 按低频变更维护
4. **每次刷新后**
   - 先看 CLI 摘要
   - 再看 Dashboard
5. **日常运营时**
   - 用 Copilot 做查询、解释、preview、confirm
   - 不把聊天当成底层事实批量写入通道

---

## 9. 第一步：初始化本地状态

```bash
pm init
pm config validate
pm connector validate --portable
```

### 这一步的意义

- `pm init`：初始化本地数据库结构和 starter config
- `pm config validate`：确认配置完整
- `pm connector validate --portable`：只做安全边界内的本地校验

### 这一步完成后，你应该看到什么

- 本地数据库路径可解析
- 没有明显配置缺项
- connector 配置至少在本地格式上可用

如果这里都没过，先不要继续接数据。

---

## 10. 第二步：如果你已经有现成数据库，先做副本，不要先碰活动库

最安全的做法：

```bash
pm backup create --label before-local-onboarding
```

然后把批准数据库复制到一个隔离副本，例如：

```bash
cp /approved/path/current.db /approved/temp/dm-local-onboarding.db
export DATABASE_PATH=/approved/temp/dm-local-onboarding.db
pm init
```

### 为什么一定先做副本

因为你现在做的是：

- 接入验证
- 结构检查
- 导入 rehearsal
- Dashboard 首次查看

这几个动作都不应该先碰活动数据库。

---

## 11. 第三步：如果你的数据不是完整数据库，而是结构化文件，按受控路径导入

典型导入顺序是：

1. workforce planning
2. resource capacity
3. milestone
4. project health re-import

核心原则：

- 先 dry-run
- 再 confirm
- 同一包可重放时应返回 `already_completed` 或 `no_op`
- 对保留 source family，受支持路径统一是 `pm onboarding` 的
  `profile save → preview → confirm`

例如：

```bash
DATABASE_PATH=/approved/temp/dm-local-onboarding.db \
python3 -m pm_agent.cli.app onboarding profile save \
  --profile-key workforce-json \
  --source-type workforce-planning-json \
  --file /approved/path/workforce.json

DATABASE_PATH=/approved/temp/dm-local-onboarding.db \
python3 -m pm_agent.cli.app onboarding preview --profile-key workforce-json

DATABASE_PATH=/approved/temp/dm-local-onboarding.db \
python3 -m pm_agent.cli.app onboarding confirm --run-id <onboarding-run-id>
```

其他保留导入也遵循同样模式，只是 `--source-type` 和文件路径不同。

### 什么时候才算这一步成功

你至少应该能回答：

- 是否完成导入？
- 导入的是不是 authoritative/complete manifest？
- replay 是否幂等？
- aggregate count 有没有明显异常？

---

## 12. 第四步：跑最小只读验证，不要先盯 Dashboard

在打开 Dashboard 前，先确认基础查询能返回合理结果。

最小顺序建议：

```bash
pm tool list
pm tool query team-workload-overview
pm tool query project-health-review
pm tool query management-attention
pm tool query connector-status-review
pm sync status
```

如果你已经有对应数据，再继续测：

```bash
pm tool query layered-project-health-review --project <exact-project-id>
pm tool query delivery-execution-review --project <exact-project-id>
pm tool query delivery-attention-center
pm tool query action-followup
pm tool query contract-continuity-review --days 180
pm weekly-brief query
```

如果你有 capacity 数据，再跑：

```bash
pm tool query resource-capacity-heatmap --param year=<YYYY> --param month=<1-12> --param plan_version_id=<exact-plan-id>
```

### 为什么这一步很重要

因为如果 CLI 查询都没结果，Dashboard 空白通常只是**后果**，不是问题本身。

---

## 13. 第五步：再启动 Dashboard

当本地数据已经验证过后：

```bash
pm dashboard serve
```

默认打开：

```text
http://127.0.0.1:5001
```

### 第一次打开建议这样看

1. `Overview`
2. `Connectors`
3. `Project Health`
4. `Attention`
5. `Team / Monthly Plan / HIREF`
6. `Layered Health / Delivery Execution / Capacity / Weekly Brief v2`

如果你不理解页面里每个 item 是什么，看：

- `docs/DASHBOARD_USAGE_GUIDE.md`

---

## 14. 页面没数据时，优先查什么

| 页面 | 先查什么 |
| --- | --- |
| Team / Projects / Monthly Plan | workforce / allocation 是否导入 |
| HIREF | contract / slot / continuity 数据是否存在 |
| Project Health | board mapping、JIRA / Confluence 快照、freshness |
| Attention | reconciliation 是否跑过 |
| Layered Health | 七维评估是否完成 |
| Delivery Execution | milestone / execution facts 是否存在 |
| Capacity Heatmap | plan version、month、capacity import 是否具备 |
| Weekly Brief v2 | health / attention / next actions 是否已有结果 |
| Connectors | 本地 connector registry 和 sync 结果是否存在 |
| Snapshots | 是否真的保存过 snapshot |

---

## 15. 给使用者的最短上手流程

如果你只想要“拿着现在已有数据开始”的最短版本，用这套：

### 11.1 已有批准数据库副本

```bash
cd src
source .venv/bin/activate

export DATABASE_PATH=/approved/temp/dm-local-onboarding.db
pm init
pm config validate
pm connector validate --portable
pm tool query team-workload-overview
pm tool query project-health-review
pm dashboard serve
```

### 11.2 已有批准导入文件，但还没有目标数据库

```bash
cd src
source .venv/bin/activate

export DATABASE_PATH=/approved/temp/dm-local-onboarding.db
pm init
python3 -m pm_agent.cli.app onboarding profile save --profile-key workforce-json --source-type workforce-planning-json --file /approved/path/workforce.json
python3 -m pm_agent.cli.app onboarding preview --profile-key workforce-json
python3 -m pm_agent.cli.app onboarding confirm --run-id <onboarding-run-id>
pm tool query team-workload-overview
pm dashboard serve
```

当然，实际要看到更多页面内容，你还需要继续导入 capacity / milestone /
project health / attention 所依赖的数据。

---

## 16. 什么时候必须停下来

出现以下情况时，不要继续写入或扩大范围：

- 输出暴露 credential、endpoint、raw payload、raw error
- freshness 不足，但你却要基于它做判断
- 导入不是 authoritative complete manifest
- replay 不是 `already_completed` / `no_op`
- aggregate count 异常
- integrity / foreign key 检查失败
- token / preview-confirm 行为异常
- connector 结果范围超出预期

这时请回到：

- `docs/REAL_ENVIRONMENT_UAT_RUNBOOK.md`

按正式停止条件处理。

---

## 17. 哪些文档搭配看最有用

### 给第一次接入的使用者

1. `src/README.md`
2. `docs/LOCAL_DATA_ONBOARDING_GUIDE.md`
3. `docs/EXTERNAL_IMPORT_FORMAT_MATRIX.md`
4. `docs/DASHBOARD_USAGE_GUIDE.md`

### 给要先体验系统的人

1. `src/sample-data/README.md`
2. `docs/SYNTHETIC_DEMO_WALKTHROUGH.md`
3. `docs/DASHBOARD_USAGE_GUIDE.md`

### 给要做正式真实环境验证的人

1. `docs/REAL_ENVIRONMENT_UAT_RUNBOOK.md`
2. `docs/LOCAL_PRODUCT_UPGRADE_LIFECYCLE.md`
3. `PROGRESS.md`

---

## 18. 最后一句话

如果你是使用者，最容易踩的坑只有一个：

> **以为页面空白是 Dashboard 问题，其实通常是本地数据准备还没完成。**

所以正确顺序永远是：

**先准备并验证本地数据 → 再开 Dashboard → 再解释页面结果。**
