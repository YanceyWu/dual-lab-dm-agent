from __future__ import annotations

import json
import sqlite3

from typer.testing import CliRunner

from pm_agent.cli import app as app_module
from pm_agent.dashboard import server as dashboard_server
from pm_agent.database import repository
from pm_agent.database.bootstrap import main as init_db
from pm_agent.use_cases import use_case_executor
from pm_agent.use_cases.service import UseCaseRequest
from pm_agent.use_cases.team_capacity_context import build_team_capacity_context
from pm_agent.use_cases.tool_transport import ToolTransport
from scripts import seed


def test_team_workload_reference_use_case_has_stable_trace_and_evidence(isolated_db) -> None:
    seed.main()

    result = use_case_executor.execute(
        UseCaseRequest(
            use_case_id="team-workload-overview",
            actor="contract-test",
            requested_output="json",
        )
    )

    assert result.status == "success"
    assert result.contract_version == "1.0"
    assert result.proposed_writes == []
    assert result.evidence[0]["source_kind"] == "local_sqlite"
    assert result.execution_metadata["use_case_id"] == "team-workload-overview"
    assert result.execution_metadata["actor"] == "contract-test"
    assert result.execution_metadata["execution_id"]
    assert {item["state"] for item in result.freshness} == {"unknown"}
    assert result.warnings
    assert result.context["context_type"] == "team_capacity"
    assert result.context["requested_scope"]["effective_period"] == "current"
    assert result.context["members"][0]["availability_classification"] == "available"


def test_execution_trace_is_bounded_and_retrievable(isolated_db) -> None:
    seed.main()
    source_id = "import-resource-portal"
    run_id = repository.start_sync_run(source_id, triggered_by="test")
    repository.finish_sync_run(run_id, status="success")

    result = use_case_executor.execute(
        UseCaseRequest(use_case_id="team-workload-overview", correlation_id="trace-test")
    )
    trace = use_case_executor.get_result(result.execution_metadata["execution_id"])

    assert trace is not None
    assert trace.status == "success"
    assert trace.data == {}
    assert trace.execution_metadata["correlation_id"] == "trace-test"
    assert trace.execution_metadata["duration_ms"] >= 0
    assert trace.evidence[0] == {
        "evidence_id": "team-workload-members",
        "source_kind": "local_sqlite",
        "entity_kind": "employees",
        "record_count": 4,
        "applied_filters": {"team": None},
    }
    assert not hasattr(trace, "members")


def test_workload_freshness_distinguishes_stale_and_unavailable_sources(isolated_db) -> None:
    seed.main()
    stale_id = repository.start_sync_run("import-resource-portal", triggered_by="test")
    repository.finish_sync_run(stale_id, status="success")
    failed_id = repository.start_sync_run("import-skills-matrix", triggered_by="test")
    repository.fail_sync_run(failed_id, "synthetic failure")

    result = use_case_executor.execute(UseCaseRequest(use_case_id="team-workload-overview"))
    states = {item["source_id"]: item["state"] for item in result.freshness}

    assert states["import-resource-portal"] == "fresh"
    assert states["import-skills-matrix"] == "unavailable"
    assert "freshness:import-skills-matrix:unavailable" in result.warnings


def test_workload_freshness_distinguishes_stale_and_partial_sources(isolated_db) -> None:
    seed.main()
    stale_id = repository.start_sync_run("import-resource-portal", triggered_by="test")
    repository.finish_sync_run(stale_id, status="success")
    partial_id = repository.start_sync_run("import-skills-matrix", triggered_by="test")
    repository.finish_sync_run(partial_id, status="partial")
    with sqlite3.connect(isolated_db) as connection:
        connection.execute(
            "UPDATE sync_runs SET finished_at = datetime('now', '-1000 hours') WHERE id = ?",
            [stale_id],
        )

    result = use_case_executor.execute(UseCaseRequest(use_case_id="team-workload-overview"))
    states = {item["source_id"]: item["state"] for item in result.freshness}

    assert states == {
        "import-resource-portal": "stale",
        "import-skills-matrix": "partial",
    }


