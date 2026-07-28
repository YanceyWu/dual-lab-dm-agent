from __future__ import annotations

import json
import sqlite3

import pytest
from typer.testing import CliRunner

from pm_agent.cli import app as app_module
from pm_agent.dashboard import server as dashboard_server
from pm_agent.database import repository
from pm_agent.database.bootstrap import main as init_db
from pm_agent.use_cases import use_case_executor
from pm_agent.use_cases.service import UseCaseRequest
from pm_agent.use_cases.tool_transport import ToolTransport


def _set_source_state(db_path, source_id: str, state: str) -> None:
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO data_sources
                (id, source_type, source_name, refresh_sla_hours, active)
            VALUES (?, 'synthetic', ?, 24, 1)
            """,
            [source_id, f"Synthetic {source_id}"],
        )
    if state == "unknown":
        return
    run_id = repository.start_sync_run(source_id, triggered_by="test")
    if state == "unavailable":
        repository.fail_sync_run(run_id, "synthetic failure")
        return
    repository.finish_sync_run(run_id, status="success")
    if state == "stale":
        with sqlite3.connect(db_path) as connection:
            connection.execute(
                """
                UPDATE sync_runs
                SET finished_at = datetime('now', '-1000 hours')
                WHERE id = ?
                """,
                [run_id],
            )


def _seed_active_attention(db_path) -> None:
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO projects (id, name, status, priority)
            VALUES ('project-atlas-001', 'Project Atlas', 'active', 1)
            """
        )
        connection.execute(
            """
            INSERT INTO jira_board_configs
                (id, name, project_key, base_jql, pm_project_id, active)
            VALUES
                ('atlas-board', 'Atlas Board', 'ATL', 'project = ATL',
                 'project-atlas-001', 1)
            """
        )
        connection.execute(
            """
            INSERT INTO jira_health_snapshots
                (board_id, snapshot_date, overall_score, overall_grade)
            VALUES ('atlas-board', '2026-07-27', 30, 'RED')
            """
        )
        connection.execute(
            """
            INSERT INTO action_items
                (title, source, priority, due_date)
            VALUES ('Synthetic overdue action', 'test', 'high', '2000-01-01')
            """
        )
    _set_source_state(db_path, "confluence-status-batch", "fresh")
    _set_source_state(db_path, "jira-health-atlas-board", "fresh")


def test_management_attention_maps_returned_items_to_facts_and_signals(
    isolated_db,
) -> None:
    init_db(quiet=True)
    _seed_active_attention(isolated_db)

    result = use_case_executor.execute(
        UseCaseRequest(
            use_case_id="management-attention",
            parameters={"limit": 20},
        )
    )

    assert result.status == "success"
    assert [item["attention_type"] for item in result.data["items"]] == [
        "project_health",
        "overdue_action",
    ]
    assert result.context["items"] == result.data["items"]
    assert result.context["summary"] == result.data["summary"]
    assert result.context["warnings"] == result.warnings
    assert len(result.facts) == len(result.signals) == len(result.data["items"]) == 2
    assert result.recommendations == []

    facts_by_type = {fact.fact_type: fact for fact in result.facts}
    project_fact = facts_by_type["project_health_state"]
    action_fact = facts_by_type["action_due_state"]
    assert project_fact.value == "red"
    assert project_fact.value_state == "known"
    assert project_fact.freshness_refs == [
        "confluence-status-batch",
        "jira-health-atlas-board",
    ]
    assert action_fact.value == "overdue"
    assert action_fact.value_state == "known"
    assert action_fact.freshness_refs == []

    evidence_ids = {item["evidence_id"] for item in result.evidence}
    fact_ids = {fact.fact_id for fact in result.facts}
    for fact in result.facts:
        assert fact.fact_kind == "derived"
        assert fact.rule_version == "management-attention-v1"
        assert set(fact.evidence_refs) <= evidence_ids
    for signal in result.signals:
        assert signal.state == "active"
        assert signal.rule_version == "management-attention-v1"
        assert set(signal.fact_refs) <= fact_ids
        assert set(signal.evidence_refs) <= evidence_ids


