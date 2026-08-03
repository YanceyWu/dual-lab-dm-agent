"""Backup, use case, and sync command groups."""

from __future__ import annotations

from typing import Optional

import typer
from rich import box
from rich.panel import Panel
from rich.table import Table

from pm_agent.cli.commands.common import console, format_age_hours
from pm_agent.database import repository
from pm_agent.repo_tools import backup as backup_core

backup_app = typer.Typer(help="代码备份点 / DB 快照工作流", no_args_is_help=True)
usecase_app = typer.Typer(help="PM 一级 use case registry", no_args_is_help=True)
sync_app = typer.Typer(help="数据源同步状态与历史", no_args_is_help=True)


@backup_app.command("create")
def backup_create(
    label: str = typer.Option("", "--label", "-l", help="备份点标签，例如 before-v16-redesign"),
    note: str = typer.Option("", "--note", help="补充说明，会写入 git tag 和 manifest"),
    skip_db: bool = typer.Option(False, "--skip-db", help="仅创建 git tag，不复制 DB 快照"),
    allow_dirty: bool = typer.Option(
        False,
        "--allow-dirty",
        help="允许工作区有未提交改动；tag 只会指向当前 HEAD",
    ),
):
    """创建一个本地 code backup point + DB snapshot。"""
    try:
        point = backup_core.create_backup_point(
            label=label,
            note=note,
            include_db_snapshot=not skip_db,
            allow_dirty=allow_dirty,
        )
    except backup_core.BackupError as exc:
        console.print(f"[red]❌ {exc}[/red]")
        raise typer.Exit(1)

    table = Table(box=box.SIMPLE_HEAVY, show_header=False)
    table.add_column("字段", style="bold cyan", width=16)
    table.add_column("值", overflow="fold")
    table.add_row("backup id", point.tag_name)
    table.add_row("workspace", "git-tagged" if point.git_repo_present else "manifest-only")
    table.add_row("branch", point.branch)
    table.add_row("commit", point.commit_hash)
    table.add_row("created_at", point.created_at)
    table.add_row("manifest", point.manifest_path)
    table.add_row("db_snapshot", point.db_snapshot_path or "(skipped)")
    if point.label:
        table.add_row("label", point.label)
    if point.note:
        table.add_row("note", point.note)
    console.print(table)

    if point.dirty_worktree:
        console.print(
            "\n[yellow]⚠ 工作区在备份时有未提交改动；git tag 仅标记当前 HEAD，"
            "未提交文件列表已写入 manifest。[/yellow]"
        )
        for line in point.status_lines:
            console.print(f"  [yellow]{line}[/yellow]")
    elif not point.git_repo_present:
        console.print(
            "\n[yellow]⚠ 当前工作区不是 git 仓库；本次备份只创建 manifest 和 DB 快照，"
            "不会创建 git tag。[/yellow]"
        )

    console.print("\n[bold green]✅ 备份点已创建。[/bold green]")


@backup_app.command("list")
def backup_list(
    limit: int = typer.Option(10, "--limit", min=1, max=50, help="显示最近 N 个备份点"),
):
    """查看最近的 backup/tag 记录。"""
    points = backup_core.list_backup_points(limit=limit)
    if not points:
        console.print("[yellow]暂无 backup manifest 记录。[/yellow]")
        return

    table = Table(box=box.SIMPLE_HEAVY, header_style="bold")
    table.add_column("时间", width=20)
    table.add_column("Tag", style="cyan", width=28)
    table.add_column("Commit", width=10)
    table.add_column("DB快照", width=6)
    table.add_column("Dirty", width=6)
    table.add_column("Label/Note", overflow="fold")

    for point in points:
        label_or_note = point.get("label") or point.get("note") or "-"
        table.add_row(
            str(point.get("created_at", ""))[:19],
            str(point.get("tag_name", "")),
            str(point.get("commit_hash", ""))[:8],
            "yes" if point.get("db_snapshot_path") else "no",
            "yes" if point.get("dirty_worktree") else "no",
            label_or_note,
        )

    console.print(table)


@usecase_app.command("list")
def usecase_list(
    business_only: bool = typer.Option(False, "--business-only", help="只显示 business use cases"),
    include_draft: bool = typer.Option(False, "--all-status", help="显示 draft/retired use cases"),
):
    """列出当前显式建模的 PM use cases。"""
    status = None if include_draft else "active"
    use_case_type = "business" if business_only else None
    rows = repository.get_use_cases(status=status, use_case_type=use_case_type)
    if not rows:
        console.print("[yellow]暂无 use case 定义。[/yellow]")
        return

    table = Table(box=box.SIMPLE_HEAVY, header_style="bold")
    table.add_column("ID", style="cyan", width=24)
    table.add_column("Name", width=24)
    table.add_column("Type", width=10)
    table.add_column("Decision", width=12)
    table.add_column("Pri", width=5, justify="right")
    table.add_column("Status", width=10)
    table.add_column("Sources", overflow="fold")

    for row in rows:
        sources = ", ".join(row.get("source_systems", [])[:3])
        if len(row.get("source_systems", [])) > 3:
            sources += " ..."
        table.add_row(
            row["id"],
            row["name"],
            row["use_case_type"],
            row["decision_type"],
            str(row["priority"]),
            row["status"],
            sources or "-",
        )
    console.print(table)


