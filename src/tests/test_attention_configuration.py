from __future__ import annotations

import hashlib
import json
import sqlite3

from typer.testing import CliRunner

from pm_agent.attention import AttentionService
from pm_agent.cli import app as app_module
from pm_agent.dashboard import server as dashboard_server
from pm_agent.database.bootstrap import main as init_db
from pm_agent.use_cases import use_case_executor
from pm_agent.use_cases.service import UseCaseRequest


LEGACY_OPERATION_ID = "attcfg-synthetic-legacy"
LEGACY_TOKEN = "synthetic-legacy-token"


def _current_rule_version(database_path) -> str:
    with sqlite3.connect(database_path) as connection:
        return connection.execute(
            """
            SELECT rule_version
            FROM attention_rules
            WHERE rule_key = 'project_health_attention' AND is_current = 1
            """
        ).fetchone()[0]


def _configuration_operation_count(database_path) -> int:
    with sqlite3.connect(database_path) as connection:
        return connection.execute(
            "SELECT COUNT(*) FROM attention_configuration_operations"
        ).fetchone()[0]


def _insert_legacy_configuration_operation(database_path) -> None:
    proposed = {
        "rule_key": "project_health_attention",
        "new_rule_version": "project-health-attention-v3",
        "parameters": {},
        "change": {
            "target": "project_override",
            "project_id": "project-770001",
        },
        "reconciliation_required": True,
    }
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO attention_configuration_operations
                (operation_id, actor, status, target, project_id,
                 current_rule_version, current_parameters_hash, proposed_json,
                 token_hash, created_at, expires_at)
            VALUES (?, ?, 'proposed', 'project_override', ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                LEGACY_OPERATION_ID,
                "manager-770001",
                "project-770001",
                "project-health-attention-v2",
                "synthetic-current-parameters-hash",
                json.dumps(proposed, sort_keys=True),
                hashlib.sha256(LEGACY_TOKEN.encode("utf-8")).hexdigest(),
                "2026-07-29T00:00:00+00:00",
                "2099-07-29T00:05:00+00:00",
            ],
        )


def test_rag_configuration_service_is_disabled_without_persistence(
    isolated_db,
) -> None:
    init_db(quiet=True)
    before_version = _current_rule_version(isolated_db)

    result = AttentionService().preview_project_health_rag_configuration(
        actor="manager-770001",
        target="project_override",
        project_id="project-770001",
        configuration={"jira_grade_mapping": {"YELLOW": "red"}},
    )

    assert result == {
        "status": "failed",
        "failure_code": "ATTENTION_RAG_CONFIGURATION_UNAVAILABLE",
    }
    assert _configuration_operation_count(isolated_db) == 0
    assert _current_rule_version(isolated_db) == before_version


def test_rag_configuration_cli_and_dashboard_preview_are_unavailable(
    isolated_db,
) -> None:
    init_db(quiet=True)
    runner = CliRunner()

    cli = runner.invoke(
        app_module.app,
        [
            "attention",
            "rag-config-preview",
            "--target",
            "project_override",
            "--project-id",
            "project-770001",
            "--configuration-json",
            '{"jira_grade_mapping":{"YELLOW":"red"}}',
        ],
    )
    assert cli.exit_code == 2
    assert json.loads(cli.output) == {
        "status": "failed",
        "failure_code": "ATTENTION_CLI_INVALID",
    }

    dashboard = dashboard_server.app.test_client().post(
        "/api/attention/operations",
        json={
            "operation": "preview",
            "action": "configure-project-health-rag",
            "target": "project_override",
            "project_id": "project-770001",
            "configuration": {"jira_grade_mapping": {"YELLOW": "red"}},
        },
    )
    assert dashboard.status_code == 400
    assert dashboard.get_json() == {
        "status": "failed",
        "failure_code": "ATTENTION_PREVIEW_INVALID",
    }
    assert _configuration_operation_count(isolated_db) == 0
    assert _current_rule_version(isolated_db) == "project-health-attention-v2"


def test_legacy_configuration_token_cannot_be_confirmed_from_public_interfaces(
    isolated_db,
) -> None:
    init_db(quiet=True)
    _insert_legacy_configuration_operation(isolated_db)
    runner = CliRunner()

    malformed = AttentionService().confirm(
        operation_id=LEGACY_OPERATION_ID,
        confirmation_token="",
    )
    assert malformed == {
        "status": "failed",
        "failure_code": "ATTENTION_CONFIRMATION_INVALID",
    }

    cli = runner.invoke(
        app_module.app,
        [
            "attention",
            "confirm",
            LEGACY_OPERATION_ID,
            "--token",
            LEGACY_TOKEN,
        ],
    )
    assert cli.exit_code == 2
    assert json.loads(cli.output) == {
        "status": "failed",
        "failure_code": "ATTENTION_RAG_CONFIGURATION_UNAVAILABLE",
    }

    dashboard = dashboard_server.app.test_client().post(
        "/api/attention/operations",
        json={
            "operation": "confirm",
            "operation_id": LEGACY_OPERATION_ID,
            "confirmation_token": LEGACY_TOKEN,
        },
    )
    assert dashboard.status_code == 400
    assert dashboard.get_json() == {
        "status": "failed",
        "failure_code": "ATTENTION_RAG_CONFIGURATION_UNAVAILABLE",
    }

    with sqlite3.connect(isolated_db) as connection:
        operation = connection.execute(
            """
            SELECT status, claimed_at, finished_at, failure_code
            FROM attention_configuration_operations
            WHERE operation_id = ?
            """,
            [LEGACY_OPERATION_ID],
        ).fetchone()
    assert operation == ("proposed", "", "", "")
    assert _current_rule_version(isolated_db) == "project-health-attention-v2"


def test_bootstrap_preserves_legacy_configuration_operation_storage(
    isolated_db,
) -> None:
    init_db(quiet=True)
    _insert_legacy_configuration_operation(isolated_db)

    init_db(quiet=True)

    with sqlite3.connect(isolated_db) as connection:
        operation = connection.execute(
            """
            SELECT operation_id, status, project_id
            FROM attention_configuration_operations
            """
        ).fetchone()
    assert operation == (
        LEGACY_OPERATION_ID,
        "proposed",
        "project-770001",
    )


def test_rejected_rag_configuration_preserves_compatibility_contracts(
    isolated_db,
) -> None:
    init_db(quiet=True)
    before = use_case_executor.execute(
        UseCaseRequest(
            use_case_id="management-attention",
            parameters={"limit": 20},
        )
    )

    rejected = AttentionService().preview_project_health_rag_configuration(
        actor="manager-770001",
        target="default",
        configuration={"jira_grade_mapping": {"RED": "clear"}},
    )
    after = use_case_executor.execute(
        UseCaseRequest(
            use_case_id="management-attention",
            parameters={"limit": 20},
        )
    )

    assert rejected["failure_code"] == "ATTENTION_RAG_CONFIGURATION_UNAVAILABLE"
    assert after.status == before.status
    assert after.data == before.data
    assert after.facts == before.facts
    assert after.signals == before.signals
    assert after.recommendations == before.recommendations
    assert after.warnings == before.warnings
    assert _configuration_operation_count(isolated_db) == 0
    with sqlite3.connect(isolated_db) as connection:
        pending_enabled = connection.execute(
            """
            SELECT enabled
            FROM attention_rules
            WHERE rule_key = 'pending_decision_attention' AND is_current = 1
            """
        ).fetchone()[0]
    assert pending_enabled == 0