def test_execution_trace_retention_is_bounded(isolated_db, monkeypatch) -> None:
    seed.main()
    monkeypatch.setattr(repository, "EXECUTION_TRACE_RETENTION", 2)
    for number in range(3):
        repository.save_execution_trace(
            {
                "execution_id": f"trace-{number}",
                "use_case_id": "team-workload-overview",
                "operation": "query",
                "status": "success",
                "started_at": f"2026-07-19T00:00:0{number}+00:00",
                "finished_at": f"2026-07-19T00:00:0{number}+00:00",
                "duration_ms": 1,
            }
        )

    with sqlite3.connect(isolated_db) as connection:
        retained = connection.execute(
            "SELECT execution_id FROM execution_traces ORDER BY execution_id"
        ).fetchall()
    assert retained == [("trace-1",), ("trace-2",)]


def test_team_capacity_context_is_deterministic_and_explicitly_truncated() -> None:
    members = [
        {"id": f"member-{index:02d}", "name": f"Member {index}", "current_load": index / 100,
         "active_projects": 1}
        for index in range(21)
    ]
    context = build_team_capacity_context(
        data={"members": list(reversed(members)), "stats": {"total": 21}},
        evidence=[{"applied_filters": {"team": "Example Delivery Team"}}],
        freshness=[{"source_id": "source-a", "state": "fresh"}],
        assumptions=[],
        warnings=[],
        alternatives=[],
        execution_metadata={"use_case_id": "team-workload-overview", "requested_output": "json"},
    )

    assert [item["member_id"] for item in context["members"]] == [
        f"member-{index:02d}" for index in range(20)
    ]
    assert context["truncation"] == {
        "is_truncated": True,
        "omitted_member_count": 1,
        "maximum_members": 20,
    }
    assert context["requested_scope"]["team"] == "Example Delivery Team"


def test_unknown_use_case_is_returned_as_a_result() -> None:
    result = use_case_executor.execute(UseCaseRequest(use_case_id="unknown"))

    assert result.status == "unavailable"
    assert result.warnings == ["Unknown use case: unknown"]
    assert result.execution_metadata["use_case_id"] == "unknown"


def test_cli_workload_uses_reference_contract(isolated_db) -> None:
    seed.main()

    result = CliRunner().invoke(app_module.app, ["workload"])

    assert result.exit_code == 0, result.output
    assert "团队负载概览" in result.output


def test_dashboard_team_workload_endpoint_uses_reference_contract(isolated_db) -> None:
    seed.main()
    client = dashboard_server.app.test_client()

    response = client.get("/api/use-cases/team-workload-overview")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "success"
    assert payload["execution_metadata"]["use_case_id"] == "team-workload-overview"
    assert payload["execution_metadata"]["actor"] == "dashboard"


def test_tool_transport_lists_and_describes_without_operational_data() -> None:
    transport = ToolTransport(use_case_executor)

    listed = transport.handle(UseCaseRequest(operation="list", actor="contract-test"))
    described = transport.handle(
        UseCaseRequest(
            operation="describe",
            use_case_id="team-workload-overview",
            actor="contract-test",
        )
    )

    assert listed.status == "success"
    assert {item["use_case_id"] for item in listed.data["use_cases"]} >= {
        "team-workload-overview", "project-health-review"
    }
    assert described.status == "success"
    assert described.data["use_case"]["parameter_schema"]["team"]["required"] is False


def test_tool_transport_returns_structured_invalid_and_unavailable_results() -> None:
    transport = ToolTransport(use_case_executor)

    invalid = transport.handle(UseCaseRequest(operation="delete"))
    unavailable = transport.handle(UseCaseRequest(operation="describe", use_case_id="unknown"))

    assert invalid.status == "invalid"
    assert unavailable.status == "unavailable"


