from __future__ import annotations

from typer.testing import CliRunner
from typer.main import get_command

from pm_agent import __version__
from pm_agent.cli import app as app_module
from pm_agent.cli.commands import governance, integrations, operations
from pm_agent.cli.commands import project_health_config
from pm_agent.database.bootstrap import main as init_db


def test_root_cli_builds() -> None:
    get_command(app_module.app)


def test_version_command_reports_candidate_version() -> None:
    result = CliRunner().invoke(app_module.app, ["version"])

    assert result.exit_code == 0
    assert result.output.strip() == f"ai-pm-agent {__version__}"


def test_usecase_group_builds() -> None:
    get_command(governance.usecase_app)


def test_release_group_builds() -> None:
    get_command(integrations.release_app)


def test_hiref_group_builds() -> None:
    get_command(operations.hiref_app)


def test_project_health_config_group_builds() -> None:
    project_health = get_command(project_health_config.project_health_app)
    config = project_health.commands["config"]
    assert set(config.commands) == {"show", "preview", "confirm"}


def test_core_option_params_are_not_flags() -> None:
    root = get_command(app_module.app)

    capacity = root.commands["capacity"]
    capacity_params = {param.name: param for param in capacity.params}
    assert capacity_params["month"].is_flag is False
    assert capacity_params["version"].is_flag is False

    allocate = root.commands["allocate"]
    allocate_params = {param.name: param for param in allocate.params}
    assert allocate_params["project_id"].is_flag is False
    assert allocate_params["count"].is_flag is False

    release_list = get_command(integrations.release_app).commands["list"]
    release_params = {param.name: param for param in release_list.params}
    assert release_params["board"].is_flag is False
    assert release_params["project"].is_flag is False


def test_capacity_accepts_month_option_value(isolated_db) -> None:
    init_db(quiet=True)
    runner = CliRunner()

    result = runner.invoke(app_module.app, ["capacity", "--month", "aug"])

    assert result.exit_code == 0, result.output
    assert "Aug" in result.output


def test_release_list_accepts_all_flag(isolated_db) -> None:
    init_db(quiet=True)
    runner = CliRunner()

    result = runner.invoke(app_module.app, ["release", "list", "--all"])

    assert result.exit_code == 0, result.output
