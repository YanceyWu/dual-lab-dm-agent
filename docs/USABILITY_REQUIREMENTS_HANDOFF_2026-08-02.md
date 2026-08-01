# Usability Requirements Handoff — 2026-08-02

目标：在不新增业务功能的前提下，把当前产品从"能力已验证"推进到"开箱可用、可实操、可复核"。本文件是独立会话的交接依据；`PROGRESS.md` 仍是当前状态唯一权威，本文件只记录需求、验收指标与门禁。

## 总体约束（所有条目通用）

- 不新增业务能力：只允许数据资产、测试、文档、决策记录，以及（仅在 owner 明确选择时）对既有引擎的受控接口。
- 只使用合成数据与稳定匿名 ID；不接触真实数据、凭据、connector；不推送、合入、打 tag、发布。
- 每个条目有界、可独立审查、可回退；任何持久化写入遵循 propose → preview → confirm → persist。
- 每个条目完成后：更新 `PROGRESS.md`、本地提交、停在审查门；不得自动进入下一项。
- 缺失/过期/冲突的证据必须显式记录为 UNKNOWN，不得推断为零、健康、可用或安全。

## R1 — 重建合成演示数据（让新能力开箱可见）

现状：`src/sample-data/demo/sample_pm.db` 只有 27 张旧表，`load_sample_data.py` 只跑旧导入器；Phase 1–6 能力在 demo 状态下全部查不到内容。

需求：
1. 提供一条可重复的合成流水线（扩展 `load_sample_data.py` 或新增独立脚本），从干净库依次执行：bootstrap → workforce planning 导入 → resource capacity 导入 → project health re-import（派生 + 七维评估，走 IP-033 入口）→ Milestone 导入 → Attention 对账 → Weekly Brief v2 快照。
2. 重新生成或按需生成 `src/sample-data/demo/sample_pm.db`，使 README 的 demo 路径能展示全部已提升能力。

验收指标：
- 从当前 checkout 用一条文档化的命令序列可生成演示库，且重跑幂等（不重复生成评估/快照）。
- 以下命令对同一演示项目返回非空、契约合规的结果：`layered-project-health-review`、`delivery-execution-review`、`delivery-attention-center`、`resource-capacity-heatmap`、`pm weekly-brief query`；至少一个项目存在 `completed` 的七维评估。
- 所有数据仍为合成/匿名；`make validate` 的 repository-boundary 与 synthetic-samples 检查通过。
- 生成脚本与结果均本地提交；`PROGRESS.md` 记录生成命令、幂等证据与已知限制。

非目标：不新增 runtime 能力，不改评估引擎，不引入真实数据。

## R2 — 合成集成演练手册（从零到每周简报）

需求：新增或扩展 `docs/` 下的演练文档，以合成数据完整走一遍 DM 典型周工作流，并记录每步命令与预期输出。

验收指标：
- 手册从当前 checkout 可逐条执行；每步给出命令、预期输出要点、失败时的排查提示。
- 覆盖链条：干净库 → 全部结构化导入 → 派生 → 七维评估 → Attention 对账 → Weekly Brief v2 组成（含 snapshot preview/confirm）→ Dashboard/CLI 读取。
- 手册显式列出 UNKNOWN 区域（真实 connector、真实数据、UAT 之外的任何外部分支）。
- 手册经独立只读复核；`PROGRESS.md` 记录其路径与复核结论。

## R3 — IP-033 审查与验收（当前停在门里）

现状：`codex/phase-4-assessment-entry` 提交 `1d73765` 已验证（335 项测试 + rehearse-release 通过），等待 owner 审查。

需求：独立只读复核该提交（对照 `implementation-packs/IP-033_PHASE_4_ASSESSMENT_ENTRY.md`），由 owner 决定接受或要求修正。

验收指标：
- 复核记录写入 `PROGRESS.md`（结论、证据、是否放行）。
- 若接受：在 `PROGRESS.md` 记录接受决策与确切提交；不推送、不并入 main。
- 若需修正：修正为一个有界切片，重跑聚焦测试、`make validate`、`make rehearse-release`（涉及 schema 时），再回到审查门。

## R4 — 两个"引擎有、入口无"边界的决策记录

现状：Phase 4 配置 preview/confirm 只有 Python API；Phase 5 capacity-aware Staffing 开关无公开命令（均为既有实现，非本次新增）。

