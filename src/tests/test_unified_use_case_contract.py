from __future__ import annotations

import json
import sqlite3

from typer.testing import CliRunner

from contract_coverage_test_helpers import publish_contract_coverage_from_legacy
from pm_agent.current_state_staffing import service as current_state_staffing_service
from pm_agent.cli import app as app_module
from pm_agent.dashboard import server as dashboard_server
from pm_agent.database import repository
from pm_agent.database.bootstrap import main as init_db
from pm_agent.use_cases import use_case_executor
from pm_agent.use_cases.execution import UseCaseDescriptor, UseCaseExecutor
from pm_agent.use_cases.service import (
    UseCaseRequest,
    UseCaseResult,
    new_execution_metadata,
)
from pm_agent.use_cases.team_capacity_context import build_team_capacity_context
from pm_agent.use_cases.tool_transport import ToolTransport
from current_state_staffing_test_helpers import publish_current_state_staffing_from_legacy
from scripts import seed


def _mark_current_state_publication_partial(db_path) -> None:
    with sqlite3.connect(db_path) as connection:
        report = json.loads(
            connection.execute(
                """
                SELECT report_json
                FROM current_state_staffing_publications
                WHERE is_current = 1
                LIMIT 1
                """
            ).fetchone()[0]
        )
        report["coverage"]["assignment_manifest_state"] = "partial"
        report["coverage"]["missing_record_count"] = 1
        connection.execute(
            """
            UPDATE current_state_staffing_publications
            SET report_json = ?
            WHERE is_current = 1
            """,
            [json.dumps(report)],
        )
        connection.commit()


def test_team_workload_reference_use_case_has_stable_trace_and_evidence(isolated_db) -> None:
    seed.main()
    publish_current_state_staffing_from_legacy(
        isolated_db,
        package_id="package-contract-workload-reference",
    )

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
    assert {item["source_id"] for item in result.freshness} == {
        "current-state-staffing-publication"
    }
    assert {item["state"] for item in result.freshness} == {"fresh"}
    assert result.evidence[1]["authority"] == "canonical"
    assert result.warnings == []
    assert result.context["context_type"] == "team_capacity"
    assert result.context["requested_scope"]["effective_period"] == "current"
    assert result.context["members"][0]["availability_classification"] == "available"
    assert result.context["calculation"]["freshness_state"] == "fresh"


def test_execution_trace_is_bounded_and_retrievable(isolated_db) -> None:
    seed.main()
    publish_current_state_staffing_from_legacy(
        isolated_db,
        package_id="package-contract-workload-trace",
    )
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


def test_workload_freshness_uses_current_state_publication_staleness(isolated_db) -> None:
    seed.main()
    publish_current_state_staffing_from_legacy(
        isolated_db,
        package_id="package-contract-workload-freshness-stale",
    )
    with sqlite3.connect(isolated_db) as connection:
        connection.execute(
            """
            UPDATE current_state_staffing_publications
            SET published_at = '2000-01-01T00:00:00+00:00'
            WHERE is_current = 1
            """
        )
        connection.commit()

    result = use_case_executor.execute(UseCaseRequest(use_case_id="team-workload-overview"))
    states = {item["source_id"]: item["state"] for item in result.freshness}

    assert states == {"current-state-staffing-publication": "stale"}
    assert "freshness:current-state-staffing-publication:stale" in result.warnings
    assert result.data["stats"]["avg_load"] is not None


def test_workload_freshness_uses_current_state_publication_partial_coverage(isolated_db) -> None:
    seed.main()
    publish_current_state_staffing_from_legacy(
        isolated_db,
        package_id="package-contract-workload-freshness-partial",
    )
    _mark_current_state_publication_partial(isolated_db)

    result = use_case_executor.execute(UseCaseRequest(use_case_id="team-workload-overview"))
    states = {item["source_id"]: item["state"] for item in result.freshness}

    assert states == {"current-state-staffing-publication": "partial"}
    assert result.data["stats"]["avg_load"] is None
    assert "freshness:current-state-staffing-publication:partial" in result.warnings


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


