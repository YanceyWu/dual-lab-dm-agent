"""Controlled Project Health configuration commands (R4 decision (a))."""

from __future__ import annotations

import json

import typer

from pm_agent.project_health.configuration import confirm, preview
from pm_agent.project_health.service import catalog_projection

project_health_app = typer.Typer(
    help="Project Health read and controlled configuration",
    no_args_is_help=True,
)
config_app = typer.Typer(
    help="Bounded health-condition configuration",
    no_args_is_help=True,
)
project_health_app.add_typer(config_app, name="config")

_TERMINAL_STATUSES = {
    "success",
    "proposed",
    "no_op",
    "confirmed",
    "idempotent",
    "expired",
    "rejected",
}


def _emit(value: dict) -> None:
    typer.echo(json.dumps(value, ensure_ascii=False, sort_keys=True))
    if value.get("status") not in _TERMINAL_STATUSES:
        raise typer.Exit(2)


def _failed(code: str) -> dict:
    return {"status": "failed", "warnings": [code]}


@config_app.command("show")
def config_show(
    project_id: str = typer.Option("", "--project", help="Exact stable project ID (optional)"),
) -> None:
    """Show the fixed catalog and the effective bounded configuration."""
    try:
        projection = catalog_projection(
            project_id=project_id or None,
        )
    except ValueError as exc:
        _emit(_failed(str(exc)))
        return
    _emit({"status": "success", **projection})


@config_app.command("preview")
def config_preview(
    tolerance_days: int = typer.Option(
        0,
        "--tolerance-days",
        min=0,
        max=90,
        help="Critical-milestone tolerance in days (0-90).",
    ),
    scope_green_minimum: int = typer.Option(
        100,
        "--scope-green-minimum",
        min=0,
        max=100,
        help="Release-scope completion percentage required for green (0-100).",
    ),
    project_id: str = typer.Option(
        "",
        "--project",
        help="Existing project ID for a bounded override (optional).",
    ),
) -> None:
    """Preview a bounded health-condition change (never writes)."""
    parameters = {
        "critical_milestone_tolerance_days": tolerance_days,
        "scope_completion_green_minimum": scope_green_minimum,
    }
    try:
        result = preview(
            parameters=parameters,
            project_id=project_id or None,
        )
    except ValueError as exc:
        _emit(_failed(str(exc)))
        return
    _emit(result)


@config_app.command("confirm")
def config_confirm(
    operation_id: str = typer.Option(..., "--operation-id"),
    token: str = typer.Option(..., "--token"),
) -> None:
    """Confirm one exact runtime-issued configuration preview."""
    try:
        result = confirm(
            operation_id=operation_id,
            confirmation_token=token,
        )
    except ValueError as exc:
        _emit(_failed(str(exc)))
        return
    _emit(result)
