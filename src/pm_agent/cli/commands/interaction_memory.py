"""Local CLI for repo-scoped Copilot interaction memory."""

from __future__ import annotations

import json

import typer

from pm_agent.interaction_memory import (
    demo_seed,
    disable_scope,
    enable_scope,
    inspect_memory,
    interaction_memory_status,
)
from pm_agent.use_cases import use_case_executor
from pm_agent.use_cases.service import UseCaseRequest

interaction_memory_app = typer.Typer(
    help="Repo-scoped Copilot interaction memory",
    no_args_is_help=True,
)


def _emit(value: dict) -> None:
    typer.echo(json.dumps(value, ensure_ascii=False, sort_keys=True))
    if value.get("status") != "success":
        raise typer.Exit(2)


def _scope_parameters(
    *,
    project_id: str,
    repo_root: str,
) -> dict[str, str | None]:
    return {
        "project_id": project_id or None,
        "repo_root": repo_root or None,
    }


@interaction_memory_app.command("status")
def status_command(
    project_id: str = typer.Option("", "--project-id"),
    repo_root: str = typer.Option("", "--repo-root"),
) -> None:
    """Show capability state and grouped counts for the current scope."""
    _emit(
        interaction_memory_status(
            **_scope_parameters(project_id=project_id, repo_root=repo_root)
        )
    )


@interaction_memory_app.command("demo-seed")
def demo_seed_command(
    project_id: str = typer.Option("", "--project-id"),
    repo_root: str = typer.Option("", "--repo-root"),
) -> None:
    """Insert one deterministic local demo profile for manual testing."""
    _emit(
        demo_seed(**_scope_parameters(project_id=project_id, repo_root=repo_root))
    )


@interaction_memory_app.command("inspect")
def inspect_command(
    project_id: str = typer.Option("", "--project-id"),
    repo_root: str = typer.Option("", "--repo-root"),
) -> None:
    """Inspect stored interaction-memory rows for the current scope."""
    _emit(
        inspect_memory(
            **_scope_parameters(project_id=project_id, repo_root=repo_root)
        )
    )


@interaction_memory_app.command("resolve")
def resolve_command(
    message: str = typer.Option(..., "--message"),
    project_id: str = typer.Option("", "--project-id"),
    repo_root: str = typer.Option("", "--repo-root"),
) -> None:
    """Resolve one bounded working-context object for a chat turn."""
    parameters = {"message": message}
    if project_id:
        parameters["project_id"] = project_id
    if repo_root:
        parameters["repo_root"] = repo_root
    _emit(
        use_case_executor.execute(
            UseCaseRequest(
                use_case_id="interaction-memory-context",
                actor="copilot",
                requested_output="json",
                parameters=parameters,
            )
        ).model_dump(mode="json")
    )


@interaction_memory_app.command("disable")
def disable_command(
    project_id: str = typer.Option("", "--project-id"),
    repo_root: str = typer.Option("", "--repo-root"),
) -> None:
    """Disable automatic interaction-memory selection for the current scope."""
    _emit(
        disable_scope(
            **_scope_parameters(project_id=project_id, repo_root=repo_root)
        )
    )


@interaction_memory_app.command("enable")
def enable_command(
    project_id: str = typer.Option("", "--project-id"),
    repo_root: str = typer.Option("", "--repo-root"),
) -> None:
    """Re-enable automatic interaction-memory selection for the current scope."""
    _emit(
        enable_scope(
            **_scope_parameters(project_id=project_id, repo_root=repo_root)
        )
    )