def test_team_capacity_context_suppresses_member_capacity_when_publication_is_partial() -> None:
    context = build_team_capacity_context(
        data={
            "members": [
                {
                    "id": "member-01",
                    "name": "Member 1",
                    "current_load": 0.8,
                    "active_projects": 2,
                }
            ],
            "stats": {"total": 1},
        },
        evidence=[{"applied_filters": {"team": "Example Delivery Team"}}],
        freshness=[
            {
                "source_id": "current-state-staffing-publication",
                "state": "partial",
            }
        ],
        assumptions=[],
        warnings=[],
        alternatives=[],
        execution_metadata={"use_case_id": "team-workload-overview", "requested_output": "json"},
    )

    assert context["members"][0] == {
        "member_id": "member-01",
        "display_name": "Member 1",
        "current_load": None,
        "active_project_count": None,
        "availability_classification": "unknown",
    }
    assert context["calculation"]["freshness_state"] == "partial"


def test_unknown_use_case_is_returned_as_a_result() -> None:
    result = use_case_executor.execute(UseCaseRequest(use_case_id="unknown"))

    assert result.status == "unavailable"
    assert result.warnings == [{"code": "USE_CASE_NOT_FOUND", "field": "use_case_id"}]
    assert result.execution_metadata["use_case_id"] == "unknown"


def test_cli_workload_uses_reference_contract(isolated_db) -> None:
    seed.main()
    publish_current_state_staffing_from_legacy(
        isolated_db,
        package_id="package-contract-workload-cli",
    )

    result = CliRunner().invoke(app_module.app, ["workload"])

    assert result.exit_code == 0, result.output
    assert "团队负载概览" in result.output


def test_dashboard_team_workload_endpoint_uses_reference_contract(isolated_db) -> None:
    seed.main()
    publish_current_state_staffing_from_legacy(
        isolated_db,
        package_id="package-contract-workload-dashboard",
    )
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


def test_executor_rejects_invalid_parameters_before_invoking_handler() -> None:
    calls: list[UseCaseRequest] = []
    executor = UseCaseExecutor()
    executor.register(
        UseCaseDescriptor(
            use_case_id="bounded-query",
            purpose="Synthetic bounded query.",
            parameter_schema={
                "days": {
                    "type": "integer",
                    "required": True,
                    "minimum": 1,
                    "maximum": 365,
                }
            },
        ),
        lambda request: (
            calls.append(request)
            or UseCaseResult(
                status="success",
                execution_metadata=new_execution_metadata(request),
            )
        ),
    )

    wrong_type = executor.execute(
        UseCaseRequest(use_case_id="bounded-query", parameters={"days": "abc"})
    )
    out_of_range = executor.execute(
        UseCaseRequest(use_case_id="bounded-query", parameters={"days": 9999})
    )
    unknown = executor.execute(
        UseCaseRequest(
            use_case_id="bounded-query",
            parameters={"days": 30, "unexpected": True},
        )
    )

    assert wrong_type.status == out_of_range.status == unknown.status == "invalid"
    assert wrong_type.warnings[0]["code"] == "PARAMETER_TYPE_INVALID"
    assert out_of_range.warnings[0] == {
        "code": "PARAMETER_OUT_OF_RANGE",
        "field": "days",
        "minimum": 1,
        "maximum": 365,
    }
    assert unknown.warnings[0] == {
        "code": "UNKNOWN_PARAMETER",
        "field": "unexpected",
    }
    assert calls == []


