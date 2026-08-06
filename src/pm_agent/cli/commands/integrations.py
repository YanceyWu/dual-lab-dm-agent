"""Integration-related Typer command groups."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from pm_agent.config import settings
from pm_agent.database import repository

cr_app = typer.Typer(help="Change Request 追踪 (ServiceNow)", no_args_is_help=True)
release_app = typer.Typer(help="JIRA Release Version 进度追踪", no_args_is_help=True)
health_app = typer.Typer(help="Project health scoring (JIRA sprint + burndown + defects)")
confluence_app = typer.Typer(help="Confluence status sync and cross-reference")

console = Console()

STATE_COLORS = {
    "new": "cyan",
    "assess": "blue",
    "authorize": "yellow",
    "scheduled": "yellow",
    "implement": "green",
    "review": "magenta",
    "closed": "dim",
    "cancelled": "dim",
}


def _progress_bar(pct: float, width: int = 20) -> str:
    filled = int(pct / 100 * width)
    bar = "█" * filled + "░" * (width - filled)
    color = "green" if pct >= 80 else "yellow" if pct >= 40 else "red"
    return f"[{color}]{bar}[/{color}] {pct:.0f}%"


@cr_app.command("list")
def cr_list(
    state: Optional[str] = typer.Option(None, "--state", "-s", help="Filter by state (partial match)"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Filter by project code"),
    limit: int = typer.Option(30, "--limit", "-n", help="Max rows to show"),
    open_only: bool = typer.Option(False, "--open", help="Show only non-closed CRs"),
):
    """列出 Change Requests"""
    import sqlite3

    db_path = Path(settings.database_path)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row

    conditions = []
    params: list = []

    if state:
        conditions.append("LOWER(state) LIKE ?")
        params.append(f"%{state.lower()}%")
    if project:
        conditions.append("(project_code LIKE ? OR assignment_group LIKE ?)")
        params.extend([f"%{project}%", f"%{project}%"])
    if open_only:
        conditions.append("LOWER(state) NOT IN ('closed','cancelled')")

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    rows = con.execute(
        f"SELECT * FROM change_requests {where} ORDER BY planned_start DESC, id DESC LIMIT ?",
        params + [limit],
    ).fetchall()
    con.close()

    if not rows:
        console.print(
            "[dim]没有符合条件的 CR 记录。请先通过 `pm onboarding` 导入 ServiceNow change request CSV。[/dim]"
        )
        return

    table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold", title=f"Change Requests ({len(rows)} 条)")
    table.add_column("CR#", width=14)
    table.add_column("状态", width=12)
    table.add_column("优先级", width=8)
    table.add_column("类型", width=10)
    table.add_column("摘要", width=42)
    table.add_column("计划开始", width=12)
    table.add_column("负责组", style="dim", width=22)

    for row in rows:
        state_str = (row["state"] or "-").lower()
        color = STATE_COLORS.get(state_str, "white")
        table.add_row(
            row["id"],
            f"[{color}]{row['state'] or '-'}[/{color}]",
            row["priority"] or "-",
            row["category"] or "-",
            (row["short_desc"] or "")[:40],
            row["planned_start"] or "-",
            (row["assignment_group"] or "-")[:20],
        )
    console.print(table)


@cr_app.command("summary")
def cr_summary():
    """CR 统计汇总：按状态 / 优先级 / 月份分布"""
    import sqlite3

    db_path = Path(settings.database_path)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row

    total = con.execute("SELECT COUNT(*) FROM change_requests").fetchone()[0]
    if not total:
        console.print("[dim]暂无 CR 数据，请先导入。[/dim]")
        con.close()
        return

    console.print()
    console.print(Panel(f"共 [bold]{total}[/bold] 条 Change Request", title="[bold cyan]📋 CR 汇总[/bold cyan]", border_style="cyan"))

    table_by_state = Table(box=box.SIMPLE_HEAVY, title="按状态分布", header_style="bold")
    table_by_state.add_column("状态", width=15)
    table_by_state.add_column("数量", width=8)
    table_by_state.add_column("占比", width=10)
    table_by_state.add_column("", width=30)
    for row in con.execute("SELECT COALESCE(state,'Unknown') as state, COUNT(*) as cnt FROM change_requests GROUP BY state ORDER BY cnt DESC"):
        color = STATE_COLORS.get((row["state"] or "").lower(), "white")
        pct = row["cnt"] / total
        bar = "█" * int(pct * 25)
        table_by_state.add_row(f"[{color}]{row['state']}[/{color}]", str(row["cnt"]), f"{pct:.0%}", f"[{color}]{bar}[/{color}]")
    console.print(table_by_state)

    table_by_priority = Table(box=box.SIMPLE_HEAVY, title="按优先级分布", header_style="bold")
    table_by_priority.add_column("优先级", width=18)
    table_by_priority.add_column("数量", width=8)
    for row in con.execute("SELECT COALESCE(priority,'Unknown') as priority, COUNT(*) as cnt FROM change_requests GROUP BY priority ORDER BY priority"):
        table_by_priority.add_row(row["priority"], str(row["cnt"]))
    console.print(table_by_priority)

    open_monthly = con.execute(
        """
        SELECT SUBSTR(planned_start,1,7) as month, COUNT(*) as cnt
        FROM change_requests
        WHERE LOWER(state) NOT IN ('closed','cancelled')
          AND planned_start != '' AND planned_start IS NOT NULL
        GROUP BY month ORDER BY month
        """
    ).fetchall()
    if open_monthly:
        table_by_month = Table(box=box.SIMPLE_HEAVY, title="未完结 CR 计划月份分布", header_style="bold")
        table_by_month.add_column("月份", width=10)
        table_by_month.add_column("数量", width=8)
        table_by_month.add_column("", width=20)
        for row in open_monthly:
            bar = "█" * min(row["cnt"], 20)
            table_by_month.add_row(row["month"], str(row["cnt"]), bar)
        console.print(table_by_month)

    con.close()


@cr_app.command("show")
def cr_show(cr_id: str = typer.Argument(..., help="CR number e.g. CHG0012345")):
    """查看单条 CR 详情"""
    import sqlite3

    db_path = Path(settings.database_path)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    row = con.execute("SELECT * FROM change_requests WHERE id=?", [cr_id]).fetchone()
    con.close()

    if not row:
        console.print(f"[red]CR '{cr_id}' 不存在[/red]")
        raise typer.Exit(1)

    state_str = (row["state"] or "-").lower()
    color = STATE_COLORS.get(state_str, "white")
    lines = [
        f"[bold]编号:[/bold]         {row['id']}",
        f"[bold]状态:[/bold]         [{color}]{row['state'] or '-'}[/{color}]",
        f"[bold]优先级:[/bold]       {row['priority'] or '-'}",
        f"[bold]类型:[/bold]         {row['category'] or '-'}",
        f"[bold]摘要:[/bold]         {row['short_desc'] or '-'}",
        f"[bold]负责人:[/bold]       {row['assigned_to'] or '-'}",
        f"[bold]负责组:[/bold]       {row['assignment_group'] or '-'}",
        f"[bold]申请人:[/bold]       {row['requested_by'] or '-'}",
        f"[bold]项目:[/bold]         {row['project_code'] or '-'}",
        f"[bold]计划开始:[/bold]     {row['planned_start'] or '-'}",
        f"[bold]计划结束:[/bold]     {row['planned_end'] or '-'}",
        f"[bold]实际开始:[/bold]     {row['actual_start'] or '-'}",
        f"[bold]实际结束:[/bold]     {row['actual_end'] or '-'}",
        f"[bold]创建时间:[/bold]     {row['created_on'] or '-'}",
        f"[bold]关闭代码:[/bold]     {row['close_code'] or '-'}",
        f"[bold]关闭备注:[/bold]     {row['close_notes'] or '-'}",
        f"[bold]最后导入:[/bold]     {row['imported_at'] or '-'}",
    ]
    console.print(Panel("\n".join(lines), title=f"[bold cyan]CR 详情: {cr_id}[/bold cyan]", border_style="cyan"))


@release_app.command("setup")
def release_setup(
    base_url: str = typer.Option(..., "--url", help="JIRA base URL from your local environment"),
    email: str = typer.Option(..., "--email", help="Your JIRA email"),
    token: str = typer.Option(..., "--token", help="JIRA Personal Access Token"),
):
    """配置 JIRA 连接信息（写入 .env 文件）"""
    env_path = Path(settings.database_path).parent.parent / ".env"
    existing = env_path.read_text() if env_path.exists() else ""

    def set_env_var(content: str, key: str, value: str) -> str:
        import re

        if re.search(rf"^{key}=", content, re.MULTILINE):
            return re.sub(rf"^{key}=.*", f"{key}={value}", content, flags=re.MULTILINE)
        return content + f"\n{key}={value}"

    content = set_env_var(existing, "JIRA_BASE_URL", base_url.rstrip("/"))
    content = set_env_var(content, "JIRA_USER_EMAIL", email)
    content = set_env_var(content, "JIRA_API_TOKEN", token)
    env_path.write_text(content.strip() + "\n")
    console.print(f"[green]✅ JIRA 配置已保存至 {env_path}[/green]")


@release_app.command("add-project")
def release_add_project(
    jira_key: str = typer.Argument(..., help="JIRA project key, for example ATL"),
):
    """注册一个 JIRA 项目 Key 用于 release 同步"""
    import sqlite3

    con = sqlite3.connect(settings.database_path)
    con.execute(
        """
        INSERT OR IGNORE INTO memory_facts (category, subject, fact, confidence, source)
        VALUES ('jira_project_key', ?, 'JIRA project key registered for release sync', 1.0, 'user')
        """,
        [jira_key.upper()],
    )
    con.commit()
    con.close()
    console.print(f"[green]✅ 已注册 JIRA 项目：{jira_key.upper()}[/green]")
    console.print("[dim]提示：可用 `pm release add-board` 为该项目配置 board JQL 以获得精确的进度统计[/dim]")
    console.print("[dim]运行 `pm release sync` 开始同步[/dim]")


@release_app.command("add-board")
def release_add_board(
    board_id: str = typer.Argument(..., help="Board 唯一 slug，如 atlas-board"),
    name: str = typer.Option(..., "--name", "-n", help="显示名称，如 'Atlas Board'"),
    project_key: str = typer.Option(..., "--project", "-p", help="JIRA 项目 Key，如 ATL"),
    base_jql: str = typer.Option(..., "--jql", "-j", help="Board 的过滤 JQL（定义 scope）"),
    version_pattern: str = typer.Option("", "--version-pattern", "-v", help="Release version LIKE 过滤，如 '%%ATLAS%%'"),
    board_url: str = typer.Option("", "--url", help="Board 的浏览器 URL（可选）"),
    pm_project: str = typer.Option("", "--pm-project", help="关联的 pm.db project id（可选）"),
):
    """注册一个 JIRA Board/Stream 配置

    每个 stream 独立追踪自己的 release versions：
    - base_jql 定义该 stream 的 issue scope
    - version_pattern 过滤属于该 stream 的 release versions（LIKE 语法，% 为通配符）

    示例:
      pm release add-board atlas-board \\
        --name "Atlas Board" --project ATL \\
        --jql 'project = ATL AND labels = atlas-delivery' \\
        --version-pattern '%ATLAS%'
    """
    import sqlite3
    from pm_agent.database.bootstrap import main as init_db

    init_db()

    version_pattern_value = version_pattern if version_pattern else None
    con = sqlite3.connect(settings.database_path)
    con.execute(
        """
        INSERT INTO jira_board_configs
            (id, name, project_key, base_jql, version_name_pattern, board_url, pm_project_id, active)
        VALUES (?, ?, ?, ?, ?, ?, NULLIF(?, ''), 1)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            project_key=excluded.project_key,
            base_jql=excluded.base_jql,
            version_name_pattern=excluded.version_name_pattern,
            board_url=excluded.board_url,
            pm_project_id=excluded.pm_project_id,
            updated_at=datetime('now')
        """,
        [board_id, name, project_key.upper(), base_jql, version_pattern_value, board_url, pm_project],
    )
    con.execute(
        """
        INSERT OR IGNORE INTO memory_facts (category, subject, fact, confidence, source)
        VALUES ('jira_project_key', ?, 'JIRA project key registered for release sync', 1.0, 'user')
        """,
        [project_key.upper()],
    )
    con.commit()
    con.close()

    repository.upsert_data_source(
        {
            "id": f"jira-release-{board_id}",
            "source_type": "jira",
            "source_name": f"JIRA Release Sync — {name}",
            "ingestion_mode": "api",
            "refresh_sla_hours": 24,
            "active": True,
            "config": {
                "board_id": board_id,
                "project_key": project_key.upper(),
                "version_name_pattern": version_pattern_value or "",
                "board_url": board_url,
                "pm_project_id": pm_project,
            },
            "notes": "Per-board JIRA release/version sync.",
        }
    )
    repository.upsert_data_source(
        {
            "id": f"jira-health-{board_id}",
            "source_type": "jira",
            "source_name": f"JIRA Health Sync — {name}",
            "ingestion_mode": "api",
            "refresh_sla_hours": 24,
            "active": True,
            "config": {
                "board_id": board_id,
                "project_key": project_key.upper(),
                "version_name_pattern": version_pattern_value or "",
                "board_url": board_url,
                "pm_project_id": pm_project,
            },
            "notes": "Per-board JIRA sprint/health sync.",
        }
    )

    console.print(f"[green]✅ Board 已注册：{name} ({board_id})[/green]")
    console.print(f"  项目:            [cyan]{project_key.upper()}[/cyan]")
    console.print(f"  JQL:             [dim]{base_jql}[/dim]")
    console.print(f"  Version 过滤:    [dim]{version_pattern_value or '(未设置，不追踪 release versions)'}[/dim]")
    console.print(f"\n[dim]运行 `pm release sync --board {board_id}` 同步进度[/dim]")


@release_app.command("list-boards")
def release_list_boards():
    """查看已注册的 JIRA Board/Stream 配置"""
    import sqlite3

    con = sqlite3.connect(settings.database_path)
    rows = con.execute(
        """
        SELECT id, name, project_key, base_jql, version_name_pattern, board_url, active
        FROM jira_board_configs ORDER BY project_key, name
        """
    ).fetchall()
    con.close()

    if not rows:
        console.print("[yellow]未配置任何 Board。[/yellow]")
        console.print("[dim]使用 `pm release add-board` 注册[/dim]")
        return

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("ID", style="dim")
    table.add_column("Stream 名称")
    table.add_column("项目")
    table.add_column("Version 过滤")
    table.add_column("Board JQL", max_width=55)
    table.add_column("状态")
    for row in rows:
        board_id, board_name, project_key, base_jql, version_name_pattern, board_url, active = row
        table.add_row(board_id, board_name, project_key, version_name_pattern or "-", base_jql, "✅" if active else "⏸")
    console.print(table)


@release_app.command("sync")
def release_sync(
    board: str = typer.Option("", "--board", "-b", help="只同步指定 board slug，如 atlas-board"),
    project: str = typer.Option("", "--project", "-p", help="只同步指定项目 Key 下的所有 boards"),
    dry_run: bool = typer.Option(False, "--dry-run"),
):
    """从 JIRA 同步各 stream 的 Release Version 进度（按 board JQL 独立统计）"""
    from pm_agent.connectors import jira as jira_connector

    jira_connector.sync_releases(board=board, project=project, dry_run=dry_run)


@release_app.command("list")
def release_list(
    board: str = typer.Option("", "--board", "-b", help="筛选 board/stream"),
    project: str = typer.Option("", "--project", "-p", help="筛选项目 Key"),
    show_all: bool = typer.Option(False, "--all", help="显示已发布与未发布版本"),
    limit: int = typer.Option(50, "--limit", "-n"),
):
    """列出各 stream 的 Release Versions 及进度（SP 优先）"""
    import sqlite3

    con = sqlite3.connect(settings.database_path)
    con.row_factory = sqlite3.Row

    total = con.execute("SELECT COUNT(*) FROM jira_stream_versions").fetchone()[0]
    if not total:
        console.print("[dim]暂无 Release 数据。先运行：[/dim]")
        console.print("  [cyan]pm release sync[/cyan]")
        con.close()
        return

    conditions = []
    params: list = []
    if board:
        conditions.append("sv.board_id = ?")
        params.append(board)
    if project:
        conditions.append("sv.project_key = ?")
        params.append(project.upper())
    if not show_all:
        conditions.append("sv.released = 0")

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    rows = con.execute(
        f"""
        SELECT sv.*, bc.name as stream_name
        FROM jira_stream_versions sv
        JOIN jira_board_configs bc ON sv.board_id = bc.id
        {where}
        ORDER BY sv.release_date ASC, sv.name ASC
        LIMIT ?
        """,
        params + [limit],
    ).fetchall()
    con.close()

    if not rows:
        console.print("[dim]没有符合条件的 Release Version。[/dim]")
        return

    table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold", title=f"Release Versions ({len(rows)} 条)")
    table.add_column("Stream", width=14)
    table.add_column("版本名称", width=32)
    table.add_column("SP 进度", width=28)
    table.add_column("Done SP / Total SP", width=16)
    table.add_column("#Done/#Total", width=10)
    table.add_column("发布日期", width=12)

    for row in rows:
        total_sp = row["total_sp"] or 0.0
        done_sp = row["done_sp"] or 0.0
        in_progress_sp = row["inprogress_sp"] or 0.0
        story_point_progress = row["sp_progress_pct"] or 0.0
        count_progress = row["progress_pct"] or 0.0
        done_issues = row["done_issues"] or 0
        total_issues = row["total_issues"] or 0

        if total_sp > 0:
            bar = _progress_bar(story_point_progress)
            sp_str = f"{done_sp:.0f} / {total_sp:.0f}"
            if in_progress_sp > 0:
                sp_str += f" (+{in_progress_sp:.0f} IP)"
        else:
            bar = _progress_bar(count_progress)
            sp_str = "[dim]no SP data[/dim]"

        table.add_row(
            row["stream_name"],
            row["name"],
            bar,
            sp_str,
            f"{done_issues}/{total_issues}",
            row["release_date"] or "-",
        )
    console.print(table)


@release_app.command("show")
def release_show(
    project: str = typer.Argument(..., help="JIRA project key, for example ATL"),
    version: str = typer.Argument(..., help="Version name (partial match ok)"),
):
    """查看某个 Release Version 的详细进度（基于当前 stream model）"""
    import sqlite3

    con = sqlite3.connect(settings.database_path)
    con.row_factory = sqlite3.Row

    rows = con.execute(
        """
        SELECT
            sv.*,
            bc.name AS stream_name
        FROM jira_stream_versions sv
        JOIN jira_board_configs bc ON sv.board_id = bc.id
        WHERE sv.project_key = ? AND LOWER(sv.name) LIKE ?
        ORDER BY COALESCE(sv.release_date, '') DESC, bc.name
        LIMIT 5
        """,
        [project.upper(), f"%{version.lower()}%"],
    ).fetchall()
    con.close()

    if not rows:
        console.print(f"[red]未找到 {project} 中含 '{version}' 的版本[/red]")
        raise typer.Exit(1)

    for row in rows:
        progress_pct = row["progress_pct"] or 0.0
        done_issues = row["done_issues"] or 0
        in_progress_issues = row["inprogress_issues"] or 0
        todo_issues = row["todo_issues"] or 0
        total_issues = row["total_issues"] or 0
        lines = [
            f"[bold]版本:[/bold]     {row['name']}",
            f"[bold]项目:[/bold]     {row['project_key']}",
            f"[bold]Stream:[/bold]   {row['stream_name']}",
            f"[bold]状态:[/bold]     {row['status'] or '-'}",
            f"[bold]发布日期:[/bold] {row['release_date'] or '-'}",
            f"[bold]开始日期:[/bold] {row['start_date'] or '-'}",
            "",
            f"[bold]总 Issue:[/bold] {total_issues}",
            f"  ✅ 完成:     {done_issues}",
            f"  🔄 进行中:   {in_progress_issues}",
            f"  ⬜ 待处理:   {todo_issues}",
            "",
            f"[bold]进度:[/bold]     {_progress_bar(progress_pct, 30)}",
            "",
            f"[dim]最后同步: {row['synced_at']}[/dim]",
        ]
        console.print(
            Panel(
                "\n".join(lines),
                title=f"[bold cyan]Release: {row['project_key']} / {row['stream_name']} / {row['name']}[/bold cyan]",
                border_style="cyan",
            )
        )


@health_app.callback(invoke_without_command=True)
def health_default(
    ctx: typer.Context,
    board: Optional[str] = typer.Option(None, "--board", "-b", help="Board ID, for example atlas-board"),
    history: int = typer.Option(1, "--history", "-n", help="Number of past snapshots to show"),
):
    """Show latest health snapshot for all boards (or a specific board)."""
    if ctx.invoked_subcommand:
        return

    import sqlite3

    conn = sqlite3.connect(settings.database_path)
    conn.row_factory = sqlite3.Row
    grade_map = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}

    query = """
        SELECT h.board_id, h.snapshot_date, h.sprint_name,
               h.overall_score, h.overall_grade,
               h.velocity_score, h.sprint_score, h.defect_score, h.scope_score,
               h.remaining_sp, h.done_sp, h.total_sp, h.sp_progress_pct,
               h.sprint_completion_pct,
               h.new_bugs_p1p2, h.new_bugs_p3p4, h.total_defects, h.done_stories,
               h.unestimated_count, h.unestimated_pct,
               h.scope_added_sp, h.scope_removed_sp,
               h.raw_sprint_issues, h.raw_defects, h.risks_json,
               h.version_id,
               jsv.name as version_name, jsv.release_date
        FROM jira_health_snapshots h
        LEFT JOIN jira_stream_versions jsv ON h.version_id=jsv.id AND h.board_id=jsv.board_id
        WHERE h.id IN (
            SELECT MAX(id) FROM jira_health_snapshots
            WHERE (:board IS NULL OR board_id=:board)
            GROUP BY board_id
        )
        ORDER BY h.board_id
    """
    rows = conn.execute(query, {"board": board}).fetchall()
    if not rows:
        console.print("[yellow]No health snapshots found. Run: pm health sync[/yellow]")
        return

    console.print(f"\n[bold]📊 Project Health Report[/bold] — {rows[0]['snapshot_date']}\n")

    table = Table(title="Health Summary", box=box.ROUNDED, show_lines=True)
    table.add_column("Board", style="bold cyan", width=14)
    table.add_column("Release", width=22)
    table.add_column("Rel. Date", width=12)
    table.add_column("Sprint", width=22)
    table.add_column("Overall", justify="center", width=10)
    table.add_column("Burndown\n(35%)", justify="right", width=10)
    table.add_column("Sprint\n(25%)", justify="right", width=9)
    table.add_column("Defects\n(25%)", justify="right", width=9)
    table.add_column("Scope\n(15%)", justify="right", width=8)

    for row in rows:
        grade = grade_map.get(row["overall_grade"], row["overall_grade"])
        table.add_row(
            row["board_id"],
            row["version_name"] or "-",
            row["release_date"] or "-",
            (row["sprint_name"] or "-")[:22],
            f"{grade} {row['overall_score']}",
            f"{row['velocity_score']:.1f}",
            f"{row['sprint_score']:.1f}",
            f"{row['defect_score']:.1f}",
            f"{row['scope_score']:.1f}",
        )
    console.print(table)

    for row in rows:
        grade = grade_map.get(row["overall_grade"], row["overall_grade"])
        risks = []
        try:
            risks = json.loads(row["risks_json"] or "[]")
        except Exception:
            pass

        lines = [
            f"[bold]Overall : {grade} {row['overall_score']}[/bold]  ({row['overall_grade']})",
            "",
            "[bold]── Burndown (35%) ──────────────────[/bold]",
            f"  SP Done     : {row['done_sp']:.0f} / {row['total_sp']:.0f}  ({row['sp_progress_pct']:.1f}%)",
            f"  Remaining   : {row['remaining_sp']:.0f} SP",
            f"  Score       : {row['velocity_score']:.1f}",
            "",
            "[bold]── Sprint Completion (25%) ─────────[/bold]",
            f"  Sprint      : {row['sprint_name'] or 'N/A'}",
            f"  Completion  : {row['sprint_completion_pct']:.1f}%",
            f"  Score       : {row['sprint_score']:.1f}",
            "",
            "[bold]── Defect Rate (25%) ───────────────[/bold]",
            f"  P1/P2 Bugs  : {row['new_bugs_p1p2']}  [red](weighted 3x)[/red]",
            f"  P3/P4 Bugs  : {row['new_bugs_p3p4']}",
            f"  Total Defects: {row['total_defects']}",
            f"  Done Stories: {row['done_stories']}",
            f"  Score       : {row['defect_score']:.1f}",
            "",
            "[bold]── Scope Stability (15%) ───────────[/bold]",
            f"  Added SP    : +{row['scope_added_sp']:.0f}",
            f"  Removed SP  : -{row['scope_removed_sp']:.0f}",
            f"  Score       : {row['scope_score']:.1f}",
            "",
            "[bold]── Estimation Coverage ─────────────[/bold]",
            f"  Unestimated : {row['unestimated_count']} issues ({row['unestimated_pct']:.0f}%)",
        ]

        if risks:
            lines.append("")
            lines.append("[bold]── Risks ───────────────────────────[/bold]")
            for risk in risks:
                lines.append(f"  ⚠ [{risk['type']}] {risk['msg']}")

        board_name = row["board_id"].upper()
        version_name = row["version_name"] or "-"
        console.print(
            Panel(
                "\n".join(lines),
                title=f"[bold]{grade} {board_name} | {version_name}[/bold]",
                border_style="green" if row["overall_grade"] == "GREEN" else ("yellow" if row["overall_grade"] == "YELLOW" else "red"),
            )
        )

    conn.close()


@health_app.command("sync")
def health_sync(
    board: Optional[str] = typer.Option(None, "--board", "-b", help="只同步指定 board slug，如 atlas-board"),
    dry_run: bool = typer.Option(False, "--dry-run"),
):
    """Run health sync (fetch JIRA sprint data and compute scores)."""
    from pm_agent.connectors import jira as jira_connector

    try:
        jira_connector.sync_health(board=board, dry_run=dry_run)
    except Exception as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)


@health_app.command("history")
def health_history(
    board: str = typer.Argument(..., help="Board ID"),
    limit: int = typer.Option(6, "--limit", "-n"),
):
    """Show health score trend over past N snapshots."""
    import sqlite3

    conn = sqlite3.connect(settings.database_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT h.snapshot_date, h.sprint_name, h.overall_score, h.overall_grade,
               h.velocity_score, h.sprint_score, h.defect_score, h.scope_score,
               h.sp_progress_pct, h.sprint_completion_pct, h.total_defects
        FROM jira_health_snapshots h
        WHERE h.board_id=?
        ORDER BY h.snapshot_date DESC LIMIT ?
        """,
        (board, limit),
    ).fetchall()

    if not rows:
        console.print(f"[yellow]No history for board '{board}'[/yellow]")
        return

    grade_map = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}
    table = Table(title=f"Health History — {board.upper()}", box=box.ROUNDED)
    table.add_column("Date", width=12)
    table.add_column("Sprint", width=24)
    table.add_column("Overall", justify="center", width=10)
    table.add_column("Burndown", justify="right", width=9)
    table.add_column("Sprint%", justify="right", width=8)
    table.add_column("Defects", justify="right", width=8)
    table.add_column("Scope", justify="right", width=7)
    table.add_column("SP%", justify="right", width=7)

    for row in rows:
        grade = grade_map.get(row["overall_grade"], "")
        table.add_row(
            row["snapshot_date"],
            (row["sprint_name"] or "-")[:24],
            f"{grade} {row['overall_score']}",
            f"{row['velocity_score']:.0f}",
            f"{row['sprint_completion_pct']:.0f}%",
            f"{row['total_defects']}",
            f"{row['scope_score']:.0f}",
            f"{row['sp_progress_pct']:.0f}%",
        )
    console.print(table)
    conn.close()