@usecase_app.command("show")
def usecase_show(use_case_id: str = typer.Argument(..., help="Use case ID")):
    """查看某个 use case 的问题定义、依赖数据源和输出。"""
    row = repository.get_use_case(use_case_id)
    if not row:
        console.print(f"[red]未找到 use case: {use_case_id}[/red]")
        raise typer.Exit(1)

    lines = [
        f"[bold]Name:[/bold] {row['name']}",
        f"[bold]Type:[/bold] {row['use_case_type']}",
        f"[bold]Decision:[/bold] {row['decision_type']}",
        f"[bold]Priority:[/bold] {row['priority']}",
        f"[bold]Status:[/bold] {row['status']}",
        f"[bold]Owner:[/bold] {row.get('owner') or '-'}",
        "",
        f"[bold]Problem:[/bold] {row.get('problem_statement') or '-'}",
        "",
        f"[bold]Sources:[/bold] {', '.join(row.get('source_systems', [])) or '-'}",
        f"[bold]Core tables:[/bold] {', '.join(row.get('core_tables', [])) or '-'}",
        f"[bold]Outputs:[/bold] {', '.join(row.get('outputs', [])) or '-'}",
    ]
    if row.get("notes"):
        lines.extend(["", f"[bold]Notes:[/bold] {row['notes']}"])
    console.print(
        Panel(
            "\n".join(lines),
            title=f"[bold cyan]Use Case: {row['id']}[/bold cyan]",
            border_style="cyan",
        )
    )


@sync_app.command("status")
def sync_status(
    include_inactive: bool = typer.Option(False, "--all", help="显示 inactive sources"),
):
    """查看所有数据源的 freshness 状态。"""
    rows = repository.get_data_source_freshness(active_only=not include_inactive)
    if not rows:
        console.print("[yellow]暂无 data source 定义。[/yellow]")
        return

    state_colors = {
        "fresh": "green",
        "running": "cyan",
        "partial": "yellow",
        "stale": "yellow",
        "failed": "red",
        "never_synced": "red",
        "inactive": "dim",
    }

    table = Table(box=box.SIMPLE_HEAVY, header_style="bold")
    table.add_column("Source ID", style="cyan", width=26)
    table.add_column("Type", width=10)
    table.add_column("Freshness", width=13)
    table.add_column("Last Run", width=19)
    table.add_column("Age", width=7, justify="right")
    table.add_column("SLA(h)", width=7, justify="right")
    table.add_column("Changed", width=8, justify="right")
    table.add_column("Name / Notes", overflow="fold")

    stale_count = 0
    for row in rows:
        freshness = row["freshness_state"]
        color = state_colors.get(freshness, "white")
        stale_count += 1 if row.get("is_stale") else 0
        last_run = row.get("latest_finished_at") or row.get("latest_started_at") or "-"
        latest_note = row.get("latest_notes") or row.get("notes") or row.get("source_name") or "-"
        table.add_row(
            row["id"],
            row["source_type"],
            f"[{color}]{freshness}[/{color}]",
            str(last_run)[:19],
            format_age_hours(row.get("age_hours")),
            str(row.get("refresh_sla_hours", "")),
            str(row.get("latest_rows_changed", 0)),
            latest_note,
        )

    console.print(table)
    console.print(f"\n[dim]Active stale sources: {stale_count}[/dim]")


@sync_app.command("history")
def sync_history(
    source_id: Optional[str] = typer.Option(None, "--source", "-s", help="只看某个 source"),
    limit: int = typer.Option(20, "--limit", "-n", min=1, max=100),
):
    """查看最近的 sync/import 运行记录。"""
    rows = repository.get_sync_runs(source_id=source_id, limit=limit)
    if not rows:
        console.print("[yellow]暂无 sync run 历史。[/yellow]")
        return

    state_colors = {
        "success": "green",
        "partial": "yellow",
        "failed": "red",
        "running": "cyan",
    }

    table = Table(box=box.SIMPLE_HEAVY, header_style="bold")
    table.add_column("Started", width=19)
    table.add_column("Source", style="cyan", width=26)
    table.add_column("Status", width=10)
    table.add_column("Type", width=12)
    table.add_column("Rows In", width=8, justify="right")
    table.add_column("Changed", width=8, justify="right")
    table.add_column("Notes / Error", overflow="fold")

    for row in rows:
        status = row.get("status") or "-"
        color = state_colors.get(status, "white")
        detail = row.get("error_message") or row.get("notes") or "-"
        table.add_row(
            str(row.get("started_at", ""))[:19],
            row.get("source_id", "-"),
            f"[{color}]{status}[/{color}]",
            row.get("run_type", "-"),
            str(row.get("rows_in", 0)),
            str(row.get("rows_changed", 0)),
            detail,
        )
    console.print(table)