def test_executor_enforces_contract_version_and_descriptor_read_only_mode() -> None:
    executor = UseCaseExecutor()
    executor.register(
        UseCaseDescriptor(
            use_case_id="read-query",
            purpose="Synthetic read query.",
            parameter_schema={},
            read_only=True,
        ),
        lambda request: UseCaseResult(
            status="success",
            execution_metadata=new_execution_metadata(request),
        ),
    )
    unsupported = executor.execute(
        UseCaseRequest(use_case_id="read-query", contract_version="9.9")
    )
    with_token = executor.execute(
        UseCaseRequest(
            use_case_id="read-query",
            confirmation_token="irrelevant-token",
        )
    )

    assert unsupported.status == "invalid"
    assert unsupported.warnings == [
        {
            "code": "CONTRACT_VERSION_UNSUPPORTED",
            "field": "contract_version",
            "supported": ["1.0"],
        }
    ]
    assert with_token.status == "success"
    assert with_token.execution_metadata["read_only"] is True


def test_executor_classifies_internal_failure_without_exposing_exception() -> None:
    executor = UseCaseExecutor()
    executor.register(
        UseCaseDescriptor(
            use_case_id="failing-query",
            purpose="Synthetic failing query.",
            parameter_schema={},
        ),
        lambda request: (_ for _ in ()).throw(
            RuntimeError("secret at https://internal.example.invalid")
        ),
    )

    result = executor.execute(UseCaseRequest(use_case_id="failing-query"))

    assert result.status == "failed"
    assert result.warnings == [{"code": "USE_CASE_EXECUTION_FAILED"}]
    assert "secret" not in str(result.model_dump())
    assert "example.invalid" not in str(result.model_dump())


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
    publish_contract_coverage_from_legacy(
        isolated_db,
        package_id="package-contract-continuity-read-only-r1",
    )

    attention = use_case_executor.execute(UseCaseRequest(use_case_id="management-attention", parameters={"limit": 10}))
    continuity = use_case_executor.execute(UseCaseRequest(use_case_id="contract-continuity-review", parameters={"days": 180}))
    cli = CliRunner().invoke(app_module.app, ["tool", "query", "contract-continuity-review", "--days", "180"])

    assert attention.status == continuity.status == "success"
    assert {item["reason_code"] for item in attention.data["items"]} >= {"project_health_red", "action_overdue"}
    assert continuity.data["summary"]["attention_count"] == 1
    assert continuity.data["contracts"][0]["employee_id"] == "990104"
    assert continuity.freshness[0]["source_id"] == "contract-coverage-publication"
    assert continuity.evidence[1]["authority"] == "canonical"
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
    assert response.headers["X-DM-Interface-Contract"] == "legacy-result-projection"
    payload = response.get_json()
    assert payload[0]["id"] == "snapshot-1"


def test_generic_cli_and_dashboard_return_equivalent_full_contract(
    isolated_db,
) -> None:
    init_db(quiet=True)
    with sqlite3.connect(isolated_db) as con:
        con.execute(
            """
            INSERT INTO projects (id, name, status, priority)
            VALUES ('project-atlas-990001', 'Project Atlas', 'active', 1)
            """
        )
        con.execute(
            """
            INSERT INTO project_snapshots
                (id, project_id, snapshot_date, artifact_kind,
                 artifact_state, health, title, summary)
            VALUES ('snapshot-1', 'project-atlas-990001', '2026-07-22',
                    'plan', 'draft', 'amber', 'Synthetic',
                    'Synthetic summary')
            """
        )

    cli = CliRunner().invoke(
        app_module.app,
        [
            "tool",
            "query",
            "project-snapshot-list",
            "--param",
            "health=amber",
            "--param",
            "artifact_kind=plan",
        ],
    )
    dashboard = dashboard_server.app.test_client().post(
        "/api/tool/query/project-snapshot-list",
        json={"parameters": {"health": "amber", "artifact_kind": "plan"}},
    )
    direct = use_case_executor.execute(
        UseCaseRequest(
            use_case_id="project-snapshot-list",
            parameters={"health": "amber", "artifact_kind": "plan"},
        )
    )

    assert cli.exit_code == 0, cli.output
    assert dashboard.status_code == 200
    assert (
        dashboard.headers["X-DM-Interface-Contract"]
        == "use-case-result-v1"
    )
    cli_payload = json.loads(cli.output)
    dashboard_payload = dashboard.get_json()
    for payload in (cli_payload, dashboard_payload):
        assert payload["status"] == direct.status
        assert payload["data"] == direct.data
        assert payload["evidence"] == direct.evidence
        assert payload["freshness"] == direct.freshness
        assert payload["warnings"] == direct.warnings
        assert payload["contract_version"] == direct.contract_version


