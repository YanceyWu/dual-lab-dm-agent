from __future__ import annotations

import copy
import hashlib
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from typer.testing import CliRunner

from pm_agent.attention import AttentionService
from pm_agent.cli import app as app_module
from pm_agent.dashboard import server as dashboard_server
from pm_agent.database.bootstrap import main as init_db
from pm_agent.use_cases import use_case_executor
from pm_agent.use_cases.service import UseCaseRequest


def _current_rule(database_path) -> tuple[str, dict]:
    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            """
            SELECT rule_version, parameters_json
            FROM attention_rules
            WHERE rule_key = 'project_health_attention' AND is_current = 1
            """
        ).fetchone()
    return row[0], json.loads(row[1])


def _changed_default(database_path) -> dict:
    _, parameters = _current_rule(database_path)
    definition = copy.deepcopy(parameters["default"])
    definition["jira_grade_mapping"]["YELLOW"] = "red"
    return definition


def _confirm(service: AttentionService, preview: dict) -> dict:
    assert preview["status"] == "proposed"
    return service.confirm(
        operation_id=preview["operation_id"],
        confirmation_token=preview["confirmation_token"],
    )


def test_rag_default_preview_confirm_creates_version_without_reconciliation(
    isolated_db,
) -> None:
    init_db(quiet=True)
    service = AttentionService()
    configuration = _changed_default(isolated_db)

    preview = service.preview_project_health_rag_configuration(
        actor="manager-770001",
        target="default",
        configuration=configuration,
    )

    assert preview["status"] == "proposed"
    assert preview["scope"] == {
        "rule_key": "project_health_attention",
        "target": "default",
        "project_id": "",
    }
    assert preview["proposed"] == {
        "prior_rule_version": "project-health-attention-v2",
        "new_rule_version": "project-health-attention-v3",
        "change": {
            "target": "default",
            "configuration": configuration,
            "remove_override": False,
        },
        "reconciliation_required": True,
    }
    with sqlite3.connect(isolated_db) as connection:
        operation = connection.execute(
            """
            SELECT token_hash, status
            FROM attention_configuration_operations
            WHERE operation_id = ?
            """,
            [preview["operation_id"]],
        ).fetchone()
        current_before = connection.execute(
            """
            SELECT rule_version FROM attention_rules
            WHERE rule_key = 'project_health_attention' AND is_current = 1
            """
        ).fetchone()[0]
    assert operation == (
        hashlib.sha256(
            preview["confirmation_token"].encode("utf-8")
        ).hexdigest(),
        "proposed",
    )
    assert current_before == "project-health-attention-v2"

    result = _confirm(service, preview)

    assert result == {
        "status": "success",
        "rule_key": "project_health_attention",
        "prior_rule_version": "project-health-attention-v2",
        "rule_version": "project-health-attention-v3",
        "target": "default",
        "project_id": "",
        "reconciliation_required": True,
    }
    version, parameters = _current_rule(isolated_db)
    assert version == "project-health-attention-v3"
    assert parameters["default"] == configuration
    with sqlite3.connect(isolated_db) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM attention_reconciliations"
        ).fetchone()[0] == 0
        assert connection.execute(
            "SELECT COUNT(*) FROM attention_signals"
        ).fetchone()[0] == 0
        assert connection.execute(
            "SELECT COUNT(*) FROM attention_history"
        ).fetchone()[0] == 0
        assert connection.execute(
            """
            SELECT enabled FROM attention_rules
            WHERE rule_key = 'pending_decision_attention' AND is_current = 1
            """
        ).fetchone()[0] == 0


