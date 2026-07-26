"""Repository bootstrap, config, and connector commands."""

from __future__ import annotations

import json
from typing import Optional

import typer
from rich import box
from rich.panel import Panel
from rich.table import Table

from pm_agent.cli.commands.common import console
from pm_agent.connectors import registry as connector_registry
from pm_agent.repo_tools import bootstrap as repo_bootstrap

config_app = typer.Typer(help="Starter repo 配置与落地检查", no_args_is_help=True)
connector_app = typer.Typer(help="外部系统 connector 管理与自检", no_args_is_help=True)


def _print_path_status_table(rows: list[repo_bootstrap.PathStatus]) -> None:
    table = Table(box=box.SIMPLE_HEAVY, header_style="bold")
    table.add_column("Item", width=18)
    table.add_column("Exists", width=8)
    table.add_column("Path", overflow="fold")
    for row in rows:
        exists = "[green]yes[/green]" if row.exists else "[yellow]no[/yellow]"
        table.add_row(row.label, exists, str(row.path))
    console.print(table)


def _print_connector_validation(result) -> None:
    lines = [
        f"[bold]Enabled:[/bold] {'yes' if result.enabled else 'no'}",
        f"[bold]Ready:[/bold] {'yes' if result.ready else 'no'}",
        f"[bold]Auth mode:[/bold] {result.auth_mode}",
    ]
    if result.details:
        lines.append("")
        for key, value in result.details.items():
            lines.append(f"[bold]{key}:[/bold] {value}")
    if result.warnings:
        lines.append("")
        lines.append("[bold yellow]Warnings[/bold yellow]")
        lines.extend(f"- {warning}" for warning in result.warnings)
    if result.errors:
        lines.append("")
        lines.append("[bold red]Errors[/bold red]")
        lines.extend(f"- {error}" for error in result.errors)
    border_style = "green" if result.ready else "red" if result.errors else "yellow"
    console.print(
        Panel(
            "\n".join(lines),
            title=f"[bold cyan]{result.display_name} connector[/bold cyan]",
            border_style=border_style,
        )
    )


def register(app: typer.Typer) -> None:
    @app.command("init")
    def init_repo(
        force_env: bool = typer.Option(False, "--force-env", help="覆盖现有 .env"),
        force_config: bool = typer.Option(False, "--force-config", help="覆盖现有 configs/*.yaml 示例文件"),
        skip_db: bool = typer.Option(False, "--skip-db", help="仅脚手架 starter repo 文件，不初始化 DB"),
    ):
        """初始化 starter repo 所需的本地文件与默认结构。"""
        try:
            result = repo_bootstrap.initialize_starter_repo(
                force_env=force_env,
                force_config=force_config,
                skip_db=skip_db,
            )
        except repo_bootstrap.StarterRepoError as exc:
            console.print(f"[red]❌ {exc}[/red]")
            raise typer.Exit(1)

        console.print(
            Panel(
                f"[bold]Created:[/bold] {len(result.created)}  ·  [bold]Reused:[/bold] {len(result.reused)}  ·  "
                f"[bold]Database:[/bold] {'initialized' if result.database_initialized else 'skipped'}",
                title="[bold cyan]Starter Repo Bootstrap[/bold cyan]",
                border_style="cyan",
            )
        )
        if result.created:
            console.print("\n[bold]New files[/bold]")
            _print_path_status_table(result.created)
        if result.reused:
            console.print("\n[bold]Reused files[/bold]")
            _print_path_status_table(result.reused)

        next_steps = [
            "1. Update `.env` with your local database path and connector credentials.",
            "2. Review `configs/company/baseline.yaml` and copy the example team/project overrides if needed.",
            "3. Run `pm config validate`, `pm connector validate`, and `pm validate` before using business workflows.",
        ]
        console.print(
            Panel(
                "\n".join(next_steps),
                title=f"[bold green]DB path: {result.database_path}[/bold green]",
                border_style="green",
            )
        )


@config_app.command("show")
def config_show(
    team: Optional[str] = typer.Option(None, "--team", help="团队 override ID 或 YAML path"),
    project_name: Optional[str] = typer.Option(None, "--project", help="项目 override ID 或 YAML path"),
):
    """显示 starter repo 配置相关文件的位置与存在状态。"""
    _print_path_status_table(repo_bootstrap.get_repo_path_statuses(team=team, project=project_name))