def test_generic_interfaces_preserve_executor_validation_errors() -> None:
    cli = CliRunner().invoke(
        app_module.app,
        [
            "tool",
            "query",
            "contract-continuity-review",
            "--param",
            "days=9999",
        ],
    )
    dashboard = dashboard_server.app.test_client().post(
        "/api/tool/query/contract-continuity-review",
        json={"parameters": {"days": 9999}},
    )

    assert cli.exit_code == 2
    assert dashboard.status_code == 400
    assert json.loads(cli.output)["warnings"] == dashboard.get_json()["warnings"]
    assert dashboard.get_json()["warnings"] == [
        {
            "code": "PARAMETER_OUT_OF_RANGE",
            "field": "days",
            "minimum": 1,
            "maximum": 365,
        }
    ]


def test_dashboard_current_state_routes_are_explicitly_marked_canonical(
    isolated_db,
) -> None:
    init_db(quiet=True)

    client = dashboard_server.app.test_client()

    for path in ("/api/summary", "/api/projects", "/api/employees"):
        response = client.get(path)
        assert response.status_code == 200
        assert (
            response.headers["X-DM-Interface-Contract"]
            == "current-state-staffing-canonical-read"
        )


def test_dashboard_summary_suppresses_numeric_loads_without_current_state_publication(
    isolated_db,
) -> None:
    init_db(quiet=True)
    with sqlite3.connect(isolated_db) as con:
        con.execute(
            """
            INSERT INTO employees (id, wd_id, name, status)
            VALUES ('990101', '990101', 'Alex Example', 'active')
            """
        )
        con.execute(
            """
            INSERT INTO projects (id, name, status, priority)
            VALUES ('project-atlas-990001', 'Project Atlas', 'active', 1)
            """
        )
        con.execute(
            """
            INSERT INTO assignments
                (employee_id, project_id, role, allocation, start_date, status)
            VALUES
                ('990101', 'project-atlas-990001', 'developer', 1.0, '2026-07-01', 'active')
            """
        )

    payload = dashboard_server.app.test_client().get("/api/summary").get_json()

    assert payload["total_staff"] == 1
    assert payload["current_state_staffing_state"] == "unknown"
    assert payload["current_state_staffing_freshness_state"] == "unknown"
    assert payload["avg_load"] is None
    assert payload["overloaded"] is None


def test_dashboard_summary_suppresses_numeric_loads_for_partial_current_state_publication(
    isolated_db,
) -> None:
    seed.main()
    publish_current_state_staffing_from_legacy(
        isolated_db,
        package_id="package-dashboard-summary-partial",
    )
    _mark_current_state_publication_partial(isolated_db)

    payload = dashboard_server.app.test_client().get("/api/summary").get_json()

    assert payload["current_state_staffing_state"] == "known"
    assert payload["current_state_staffing_freshness_state"] == "partial"
    assert payload["avg_load"] is None
    assert payload["overloaded"] is None


def test_dashboard_employees_suppress_load_for_partial_current_state_publication(
    isolated_db,
) -> None:
    seed.main()
    publish_current_state_staffing_from_legacy(
        isolated_db,
        package_id="package-dashboard-employees-partial",
    )
    _mark_current_state_publication_partial(isolated_db)

    payload = dashboard_server.app.test_client().get("/api/employees").get_json()

    assert payload
    assert {
        employee["current_state_staffing_freshness_state"] for employee in payload
    } == {"partial"}
    assert all(employee["load_pct"] is None for employee in payload)


