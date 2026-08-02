"""Focused tests for the controlled Project Health configuration CLI (R4 (a))."""

from __future__ import annotations

import json
import sqlite3

from typer.testing import CliRunner

from pm_agent.cli import app as app_module
from pm_agent.database.bootstrap import main as init_db

runner = CliRunner()
DEFAULTS = {
    "critical_milestone_tolerance_days": 0,
    "scope_completion_green_minimum": 100,
}


def _invoke(*args: str):
    return runner.invoke(app_module.app, list(args))


def _payload(result) -> dict:
    return json.loads(result.stdout)


def _seed_project(db_path: str) -> None:
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "INSERT INTO projects(id,name,status) VALUES ('project-config-1','Synthetic','active')"
        )


def test_config_show_reports_fixed_catalog_and_default_effective_configuration(
    isolated_db,
) -> None:
    init_db(quiet=True)
    result = _invoke("project-health", "config", "show")
    assert result.exit_code == 0, result.output
    payload = _payload(result)
    assert payload["status"] == "success"
    assert payload["catalog_version"] == "project-health-catalog-v1"
    assert len(payload["factors"]) == 9
    assert payload["effective_configuration"] == DEFAULTS
    assert payload["configuration_version_id"] == "catalog-default-v1"
    assert payload["override_state"] == "not_available"


def test_config_show_unknown_project_fails_closed(isolated_db) -> None:
    init_db(quiet=True)
    result = _invoke("project-health", "config", "show", "--project", "missing")
    assert result.exit_code == 2
    assert _payload(result)["status"] == "failed"
    assert _payload(result)["warnings"] == ["PROJECT_NOT_FOUND"]


def test_config_preview_confirm_round_trip_updates_effective_configuration(
    isolated_db,
) -> None:
    init_db(quiet=True)
    preview = _invoke(
        "project-health",
        "config",
        "preview",
        "--tolerance-days",
        "5",
        "--scope-green-minimum",
        "90",
    )
    assert preview.exit_code == 0, preview.output
    proposed = _payload(preview)
    assert proposed["status"] == "proposed"
    assert proposed["prior"] == DEFAULTS
    assert proposed["proposed"] == {
        "critical_milestone_tolerance_days": 5,
        "scope_completion_green_minimum": 90,
    }
    confirmed = _invoke(
        "project-health",
        "config",
        "confirm",
        "--operation-id",
        proposed["operation_id"],
        "--token",
        proposed["confirmation_token"],
    )
    assert confirmed.exit_code == 0, confirmed.output
    result = _payload(confirmed)
    assert result["status"] == "confirmed"
    assert result["configuration_version_id"] != "catalog-default-v1"

    shown = _payload(_invoke("project-health", "config", "show"))
    assert shown["effective_configuration"] == {
        "critical_milestone_tolerance_days": 5,
        "scope_completion_green_minimum": 90,
    }


def test_config_project_override_is_scoped_and_visible(isolated_db) -> None:
    init_db(quiet=True)
    _seed_project(isolated_db)
    preview = _payload(
        _invoke(
            "project-health",
            "config",
            "preview",
            "--project",
            "project-config-1",
            "--tolerance-days",
            "7",
        )
    )
    assert preview["status"] == "proposed"
    confirmed = _payload(
        _invoke(
            "project-health",
            "config",
            "confirm",
            "--operation-id",
            preview["operation_id"],
            "--token",
            preview["confirmation_token"],
        )
    )
    assert confirmed["status"] == "confirmed"

    override = _payload(
        _invoke(
            "project-health",
            "config",
            "show",
            "--project",
            "project-config-1",
        )
    )
    assert override["override_state"] == "available"
    assert override["effective_configuration"]["critical_milestone_tolerance_days"] == 7
    default = _payload(_invoke("project-health", "config", "show"))
    assert default["effective_configuration"] == DEFAULTS


def test_config_preview_no_op_when_unchanged(isolated_db) -> None:
    init_db(quiet=True)
    preview = _invoke(
        "project-health",
        "config",
        "preview",
        "--tolerance-days",
        "0",
        "--scope-green-minimum",
        "100",
    )
    assert preview.exit_code == 0, preview.output
    assert _payload(preview)["status"] == "no_op"


def test_config_confirm_rejects_wrong_token(isolated_db) -> None:
    init_db(quiet=True)
    proposed = _payload(
        _invoke(
            "project-health",
            "config",
            "preview",
            "--tolerance-days",
            "3",
        )
    )
    result = _invoke(
        "project-health",
        "config",
        "confirm",
        "--operation-id",
        proposed["operation_id"],
        "--token",
        "wrong-token",
    )
    assert result.exit_code == 2
    assert _payload(result) == {
        "status": "failed",
        "warnings": ["HEALTH_CONFIGURATION_CONFIRMATION_INVALID"],
    }


def test_config_confirm_expired_operation(isolated_db) -> None:
    init_db(quiet=True)
    proposed = _payload(
        _invoke(
            "project-health",
            "config",
            "preview",
            "--tolerance-days",
            "3",
        )
    )
    with sqlite3.connect(isolated_db) as connection:
        connection.execute(
            """
            UPDATE project_health_configuration_changes
            SET expires_at = '2020-01-01T00:00:00+00:00'
            WHERE operation_id = ?
            """,
            [proposed["operation_id"]],
        )
    result = _invoke(
        "project-health",
        "config",
        "confirm",
        "--operation-id",
        proposed["operation_id"],
        "--token",
        proposed["confirmation_token"],
    )
    assert result.exit_code == 0, result.output
    assert _payload(result)["status"] == "expired"


def test_config_confirm_rejects_stale_fingerprint(isolated_db) -> None:
    init_db(quiet=True)
    first = _payload(
        _invoke(
            "project-health",
            "config",
            "preview",
            "--tolerance-days",
            "5",
        )
    )
    second = _payload(
        _invoke(
            "project-health",
            "config",
            "preview",
            "--tolerance-days",
            "10",
        )
    )
    confirmed = _payload(
        _invoke(
            "project-health",
            "config",
            "confirm",
            "--operation-id",
            second["operation_id"],
            "--token",
            second["confirmation_token"],
        )
    )
    assert confirmed["status"] == "confirmed"
    stale = _invoke(
        "project-health",
        "config",
        "confirm",
        "--operation-id",
        first["operation_id"],
        "--token",
        first["confirmation_token"],
    )
    assert stale.exit_code == 0, stale.output
    assert _payload(stale)["status"] == "rejected"
    assert _payload(stale)["reason"] == "STALE_FINGERPRINT"


def test_config_preview_rejects_out_of_range_parameter(isolated_db) -> None:
    init_db(quiet=True)
    result = _invoke(
        "project-health",
        "config",
        "preview",
        "--tolerance-days",
        "91",
    )
    assert result.exit_code == 2
