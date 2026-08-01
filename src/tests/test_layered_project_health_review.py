from __future__ import annotations

import json
import sqlite3

from typer.testing import CliRunner

from pm_agent.cli import app as app_module
from pm_agent.dashboard import server as dashboard_server
from pm_agent.database.bootstrap import main as init_db
from pm_agent.project_health.evaluation import evaluate
from pm_agent.use_cases import use_case_executor
from pm_agent.use_cases.service import UseCaseRequest


def _assessment(db_path) -> None:
    init_db(quiet=True)
    with sqlite3.connect(db_path) as connection:
        connection.execute("INSERT INTO projects(id,name,status) VALUES ('project-layered-1','Synthetic','active')")
        connection.execute(
            """INSERT INTO execution_milestones
               (milestone_id,project_id,milestone_type,criticality,lifecycle_state,planned_date,authority,completeness_state,observed_at,schema_version)
               VALUES ('milestone-layered-1','project-layered-1','release','critical','in_progress','2020-01-01','synthetic','known','2026-01-01T00:00:00+00:00','synthetic-v1')"""
        )
    evaluate("project-layered-1", db_path=db_path)


def test_layered_review_reads_persisted_assessment_without_changing_legacy_or_attention(isolated_db) -> None:
    _assessment(isolated_db)
    result = use_case_executor.execute(
        UseCaseRequest(use_case_id="layered-project-health-review", parameters={"project_id": "project-layered-1"})
    )
    assert result.status == "success"
    assert result.data["assessments"][0]["state"] == "red"
    assert result.facts[0].value["dimensions"]["schedule"] == "red"
    assert result.signals[0].signal_type == "layered_project_health_state"
    assert result.freshness[0]["state"] == "unknown"
    assert result.recommendations == []
    with sqlite3.connect(isolated_db) as connection:
        assert connection.execute("SELECT COUNT(*) FROM project_health_assessment_runs").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM jira_health_snapshots").fetchone()[0] == 0


def test_layered_review_has_generic_transport_parity_and_fail_closed_empty_state(isolated_db) -> None:
    init_db(quiet=True)
    empty = use_case_executor.execute(UseCaseRequest(use_case_id="layered-project-health-review"))
    assert empty.status == "success"
    assert empty.warnings == ["LAYERED_PROJECT_HEALTH_NOT_AVAILABLE"]
    _assessment(isolated_db)
    runner = CliRunner()
    cli = runner.invoke(app_module.app, ["tool", "query", "layered-project-health-review", "--project", "project-layered-1"])
    dashboard = dashboard_server.app.test_client().post(
        "/api/tool/query/layered-project-health-review", json={"parameters": {"project_id": "project-layered-1"}}
    )
    assert cli.exit_code == 0, cli.output
    assert dashboard.status_code == 200
    assert json.loads(cli.output)["data"] == dashboard.get_json()["data"]


def test_layered_review_rejects_unknown_project(isolated_db) -> None:
    init_db(quiet=True)
    result = use_case_executor.execute(
        UseCaseRequest(use_case_id="layered-project-health-review", parameters={"project_id": "missing"})
    )
    assert result.status == "unavailable"
    assert result.warnings == [{"code": "PROJECT_NOT_FOUND"}]


def test_layered_review_unknown_assessment_is_contract_compliant_through_executor(isolated_db) -> None:
    """An unknown overall state must not carry an invented fact value."""
    init_db(quiet=True)
    with sqlite3.connect(isolated_db) as connection:
        connection.execute("INSERT INTO projects(id,name,status) VALUES ('project-layered-2','Synthetic','active')")
    evaluate("project-layered-2", db_path=isolated_db)
    result = use_case_executor.execute(
        UseCaseRequest(use_case_id="layered-project-health-review", parameters={"project_id": "project-layered-2"})
    )
    assert result.status == "success"
    assert result.data["assessments"][0]["state"] == "unknown"
    assert result.facts[0].value is None
    assert result.facts[0].value_state == "unknown"
    assert result.data["assessments"][0]["dimensions"]["schedule"] == "unknown"
