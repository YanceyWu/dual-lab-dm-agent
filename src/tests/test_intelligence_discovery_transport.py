from __future__ import annotations

import json
import sqlite3

import pytest
from typer.testing import CliRunner

from pm_agent.cli import app as app_module
from pm_agent.dashboard import server as dashboard_server
from pm_agent.database.bootstrap import main as init_db
from pm_agent.use_cases import use_case_executor
from pm_agent.use_cases.execution import (
    IntelligenceCapabilities,
    UseCaseDescriptor,
    UseCaseExecutor,
)
from pm_agent.use_cases.service import UseCaseRequest, UseCaseResult
from pm_agent.use_cases.tool_transport import ToolTransport


EMPTY_CAPABILITIES = {
    "facts": False,
    "signals": False,
    "recommendations": False,
}

MANAGEMENT_ATTENTION_CAPABILITIES = {
    "facts": True,
    "signals": True,
    "recommendations": False,
}

CENTER_CAPABILITIES = {
    "facts": True,
    "signals": True,
    "recommendations": True,
}

PRODUCTION_USE_CASE_IDS = {
    "action-followup",
    "connector-status-review",
    "connector-sync-results",
    "contract-continuity-review",
    "delivery-attention-center",
    "management-attention",
    "project-health-review",
    "project-snapshot-list",
    "team-workload-overview",
    "weekly-dm-brief",
}


def test_descriptor_capabilities_default_false_and_explicit_values_round_trip() -> None:
    executor = UseCaseExecutor()
    executor.register(
        UseCaseDescriptor(
            use_case_id="empty-intelligence",
            purpose="Synthetic empty intelligence output.",
            parameter_schema={},
        ),
        lambda request: UseCaseResult(status="success"),
    )
    executor.register(
        UseCaseDescriptor(
            use_case_id="synthetic-facts",
            purpose="Synthetic descriptor capability.",
            parameter_schema={},
            intelligence_capabilities=IntelligenceCapabilities(facts=True),
        ),
        lambda request: UseCaseResult(status="success"),
    )
    transport = ToolTransport(executor)

    listed = transport.handle(UseCaseRequest(operation="list"))
    described = transport.handle(
        UseCaseRequest(operation="describe", use_case_id="synthetic-facts")
    )

    by_id = {
        item["use_case_id"]: item["intelligence_capabilities"]
        for item in listed.data["use_cases"]
    }
    assert by_id == {
        "empty-intelligence": EMPTY_CAPABILITIES,
        "synthetic-facts": {
            "facts": True,
            "signals": False,
            "recommendations": False,
        },
    }
    assert described.data["use_case"]["intelligence_capabilities"] == by_id[
        "synthetic-facts"
    ]
    assert listed.facts == listed.signals == listed.recommendations == []
    assert described.facts == described.signals == described.recommendations == []


@pytest.mark.parametrize(
    "values",
    [
        {"facts": "yes"},
        {"signals": 1},
        {"recommendations": None},
    ],
)
def test_descriptor_capabilities_require_strict_booleans(
    values: dict[str, object],
) -> None:
    with pytest.raises(TypeError, match="must be a boolean"):
        IntelligenceCapabilities(**values)

    with pytest.raises(
        TypeError,
        match="must be IntelligenceCapabilities",
    ):
        UseCaseDescriptor(
            use_case_id="invalid-capabilities",
            purpose="Synthetic invalid descriptor.",
            parameter_schema={},
            intelligence_capabilities=values,
        )


def test_production_list_and_describe_advertise_only_implemented_capabilities() -> None:
    transport = ToolTransport(use_case_executor)
    direct_list = transport.handle(UseCaseRequest(operation="list"))
    direct_describe = transport.handle(
        UseCaseRequest(operation="describe", use_case_id="management-attention")
    )
    runner = CliRunner()
    cli_list = runner.invoke(app_module.app, ["tool", "list"])
    cli_describe = runner.invoke(
        app_module.app,
        ["tool", "describe", "management-attention"],
    )

    assert cli_list.exit_code == cli_describe.exit_code == 0
    listed_payload = json.loads(cli_list.output)
    described_payload = json.loads(cli_describe.output)
    assert {
        item["use_case_id"] for item in direct_list.data["use_cases"]
    } == PRODUCTION_USE_CASE_IDS
    assert {
        item["use_case_id"] for item in listed_payload["data"]["use_cases"]
    } == PRODUCTION_USE_CASE_IDS
    for item in direct_list.data["use_cases"]:
        expected = (
            MANAGEMENT_ATTENTION_CAPABILITIES
            if item["use_case_id"] == "management-attention"
            else CENTER_CAPABILITIES
            if item["use_case_id"] == "delivery-attention-center"
            else EMPTY_CAPABILITIES
        )
        assert item["intelligence_capabilities"] == expected
    assert (
        direct_describe.data["use_case"]["intelligence_capabilities"]
        == MANAGEMENT_ATTENTION_CAPABILITIES
    )
    for item in listed_payload["data"]["use_cases"]:
        expected = (
            MANAGEMENT_ATTENTION_CAPABILITIES
            if item["use_case_id"] == "management-attention"
            else CENTER_CAPABILITIES
            if item["use_case_id"] == "delivery-attention-center"
            else EMPTY_CAPABILITIES
        )
        assert item["intelligence_capabilities"] == expected
    assert (
        described_payload["data"]["use_case"]["intelligence_capabilities"]
        == MANAGEMENT_ATTENTION_CAPABILITIES
    )
    for payload in (listed_payload, described_payload):
        assert payload["contract_version"] == "1.0"
        assert payload["facts"] == []
        assert payload["signals"] == []
        assert payload["recommendations"] == []


def test_structured_cli_dashboard_and_direct_query_share_empty_intelligence(
    isolated_db,
) -> None:
    init_db(quiet=True)
    cli = CliRunner().invoke(
        app_module.app,
        ["tool", "query", "project-snapshot-list"],
    )
    dashboard = dashboard_server.app.test_client().post(
        "/api/tool/query/project-snapshot-list",
        json={},
    )
    direct = use_case_executor.execute(
        UseCaseRequest(use_case_id="project-snapshot-list")
    )

    assert cli.exit_code == 0, cli.output
    assert dashboard.status_code == 200
    assert dashboard.headers["X-DM-Interface-Contract"] == "use-case-result-v1"
    for payload in (json.loads(cli.output), dashboard.get_json()):
        assert payload["facts"] == direct.facts == []
        assert payload["signals"] == direct.signals == []
        assert payload["recommendations"] == direct.recommendations == []
        assert payload["contract_version"] == direct.contract_version == "1.0"


def test_trace_summary_stays_bounded_and_has_empty_intelligence(isolated_db) -> None:
    init_db(quiet=True)
    result = use_case_executor.execute(
        UseCaseRequest(use_case_id="project-snapshot-list")
    )
    trace = use_case_executor.get_result(result.execution_metadata["execution_id"])

    assert trace is not None
    assert trace.execution_metadata["trace_summary"] is True
    assert trace.data == {}
    assert trace.facts == []
    assert trace.signals == []
    assert trace.recommendations == []
    with sqlite3.connect(isolated_db) as connection:
        trace_columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(execution_traces)"
            ).fetchall()
        }
    assert {"facts", "signals", "recommendations"}.isdisjoint(trace_columns)