@confluence_app.command("sync")
def confluence_sync():
    """Sync all project Confluence status pages to DB (batch, parallel)."""
    from pm_agent.connectors import confluence as confluence_connector

    try:
        result = confluence_connector.sync_status_pages()
        console.print(
            f"[green]✅ Confluence 已同步：{result['pages_synced']}/{result['page_count']} 项目页，"
            f"行动项 {result['action_tracker_rows']} 行[/green]"
        )
    except Exception as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)


@confluence_app.command("actions")
def confluence_actions(
    status_filter: Optional[str] = typer.Option(
        None,
        "--status",
        "-s",
        help="Filter: todo / inprogress / done / blocked",
    ),
    assignee: Optional[str] = typer.Option(None, "--assignee", "-a", help="Filter by assignee name"),
):
    """Show the locally configured Confluence action tracker."""
    import sqlite3 as sqlite

    conn = sqlite.connect(settings.database_path)
    conn.row_factory = sqlite.Row

    query = """
        SELECT item, action_required, assignee, due_date, status, remarks, synced_date
        FROM action_tracker
        WHERE synced_date = (SELECT MAX(synced_date) FROM action_tracker)
    """
    params = []
    if status_filter:
        status_filter_lower = status_filter.lower()
        if "todo" in status_filter_lower or "to_do" in status_filter_lower:
            query += " AND LOWER(status) = 'to do'"
        elif "inprogress" in status_filter_lower or "progress" in status_filter_lower:
            query += " AND LOWER(status) = 'in progress'"
        elif "done" in status_filter_lower:
            query += " AND LOWER(status) = 'done'"
        elif "blocked" in status_filter_lower:
            query += " AND LOWER(status) = 'blocked'"
    if assignee:
        query += " AND LOWER(assignee) LIKE ?"
        params.append(f"%{assignee.lower()}%")

    query += " ORDER BY CASE status WHEN 'Blocked' THEN 1 WHEN 'To Do' THEN 2 WHEN 'In Progress' THEN 3 WHEN 'Done' THEN 4 ELSE 5 END, assignee"
    rows = conn.execute(query, params).fetchall()
    conn.close()

    if not rows:
        console.print("[yellow]No action-tracker items found.[/yellow]")
        return

    sync_date = rows[0]["synced_date"] if rows else "-"
    status_icon = {"To Do": "⬜", "In Progress": "🔵", "Done": "✅", "Blocked": "🔴"}

    table = Table(title=f"📋 Action Tracker (synced {sync_date})", box=box.ROUNDED)
    table.add_column("#", width=3, justify="right")
    table.add_column("Item", width=36)
    table.add_column("Assignee", width=18)
    table.add_column("Due", width=8)
    table.add_column("Status", width=14)
    table.add_column("Action Required", width=46)

    for index, row in enumerate(rows, 1):
        status = row["status"] or "?"
        icon = status_icon.get(status, "❓")
        color = {"To Do": "white", "In Progress": "cyan", "Done": "green", "Blocked": "red"}.get(status, "white")
        table.add_row(
            str(index),
            row["item"] or "",
            row["assignee"] or "-",
            row["due_date"] or "-",
            f"[{color}]{icon} {status}[/{color}]",
            (row["action_required"] or "-")[:46],
        )

    console.print(table)

    all_rows_query = "SELECT status, COUNT(*) as cnt FROM action_tracker WHERE synced_date = (SELECT MAX(synced_date) FROM action_tracker) GROUP BY status"
    conn2 = sqlite.connect(settings.database_path)
    counts = {row[0]: row[1] for row in conn2.execute(all_rows_query).fetchall()}
    conn2.close()
    total = sum(counts.values())
    done_count = counts.get("Done", 0)
    console.print(
        f"\nTotal: {total} | ✅ Done: {done_count} | 🔵 In Progress: {counts.get('In Progress', 0)} | "
        f"⬜ To Do: {counts.get('To Do', 0)} | 🔴 Blocked: {counts.get('Blocked', 0)} | Progress: {done_count * 100 // total if total else 0}%"
    )
    console.print("[dim]Source: locally configured Confluence action tracker[/dim]")


