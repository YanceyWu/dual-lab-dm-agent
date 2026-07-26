"""Main CLI wiring for the PM toolkit."""

from __future__ import annotations

import typer

from pm_agent import __version__
from pm_agent.cli.commands import dashboard as dashboard_commands
from pm_agent.cli.commands import governance, integrations, operations, planning, setup, staffing, tool_transport

app = typer.Typer(help="PM Toolkit — 项目管理工作台", no_args_is_help=True)

app.add_typer(operations.action_app, name="action")
app.add_typer(operations.project_app, name="project")
app.add_typer(operations.decision_app, name="decision")
app.add_typer(operations.hiref_app, name="hiref")
app.add_typer(integrations.cr_app, name="cr")
app.add_typer(integrations.release_app, name="release")
app.add_typer(governance.backup_app, name="backup")
app.add_typer(governance.usecase_app, name="usecase")
app.add_typer(governance.sync_app, name="sync")
app.add_typer(planning.planning_app, name="planning")
app.add_typer(setup.config_app, name="config")
app.add_typer(setup.connector_app, name="connector")
app.add_typer(integrations.confluence_app, name="confluence")
app.add_typer(integrations.health_app, name="health")
app.add_typer(dashboard_commands.dashboard_app, name="dashboard")
app.add_typer(tool_transport.tool_app, name="tool")
app.add_typer(staffing.staffing_app, name="staffing")


@app.command("version")
def version_command() -> None:
    """Print the installed candidate version."""
    typer.echo(f"ai-pm-agent {__version__}")


setup.register(app)
operations.register(app)


if __name__ == "__main__":
    app()
