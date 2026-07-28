from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone

from typer.testing import CliRunner

from pm_agent.attention import AttentionService
from pm_agent.cli import app as app_module
from pm_agent.dashboard import server as dashboard_server
from pm_agent.database.bootstrap import main as init_db
from pm_agent.use_cases import use_case_executor
from pm_agent.use_cases.service import UseCaseRequest


def _now_text() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(
        timespec="seconds"
    )


def _seed_center_scenario(database_path) -> None:
    init_db(quiet=True)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO employees (id, wd_id, name, status)
            VALUES (
                'member-880101', 'member-880101',
                'Synthetic Member', 'active'
            )
            """
        )
        connection.executemany(
            """
            INSERT INTO projects (id, name, status, priority)
            VALUES (?, ?, 'active', ?)
            """,
            [
                ("project-880001", "Synthetic Project 1", 1),
                ("project-880002", "Synthetic Project 2", 2),
            ],
        )
        connection.execute(
            """
            INSERT INTO jira_board_configs
                (id, name, project_key, base_jql, pm_project_id, active)
            VALUES (
                'board-880001', 'Synthetic Board', 'SYN',
                'project = SYN', 'project-880001', 1
            )
            """
        )
        connection.execute(
            """
            INSERT INTO jira_health_snapshots
                (board_id, snapshot_date, overall_grade)
            VALUES ('board-880001', '2026-07-28', 'RED')
            """
        )
        connection.execute(
            """
            INSERT INTO action_items
                (title, owner_id, priority, status, due_date)
            VALUES (
                'Synthetic overdue follow-up', 'member-880101',
                'high', 'open', '2000-01-01'
            )
            """
        )
        connection.executemany(
            """
            INSERT INTO assignments
                (employee_id, project_id, allocation, status)
            VALUES ('member-880101', ?, ?, 'active')
            """,
            [
                ("project-880001", 0.6),
                ("project-880002", 0.5),
            ],
        )
        connection.execute(
            """
            INSERT INTO data_sources
                (id, source_type, source_name, refresh_sla_hours, active)
            VALUES (
                'jira-health-board-880001', 'jira',
                'Synthetic Jira Health', 24, 1
            )
            ON CONFLICT(id) DO UPDATE SET active = 1, refresh_sla_hours = 24
            """
        )
        connection.executemany(
            """
            INSERT INTO sync_runs
                (id, source_id, started_at, finished_at, status)
            VALUES (?, ?, ?, ?, 'success')
            """,
            [
                (
                    "sync-confluence-fresh-880001",
                    "confluence-status-batch",
                    _now_text(),
                    _now_text(),
                ),
                (
                    "sync-jira-stale-880001",
                    "jira-health-board-880001",
                    "2000-01-01T00:00:00",
                    "2000-01-01T00:00:01",
                ),
            ],
        )


def _confirm_reconciliation(
    service: AttentionService,
    *,
    rule_keys: list[str] | None = None,
) -> dict:
    preview = service.preview_reconciliation(
        actor="manager-880001",
        rule_keys=rule_keys,
    )
    assert preview["status"] == "proposed"
    result = service.confirm(
        operation_id=preview["operation_id"],
        confirmation_token=preview["confirmation_token"],
    )
    assert result["status"] == "success"
    return result


def _counts(database_path) -> tuple[int, int, int, int]:
    with sqlite3.connect(database_path) as connection:
        return tuple(
            connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in (
                "attention_operations",
                "attention_reconciliations",
                "attention_signals",
                "attention_history",
            )
        )


def test_empty_center_reports_absent_coverage_without_side_effect(isolated_db) -> None:
    init_db(quiet=True)
    before = _counts(isolated_db)

    result = use_case_executor.execute(
        UseCaseRequest(use_case_id="delivery-attention-center")
    )

    assert result.status == "success"
    assert result.data == result.context
    assert result.data["items"] == []
    assert result.data["summary"]["matched_count"] == 0
    assert result.data["summary"]["by_rule_state"] == {
        "active": 0,
        "clear": 0,
        "unknown": 0,
        "unavailable": 0,
    }
    assert result.data["reconciliation_coverage"] == {"status": "absent"}
    assert result.warnings == ["ATTENTION_NOT_RECONCILED"]
    assert _counts(isolated_db) == before


def test_center_projects_references_recommendations_summary_and_history(
    isolated_db,
) -> None:
    _seed_center_scenario(isolated_db)
    service = AttentionService()
    _confirm_reconciliation(service)

    result = use_case_executor.execute(
        UseCaseRequest(
            use_case_id="delivery-attention-center",
            parameters={
                "include_history": True,
                "history_limit": 1,
                "limit": 50,
            },
        )
    )

    assert result.status == "success"
    assert result.contract_version == "1.0"
    assert result.data == result.context
    assert result.data["summary"]["matched_count"] == 4
    assert result.data["summary"]["returned_count"] == 4
    assert result.data["summary"]["truncated"] is False
    assert result.data["summary"]["by_rule_key"] == {
        "project_health_attention": 1,
        "overdue_action_attention": 1,
        "source_freshness_attention": 1,
        "resource_overload_attention": 1,
        "pending_decision_attention": 0,
    }
    assert result.data["reconciliation_coverage"]["status"] == "partial"
    assert "ATTENTION_SOURCE_NOT_FRESH" in result.warnings
    assert len(result.facts) == len(result.signals) == len(result.recommendations) == 4
    severity_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3, "none": 4}
    severities = [item["severity"] for item in result.data["items"]]
    assert severities == sorted(severities, key=severity_rank.__getitem__)
    for item in result.data["items"]:
        assert len(item["recent_events"]) == 1
        assert item["fact_ref"] in {fact.fact_id for fact in result.facts}
        assert item["signal_ref"] in {
            signal.signal_id for signal in result.signals
        }
        assert item["recommendation_ref"] in {
            recommendation.recommendation_id
            for recommendation in result.recommendations
        }
        assert set(item["evidence_refs"]) <= {
            evidence["evidence_id"] for evidence in result.evidence
        }
        assert set(item["freshness_refs"]) <= {
            freshness["source_id"] for freshness in result.freshness
        }
        assert "operation_id" not in item["recent_events"][0]
        assert "timestamp" in item["recent_events"][0]
    recommendation_by_subject = {
        item.subject.id: item for item in result.recommendations
    }
    assert recommendation_by_subject["project-880001"].state == "blocked"
    assert recommendation_by_subject["jira-health-board-880001"].state == "available"
    assert recommendation_by_subject["member-880101"].state == "available"
    assert recommendation_by_subject["1"].state == "available"
    assert result.proposed_writes == []

    limited = use_case_executor.execute(
        UseCaseRequest(
            use_case_id="delivery-attention-center",
            parameters={"limit": 2},
        )
    )
    assert limited.data["summary"]["matched_count"] == 4
    assert limited.data["summary"]["returned_count"] == 2
    assert limited.data["summary"]["truncated"] is True


def test_center_scope_validation_and_coverage_are_explicit(isolated_db) -> None:
    _seed_center_scenario(isolated_db)
    _confirm_reconciliation(
        AttentionService(),
        rule_keys=["overdue_action_attention"],
    )

    invalid_states = use_case_executor.execute(
        UseCaseRequest(
            use_case_id="delivery-attention-center",
            parameters={"attention_states": ["open", "open"]},
        )
    )
    invalid_scope = use_case_executor.execute(
        UseCaseRequest(
            use_case_id="delivery-attention-center",
            parameters={
                "rule_key": "project_health_attention",
                "subject_kind": "action",
            },
        )
    )
    uncovered = use_case_executor.execute(
        UseCaseRequest(
            use_case_id="delivery-attention-center",
            parameters={"rule_key": "resource_overload_attention"},
        )
    )
    covered_by_canonical_kind = use_case_executor.execute(
        UseCaseRequest(
            use_case_id="delivery-attention-center",
            parameters={"subject_kind": "action"},
        )
    )

    assert invalid_states.status == invalid_scope.status == "invalid"
    assert invalid_states.warnings == [{"code": "ATTENTION_STATES_INVALID"}]
    assert invalid_scope.warnings == [
        {"code": "ATTENTION_SUBJECT_SCOPE_INVALID"}
    ]
    assert uncovered.data["reconciliation_coverage"] == {
        "status": "out_of_scope"
    }
    assert uncovered.warnings == ["ATTENTION_SCOPE_NOT_RECONCILED"]
    assert covered_by_canonical_kind.data["reconciliation_coverage"]["status"] == (
        "complete"
    )


def test_center_direct_cli_and_dashboard_query_share_projection(isolated_db) -> None:
    _seed_center_scenario(isolated_db)
    _confirm_reconciliation(AttentionService())

    direct = use_case_executor.execute(
        UseCaseRequest(use_case_id="delivery-attention-center")
    )
    cli = CliRunner().invoke(
        app_module.app,
        ["tool", "query", "delivery-attention-center"],
    )
    dashboard = dashboard_server.app.test_client().post(
        "/api/tool/query/delivery-attention-center",
        json={},
    )

    assert cli.exit_code == 0, cli.output
    assert dashboard.status_code == 200
    assert dashboard.headers["X-DM-Interface-Contract"] == "use-case-result-v1"
    for payload in (json.loads(cli.output), dashboard.get_json()):
        assert payload["contract_version"] == "1.0"
        assert payload["data"] == direct.data
        assert payload["facts"] == [
            item.model_dump(mode="json") for item in direct.facts
        ]
        assert payload["signals"] == [
            item.model_dump(mode="json") for item in direct.signals
        ]
        assert payload["recommendations"] == [
            item.model_dump(mode="json") for item in direct.recommendations
        ]


def test_lifecycle_no_ops_create_no_operation_or_history(isolated_db) -> None:
    _seed_center_scenario(isolated_db)
    service = AttentionService()
    _confirm_reconciliation(service)
    with sqlite3.connect(isolated_db) as connection:
        attention_id = connection.execute(
            """
            SELECT attention_id FROM attention_signals
            WHERE rule_key = 'overdue_action_attention'
            """
        ).fetchone()[0]

    acknowledgement = service.preview_acknowledgement(
        attention_id=attention_id,
        actor="manager-880001",
    )
    service.confirm(
        operation_id=acknowledgement["operation_id"],
        confirmation_token=acknowledgement["confirmation_token"],
    )
    before_ack_noop = _counts(isolated_db)
    assert service.preview_acknowledgement(
        attention_id=attention_id,
        actor="manager-880001",
    ) == {
        "status": "failed",
        "failure_code": "ATTENTION_ALREADY_ACKNOWLEDGED",
    }
    assert _counts(isolated_db) == before_ack_noop

    expiry = (
        datetime.now(timezone.utc) + timedelta(hours=2)
    ).isoformat(timespec="seconds")
    snooze = service.preview_snooze(
        attention_id=attention_id,
        actor="manager-880001",
        snoozed_until=expiry,
    )
    service.confirm(
        operation_id=snooze["operation_id"],
        confirmation_token=snooze["confirmation_token"],
    )
    before_snooze_noop = _counts(isolated_db)
    assert service.preview_snooze(
        attention_id=attention_id,
        actor="manager-880001",
        snoozed_until=expiry,
    ) == {
        "status": "failed",
        "failure_code": "ATTENTION_SNOOZE_UNCHANGED",
    }
    assert _counts(isolated_db) == before_snooze_noop

    with sqlite3.connect(isolated_db) as connection:
        connection.execute("UPDATE action_items SET status = 'done'")
    _confirm_reconciliation(service, rule_keys=["overdue_action_attention"])
    before_resolve_noop = _counts(isolated_db)
    assert service.preview_resolution(
        attention_id=attention_id,
        actor="manager-880001",
    ) == {
        "status": "failed",
        "failure_code": "ATTENTION_ALREADY_RESOLVED",
    }
    assert _counts(isolated_db) == before_resolve_noop


def test_attention_cli_and_dashboard_api_preserve_service_contract(
    isolated_db,
) -> None:
    _seed_center_scenario(isolated_db)
    runner = CliRunner()
    cli_preview = runner.invoke(
        app_module.app,
        [
            "attention",
            "reconcile-preview",
            "--rule",
            "overdue_action_attention",
        ],
    )
    assert cli_preview.exit_code == 0, cli_preview.output
    cli_payload = json.loads(cli_preview.output)
    assert cli_payload["status"] == "proposed"
    assert cli_payload["actor"] == "copilot"
    cli_failure = runner.invoke(
        app_module.app,
        ["attention", "acknowledge-preview", "attn-missing"],
    )
    assert cli_failure.exit_code == 2
    assert json.loads(cli_failure.output) == {
        "status": "failed",
        "failure_code": "ATTENTION_NOT_FOUND",
    }

    client = dashboard_server.app.test_client()
    rejected_actor = client.post(
        "/api/attention/operations",
        json={
            "operation": "preview",
            "action": "reconcile",
            "actor": "caller-supplied",
        },
    )
    assert rejected_actor.status_code == 400
    assert rejected_actor.get_json()["failure_code"] == "ATTENTION_PREVIEW_INVALID"

    preview = client.post(
        "/api/attention/operations",
        json={
            "operation": "preview",
            "action": "reconcile",
            "rule_keys": ["overdue_action_attention"],
        },
    )
    preview_payload = preview.get_json()
    assert preview.status_code == 200
    assert preview.headers["X-DM-Interface-Contract"] == "attention-operation-v1"
    assert preview_payload["status"] == "proposed"
    assert preview_payload["actor"] == "dashboard-local-user"

    confirm = client.post(
        "/api/attention/operations",
        json={
            "operation": "confirm",
            "operation_id": preview_payload["operation_id"],
            "confirmation_token": preview_payload["confirmation_token"],
        },
    )
    assert confirm.status_code == 200
    assert confirm.headers["X-DM-Interface-Contract"] == "attention-operation-v1"
    assert confirm.get_json()["status"] == "success"

    reused = client.post(
        "/api/attention/operations",
        json={
            "operation": "confirm",
            "operation_id": preview_payload["operation_id"],
            "confirmation_token": preview_payload["confirmation_token"],
        },
    )
    assert reused.status_code == 409
    assert reused.get_json()["failure_code"] == "ATTENTION_OPERATION_ALREADY_USED"
    assert "X-DM-Interface-Contract" not in reused.headers

    missing = client.post(
        "/api/attention/operations",
        json={
            "operation": "confirm",
            "operation_id": "attop-missing",
            "confirmation_token": "synthetic-token",
        },
    )
    assert missing.status_code == 404

    with dashboard_server.app.app_context():
        _, expired_status = dashboard_server._attention_response(
            {
                "status": "failed",
                "failure_code": "ATTENTION_CONFIRMATION_EXPIRED",
            }
        )
        _, unavailable_status = dashboard_server._attention_response(
            {"status": "failed", "failure_code": "DATA_ACCESS_FAILED"}
        )
    assert expired_status == 410
    assert unavailable_status == 503


def test_management_attention_remains_read_only_and_pending_rule_disabled(
    isolated_db,
) -> None:
    _seed_center_scenario(isolated_db)
    before = _counts(isolated_db)

    legacy = use_case_executor.execute(
        UseCaseRequest(use_case_id="management-attention", parameters={"limit": 20})
    )

    assert legacy.status == "success"
    assert legacy.recommendations == []
    assert _counts(isolated_db) == before
    with sqlite3.connect(isolated_db) as connection:
        assert connection.execute(
            """
            SELECT enabled FROM attention_rules
            WHERE rule_key = 'pending_decision_attention'
            """
        ).fetchone()[0] == 0