@confluence_app.command("status")
def confluence_status():
    """Show latest Confluence RAG status for all projects + JIRA health cross-reference."""
    import sqlite3 as sqlite

    conn = sqlite.connect(settings.database_path)
    conn.row_factory = sqlite.Row

    confluence_rows = conn.execute(
        """
        SELECT cs.board_id, cs.snapshot_date, cs.rag_status, cs.status_as_of,
               cs.owner, cs.summary_text, cs.risks_text, cs.sprint_iteration
        FROM confluence_status_snapshots cs
        WHERE cs.snapshot_date = (
            SELECT MAX(snapshot_date) FROM confluence_status_snapshots cs2
            WHERE cs2.board_id = cs.board_id
        )
        ORDER BY cs.board_id
        """
    ).fetchall()

    jira_rows = conn.execute(
        """
        SELECT h.board_id, h.overall_score, h.overall_grade, h.sp_progress_pct,
               h.sprint_completion_pct, h.total_defects
        FROM jira_health_snapshots h
        WHERE h.snapshot_date = (
            SELECT MAX(snapshot_date) FROM jira_health_snapshots h2
            WHERE h2.board_id = h.board_id
        )
        GROUP BY h.board_id
        """
    ).fetchall()
    conn.close()

    jira_map = {row["board_id"]: row for row in jira_rows}
    rag_icon = {"GREEN": "🟢", "RED": "🔴", "AMBER": "🟠"}
    grade_icon = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}

    table = Table(title="📊 Confluence × JIRA Cross-Reference", box=box.ROUNDED)
    table.add_column("Project", width=14)
    table.add_column("Conf RAG", justify="center", width=11)
    table.add_column("Updated", width=11)
    table.add_column("JIRA Score", justify="center", width=11)
    table.add_column("SP%", justify="right", width=6)
    table.add_column("Sprint%", justify="right", width=8)
    table.add_column("Bugs", justify="right", width=5)
    table.add_column("Match?", width=12)
    table.add_column("Owner", width=24)

    for row in confluence_rows:
        board_id = row["board_id"]
        jira_row = jira_map.get(board_id)
        confluence_rag = row["rag_status"]
        confluence_icon = rag_icon.get(confluence_rag, "⚪")

        if jira_row:
            jira_grade = jira_row["overall_grade"]
            jira_cell = f"{grade_icon.get(jira_grade, '')} {jira_row['overall_score']:.0f}"
            sp_pct = f"{jira_row['sp_progress_pct']:.0f}%"
            sprint_pct = f"{jira_row['sprint_completion_pct']:.0f}%"
            bugs = str(jira_row["total_defects"])
            confluence_bad = confluence_rag in ("RED", "AMBER")
            jira_bad = jira_grade in ("RED", "YELLOW")
            if confluence_bad and not jira_bad:
                match = "[yellow]⚠️ Conf worse[/yellow]"
            elif not confluence_bad and jira_bad:
                match = "[red]⚠️ JIRA worse[/red]"
            else:
                match = "[green]✅ aligned[/green]"
        else:
            jira_cell, sp_pct, sprint_pct, bugs = "[dim]—[/dim]", "-", "-", "-"
            match = "[dim]no board[/dim]"

        table.add_row(
            board_id,
            f"{confluence_icon} {confluence_rag or '?'}",
            row["snapshot_date"] or "-",
            jira_cell,
            sp_pct,
            sprint_pct,
            bugs,
            match,
            (row["owner"] or "-")[:24],
        )

    console.print(table)

    for row in confluence_rows:
        risks = (row["risks_text"] or "").strip()
        if risks and risks.upper() not in ("N/A", "NA", "-"):
            console.print(f"\n[bold yellow]⚠️  {row['board_id'].upper()} Risks:[/bold yellow]")
            for line in risks.split("\n")[:5]:
                if line.strip():
                    console.print(f"   {line.strip()}")
