"""Project snapshot command group."""

from __future__ import annotations

from datetime import date
from typing import Optional

import typer
from rich import box
from rich.panel import Panel
from rich.table import Table

from pm_agent.cli.commands.common import console
from pm_agent.database import repository

planning_app = typer.Typer(help="项目 snapshots / PM 快照", no_args_is_help=True)

_SNAPSHOT_ARTIFACT_KINDS = {"plan", "status", "recovery", "scenario", "decision_support"}
_SNAPSHOT_HORIZONS = {"weekly", "monthly", "quarterly", "milestone", "ad_hoc"}
_SNAPSHOT_STATES = {"draft", "active", "superseded", "archived"}
_SNAPSHOT_HEALTH = {"green", "amber", "red", "unknown"}
_SNAPSHOT_GENERATION_MODES = {"user", "ai", "system"}


def _normalize_snapshot_choice(label: str, value: str, allowed: set[str]) -> str:
    normalized = (value or "").strip().lower()
    if normalized not in allowed:
        console.print(
            f"[red]{label} 不合法: {value}[/red] "
            f"[yellow](允许值: {', '.join(sorted(allowed))})[/yellow]"
        )
        raise typer.Exit(1)
    return normalized


def _apply_legacy_snapshot_type(
    legacy_type: Optional[str],
    artifact_kind: str,
    horizon: str,
    generation_mode: str,
) -> tuple[str, str, str]:
    normalized = (legacy_type or "").strip().lower()
    if not normalized:
        return artifact_kind, horizon, generation_mode

    if normalized == "weekly_plan":
        if horizon not in {"ad_hoc", "weekly"}:
            console.print("[red]--type weekly_plan 与当前 --horizon 冲突。[/red]")
            raise typer.Exit(1)
        return artifact_kind, "weekly", generation_mode
    if normalized == "milestone_plan":
        if horizon not in {"ad_hoc", "milestone"}:
            console.print("[red]--type milestone_plan 与当前 --horizon 冲突。[/red]")
            raise typer.Exit(1)
        return artifact_kind, "milestone", generation_mode
    if normalized == "recovery_plan":
        if artifact_kind not in {"plan", "recovery"}:
            console.print("[red]--type recovery_plan 与当前 --kind 冲突。[/red]")
            raise typer.Exit(1)
        return "recovery", horizon, generation_mode
    if normalized == "ai_draft":
        if generation_mode not in {"user", "ai"}:
            console.print("[red]--type ai_draft 与当前 --mode 冲突。[/red]")
            raise typer.Exit(1)
        return artifact_kind, horizon, "ai"

    console.print(f"[red]不支持的旧版 --type: {legacy_type}[/red]")
    raise typer.Exit(1)


def _default_snapshot_title(project_name: str, artifact_kind: str, horizon: str) -> str:
    parts = []
    if horizon != "ad_hoc":
        parts.append(horizon.replace("_", " ").title())
    parts.append(artifact_kind.replace("_", " ").title())
    return f"{' '.join(parts)} Snapshot — {project_name}"


def _append_snapshot_section(lines: list[str], title: str, values: list[str]) -> None:
    if not values:
        return
    lines.extend(["", f"[bold]{title}:[/bold]"])
    for idx, value in enumerate(values, 1):
        lines.append(f"  {idx}. {value}")


