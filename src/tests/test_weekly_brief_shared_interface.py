from __future__ import annotations

import json

from typer.testing import CliRunner

from pm_agent.cli import app as app_module
from pm_agent.dashboard import server as dashboard_server
from pm_agent.database.bootstrap import main as init_db
from pm_agent.use_cases import use_case_executor
from pm_agent.use_cases.service import UseCaseRequest


def test_weekly_brief_v2_use_case_is_opt_in_read_only_and_contract_versioned(
    isolated_db,
) -> None:
    init_db(quiet=True)
    descriptor = next(
        item
        for item in use_case_executor.list_descriptors()
        if item.use_case_id == "weekly-dm-brief-v2"
    )
    assert descriptor.contract_version == "2.0"
    assert descriptor.read_only is True

    result = use_case_executor.execute(
        UseCaseRequest(
            contract_version="2.0",
            use_case_id="weekly-dm-brief-v2",
            actor="test-agent",
            parameters={},
        )
    )
    assert result.status == "success"
    assert result.contract_version == "2.0"
    assert result.context["context_type"] == "weekly_dm_brief_v2"
    assert result.data["brief_version"] == "2.0"
    assert result.execution_metadata["read_only"] is True
    assert isinstance(result.facts, list)
    assert isinstance(result.signals, list)
    assert isinstance(result.recommendations, list)


def test_weekly_brief_v2_rejects_unknown_or_malformed_parameters(isolated_db) -> None:
    init_db(quiet=True)
    unknown = use_case_executor.execute(
        UseCaseRequest(
            contract_version="2.0",
            use_case_id="weekly-dm-brief-v2",
            parameters={"unexpected_parameter": True},
        )
    )
    assert unknown.status == "invalid"

    malformed = use_case_executor.execute(
        UseCaseRequest(
            contract_version="2.0",
            use_case_id="weekly-dm-brief-v2",
            parameters={"project_ids": [1]},
        )
    )
    assert malformed.status == "invalid"


def test_generic_tool_transport_stays_v1_only_and_legacy_route_is_preserved(
    isolated_db,
) -> None:
    init_db(quiet=True)
    generic_v2 = use_case_executor.execute(
        UseCaseRequest(use_case_id="weekly-dm-brief-v2")
    )
    assert generic_v2.status == "invalid"
    assert any(
        item.get("code") == "CONTRACT_VERSION_UNSUPPORTED"
        for item in generic_v2.warnings
    )

    legacy = use_case_executor.execute(
        UseCaseRequest(use_case_id="weekly-dm-brief")
    )
    assert legacy.contract_version == "1.0"
    assert legacy.status in {"success", "failed", "unavailable"}


