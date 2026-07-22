"""Machine-readable local transport commands for Copilot and automation."""

from __future__ import annotations

import json
from typing import Optional

import typer

from pm_agent.use_cases import use_case_executor
from pm_agent.use_cases.service import UseCaseRequest
from pm_agent.use_cases.tool_transport import ToolTransport

tool_app = typer.Typer(help="Structured read-only use-case transport", no_args_is_help=True)
transport = ToolTransport(use_case_executor)


def _emit(request: UseCaseRequest) -> None:
    result = transport.handle(request)
    typer.echo(json.dumps(result.model_dump(), ensure_ascii=False, sort_keys=True))
    if result.status not in {"success", "unavailable"}:
        raise typer.Exit(2)


@tool_app.command("list")
def list_use_cases(
    actor: str = typer.Option("copilot", "--actor"),
    correlation_id: Optional[str] = typer.Option(None, "--correlation-id"),
):
    """List safe structured use cases without reading operational data."""
    _emit(UseCaseRequest(operation="list", actor=actor, requested_output="json", correlation_id=correlation_id))


@tool_app.command("describe")
def describe_use_case(
    use_case_id: str = typer.Argument(..., help="Stable use-case ID"),
    actor: str = typer.Option("copilot", "--actor"),
    correlation_id: Optional[str] = typer.Option(None, "--correlation-id"),
):
    """Describe one structured use case without reading operational data."""
    _emit(
        UseCaseRequest(
            operation="describe",
            use_case_id=use_case_id,
            actor=actor,
            requested_output="json",
            correlation_id=correlation_id,
        )
    )


@tool_app.command("query")
def query_use_case(
    use_case_id: str = typer.Argument(..., help="Stable use-case ID"),
    team: Optional[str] = typer.Option(None, "--team", help="Exact team filter"),
    project_id: Optional[str] = typer.Option(None, "--project", help="Exact project ID"),
    days: Optional[int] = typer.Option(None, "--days", help="Review window in days"),
    limit: Optional[int] = typer.Option(None, "--limit", help="Maximum returned items"),
    connector: Optional[str] = typer.Option(None, "--connector", help="Exact connector name"),
    actor: str = typer.Option("copilot", "--actor"),
    correlation_id: Optional[str] = typer.Option(None, "--correlation-id"),
):
    """Run one approved read-only use case and emit only JSON."""
    _emit(
        UseCaseRequest(
            operation="query",
            use_case_id=use_case_id,
            actor=actor,
            parameters={key: value for key, value in {"team": team, "project_id": project_id, "days": days, "limit": limit, "connector": connector}.items() if value is not None},
            requested_output="json",
            correlation_id=correlation_id,
        )
    )