@planning_app.command("add")
def planning_add(
    project_id: str = typer.Option(..., "--project", "-p", help="Project ID"),
    summary: str = typer.Option(..., "--summary", help="Snapshot 摘要"),
    title: str = typer.Option("", "--title", help="显示标题"),
    snapshot_date: str = typer.Option(date.today().isoformat(), "--date", help="Snapshot date YYYY-MM-DD"),
    artifact_kind: str = typer.Option("plan", "--kind", help="plan / status / recovery / scenario / decision_support"),
    horizon: str = typer.Option("ad_hoc", "--horizon", help="weekly / monthly / quarterly / milestone / ad_hoc"),
    artifact_state: str = typer.Option("draft", "--state", "--status", help="draft / active / superseded / archived"),
    health: str = typer.Option("unknown", "--health", help="green / amber / red / unknown"),
    staffing_scenario_id: Optional[str] = typer.Option(None, "--scenario", "--version", help="可选 staffing/capacity scenario ID"),
    origin_context: str = typer.Option("", "--origin", "--use-case", help="可选来源/场景标签，例如 weekly-project-status"),
    generation_mode: str = typer.Option("user", "--mode", help="user / ai / system"),
    legacy_type: Optional[str] = typer.Option(None, "--type", help="(兼容旧版) weekly_plan / milestone_plan / recovery_plan / ai_draft"),
    priority: Optional[list[str]] = typer.Option(None, "--priority", "--item", help="Priority / 旧版 item，可重复"),
    milestone: Optional[list[str]] = typer.Option(None, "--milestone", help="Milestone，可重复"),
    action: Optional[list[str]] = typer.Option(None, "--action", help="Action，可重复"),
    decision: Optional[list[str]] = typer.Option(None, "--decision", help="Decision，可重复"),
    dependency: Optional[list[str]] = typer.Option(None, "--dependency", help="Dependency，可重复"),
    change: Optional[list[str]] = typer.Option(None, "--change", help="Change，可重复"),
    assumption: Optional[list[str]] = typer.Option(None, "--assumption", help="Assumption，可重复"),
    risk: Optional[list[str]] = typer.Option(None, "--risk", help="Risk，可重复"),
    created_by: str = typer.Option("user", "--created-by"),
):
    """手工写入一个 project snapshot。"""
    project = repository.get_project(project_id)
    if not project:
        console.print(f"[red]项目不存在: {project_id}[/red]")
        raise typer.Exit(1)

    artifact_kind = _normalize_snapshot_choice("kind", artifact_kind, _SNAPSHOT_ARTIFACT_KINDS)
    horizon = _normalize_snapshot_choice("horizon", horizon, _SNAPSHOT_HORIZONS)
    artifact_state = _normalize_snapshot_choice("state", artifact_state, _SNAPSHOT_STATES)
    health = _normalize_snapshot_choice("health", health, _SNAPSHOT_HEALTH)
    generation_mode = _normalize_snapshot_choice("mode", generation_mode, _SNAPSHOT_GENERATION_MODES)
    artifact_kind, horizon, generation_mode = _apply_legacy_snapshot_type(
        legacy_type,
        artifact_kind,
        horizon,
        generation_mode,
    )

    if staffing_scenario_id:
        valid_ids = {row["plan_version_id"] for row in repository.get_plan_versions()}
        if staffing_scenario_id not in valid_ids:
            console.print(f"[red]scenario 不存在: {staffing_scenario_id}[/red]")
            raise typer.Exit(1)

    snapshot_id = repository.create_project_snapshot(
        {
            "project_id": project_id,
            "snapshot_date": snapshot_date,
            "artifact_kind": artifact_kind,
            "horizon": horizon,
            "artifact_state": artifact_state,
            "health": health,
            "title": title or _default_snapshot_title(project["name"], artifact_kind, horizon),
            "summary": summary,
            "priorities": priority or [],
            "milestones": milestone or [],
            "actions": action or [],
            "decisions": decision or [],
            "dependencies": dependency or [],
            "changes": change or [],
            "assumptions": assumption or [],
            "risks": risk or [],
            "staffing_scenario_id": staffing_scenario_id,
            "origin_context": origin_context,
            "generation_mode": generation_mode,
            "created_by": created_by,
        }
    )
    console.print(f"[green]✅ 已创建 project snapshot: {snapshot_id}[/green]")