def test_weekly_brief_v2_cli_query_is_structured(isolated_db) -> None:
    init_db(quiet=True)
    runner = CliRunner()
    result = runner.invoke(app_module.app, ["weekly-brief", "query"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["contract_version"] == "2.0"
    assert payload["status"] == "success"
    assert payload["data"]["brief_version"] == "2.0"


def test_weekly_brief_cli_snapshot_preview_and_confirm_fail_closed(
    monkeypatch,
) -> None:
    from pm_agent.cli.commands import weekly_brief as weekly_brief_commands

    runner = CliRunner()
    malformed = runner.invoke(
        app_module.app,
        [
            "weekly-brief",
            "snapshot-preview",
            "--candidate-json",
            "not-json",
            "--idempotency-key",
            "capture-key-001",
        ],
    )
    assert malformed.exit_code == 2
    assert json.loads(malformed.output)["warnings"] == [
        "WEEKLY_BRIEF_CAPTURE_CANDIDATE_INVALID"
    ]

    monkeypatch.setattr(
        weekly_brief_commands,
        "preview_capture",
        lambda **_kwargs: {
            "status": "previewed",
            "operation_id": "weekly-brief-capture-001",
            "candidate": {"execution_id": "weekly-v2-execution-synthetic-001"},
            "confirmation_required": True,
            "expires_at": "2026-08-01T00:10:00Z",
            "confirmation_token": "synthetic-one-time-token",
            "warnings": [],
        },
    )
    preview = runner.invoke(
        app_module.app,
        [
            "weekly-brief",
            "snapshot-preview",
            "--candidate-json",
            "{}",
            "--idempotency-key",
            "capture-key-001",
        ],
    )
    assert preview.exit_code == 0, preview.output
    assert json.loads(preview.output)["status"] == "previewed"

    monkeypatch.setattr(
        weekly_brief_commands,
        "confirm_capture",
        lambda **_kwargs: {
            "status": "failed",
            "warnings": ["WEEKLY_BRIEF_CAPTURE_TOKEN_INVALID"],
        },
    )
    failed = runner.invoke(
        app_module.app,
        [
            "weekly-brief",
            "snapshot-confirm",
            "--operation-id",
            "weekly-brief-capture-001",
            "--confirmation-token",
            "wrong-token",
        ],
    )
    assert failed.exit_code == 2
    assert json.loads(failed.output)["status"] == "failed"


def test_weekly_brief_dashboard_operations_contract(isolated_db, monkeypatch) -> None:
    client = dashboard_server.app.test_client()

    malformed = client.post(
        "/api/weekly-brief/operations",
        json={
            "operation": "preview",
            "candidate": "not-a-dict",
            "idempotency_key": "capture-key-001",
        },
    )
    assert malformed.status_code == 400
    assert malformed.get_json()["status"] == "failed"
    assert malformed.get_json()["warnings"] == [
        "WEEKLY_BRIEF_CAPTURE_CANDIDATE_INVALID"
    ]

    monkeypatch.setattr(
        dashboard_server,
        "preview_capture",
        lambda **_kwargs: {
            "status": "previewed",
            "operation_id": "weekly-brief-capture-001",
            "candidate": {"execution_id": "weekly-v2-execution-synthetic-001"},
            "confirmation_required": True,
            "expires_at": "2026-08-01T00:10:00Z",
            "confirmation_token": "synthetic-one-time-token",
            "warnings": [],
        },
    )
    preview = client.post(
        "/api/weekly-brief/operations",
        json={
            "operation": "preview",
            "candidate": {"execution_id": "weekly-v2-execution-synthetic-001"},
            "idempotency_key": "capture-key-001",
        },
    )
    assert preview.status_code == 200
    assert (
        preview.headers["X-DM-Interface-Contract"]
        == "weekly-brief-operation-v1"
    )
    assert preview.get_json()["status"] == "previewed"

    monkeypatch.setattr(
        dashboard_server,
        "confirm_capture",
        lambda **_kwargs: {
            "status": "confirmed",
            "confirmed_snapshot_id": "weekly-brief-snapshot-001",
            "warnings": [],
        },
    )
    confirmed = client.post(
        "/api/weekly-brief/operations",
        json={
            "operation": "confirm",
            "operation_id": "weekly-brief-capture-001",
            "confirmation_token": "synthetic-one-time-token",
        },
    )
    assert confirmed.status_code == 200
    assert confirmed.get_json()["status"] == "confirmed"

    monkeypatch.setattr(
        dashboard_server,
        "confirm_capture",
        lambda **_kwargs: {
            "status": "failed",
            "warnings": ["WEEKLY_BRIEF_CAPTURE_TOKEN_INVALID"],
        },
    )
    failed = client.post(
        "/api/weekly-brief/operations",
        json={
            "operation": "confirm",
            "operation_id": "weekly-brief-capture-001",
            "confirmation_token": "wrong-token",
        },
    )
    assert failed.status_code == 400
    assert failed.get_json()["status"] == "failed"


def test_typed_intelligence_projection_preserves_subject_kind_and_known_states() -> None:
    from pm_agent.use_cases import weekly_brief_v2

    execution_statement = {
        "statement_id": "risks-and-dependencies:execution:milestone-synthetic-001:adherence",
        "subject_kind": "execution",
        "subject_id": "milestone-synthetic-001",
    }
    fact = weekly_brief_v2._fact(
        {
            "fact_id": "fact-risks-and-dependencies:execution:milestone-synthetic-001:adherence",
            "producer": "execution",
            "subject_id": "milestone-synthetic-001",
            "statement_id": execution_statement["statement_id"],
            "value_state": "known",
            "evidence_refs": [],
        },
        execution_statement,
    )
    assert fact.subject.kind == "execution"
    assert fact.subject.id == "milestone-synthetic-001"
    assert fact.value_state == "known"
    assert fact.value == {"statement_id": execution_statement["statement_id"]}

    green_health = weekly_brief_v2._fact(
        {
            "fact_id": "fact-project-health-project-synthetic-001",
            "producer": "project_health",
            "subject_id": "project-synthetic-001",
            "statement_id": None,
            "value_state": "green",
            "evidence_refs": [],
        },
        None,
    )
    assert green_health.subject.kind == "project"
    assert green_health.value_state == "known"
    assert green_health.value == {"statement_id": None, "state": "green"}

    unavailable_health = weekly_brief_v2._fact(
        {
            "fact_id": "fact-project-health-project-synthetic-002",
            "producer": "project_health",
            "subject_id": "project-synthetic-002",
            "statement_id": None,
            "value_state": "unknown",
            "evidence_refs": [],
        },
        None,
    )
    assert unavailable_health.value_state == "unknown"
    assert unavailable_health.value == {"statement_id": None}