需求：由 owner 决策并记录：(a) 配置操作是否需要一个受控命令；(b) 容量约束开关是否需要一个受控命令；或两者都维持 Python-only。

验收指标：
- 决策（含理由与后果）写入 `PROGRESS.md` 与相关实施包/架构文档。
- 若选择"维持 Python-only"：文档明确"操作者不可经产品界面修改配置/启用容量约束"为已知边界，不再隐含可用。
- 若选择"补受控命令"：作为单独授权的有界批次执行，遵循 preview/confirm、聚焦测试、全量验证与独立复核；仍不构成新业务能力。

## R5 — 跨能力集成测试

需求：新增一条自动化集成测试，覆盖 R2 的核心链条，防止各能力"各自验证通过、合起来不可用"。

验收指标：
- 测试从空临时库开始：bootstrap → workforce/resource 导入 → project health re-import（含评估）→ Milestone 导入 → Attention 对账 → Weekly Brief v2 组成；断言关键结果非空且契约合规。
- 断言至少一项：评估结果可被 `layered-project-health-review` 读取；Attention 对账后 Center 返回覆盖状态；Weekly Brief v2 的 section 覆盖非 `not_available` 项目存在。
- 测试使用合成数据；`make validate` 通过（运行时测试数增加并记录）。

## R6 — UAT 手册修订（仅文档，不执行）

需求：按集成候选修订 `docs/REAL_ENVIRONMENT_UAT_RUNBOOK.md`，使未来真实环境 UAT 有可批准的流程依据。

验收指标：
- 手册与当前架构/契约一致：配置与只读 use cases、connector 探针/同步、staffing 写路径、Dashboard 预览/确认/回放、停止条件均对应现版本。
- 修订稿经 owner 批准后才视为有效；批准前不得执行任何真实环境动作。
- `PROGRESS.md` 记录"手册已修订待批准"或"已批准"状态。

非目标：不执行 UAT，不接触真实数据/connector。

## R7 — 文档状态一致性扫描

现状：2026-08-02 已发现并修正 ROADMAP 落后三个 Phase 的漂移；需要防止复发。

需求：全库扫描状态声明（PROGRESS、ROADMAP、architecture、implementation-packs/INDEX、agent instructions），收敛"当前状态"的唯一事实源。

验收指标：
- 输出一份扫描清单：每处状态声明的位置、与 PROGRESS 的差异、处置（修正/删除/改为引用）。
- 处置后：ROADMAP/architecture/IP 索引不再复制可漂移的当前状态，或明确标注"以 PROGRESS.md 为准"；agent instructions 与已提升能力清单一致。
- 扫描清单与处置记录写入 `PROGRESS.md`；不涉及 runtime 改动，无需 `make rehearse-release`，但 `make validate` 通过。

## 建议执行顺序与门禁

1. R3（先清掉已停在门里的验收，避免新会话分心）。
2. R1 → R2 → R5（共享同一条合成流水线，可连续但逐项停止审查）。
3. R4（独立决策，可与 R1–R3 并行；决策不实施）。
4. R6、R7（独立文档批次，可与任何一项并行）。

每项完成后停止并汇报，等待 owner 批准再进下一项；不得把"总体批准"当成单项放行。

## 新会话开场提示词（copy-ready）

```text
你是本仓库的交付交接执行者。先读 AGENTS.md、PROGRESS.md、docs/USABILITY_REQUIREMENTS_HANDOFF_2026-08-02.md，并检查 Git 状态（分支/HEAD/工作区）。

任务：在不新增业务功能的前提下，按交接文档执行 R3 → R1 → R2 → R5 → R4 → R6 → R7（R4/R6/R7 可在 owner 明确指示下并行）。每项开始前：复述该项需求与验收指标；只做该有界切片；不自动进入下一项。

每项完成后：跑聚焦测试与 make validate（涉及 schema/导入/打包时加 make rehearse-release），做独立只读复核，更新 PROGRESS.md（变更、验证证据、未解决风险、确切的下一步与提交状态），本地提交，停止等待 owner 审查。全程只读外部状态：不推送、不合入 main、不打 tag、不访问 connector、不使用真实数据。任何写入遵循 propose → preview → confirm → persist。

最终汇报按 AGENTS.md 的强制性完成报告格式：改了什么和为什么；可用功能与用法；对现有模块/数据/兼容性的影响；未做范围与下一门；测试与复核证据；提交/推送状态。
```