@pytest.mark.parametrize(
    "source_state,expected_value,expected_value_state,expected_record_count",
    [
        ("unknown", None, "unknown", 1),
        ("unavailable", None, "unavailable", 1),
        ("stale", "stale", "known", 1),
    ],
)
def test_source_freshness_fact_preserves_missing_data_state(
    isolated_db,
    source_state: str,
    expected_value: str | None,
    expected_value_state: str,
    expected_record_count: int,
) -> None:
    init_db(quiet=True)
    _set_source_state(isolated_db, "confluence-status-batch", source_state)

    result = use_case_executor.execute(
        UseCaseRequest(use_case_id="management-attention")
    )

    assert len(result.data["items"]) == len(result.facts) == len(result.signals) == 1
    fact = result.facts[0]
    signal = result.signals[0]
    assert fact.fact_type == "source_freshness_state"
    assert fact.value == expected_value
    assert fact.value_state == expected_value_state
    assert fact.freshness_refs == ["confluence-status-batch"]
    assert signal.signal_type == "source_freshness_attention"
    assert signal.fact_refs == [fact.fact_id]
    evidence = next(
        item
        for item in result.evidence
        if item["evidence_id"] == fact.evidence_refs[0]
    )
    assert evidence["record_count"] == expected_record_count
    assert result.recommendations == []


def test_missing_source_record_is_unknown_with_zero_record_evidence(
    isolated_db,
) -> None:
    init_db(quiet=True)
    _set_source_state(isolated_db, "confluence-status-batch", "fresh")
    with sqlite3.connect(isolated_db) as connection:
        connection.execute(
            """
            INSERT INTO projects (id, name, status, priority)
            VALUES ('project-missing-source', 'Missing Source', 'active', 1)
            """
        )
        connection.execute(
            """
            INSERT INTO jira_board_configs
                (id, name, project_key, base_jql, pm_project_id, active)
            VALUES
                ('missing-board', 'Missing Board', 'MIS', 'project = MIS',
                 'project-missing-source', 1)
            """
        )
        connection.execute(
            """
            INSERT INTO jira_health_snapshots
                (board_id, snapshot_date, overall_score, overall_grade)
            VALUES ('missing-board', '2026-07-27', 90, 'GREEN')
            """
        )

    result = use_case_executor.execute(
        UseCaseRequest(use_case_id="management-attention")
    )

    fact = result.facts[0]
    assert fact.subject.id == "jira-health-missing-board"
    assert fact.value is None
    assert fact.value_state == "unknown"
    evidence = next(
        item
        for item in result.evidence
        if item["evidence_id"] == fact.evidence_refs[0]
    )
    assert evidence["record_count"] == 0


def test_management_attention_empty_and_bounded_results_remain_aligned(
    isolated_db,
) -> None:
    init_db(quiet=True)
    _set_source_state(isolated_db, "confluence-status-batch", "fresh")

    empty = use_case_executor.execute(
        UseCaseRequest(use_case_id="management-attention")
    )
    assert empty.data["items"] == []
    assert empty.facts == empty.signals == empty.recommendations == []

    with sqlite3.connect(isolated_db) as connection:
        connection.executemany(
            """
            INSERT INTO action_items
                (title, source, priority, due_date)
            VALUES (?, 'test', 'high', '2000-01-01')
            """,
            [(f"Synthetic action {index}",) for index in range(3)],
        )
    bounded = use_case_executor.execute(
        UseCaseRequest(
            use_case_id="management-attention",
            parameters={"limit": 2},
        )
    )

    assert bounded.data["summary"]["total_attention_count"] == 3
    assert bounded.data["summary"]["returned_count"] == 2
    assert bounded.context["truncation"]["is_truncated"] is True
    assert len(bounded.data["items"]) == len(bounded.facts) == len(bounded.signals) == 2


def test_management_attention_descriptor_and_interfaces_match(
    isolated_db,
) -> None:
    init_db(quiet=True)
    _seed_active_attention(isolated_db)
    described = ToolTransport(use_case_executor).handle(
        UseCaseRequest(operation="describe", use_case_id="management-attention")
    )
    direct = use_case_executor.execute(
        UseCaseRequest(
            use_case_id="management-attention",
            parameters={"limit": 20},
        )
    )
    cli = CliRunner().invoke(
        app_module.app,
        ["tool", "query", "management-attention", "--limit", "20"],
    )
    dashboard = dashboard_server.app.test_client().post(
        "/api/tool/query/management-attention",
        json={"parameters": {"limit": 20}},
    )

    assert described.data["use_case"]["intelligence_capabilities"] == {
        "facts": True,
        "signals": True,
        "recommendations": False,
    }
    assert cli.exit_code == 0, cli.output
    assert dashboard.status_code == 200
    for payload in (json.loads(cli.output), dashboard.get_json()):
        assert payload["facts"] == [
            fact.model_dump(mode="json") for fact in direct.facts
        ]
        assert payload["signals"] == [
            signal.model_dump(mode="json") for signal in direct.signals
        ]
        assert payload["recommendations"] == []