def test_rag_project_override_add_remove_and_no_op_are_bounded(isolated_db) -> None:
    init_db(quiet=True)
    service = AttentionService()
    override = {"jira_grade_mapping": {"YELLOW": "red"}}
    add_preview = service.preview_project_health_rag_configuration(
        actor="manager-770001",
        target="project_override",
        project_id="project-770001",
        configuration=override,
    )
    assert _confirm(service, add_preview)["rule_version"] == (
        "project-health-attention-v3"
    )
    assert _current_rule(isolated_db)[1]["project_overrides"] == {
        "project-770001": override
    }

    remove_preview = service.preview_project_health_rag_configuration(
        actor="manager-770001",
        target="project_override",
        project_id="project-770001",
        remove_override=True,
    )
    assert remove_preview["proposed"]["change"]["configuration"] is None
    assert _confirm(service, remove_preview)["rule_version"] == (
        "project-health-attention-v4"
    )
    assert _current_rule(isolated_db)[1]["project_overrides"] == {}

    with sqlite3.connect(isolated_db) as connection:
        before = connection.execute(
            "SELECT COUNT(*) FROM attention_configuration_operations"
        ).fetchone()[0]
    unchanged = service.preview_project_health_rag_configuration(
        actor="manager-770001",
        target="project_override",
        project_id="project-770001",
        remove_override=True,
    )
    with sqlite3.connect(isolated_db) as connection:
        after = connection.execute(
            "SELECT COUNT(*) FROM attention_configuration_operations"
        ).fetchone()[0]
    assert unchanged == {
        "status": "failed",
        "failure_code": "ATTENTION_CONFIGURATION_UNCHANGED",
    }
    assert after == before


def test_rag_configuration_rejects_unbounded_or_malformed_payloads(
    isolated_db,
) -> None:
    init_db(quiet=True)
    service = AttentionService()
    invalid_requests = [
        {
            "target": "default",
            "configuration": {"prompt": "classify project"},
        },
        {
            "target": "project_override",
            "project_id": "Project Display Name",
            "configuration": {"jira_grade_mapping": {"YELLOW": "red"}},
        },
        {
            "target": "project_override",
            "project_id": "project-770001",
            "configuration": {"sql": "SELECT 1"},
        },
        {
            "target": "project_override",
            "project_id": "project-770001",
            "configuration": {"jira_grade_mapping": {"yellow": "red"}},
        },
        {
            "target": "project_override",
            "project_id": "project-770001",
            "configuration": {},
        },
    ]

    for request in invalid_requests:
        assert service.preview_project_health_rag_configuration(
            actor="manager-770001",
            **request,
        ) == {
            "status": "failed",
            "failure_code": "ATTENTION_RAG_CONFIG_INVALID",
        }
    with sqlite3.connect(isolated_db) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM attention_configuration_operations"
        ).fetchone()[0] == 0
    assert _current_rule(isolated_db)[0] == "project-health-attention-v2"


def test_rag_configuration_stale_preview_fails_without_overwrite(
    isolated_db,
) -> None:
    init_db(quiet=True)
    service = AttentionService()
    first = service.preview_project_health_rag_configuration(
        actor="manager-770001",
        target="project_override",
        project_id="project-770001",
        configuration={"jira_grade_mapping": {"YELLOW": "red"}},
    )
    second = service.preview_project_health_rag_configuration(
        actor="manager-770002",
        target="project_override",
        project_id="project-770002",
        configuration={"confluence_rag_mapping": {"YELLOW": "red"}},
    )

    assert _confirm(service, first)["status"] == "success"
    assert _confirm(service, second) == {
        "status": "failed",
        "failure_code": "ATTENTION_CONFIGURATION_STALE",
    }
    version, parameters = _current_rule(isolated_db)
    assert version == "project-health-attention-v3"
    assert set(parameters["project_overrides"]) == {"project-770001"}
    with sqlite3.connect(isolated_db) as connection:
        second_status = connection.execute(
            """
            SELECT status, failure_code
            FROM attention_configuration_operations
            WHERE operation_id = ?
            """,
            [second["operation_id"]],
        ).fetchone()
        versions = connection.execute(
            """
            SELECT rule_version FROM attention_rules
            WHERE rule_key = 'project_health_attention'
            ORDER BY rule_version
            """
        ).fetchall()
    assert second_status == ("failed", "ATTENTION_CONFIGURATION_STALE")
    assert versions == [
        ("project-health-attention-v2",),
        ("project-health-attention-v3",),
    ]


