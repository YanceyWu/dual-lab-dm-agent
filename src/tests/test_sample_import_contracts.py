from __future__ import annotations

from typer.testing import CliRunner

from pm_agent.cli.app import app


def test_portable_connector_validation_is_redacted_and_offline() -> None:
    result = CliRunner().invoke(app, ["connector", "validate", "--portable"])

    assert result.exit_code == 0
    assert "runtime_configuration: not inspected" in result.stdout
    assert "network: disabled" in result.stdout
    assert "http://" not in result.stdout
    assert "https://" not in result.stdout
    assert "/" + "Users/" not in result.stdout
