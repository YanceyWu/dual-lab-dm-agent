"""Weekly report service with deterministic text output."""

from __future__ import annotations

from datetime import date

from pm_agent.use_cases.service import ServiceRequest, ServiceResponse, BaseService
from pm_agent.database import repository


class WeeklyReportService(BaseService):
    supported_requests = ["weekly_report", "status_summary"]

    def run(self, inp: ServiceRequest) -> ServiceResponse:
        return self.weekly()

    def weekly(self, reference_date: date | None = None) -> ServiceResponse:
        today = reference_date or date.today()
        week_label = f"{today.year}-W{today.isocalendar().week:02d}"

        # Gather data — include all non-done/cancelled projects
        all_projects = repository.get_all_projects()
        projects = [p for p in all_projects if p.get("status") not in ("done", "cancelled")]
        members = repository.get_all_members()
        actions = repository.get_action_items(status="open")
        overdue = repository.get_action_items(overdue_only=True)
        decisions = repository.get_recent_decisions(limit=10)
        confluence_signals = repository.get_project_confluence_signals()
        change_request_summaries = repository.get_project_change_request_summaries()
        action_tracker_summary = repository.get_latest_action_tracker_summary()
        current_state_freshness = repository.get_current_state_staffing_publication_freshness()

        report = _build_report(
            week_label,
            projects,
            members,
            actions,
            overdue,
            decisions,
            confluence_signals,
            change_request_summaries,
            action_tracker_summary,
            current_state_freshness,
        )

        return ServiceResponse(
            success=True,
            message=f"周报已生成：{week_label}",
            data={
                "week":      week_label,
                "report":    report,
                "raw": {
                    "projects":  projects,
                    "members":   members,
                    "actions":   actions,
                    "overdue":   overdue,
                    "decisions": decisions,
                    "confluence_signals": confluence_signals,
                    "change_request_summaries": change_request_summaries,
                    "action_tracker_summary": action_tracker_summary,
                },
            },
        )