def test_dashboard_projects_resolve_hiref_risk_from_current_state_identity(
    isolated_db,
) -> None:
    init_db(quiet=True)
    with sqlite3.connect(isolated_db) as con:
        con.execute(
            """
            INSERT INTO employees (id, wd_id, name, status, resource_type, current_hiref)
            VALUES ('employee-990201', 'WD-990201', 'Alex Example', 'active', 'STFTE', 'HIREF-990201')
            """
        )
        con.execute(
            """
            INSERT INTO hiref (id, project, request_type, start_date, end_date)
            VALUES ('HIREF-990201', 'Project Atlas', 'extend', '2026-08-01', '2026-08-31')
            """
        )
        con.execute(
            """
            INSERT INTO projects (id, name, status, priority)
            VALUES ('project-atlas-990001', 'Project Atlas', 'active', 1)
            """
        )
        con.commit()
    publish_contract_coverage_from_legacy(
        isolated_db,
        package_id="package-dashboard-projects-contract-coverage-r1",
    )

    package = {
        "dataset_marker": "TEST_CURRENT_STATE_STAFFING",
        "package_id": "package-dashboard-projects-r1",
        "schema_version": current_state_staffing_service.PACKAGE_SCHEMA_VERSION,
        "generated_at": "2026-08-15T00:00:00+00:00",
        "source_id": "source-test-current-state-staffing",
        "publication_scope": {
            "scope_key": "test-current-state-staffing",
            "as_of_date": "2026-08-15",
            "effective_year": 2026,
            "effective_month": 8,
        },
        "manifest": {
            "member_ids": ["WD-990201"],
            "project_ids": ["project-atlas-990001"],
            "assignment_keys": [
                {
                    "member_id": "WD-990201",
                    "project_id": "project-atlas-990001",
                }
            ],
        },
        "members": [
            {
                "member_id": "WD-990201",
                "display_name": "Alex Example",
                "status": "active",
                "role": "developer",
                "level": "senior",
                "resource_type": "LTFTE",
                "current_hiref_id": "HIREF-990201",
                "hiref_end_date": "2026-08-31",
            }
        ],
        "projects": [
            {
                "project_id": "project-atlas-990001",
                "display_name": "Project Atlas",
                "status": "active",
                "priority": 1,
            }
        ],
        "assignments": [
            {
                "member_id": "WD-990201",
                "project_id": "project-atlas-990001",
                "allocation": 0.8,
            }
        ],
    }
    preview = current_state_staffing_service.preview_import(package, db_path=isolated_db)
    current_state_staffing_service.confirm_import(preview["session_id"], db_path=isolated_db)

    payload = dashboard_server.app.test_client().get("/api/projects").get_json()

    assert payload[0]["contract_coverage_freshness_state"] == "fresh"
    assert payload[0]["hiref_risk"] == 1
    assert payload[0]["members"][0]["wd_id"] == "WD-990201"
    assert payload[0]["members"][0]["id"] == "employee-990201"


def test_dashboard_projects_suppress_active_members_for_partial_publication(
    isolated_db,
) -> None:
    seed.main()
    publish_current_state_staffing_from_legacy(
        isolated_db,
        package_id="package-dashboard-projects-partial",
    )
    with sqlite3.connect(isolated_db) as con:
        con.execute(
            """
            INSERT INTO assignments
                (employee_id, project_id, role, allocation, start_date, end_date, status)
            VALUES
                ('990004', 'project-atlas-990001', 'delivery_manager', 0.5, '2026-08-01', '2026-08-31', 'planned')
            """
        )
        con.commit()
    _mark_current_state_publication_partial(isolated_db)

    payload = dashboard_server.app.test_client().get("/api/projects").get_json()
    command = CliRunner().invoke(
        app_module.app,
        ["project", "team", "project-atlas-990001"],
    )
    atlas = next(project for project in payload if project["id"] == "project-atlas-990001")

    assert atlas["current_state_staffing_freshness_state"] == "partial"
    assert atlas["team_size"] is None
    assert atlas["hiref_risk"] is None
    assert [member["assign_status"] for member in atlas["members"]] == ["planned"]
    assert command.exit_code == 0, command.output
    assert "当前状态团队不可用" in command.output
    assert "暂无分配成员" not in command.output