def test_tool_cli_query_is_json_and_matches_direct_executor(isolated_db) -> None:
    seed.main()
    runner = CliRunner()

    command = runner.invoke(
        app_module.app,
        ["tool", "query", "team-workload-overview", "--actor", "copilot-test"],
    )
    direct = use_case_executor.execute(
        UseCaseRequest(
            operation="query",
            use_case_id="team-workload-overview",
            actor="copilot-test",
            requested_output="json",
        )
    )

    assert command.exit_code == 0, command.output
    payload = json.loads(command.output)
    assert payload["status"] == direct.status == "success"
    assert payload["data"] == direct.data
    assert payload["execution_metadata"]["operation"] == "query"


def test_project_health_review_is_read_only_evidence_rich_and_available_to_tool_cli(isolated_db) -> None:
    init_db(quiet=True)
    with sqlite3.connect(isolated_db) as con:
        con.execute(
            "INSERT INTO projects (id, name, status, priority) VALUES ('project-atlas-990001', 'Project Atlas', 'active', 1)"
        )
        con.execute(
            """INSERT INTO jira_board_configs (id, name, project_key, base_jql, pm_project_id, active)
               VALUES ('atlas-board', 'Atlas Board', 'ATL', 'project = ATL', 'project-atlas-990001', 1)"""
        )
        con.execute(
            """INSERT INTO jira_health_snapshots
               (board_id, snapshot_date, overall_score, overall_grade, velocity_score, sprint_score, defect_score, scope_score, risks_json)
               VALUES ('atlas-board', '2026-07-22', 42, 'RED', 30, 40, 50, 60, '[{\"type\":\"scope\",\"msg\":\"Synthetic risk\"}]')"""
        )
        con.execute(
            """INSERT INTO confluence_status_snapshots
               (board_id, snapshot_date, rag_status, risks_text) VALUES ('atlas-board', '2026-07-22', 'GREEN', 'Synthetic status risk')"""
        )
        before = con.execute("SELECT COUNT(*) FROM jira_health_snapshots").fetchone()[0]

    direct = use_case_executor.execute(
        UseCaseRequest(use_case_id="project-health-review", parameters={"project_id": "project-atlas-990001"})
    )
    command = CliRunner().invoke(
        app_module.app,
        ["tool", "query", "project-health-review", "--project", "project-atlas-990001"],
    )

    assert direct.status == "success"
    assert direct.proposed_writes == []
    assert direct.data["summary"] == {"project_count": 1, "green_count": 0, "amber_count": 0, "red_count": 1, "unknown_count": 0}
    assert direct.data["projects"][0]["health_state"] == "red"
    assert direct.context["context_type"] == "project_health"
    assert direct.context["projects"][0]["boards"][0]["overall_grade"] == "RED"
    assert command.exit_code == 0, command.output
    assert json.loads(command.output)["data"] == direct.data
    with sqlite3.connect(isolated_db) as con:
        assert con.execute("SELECT COUNT(*) FROM jira_health_snapshots").fetchone()[0] == before


def test_project_health_review_returns_unknown_for_missing_local_snapshot(isolated_db) -> None:
    init_db(quiet=True)
    with sqlite3.connect(isolated_db) as con:
        con.execute("INSERT INTO projects (id, name, status, priority) VALUES ('project-beacon-990002', 'Project Beacon', 'active', 1)")

    result = use_case_executor.execute(UseCaseRequest(use_case_id="project-health-review"))

    assert result.status == "success"
    assert result.data["projects"][0]["health_state"] == "unknown"
    assert result.warnings == ["freshness:confluence-status-batch:unknown", "health_snapshot_missing:project-beacon-990002"]


