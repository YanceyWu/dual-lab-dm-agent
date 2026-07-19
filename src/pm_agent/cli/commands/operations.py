"""Operational PM command groups and root commands."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

import typer
from rich import box
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from pm_agent.use_cases import (
    action_items_service,
    hiref_management_service,
    resource_planning_service,
    team_workload_service,
    weekly_report_service,
    use_case_executor,
)
from pm_agent.use_cases.resource_planning import AllocationRequest
from pm_agent.use_cases.service import ServiceResponse, UseCaseRequest
from pm_agent.cli.commands.common import console, spin
from pm_agent.rules import scoring as scoring_core
from pm_agent.rules.validation import validate_member, validate_project
from pm_agent.database import decision_log, repository

action_app = typer.Typer(help="Action Items 管理", no_args_is_help=True)
project_app = typer.Typer(help="项目管理", no_args_is_help=True)
decision_app = typer.Typer(help="决策记录", no_args_is_help=True)
hiref_app = typer.Typer(help="HIREF 合同与占位需求治理", no_args_is_help=True)

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

HIREF_URGENCY_LABELS = {
    "expired": "[bold red]expired[/bold red]",
    "critical": "[red]critical[/red]",
    "high": "[yellow]high[/yellow]",
    "medium": "[cyan]medium[/cyan]",
    "ok": "[green]ok[/green]",
    "unknown": "[dim]unknown[/dim]",
}

HIREF_ALIGNMENT_LABELS = {
    "aligned": "[green]aligned[/green]",
    "mismatch": "[red]mismatch[/red]",
    "no_active_assignment": "[yellow]no active project[/yellow]",
    "missing_current_hiref": "[red]missing current HIREF[/red]",
    "unknown": "[dim]unknown[/dim]",
}

HIREF_SLOT_LABELS = {
    "assigned": "[green]assigned[/green]",
    "reserved_for_next": "[cyan]reserved next[/cyan]",
    "placeholder_reserved": "[yellow]placeholder[/yellow]",
    "free": "[bold green]free[/bold green]",
}


def register(app: typer.Typer) -> None:
    @app.command()
    def allocate(
        project_id: str = typer.Option(..., "--project", "-p", help="项目ID (slug)"),
        skills: str = typer.Option("", "--skills", "-s", help="技能列表, 逗号分隔: java,aws"),
        role: str = typer.Option("", "--role", "-r", help="角色: backend_developer"),
        task_type: str = typer.Option("general", "--type", help="任务类型, 用于历史查询"),
        count: int = typer.Option(1, "--count", "-n", help="需要人数"),
    ):
        """推荐最佳人员分配方案"""
        required_skills = [skill.strip().lower() for skill in skills.split(",") if skill.strip()]

        allocation_input = AllocationRequest(
            query=f"allocate for {project_id}",
            project_id=project_id,
            role=role,
            required_skills=required_skills,
            task_type=task_type,
            count=count,
        )

        with spin("正在评估所有成员..."):
            result = resource_planning_service.recommend(allocation_input)

        if not result.success:
            console.print(f"[red]❌ {result.message}[/red]")
            raise typer.Exit(1)

        data = result.data
        project = data["project"]
        options = data["options"]
        all_scores = data["all_scores"]
        warnings = data.get("warnings", [])

        for warning in warnings:
            console.print(f"  [yellow]⚠  {warning}[/yellow]")

        console.print()
        console.print(
            Panel(
                f"[bold]项目：[/bold]{project['name']}  "
                f"[bold]需求：[/bold]{count}人 {role or ''}  "
                + (f"[bold]技能：[/bold]{', '.join(required_skills)}" if required_skills else ""),
                title="[bold cyan]📋 资源分配推荐[/bold cyan]",
                border_style="cyan",
            )
        )

        for option in options:
            table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold")
            table.add_column("姓名", style="bold", width=10)
            table.add_column("级别", width=8)
            table.add_column("负载", width=6)
            table.add_column("综合分", width=8)
            table.add_column("技能", width=6)
            table.add_column("推荐原因", style="dim")

            for member in option["members"]:
                breakdown = member.get("breakdown", {})
                load = 1.0 - breakdown.get("availability", 0.5)
                load_color = "green" if load < 0.6 else "yellow" if load < 0.9 else "red"
                score_color = "green" if member["score"] >= 0.75 else "yellow"
                table.add_row(
                    member["name"],
                    "",
                    f"[{load_color}]{load:.0%}[/{load_color}]",
                    f"[{score_color}]{member['score']:.3f}[/{score_color}]",
                    f"{breakdown.get('skill', 0):.0%}",
                    member.get("reason", ""),
                )

            console.print(f"\n[bold green]{option['label']}[/bold green]  (综合得分 {option['combined_score']:.3f})")
            console.print(table)

        blocked = [score for score in all_scores if score["blocked"]]
        if blocked:
            console.print("[dim]排除人员：[/dim]" + "，".join(f"{item['name']}({item['blocked_reason']})" for item in blocked))

        console.print()
        choice = typer.prompt("选择方案 [A/B/C] 或 [S]kip", default="S").strip().upper()

        if choice == "S":
            console.print("[dim]已跳过，未写入分配记录。[/dim]")
            return

        label_map = {"A": "方案A", "B": "方案B", "C": "方案C"}
        chosen_label = label_map.get(choice)
        if not chosen_label:
            console.print("[red]无效选择[/red]")
            raise typer.Exit(1)

        chosen_option_data = next((option for option in options if option["label"] == chosen_label), None)
        if not chosen_option_data:
            console.print(f"[red]{chosen_label} 不存在[/red]")
            raise typer.Exit(1)

        all_scoring_results = [
            scoring_core.ScoringResult(
                member_id=score["member_id"],
                member_name=score["name"],
                score=score["score"],
                breakdown=score.get("breakdown", {}),
                blocked=score["blocked"],
                blocked_reason=score.get("blocked_reason", ""),
                reason_text=score.get("reason", ""),
            )
            for score in all_scores
        ]
        all_options = [
            scoring_core.AllocationOption(
                label=option["label"],
                members=[
                    scoring_core.ScoringResult(
                        member_id=member["member_id"],
                        member_name=member["name"],
                        score=member["score"],
                        breakdown=member.get("breakdown", {}),
                    )
                    for member in option["members"]
                ],
                combined_score=option["combined_score"],
            )
            for option in options
        ]
        chosen_option = next(option for option in all_options if option.label == chosen_label)

        confirm_result = resource_planning_service.confirm(
            allocation_input, chosen_option, all_scoring_results, all_options
        )
        if confirm_result.success:
            console.print(f"\n[bold green]{confirm_result.message}[/bold green]")
            console.print(
                f"[dim]决策ID: #{confirm_result.decision_id}  "
                f"（后续可用 `pm decision outcome {confirm_result.decision_id}` 记录结果）[/dim]"
            )
            return
        console.print(f"[red]{confirm_result.message}[/red]")

    @app.command()
    def workload(
        team: Optional[str] = typer.Option(None, "--team", help="筛选特定团队"),
        member: Optional[str] = typer.Option(None, "--member", "-m", help="查看特定成员"),
    ):
        """查看团队工作负载"""
        if member:
            result = team_workload_service.member_detail(member)
        else:
            execution = use_case_executor.execute(
                UseCaseRequest(
                    use_case_id="team-workload-overview",
                    parameters={"team": team} if team else {},
                )
            )
            if execution.status != "success":
                console.print(f"[red]{'; '.join(execution.warnings)}[/red]")
                raise typer.Exit(1)
            result = ServiceResponse(success=True, data=execution.data)

        if not result.success:
            console.print(f"[red]{result.message}[/red]")
            raise typer.Exit(1)

        data = result.data
        members = data.get("members", [])
        stats = data.get("stats", {})

        if not members:
            console.print("[yellow]暂无成员数据。请先运行 `python scripts/seed.py`[/yellow]")
            return

        console.print()
        console.print(
            Panel(
                f"总人数 [bold]{stats['total']}[/bold]  ·  "
                f"可用（<80%）[bold green]{stats['available']}[/bold green]  ·  "
                f"满载（100%）[bold red]{stats['overloaded']}[/bold red]  ·  "
                f"平均负载 [bold]{stats['avg_load']:.0%}[/bold]",
                title="[bold cyan]👥 团队负载概览[/bold cyan]",
                border_style="cyan",
            )
        )

        table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold")
        table.add_column("姓名", width=12)
        table.add_column("级别", width=8)
        table.add_column("团队", width=12)
        table.add_column("负载", width=8)
        table.add_column("项目数", width=6)
        table.add_column("技能", style="dim")

        for member_row in sorted(members, key=lambda item: -item.get("current_load", 0)):
            load = member_row.get("current_load", 0.0)
            proj_count = member_row.get("active_projects", 0)
            load_color = "green" if load < 0.6 else "yellow" if load < 0.9 else "red"
            skills_preview = ", ".join(list(member_row.get("skills", {}).keys())[:4])
            table.add_row(
                member_row["name"],
                member_row.get("level", "-"),
                member_row.get("team", "-"),
                f"[{load_color}]{load:.0%}[/{load_color}]",
                str(proj_count),
                skills_preview,
            )

        console.print(table)

    @app.command()
    def report(
        output: Optional[str] = typer.Option(None, "--output", "-o", help="输出到文件 (Markdown)"),
    ):
        """生成本周状态周报"""
        with spin("正在汇总数据..."):
            result = weekly_report_service.weekly()

        if not result.success:
            console.print(f"[red]{result.message}[/red]")
            raise typer.Exit(1)

        report_text = result.data["report"]

        if output:
            Path(output).write_text(report_text, encoding="utf-8")
            console.print(f"[green]✅ 周报已保存至 {output}[/green]")
            return
        console.print(Markdown(report_text))

    @app.command()
    def capacity(
        month: str = typer.Option(
            "",
            "--month",
            "-m",
            help="Target month: jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec",
        ),
        version: str = typer.Option(
            "",
            "--version",
            "-v",
            help="Plan version id (v1.5). Default: auto-pick active forecast/baseline.",
        ),
        project_id: Optional[str] = typer.Option(None, "--project", "-p", help="Show who's free for a specific project"),
    ):
        """View team capacity for an upcoming month (who will have bandwidth?)"""
        del project_id

        if month:
            try:
                month_idx = next(
                    index + 1 for index, name in enumerate(MONTH_NAMES) if name.lower().startswith(month.lower()[:3])
                )
            except StopIteration:
                console.print(f"[red]Unknown month '{month}'. Use: jan|feb|mar|...[/red]")
                raise typer.Exit(1)
        else:
            month_idx = date.today().month
            month = MONTH_NAMES[month_idx - 1]

        month_label = MONTH_NAMES[month_idx - 1]
        rows, default_version = repository.get_capacity_rows(
            year=date.today().year,
            month=month_idx,
            plan_version_id=version or None,
        )

        free = [row for row in rows if row["month_load"] < 0.5]
        partial = [row for row in rows if 0.5 <= row["month_load"] < 1.0]
        full = [row for row in rows if row["month_load"] >= 1.0]

        version_label = ""
        if version:
            version_label = f"  ·  版本: [bold]{version}[/bold]"
        elif default_version:
            version_label = f"  ·  版本: [bold]{default_version['plan_version_id']}[/bold]"

        console.print()
        console.print(
            Panel(
                f"月份: [bold]{month_label} 2026[/bold]  ·  "
                f"完全空闲(<50%): [bold green]{len(free)}[/bold green]  ·  "
                f"部分可用(50-99%): [bold yellow]{len(partial)}[/bold yellow]  ·  "
                f"满载(100%+): [bold red]{len(full)}[/bold red]"
                f"{version_label}",
                title="[bold cyan]📅 人员容量预测[/bold cyan]",
                border_style="cyan",
            )
        )

        if free or partial:
            table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold")
            table.add_column("姓名", width=22)
            table.add_column("级别", width=8)
            table.add_column("团队", width=12)
            table.add_column(f"{month_label}负载", width=8)
            table.add_column("可用带宽", width=8)
            table.add_column("当前项目", style="dim")

            for row in free + partial:
                load = row["month_load"]
                load_color = "green" if load < 0.5 else "yellow"
                table.add_row(
                    row["name"],
                    row["level"] or "-",
                    row["team"] or "-",
                    f"[{load_color}]{load:.0%}[/{load_color}]",
                    f"{1.0 - load:.0%}",
                    (row["projects"] or "-")[:40],
                )
            console.print(table)
            return

        console.print(f"[yellow]  {month_label}月份所有人员均已满载。[/yellow]")

    @app.command()
    def validate():
        """检查数据完整性"""
        members = repository.get_all_members()
        projects = repository.get_all_projects()

        total_warnings = 0
        console.print(f"\n[bold]检查 {len(members)} 名员工...[/bold]")
        for member_row in members:
            validation_result = validate_member(member_row)
            for warning in validation_result.warnings:
                console.print(f"  [yellow]⚠  {member_row.get('name', member_row.get('id'))}: {warning}[/yellow]")
                total_warnings += 1
            for error in validation_result.errors:
                console.print(f"  [red]❌ {error}[/red]")

        console.print(f"\n[bold]检查 {len(projects)} 个项目...[/bold]")
        for project_row in projects:
            validation_result = validate_project(project_row)
            for error in validation_result.errors:
                console.print(f"  [red]❌ {error}[/red]")

        overdue = repository.get_action_items(overdue_only=True)
        if overdue:
            console.print(f"\n[yellow]⚠  {len(overdue)} 条逾期 Action Items[/yellow]")

        ext_ids = repository.get_employee_external_ids()
        if not ext_ids:
            console.print("\n[yellow]⚠  employee_external_ids 为空，JIRA assignee 到员工映射将退回名字匹配。[/yellow]")
            total_warnings += 1

        plan_versions = repository.get_plan_versions()
        if not plan_versions:
            console.print("\n[yellow]⚠  plan_versions 为空，capacity 将退回 legacy monthly_allocations 视图。[/yellow]")
            total_warnings += 1

        if total_warnings == 0:
            console.print("\n[bold green]✅ 数据检查通过，无异常。[/bold green]")
            return
        console.print(f"\n[yellow]共 {total_warnings} 条警告，建议修正后重新运行。[/yellow]")


@action_app.command("add")
def action_add(
    title: str = typer.Argument(..., help="Action Item 标题"),
    owner: Optional[str] = typer.Option(None, "--owner", help="负责人ID"),
    due: Optional[str] = typer.Option(None, "--due", help="截止日期 YYYY-MM-DD"),
    priority: str = typer.Option("medium", "--priority", "-p"),
    source: str = typer.Option("manual", "--source"),
    notes: str = typer.Option("", "--notes"),
):
    """添加一条 Action Item"""
    result = action_items_service.add(
        title=title,
        owner_id=owner,
        due_date=due,
        priority=priority,
        source=source,
        notes=notes,
    )
    console.print(f"[green]{result.message}[/green]" if result.success else f"[red]{result.message}[/red]")


@action_app.command("list")
def action_list(
    overdue: bool = typer.Option(False, "--overdue", help="只看逾期"),
    owner: Optional[str] = typer.Option(None, "--owner"),
):
    """列出 Action Items"""
    result = action_items_service.list_open(owner_id=owner, overdue_only=overdue)
    items = result.data.get("items", [])

    if not items:
        console.print("[dim]没有待处理的 Action Items。[/dim]")
        return

    table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold")
    table.add_column("ID", width=5)
    table.add_column("优先级", width=6)
    table.add_column("标题", width=35)
    table.add_column("负责人", width=10)
    table.add_column("截止日期", width=12)
    table.add_column("来源", style="dim", width=20)

    for item in items:
        priority = item.get("priority", "medium")
        pri_color = "red" if priority == "high" else "yellow" if priority == "medium" else "dim"
        table.add_row(
            str(item["id"]),
            f"[{pri_color}]{priority}[/{pri_color}]",
            item["title"],
            item.get("owner_name") or "-",
            item.get("due_date") or "-",
            item.get("source") or "-",
        )

    console.print(table)


@action_app.command("done")
def action_done(
    item_id: int = typer.Argument(..., help="Action Item ID"),
):
    """标记 Action Item 为完成"""
    result = action_items_service.complete(item_id)
    console.print(f"[green]{result.message}[/green]" if result.success else f"[red]{result.message}[/red]")


@project_app.command("list")
def project_list(
    status: Optional[str] = typer.Option(None, "--status", help="active|planning|at_risk|done"),
):
    """列出项目"""
    projects = repository.get_all_projects(status=status)
    if not projects:
        console.print("[dim]暂无项目数据。[/dim]")
        return

    table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold")
    table.add_column("ID", width=20)
    table.add_column("名称", width=25)
    table.add_column("优先级", width=6)
    table.add_column("状态", width=10)
    table.add_column("JIRA Key", width=8)
    table.add_column("目标完成", width=12)

    status_colors = {
        "active": "green",
        "at_risk": "red",
        "planning": "yellow",
        "done": "dim",
    }
    for project in projects:
        status_value = project.get("status", "active")
        color = status_colors.get(status_value, "white")
        table.add_row(
            project["id"],
            project["name"],
            f"P{project.get('priority', 3)}",
            f"[{color}]{status_value}[/{color}]",
            project.get("jira_key") or "-",
            project.get("target_end") or "-",
        )
    console.print(table)


@project_app.command("team")
def project_team(
    project_id: str = typer.Argument(..., help="项目ID"),
):
    """查看项目团队成员"""
    team = repository.get_project_team(project_id)
    if not team:
        project = repository.get_project(project_id)
        if not project:
            console.print(f"[red]项目 '{project_id}' 不存在[/red]")
        else:
            console.print("[dim]该项目暂无分配成员。[/dim]")
        return

    table = Table(box=box.SIMPLE_HEAVY, title=f"项目团队: {team[0]['project_name']}")
    table.add_column("姓名")
    table.add_column("角色")
    table.add_column("投入比例")
    for row in team:
        table.add_row(row["member_name"], row.get("role") or "-", f"{row.get('allocation', 0):.0%}")
    console.print(table)


@decision_app.command("list")
def decision_list(limit: int = typer.Option(10, "--limit", "-n")):
    """查看最近决策记录"""
    records = repository.get_recent_decisions(limit=limit)
    if not records:
        console.print("[dim]暂无决策记录。[/dim]")
        return

    table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold")
    table.add_column("ID", width=5)
    table.add_column("类型", width=12)
    table.add_column("描述", width=40)
    table.add_column("结果", width=10)
    table.add_column("时间", width=20)

    outcome_colors = {
        "pending": "yellow",
        "success": "green",
        "delayed": "orange3",
        "failed": "red",
        "cancelled": "dim",
    }
    for record in records:
        outcome = record.get("outcome", "pending")
        color = outcome_colors.get(outcome, "white")
        table.add_row(
            str(record["id"]),
            record.get("type", "-"),
            record.get("description", "")[:38],
            f"[{color}]{outcome}[/{color}]",
            record.get("created_at", "")[:16],
        )
    console.print(table)


@decision_app.command("outcome")
def decision_outcome(
    decision_id: int = typer.Argument(...),
    result: str = typer.Option(..., "--result", "-r", help="success|delayed|failed|cancelled"),
    note: str = typer.Option("", "--note", help="备注说明"),
):
    """更新决策结果"""
    try:
        decision_log.set_outcome(decision_id, result, note)
        console.print(f"[green]✅ 决策 #{decision_id} 结果已记录：{result}[/green]")
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")


def _hiref_days_text(days: int | None) -> str:
    if days is None:
        return "-"
    return str(days)


@hiref_app.command("summary")
def hiref_summary(
    days: int = typer.Option(180, "--days", min=1, help="审查未来 N 天内的 HIREF 风险"),
):
    """汇总 STFTE 合同到期、可复用 HIREF slots、以及 open placeholders。"""
    result = hiref_management_service.summary(days=days)
    if not result.success:
        console.print(f"[red]{result.message}[/red]")
        raise typer.Exit(1)

    summary = result.data["summary"]
    console.print()
    console.print(
        Panel(
            f"STFTE: [bold]{summary['active_stfte']}[/bold]  ·  "
            f"缺少当前HIREF: [bold red]{summary['missing_current_hiref']}[/bold red]  ·  "
            f"{days}天内到期(无next): [bold yellow]{summary['expiring_without_next']}[/bold yellow]  ·  "
            f"{days}天内已预留next: [bold cyan]{summary['expiring_with_next']}[/bold cyan]  ·  "
            f"项目不匹配: [bold red]{summary['project_mismatches']}[/bold red]  ·  "
            f"空闲slots: [bold green]{summary['free_slots']}[/bold green]  ·  "
            f"open placeholders: [bold]{summary['open_placeholders']}[/bold]",
            title="[bold cyan]📄 HIREF Summary[/bold cyan]",
            border_style="cyan",
        )
    )

    top_risks = result.data.get("top_risks", [])
    if top_risks:
        table = Table(box=box.SIMPLE_HEAVY, header_style="bold")
        table.add_column("姓名", width=14)
        table.add_column("当前HIREF", width=18)
        table.add_column("到期", width=10)
        table.add_column("天数", width=6, justify="right")
        table.add_column("风险", width=12)
        table.add_column("项目检查", width=16)
        table.add_column("建议", overflow="fold")
        for row in top_risks:
            table.add_row(
                row["name"],
                row.get("current_hiref") or "-",
                row.get("end_date") or "-",
                _hiref_days_text(row.get("days_until_expiry")),
                HIREF_URGENCY_LABELS.get(row["urgency"], row["urgency"]),
                HIREF_ALIGNMENT_LABELS.get(row["project_alignment_status"], row["project_alignment_status"]),
                row["recommendation"],
            )
        console.print("\n[bold]Top review items[/bold]")
        console.print(table)

    placeholders = result.data.get("open_placeholders", [])
    if placeholders:
        table = Table(box=box.SIMPLE_HEAVY, header_style="bold")
        table.add_column("Placeholder", width=18)
        table.add_column("HIREF ID", width=18)
        table.add_column("Project", width=24)
        table.add_column("Next Demand", width=11)
        table.add_column("Peak", width=6, justify="right")
        table.add_column("建议", overflow="fold")
        for row in placeholders:
            table.add_row(
                row["display_name"],
                row.get("hiref_id") or "-",
                row.get("project_display") or "-",
                row.get("next_demand_month") or "-",
                f"{row.get('peak_allocation', 0.0):.0%}",
                row["recommendation"],
            )
        console.print("\n[bold]Open placeholder demand[/bold]")
        console.print(table)


@hiref_app.command("review")
def hiref_review(
    days: int = typer.Option(180, "--days", min=1, help="审查未来 N 天内到期或异常的 STFTE"),
    all_stfte: bool = typer.Option(False, "--all-stfte", help="显示全部 active STFTE，而不是只看审查窗口"),
):
    """查看 STFTE / HIREF 逐人审查清单。"""
    result = hiref_management_service.review(days=None if all_stfte else days)
    if not result.success:
        console.print(f"[red]{result.message}[/red]")
        raise typer.Exit(1)

    rows = result.data["rows"]
    if not rows:
        console.print("[green]没有需要展示的 STFTE / HIREF 记录。[/green]")
        return

    table = Table(box=box.SIMPLE_HEAVY, header_style="bold")
    table.add_column("姓名", width=14)
    table.add_column("当前HIREF", width=18)
    table.add_column("到期", width=10)
    table.add_column("天数", width=6, justify="right")
    table.add_column("风险", width=10)
    table.add_column("项目检查", width=16)
    table.add_column("实际项目", width=20)
    table.add_column("HIREF项目", width=20)
    table.add_column("Next HIREF", width=18)
    table.add_column("建议", overflow="fold")

    for row in rows:
        table.add_row(
            row["name"],
            row.get("current_hiref") or "-",
            row.get("end_date") or "-",
            _hiref_days_text(row.get("days_until_expiry")),
            HIREF_URGENCY_LABELS.get(row["urgency"], row["urgency"]),
            HIREF_ALIGNMENT_LABELS.get(row["project_alignment_status"], row["project_alignment_status"]),
            row.get("actual_project_display") or "-",
            row.get("hiref_project") or "-",
            row.get("next_hiref") or "-",
            row["recommendation"],
        )

    console.print(table)
    actionable = sum(1 for row in rows if row["requires_action"])
    console.print(f"\n[dim]Rows: {len(rows)} · Actionable: {actionable}[/dim]")


@hiref_app.command("slots")
def hiref_slots(
    free_only: bool = typer.Option(False, "--free-only", help="只显示当前无人占用的 HIREF slots"),
):
    """查看已登记的 HIREF slot 占用情况。"""
    result = hiref_management_service.slots(free_only=free_only)
    if not result.success:
        console.print(f"[red]{result.message}[/red]")
        raise typer.Exit(1)

    rows = result.data["rows"]
    if not rows:
        console.print("[yellow]没有符合条件的 HIREF slots。[/yellow]")
        return

    table = Table(box=box.SIMPLE_HEAVY, header_style="bold")
    table.add_column("HIREF ID", width=18)
    table.add_column("Project", width=24)
    table.add_column("到期", width=10)
    table.add_column("天数", width=6, justify="right")
    table.add_column("状态", width=14)
    table.add_column("Assigned To", width=14)
    table.add_column("Reserved For", width=14)
    table.add_column("Placeholder", width=16)
    table.add_column("建议", overflow="fold")

    for row in rows:
        table.add_row(
            row["id"],
            row.get("project") or "-",
            row.get("end_date") or "-",
            _hiref_days_text(row.get("days_until_expiry")),
            HIREF_SLOT_LABELS.get(row["occupancy_status"], row["occupancy_status"]),
            row.get("assigned_to") or "-",
            row.get("reserved_for_next") or "-",
            row.get("placeholder_name") or "-",
            row["recommendation"],
        )

    console.print(table)


@hiref_app.command("placeholders")
def hiref_placeholders():
    """查看 open HIREF placeholders / staffing demand。"""
    result = hiref_management_service.placeholders()
    if not result.success:
        console.print(f"[red]{result.message}[/red]")
        raise typer.Exit(1)

    rows = result.data["rows"]
    if not rows:
        console.print("[green]没有 open HIREF placeholders。[/green]")
        return

    table = Table(box=box.SIMPLE_HEAVY, header_style="bold")
    table.add_column("Placeholder", width=18)
    table.add_column("HIREF ID", width=18)
    table.add_column("Registered", width=10)
    table.add_column("Project", width=24)
    table.add_column("Next Demand", width=11)
    table.add_column("Peak", width=6, justify="right")
    table.add_column("Linked Employee", width=16)
    table.add_column("Status", width=10)
    table.add_column("建议", overflow="fold")

    for row in rows:
        table.add_row(
            row["display_name"],
            row.get("hiref_id") or "-",
            "yes" if row["slot_registered"] else "no",
            row.get("project_display") or "-",
            row.get("next_demand_month") or "-",
            f"{row.get('peak_allocation', 0.0):.0%}",
            row.get("linked_employee_name") or "-",
            row.get("status") or "-",
            row["recommendation"],
        )

    console.print(table)