@config_app.command("effective")
def config_effective(
    team: Optional[str] = typer.Option(None, "--team", help="团队 override ID 或 YAML path"),
    project_name: Optional[str] = typer.Option(None, "--project", help="项目 override ID 或 YAML path"),
):
    """显示合并后的 effective config（默认隐藏 secrets）。"""
    try:
        result = repo_bootstrap.build_effective_config(team=team, project=project_name)
    except repo_bootstrap.StarterRepoError as exc:
        console.print(f"[red]❌ {exc}[/red]")
        raise typer.Exit(1)

    console.print("[bold]Config sources[/bold]")
    _print_path_status_table(result.sources)
    console.print(
        Panel(
            json.dumps(repo_bootstrap.mask_secrets(result.config), ensure_ascii=False, indent=2),
            title="[bold cyan]Effective Config[/bold cyan]",
            border_style="cyan",
        )
    )


@config_app.command("validate")
def config_validate(
    team: Optional[str] = typer.Option(None, "--team", help="团队 override ID 或 YAML path"),
    project_name: Optional[str] = typer.Option(None, "--project", help="项目 override ID 或 YAML path"),
):
    """检查 starter repo 配置层是否可复用、可落地。"""
    result = repo_bootstrap.validate_config(team=team, project=project_name)
    _print_path_status_table(result.checked_paths)

    for warning in result.warnings:
        console.print(f"[yellow]⚠ {warning}[/yellow]")
    for error in result.errors:
        console.print(f"[red]❌ {error}[/red]")

    if result.errors:
        raise typer.Exit(1)
    console.print("[bold green]✅ Starter repo config validation passed.[/bold green]")


@connector_app.command("list")
def connector_list():
    """列出当前 starter repo 支持的 connectors。"""
    rows = connector_registry.get_connector_status_rows()
    table = Table(box=box.SIMPLE_HEAVY, header_style="bold")
    table.add_column("Name", width=14)
    table.add_column("Sources", width=8)
    table.add_column("Ready", width=12)
    table.add_column("Auth", width=20)
    table.add_column("Freshness", width=16)
    table.add_column("Active sources", justify="right", width=14)
    for row in rows:
        table.add_row(
            row.display_name,
            "yes" if row.enabled else "no",
            "not probed" if row.ready is None else ("yes" if row.ready else "no"),
            row.auth_mode,
            row.freshness_summary,
            str(row.active_sources),
        )
    console.print(table)


@connector_app.command("validate")
def connector_validate(
    name: Optional[str] = typer.Argument(None, help="connector name: jira|confluence|servicenow"),
    portable: bool = typer.Option(
        False,
        "--portable",
        help="仅检查可移植 connector contract；不读取或显示运行时配置",
    ),
):
    """检查 connector 配置、认证和运行时 readiness。"""
    try:
        results = (
            connector_registry.validate_portable_contracts(name=name)
            if portable
            else connector_registry.validate_connectors(name=name)
        )
    except ValueError as exc:
        console.print(f"[red]❌ {exc}[/red]")
        raise typer.Exit(1)

    has_errors = False
    for result in results:
        _print_connector_validation(result)
        has_errors = has_errors or bool(result.errors)
    if has_errors:
        raise typer.Exit(1)


@connector_app.command("status")
def connector_status():
    """离线查看本地 connector source 和 sync freshness 概况。"""
    rows = connector_registry.get_connector_status_rows()
    table = Table(box=box.SIMPLE_HEAVY, header_style="bold")
    table.add_column("Connector", width=14)
    table.add_column("Sources", width=8)
    table.add_column("Ready", width=12)
    table.add_column("Auth", width=18)
    table.add_column("Freshness", width=16)
    table.add_column("Stale", justify="right", width=7)
    table.add_column("Last run", width=20)
    for row in rows:
        table.add_row(
            row.display_name,
            "yes" if row.enabled else "no",
            "not probed" if row.ready is None else ("yes" if row.ready else "no"),
            row.auth_mode,
            row.freshness_summary,
            str(row.stale_sources),
            row.latest_run_at,
        )
    console.print(table)


@connector_app.command("probe")
def connector_probe(
    name: str = typer.Argument(
        ...,
        help="connector name: jira|confluence|servicenow",
    ),
):
    """显式执行运行时连接检查；OAuth token 可自动刷新但不会被显示。"""
    try:
        results = connector_registry.probe_connectors(name=name)
    except ValueError as exc:
        console.print(
            json.dumps(
                {"status": "invalid", "error_code": "UNKNOWN_CONNECTOR"},
                sort_keys=True,
            )
        )
        raise typer.Exit(1) from exc
    payload = {
        "status": (
            "success"
            if all(result.ready for result in results)
            else "unavailable"
        ),
        "probes": [
            {
                "connector": result.name,
                "display_name": result.display_name,
                "enabled": result.enabled,
                "ready": result.ready,
                "auth_mode": result.auth_mode,
                "runtime_probe_requested": True,
                "token_refreshed": result.token_refreshed,
                "warning_codes": result.warning_codes,
                "error_codes": result.error_codes,
            }
            for result in results
        ],
    }
    console.print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    if payload["status"] != "success":
        raise typer.Exit(1)