def test_management_attention_and_contract_continuity_are_read_only(isolated_db) -> None:
    init_db(quiet=True)
    with sqlite3.connect(isolated_db) as con:
        con.execute("INSERT INTO projects (id, name, status, priority) VALUES ('project-atlas-990001', 'Project Atlas', 'active', 1)")
        con.execute("INSERT INTO jira_board_configs (id, name, project_key, base_jql, pm_project_id, active) VALUES ('atlas-board', 'Atlas Board', 'ATL', 'project = ATL', 'project-atlas-990001', 1)")
        con.execute("INSERT INTO jira_health_snapshots (board_id, snapshot_date, overall_score, overall_grade) VALUES ('atlas-board', '2026-07-22', 30, 'RED')")
        con.execute("INSERT INTO action_items (title, source, priority, due_date) VALUES ('Synthetic overdue action', 'test', 'high', '2000-01-01')")
        con.execute("INSERT INTO employees (id, name, status, resource_type, current_hiref) VALUES ('990104', 'Drew Example', 'active', 'STFTE', 'HIREF-990104')")
        con.execute("INSERT INTO hiref (id, project, request_type, start_date, end_date) VALUES ('HIREF-990104', 'Project Atlas', 'extend', '2025-01-01', '2025-01-02')")
        action_count = con.execute("SELECT COUNT(*) FROM action_items").fetchone()[0]
        hiref_count = con.execute("SELECT COUNT(*) FROM hiref").fetchone()[0]

    attention = use_case_executor.execute(UseCaseRequest(use_case_id="management-attention", parameters={"limit": 10}))
    continuity = use_case_executor.execute(UseCaseRequest(use_case_id="contract-continuity-review", parameters={"days": 180}))
    cli = CliRunner().invoke(app_module.app, ["tool", "query", "contract-continuity-review", "--days", "180"])

    assert attention.status == continuity.status == "success"
    assert {item["reason_code"] for item in attention.data["items"]} >= {"project_health_red", "action_overdue"}
    assert continuity.data["summary"]["attention_count"] == 1
    assert continuity.data["contracts"][0]["employee_id"] == "990104"
    assert cli.exit_code == 0, cli.output
    with sqlite3.connect(isolated_db) as con:
        assert con.execute("SELECT COUNT(*) FROM action_items").fetchone()[0] == action_count
        assert con.execute("SELECT COUNT(*) FROM hiref").fetchone()[0] == hiref_count


def test_connector_sync_results_normalize_latest_run_without_raw_error(isolated_db) -> None:
    init_db(quiet=True)
    with sqlite3.connect(isolated_db) as con:
        con.execute("INSERT INTO data_sources (id, source_type, source_name, refresh_sla_hours, active) VALUES ('jira-health-atlas', 'jira', 'Atlas health', 24, 1)")
        con.execute("""INSERT INTO sync_runs (id, source_id, run_type, started_at, finished_at, status, rows_in, rows_changed, target_tables_json, error_message)
                     VALUES ('run-jira-atlas', 'jira-health-atlas', 'incremental', '2026-07-22T10:00:00', '2026-07-22T10:01:00', 'failed', 12, 3, '[\"jira_health_snapshots\"]', 'synthetic confidential error text')""")

    result = use_case_executor.execute(UseCaseRequest(use_case_id="connector-sync-results", parameters={"connector": "jira"}))

    assert result.status == "success"
    item = result.data["sync_results"][0]
    assert item == {
        "connector": "jira", "source_id": "jira-health-atlas", "outcome": "failed", "freshness_state": "failed",
        "started_at": "2026-07-22T10:00:00", "finished_at": "2026-07-22T10:01:00", "rows_observed": 12,
        "rows_changed": 3, "target_tables": ["jira_health_snapshots"], "retry_recommended": True,
        "error_present": True, "refresh_sla_hours": 24,
    }
    assert "confidential" not in str(result.model_dump())


def test_dashboard_project_snapshots_uses_shared_executor(isolated_db) -> None:
    init_db(quiet=True)
    with sqlite3.connect(isolated_db) as con:
        con.execute("INSERT INTO projects (id, name, status, priority) VALUES ('project-atlas-990001', 'Project Atlas', 'active', 1)")
        con.execute("INSERT INTO project_snapshots (id, project_id, snapshot_date, artifact_kind, artifact_state, health, title, summary) VALUES ('snapshot-1', 'project-atlas-990001', '2026-07-22', 'plan', 'draft', 'amber', 'Synthetic', 'Synthetic summary')")

    client = dashboard_server.app.test_client()
    response = client.get("/api/project-snapshots?project_id=project-atlas-990001&health=amber")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload[0]["id"] == "snapshot-1"
    assert payload[0]["project_name"] == "Project Atlas"