def test_rag_configuration_token_is_one_time_and_invalid_token_does_not_claim(
    isolated_db,
) -> None:
    init_db(quiet=True)
    service = AttentionService()
    preview = service.preview_project_health_rag_configuration(
        actor="manager-770001",
        target="project_override",
        project_id="project-770001",
        configuration={"jira_grade_mapping": {"YELLOW": "red"}},
    )

    assert service.confirm(
        operation_id=preview["operation_id"],
        confirmation_token="synthetic-invalid-token",
    ) == {
        "status": "failed",
        "failure_code": "ATTENTION_CONFIRMATION_INVALID",
    }
    assert _confirm(service, preview)["status"] == "success"
    assert service.confirm(
        operation_id=preview["operation_id"],
        confirmation_token=preview["confirmation_token"],
    ) == {
        "status": "failed",
        "failure_code": "ATTENTION_OPERATION_ALREADY_USED",
    }


def test_rag_configuration_expired_preview_cannot_create_version(
    isolated_db,
) -> None:
    init_db(quiet=True)
    service = AttentionService()
    preview = service.preview_project_health_rag_configuration(
        actor="manager-770001",
        target="project_override",
        project_id="project-770001",
        configuration={"jira_grade_mapping": {"YELLOW": "red"}},
    )
    expired_at = (
        datetime.now(timezone.utc) - timedelta(seconds=1)
    ).isoformat(timespec="seconds")
    with sqlite3.connect(isolated_db) as connection:
        connection.execute(
            """
            UPDATE attention_configuration_operations
            SET expires_at = ?
            WHERE operation_id = ?
            """,
            [expired_at, preview["operation_id"]],
        )

    assert _confirm(service, preview) == {
        "status": "failed",
        "failure_code": "ATTENTION_CONFIRMATION_EXPIRED",
    }
    assert _current_rule(isolated_db)[0] == "project-health-attention-v2"
    with sqlite3.connect(isolated_db) as connection:
        assert connection.execute(
            """
            SELECT status FROM attention_configuration_operations
            WHERE operation_id = ?
            """,
            [preview["operation_id"]],
        ).fetchone()[0] == "expired"


def test_rag_configuration_concurrent_confirmation_applies_once(
    isolated_db,
) -> None:
    init_db(quiet=True)
    service = AttentionService()
    preview = service.preview_project_health_rag_configuration(
        actor="manager-770001",
        target="project_override",
        project_id="project-770001",
        configuration={"jira_grade_mapping": {"YELLOW": "red"}},
    )

    def confirm_once() -> dict:
        return service.confirm(
            operation_id=preview["operation_id"],
            confirmation_token=preview["confirmation_token"],
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: confirm_once(), range(2)))

    assert sorted(result["status"] for result in results) == [
        "failed",
        "success",
    ]
    assert {
        result.get("failure_code")
        for result in results
        if result["status"] == "failed"
    } == {"ATTENTION_OPERATION_ALREADY_USED"}
    with sqlite3.connect(isolated_db) as connection:
        assert connection.execute(
            """
            SELECT COUNT(*) FROM attention_rules
            WHERE rule_key = 'project_health_attention'
            """
        ).fetchone()[0] == 2
        assert connection.execute(
            """
            SELECT COUNT(*) FROM attention_rules
            WHERE rule_key = 'project_health_attention' AND is_current = 1
            """
        ).fetchone()[0] == 1


def test_rag_configuration_write_failure_rolls_back_rule_version(
    isolated_db,
) -> None:
    init_db(quiet=True)
    service = AttentionService()
    preview = service.preview_project_health_rag_configuration(
        actor="manager-770001",
        target="project_override",
        project_id="project-770001",
        configuration={"jira_grade_mapping": {"YELLOW": "red"}},
    )
    with sqlite3.connect(isolated_db) as connection:
        connection.execute(
            """
            CREATE TRIGGER synthetic_rag_version_failure
            BEFORE INSERT ON attention_rules
            WHEN NEW.rule_version = 'project-health-attention-v3'
            BEGIN
                SELECT RAISE(ABORT, 'synthetic failure');
            END
            """
        )

    assert _confirm(service, preview) == {
        "status": "failed",
        "failure_code": "DATA_ACCESS_FAILED",
    }
    assert _current_rule(isolated_db)[0] == "project-health-attention-v2"
    with sqlite3.connect(isolated_db) as connection:
        operation = connection.execute(
            """
            SELECT status, failure_code
            FROM attention_configuration_operations
            WHERE operation_id = ?
            """,
            [preview["operation_id"]],
        ).fetchone()
        assert operation == ("failed", "DATA_ACCESS_FAILED")
        assert connection.execute(
            """
            SELECT COUNT(*) FROM attention_rules
            WHERE rule_key = 'project_health_attention'
            """
        ).fetchone()[0] == 1