@planning_app.command("list")
def planning_list(
    project_id: Optional[str] = typer.Option(None, "--project", "-p"),
    artifact_kind: Optional[str] = typer.Option(None, "--kind"),
    horizon: Optional[str] = typer.Option(None, "--horizon"),
    artifact_state: Optional[str] = typer.Option(None, "--state", "--status"),
    health: Optional[str] = typer.Option(None, "--health"),
    generation_mode: Optional[str] = typer.Option(None, "--mode"),
    legacy_type: Optional[str] = typer.Option(None, "--type", help="(兼容旧版) 过滤旧版 plan_type"),
    limit: int = typer.Option(20, "--limit", "-n", min=1, max=100),
):
    """列出 project snapshots。"""
    if artifact_kind:
        artifact_kind = _normalize_snapshot_choice("kind", artifact_kind, _SNAPSHOT_ARTIFACT_KINDS)
    if horizon:
        horizon = _normalize_snapshot_choice("horizon", horizon, _SNAPSHOT_HORIZONS)
    if artifact_state:
        artifact_state = _normalize_snapshot_choice("state", artifact_state, _SNAPSHOT_STATES)
    if health:
        health = _normalize_snapshot_choice("health", health, _SNAPSHOT_HEALTH)
    if generation_mode:
        generation_mode = _normalize_snapshot_choice("mode", generation_mode, _SNAPSHOT_GENERATION_MODES)
    artifact_kind, horizon, generation_mode = (
        _apply_legacy_snapshot_type(
            legacy_type,
            artifact_kind or "plan",
            horizon or "ad_hoc",
            generation_mode or "user",
        )
        if legacy_type
        else (artifact_kind, horizon, generation_mode)
    )

    rows = repository.get_project_snapshots(
        project_id=project_id,
        artifact_kind=artifact_kind,
        horizon=horizon,
        artifact_state=artifact_state,
        health=health,
        generation_mode=generation_mode,
        limit=limit,
    )
    if not rows:
        console.print("[yellow]暂无 project snapshots。[/yellow]")
        return

    table = Table(box=box.SIMPLE_HEAVY, header_style="bold")
    table.add_column("ID", style="cyan", width=30)
    table.add_column("Project", width=24)
    table.add_column("Kind", width=12)
    table.add_column("Horizon", width=10)
    table.add_column("Health", width=8)
    table.add_column("Date", width=12)
    table.add_column("State", width=11)
    table.add_column("Origin", width=24)
    table.add_column("Summary", overflow="fold")

    for row in rows:
        table.add_row(
            row["id"],
            row.get("project_name", row["project_id"]),
            row["artifact_kind"],
            row["horizon"],
            row["health"],
            row["snapshot_date"],
            row["artifact_state"],
            row.get("origin_context") or "-",
            row.get("summary") or row.get("title") or "-",
        )
    console.print(table)


@planning_app.command("show")
def planning_show(
    snapshot_id: Optional[str] = typer.Argument(None, help="Snapshot ID"),
    project_id: Optional[str] = typer.Option(None, "--project", "-p", help="按项目看最新一条"),
):
    """查看 project snapshot 详情。"""
    row = None
    if snapshot_id:
        row = repository.get_project_snapshot(snapshot_id)
    elif project_id:
        rows = repository.get_project_snapshots(project_id=project_id, limit=1)
        row = rows[0] if rows else None
    else:
        console.print("[red]请提供 snapshot_id 或 --project。[/red]")
        raise typer.Exit(1)

    if not row:
        console.print("[red]未找到 project snapshot。[/red]")
        raise typer.Exit(1)

    lines = [
        f"[bold]Project:[/bold] {row.get('project_name', row['project_id'])}",
        f"[bold]Kind:[/bold] {row['artifact_kind']}",
        f"[bold]Horizon:[/bold] {row['horizon']}",
        f"[bold]Health:[/bold] {row['health']}",
        f"[bold]Date:[/bold] {row['snapshot_date']}",
        f"[bold]State:[/bold] {row['artifact_state']}",
        f"[bold]Scenario:[/bold] {row.get('staffing_scenario_id') or '-'}",
        f"[bold]Origin:[/bold] {row.get('origin_context') or '-'}",
        f"[bold]Generation mode:[/bold] {row.get('generation_mode') or '-'}",
        f"[bold]Created by:[/bold] {row.get('created_by') or '-'}",
        "",
        f"[bold]Summary:[/bold] {row.get('summary') or '-'}",
    ]
    _append_snapshot_section(lines, "Priorities", row.get("priorities", []))
    _append_snapshot_section(lines, "Milestones", row.get("milestones", []))
    _append_snapshot_section(lines, "Actions", row.get("actions", []))
    _append_snapshot_section(lines, "Decisions", row.get("decisions", []))
    _append_snapshot_section(lines, "Dependencies", row.get("dependencies", []))
    _append_snapshot_section(lines, "Changes", row.get("changes", []))
    _append_snapshot_section(lines, "Assumptions", row.get("assumptions", []))
    _append_snapshot_section(lines, "Risks", row.get("risks", []))

    console.print(
        Panel(
            "\n".join(lines),
            title=f"[bold cyan]Project Snapshot: {row['id']}[/bold cyan]",
            border_style="cyan",
        )
    )