def _build_report(
    week: str,
    projects: list[dict],
    members: list[dict],
    actions: list[dict],
    overdue: list[dict],
    decisions: list[dict],
    confluence_signals: dict[str, dict],
    change_request_summaries: dict[str, dict],
    action_tracker_summary: dict | None,
    current_state_freshness: dict,
) -> str:
    at_risk = [p for p in projects if p.get("status") == "at_risk"]
    known_members = [
        member for member in members if isinstance(member.get("current_load"), (int, float))
    ]
    overloaded = [m for m in known_members if float(m.get("current_load", 0.0)) >= 1.0]
    member_states = {str(member.get("current_state_staffing_state") or "unknown") for member in members}
    freshness_state = str(current_state_freshness.get("state") or "unknown")
    member_load_summary = (
        f"，{len(overloaded)} 人满载"
        + ("（当前态数据已过期）" if freshness_state == "stale" else "")
        if members
        and member_states == {"known"}
        and freshness_state in {"fresh", "stale"}
        else (
            "，当前态负载部分可用"
            if freshness_state == "partial"
            else "，当前态负载不可用"
            if freshness_state == "unavailable"
            else "，当前态负载未知"
        )
        if members
        else "，负载正常"
    )
    high_actions = [a for a in actions if a.get("priority") == "high"]
    open_changes = sum(
        int(item.get("open_changes") or 0)
        for item in change_request_summaries.values()
    )
    confluence_covered = sum(1 for p in projects if p["id"] in confluence_signals)

    lines = [
        f"# 周报  {week}",
        "",
        "## 📊 整体状态",
        f"- 活跃项目：{len(projects)} 个"
        + (f"，其中 **{len(at_risk)} 个风险项目**" if at_risk else ""),
        f"- 团队规模：{len(members)} 人"
        + member_load_summary,
        f"- 待办事项：{len(actions)} 条开放"
        + (f"，**{len(overdue)} 条逾期**" if overdue else ""),
        f"- 变更请求：{open_changes} 条开放"
        + (f"，Confluence 状态覆盖 {confluence_covered}/{len(projects)} 个项目" if projects else ""),
        "",
    ]

    if at_risk:
        lines += ["## ⚠️  风险项目"]
        for p in at_risk:
            lines.append(f"- **{p['name']}** — {p.get('notes', '无备注')}")
        lines.append("")

    lines += ["## 📁 项目进展"]
    for p in projects:
        status_icon = {"active": "🟢", "at_risk": "🔴", "planning": "🟡"}.get(
            p.get("status", ""), "⚪"
        )
        target = p.get("target_end") or "未设定"
        lines.append(f"- {status_icon} **{p['name']}**（优先级P{p.get('priority',3)}，目标：{target}）")
        lines.extend(_build_project_signal_lines(p, confluence_signals, change_request_summaries))
    lines.append("")

    if overloaded and member_states == {"known"} and freshness_state in {"fresh", "stale"}:
        lines += ["## 👥 资源警告（满载人员）"]
        lines.append(f"- 共 **{len(overloaded)}** 人当前满载（100%）")
        if freshness_state == "stale":
            lines.append("- 当前态人员负载来自最近一次已发布但已过期的 current-state staffing publication。")
        # Only list people with >1 project (at risk of dropping things)
        multi = [m for m in overloaded if m.get('active_projects', 0) > 1]
        if multi:
            lines.append("- 跨多项目满载（重点关注）：")
            for m in multi:
                lines.append(
                    f"  - {m['name']}（{m.get('level','')}）："
                    f"{m.get('active_projects',0)} 个项目"
                )
        lines.append("")

    if action_tracker_summary:
        lines += ["## 🔗 跨项目 Tracker"]
        lines.append(
            f"- 最新快照 {action_tracker_summary['synced_date']}："
            f"开放 {action_tracker_summary['open']} 条，Blocked {action_tracker_summary['blocked']} 条，"
            f"In Progress {action_tracker_summary['in_progress']} 条"
        )
        lines.append("")

    if high_actions:
        lines += ["## 🔥 高优先级待办"]
        for a in high_actions[:5]:
            owner = a.get("owner_name") or "未分配"
            due = a.get("due_date") or "未设期限"
            lines.append(f"- [{owner}] {a['title']}（截止：{due}）")
        lines.append("")

    if decisions:
        lines += ["## 📋 本周决策记录"]
        for d in decisions[:5]:
            outcome_map = {
                "pending": "⏳", "success": "✅",
                "delayed": "⚠️", "failed": "❌", "cancelled": "🚫",
            }
            icon = outcome_map.get(d.get("outcome", "pending"), "⏳")
            lines.append(f"- {icon} {d['description']}")
        lines.append("")

    lines.append("---")
    lines.append(f"*由 PM 工作台自动生成 · {date.today().isoformat()}*")

    return "\n".join(lines)


def _build_project_signal_lines(
    project: dict,
    confluence_signals: dict[str, dict],
    change_request_summaries: dict[str, dict],
) -> list[str]:
    lines: list[str] = []
    project_id = project["id"]

    confluence = confluence_signals.get(project_id)
    if confluence:
        if confluence.get("source") == "snapshot":
            summary = confluence.get("summary_text") or confluence.get("risks_text") or "无摘要"
            status_as_of = confluence.get("status_as_of") or confluence.get("snapshot_date") or "-"
            rag_status = confluence.get("rag_status") or "UNKNOWN"
            lines.append(
                f"  - Confluence: {rag_status} / {status_as_of} — {summary}"
            )
        else:
            modified = confluence.get("last_modified") or confluence.get("last_synced") or "-"
            summary = confluence.get("content_summary") or "已登记状态页，暂无摘要"
            lines.append(
                "  - Confluence: "
                f"{confluence.get('title') or confluence.get('board_name') or '状态页'} "
                f"（registry / 未拉取快照，更新于 {modified}）— {summary}"
            )

    change_summary = change_request_summaries.get(project_id)
    if change_summary and int(change_summary.get("open_changes") or 0) > 0:
        lines.append(
            "  - Change Requests: "
            f"{change_summary['open_changes']} 条开放，"
            f"高优先级 {change_summary['high_priority_changes']} 条，"
            f"下一窗口 {change_summary.get('next_change_start') or '-'}"
        )
        for item in change_summary.get("open_change_items", [])[:2]:
            lines.append(
                f"    - {item['id']} | {item['state']} | {item['summary']}"
            )

    return lines