def test_rag_configuration_cli_and_dashboard_use_exact_attention_boundary(
    isolated_db,
) -> None:
    init_db(quiet=True)
    runner = CliRunner()
    configuration = {"jira_grade_mapping": {"YELLOW": "red"}}
    cli_preview = runner.invoke(
        app_module.app,
        [
            "attention",
            "rag-config-preview",
            "--target",
            "project_override",
            "--project-id",
            "project-770001",
            "--configuration-json",
            json.dumps(configuration),
        ],
    )
    assert cli_preview.exit_code == 0, cli_preview.output
    cli_payload = json.loads(cli_preview.output)
    assert cli_payload["status"] == "proposed"
    assert cli_payload["actor"] == "copilot"
    assert cli_payload["proposed"]["reconciliation_required"] is True

    malformed = runner.invoke(
        app_module.app,
        [
            "attention",
            "rag-config-preview",
            "--target",
            "project_override",
            "--project-id",
            "project-770002",
            "--configuration-json",
            "{not-json}",
        ],
    )
    assert malformed.exit_code == 2
    assert json.loads(malformed.output) == {
        "status": "failed",
        "failure_code": "ATTENTION_RAG_CONFIG_INVALID",
    }

    client = dashboard_server.app.test_client()
    rejected_actor = client.post(
        "/api/attention/operations",
        json={
            "operation": "preview",
            "action": "configure-project-health-rag",
            "actor": "caller-supplied",
            "target": "project_override",
            "project_id": "project-770002",
            "configuration": configuration,
        },
    )
    assert rejected_actor.status_code == 400
    assert rejected_actor.get_json()["failure_code"] == (
        "ATTENTION_RAG_CONFIG_INVALID"
    )

    preview = client.post(
        "/api/attention/operations",
        json={
            "operation": "preview",
            "action": "configure-project-health-rag",
            "target": "project_override",
            "project_id": "project-770002",
            "configuration": configuration,
        },
    )
    payload = preview.get_json()
    assert preview.status_code == 200
    assert preview.headers["X-DM-Interface-Contract"] == (
        "attention-operation-v1"
    )
    assert payload["actor"] == "dashboard-local-user"

    confirm = client.post(
        "/api/attention/operations",
        json={
            "operation": "confirm",
            "operation_id": payload["operation_id"],
            "confirmation_token": payload["confirmation_token"],
        },
    )
    assert confirm.status_code == 200
    assert confirm.get_json()["reconciliation_required"] is True


def test_rag_configuration_preserves_management_attention_contract(
    isolated_db,
) -> None:
    init_db(quiet=True)
    service = AttentionService()
    before = use_case_executor.execute(
        UseCaseRequest(
            use_case_id="management-attention",
            parameters={"limit": 20},
        )
    )
    preview = service.preview_project_health_rag_configuration(
        actor="manager-770001",
        target="project_override",
        project_id="project-770001",
        configuration={"jira_grade_mapping": {"YELLOW": "red"}},
    )
    assert _confirm(service, preview)["status"] == "success"
    after = use_case_executor.execute(
        UseCaseRequest(
            use_case_id="management-attention",
            parameters={"limit": 20},
        )
    )

    assert after.status == before.status
    assert after.data == before.data
    assert {
        key: value
        for key, value in after.context.items()
        if key != "execution_metadata"
    } == {
        key: value
        for key, value in before.context.items()
        if key != "execution_metadata"
    }
    assert after.facts == before.facts
    assert after.signals == before.signals
    assert after.recommendations == before.recommendations
    assert after.warnings == before.warnings
