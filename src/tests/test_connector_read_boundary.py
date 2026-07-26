from __future__ import annotations

import json
import sqlite3
import time

from typer.testing import CliRunner

from pm_agent.cli import app as app_module
from pm_agent.connectors import registry
from pm_agent.connectors import jira
from pm_agent.connectors.base import ConnectorValidationResult
from pm_agent.connectors.shared import AtlassianAuthError, atlassian
from pm_agent.database.bootstrap import main as init_db
from pm_agent.use_cases import use_case_executor
from pm_agent.use_cases.service import UseCaseRequest


def test_connector_status_review_is_offline_and_does_not_validate_runtime(
    isolated_db,
    monkeypatch,
) -> None:
    init_db(quiet=True)
    with sqlite3.connect(isolated_db) as con:
        con.execute(
            """INSERT INTO data_sources
               (id, source_type, source_name, refresh_sla_hours, active)
               VALUES ('jira-health-atlas', 'jira', 'Atlas health', 24, 1)"""
        )
        con.execute(
            """INSERT INTO sync_runs
               (id, source_id, run_type, started_at, finished_at, status)
               VALUES ('run-jira-local', 'jira-health-atlas', 'incremental',
                       '2026-07-26T10:00:00', '2026-07-26T10:01:00', 'success')"""
        )

    def fail_if_runtime_validation_runs(*_args, **_kwargs):
        raise AssertionError("offline status must not inspect runtime validation")

    monkeypatch.setattr(registry, "validate_connectors", fail_if_runtime_validation_runs)
    monkeypatch.setattr(atlassian, "_load_tokens", fail_if_runtime_validation_runs)
    monkeypatch.setattr(atlassian, "_save_tokens", fail_if_runtime_validation_runs)

    result = use_case_executor.execute(
        UseCaseRequest(
            use_case_id="connector-status-review",
            parameters={"connector": "jira"},
        )
    )

    assert result.status == "success"
    assert result.data["connectors"][0]["ready"] is None
    assert result.data["connectors"][0]["runtime_probe_state"] == "not_performed"
    assert result.data["connectors"][0]["auth_mode"] == "not_inspected"
    serialized = json.dumps(result.model_dump(), sort_keys=True)
    assert "token_source" not in serialized
    assert "base_url" not in serialized

    cli = CliRunner().invoke(
        app_module.app,
        ["connector", "status"],
        terminal_width=200,
    )
    assert cli.exit_code == 0, cli.output
    assert "Ready" in cli.output


def test_safe_probe_result_redacts_validation_details_and_raw_errors(
    monkeypatch,
) -> None:
    validation = ConnectorValidationResult(
        name="jira",
        display_name="JIRA",
        enabled=True,
        ready=False,
        auth_mode="atlassian_oauth",
        details={
            "base_url": "https://internal.example.invalid",
            "token_source": "/private/token.json",
            "token_refreshed": "yes",
        },
        warnings=["Synthetic local path warning"],
        errors=["Synthetic confidential authentication error"],
    )
    monkeypatch.setattr(
        registry,
        "validate_connectors",
        lambda name=None: [validation],
    )

    result = registry.probe_connectors(name="jira")[0]
    serialized = json.dumps(result.__dict__, sort_keys=True)

    assert result.token_refreshed is True
    assert "OAUTH_TOKEN_AUTO_REFRESHED" in result.warning_codes
    assert result.error_codes == ["RUNTIME_PROBE_FAILED"]
    assert "internal.example.invalid" not in serialized
    assert "private/token" not in serialized
    assert "confidential" not in serialized


def test_connector_probe_cli_reports_automatic_token_refresh_without_details(
    monkeypatch,
) -> None:
    validation = ConnectorValidationResult(
        name="jira",
        display_name="JIRA",
        enabled=True,
        ready=True,
        auth_mode="atlassian_oauth",
        details={
            "resolved_base_url": "https://internal.example.invalid",
            "token_source": "/private/token.json",
            "token_refreshed": "yes",
        },
    )
    monkeypatch.setattr(
        registry,
        "validate_connectors",
        lambda name=None: [validation],
    )

    command = CliRunner().invoke(
        app_module.app,
        ["connector", "probe", "jira"],
    )

    assert command.exit_code == 0, command.output
    payload = json.loads(command.output)
    assert payload["status"] == "success"
    assert payload["probes"][0]["token_refreshed"] is True
    assert "OAUTH_TOKEN_AUTO_REFRESHED" in payload["probes"][0]["warning_codes"]
    assert "internal.example.invalid" not in command.output
    assert "private/token" not in command.output


def test_probe_reports_refresh_even_when_later_runtime_check_fails(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        jira,
        "_effective_config",
        lambda: {
            "enabled": True,
            "base_url": "https://atlas.example.invalid",
            "auth_mode": "atlassian_oauth",
        },
    )

    def refresh_then_fail(*_args, refresh_observer=None, **_kwargs):
        assert refresh_observer is not None
        refresh_observer()
        raise AtlassianAuthError("synthetic confidential failure")

    monkeypatch.setattr(jira, "get_auth_session", refresh_then_fail)

    validation = jira.validate_connector()
    safe = registry._safe_probe_result(validation)

    assert validation.ready is False
    assert validation.details["token_refreshed"] == "yes"
    assert safe.token_refreshed is True
    assert safe.error_codes == ["RUNTIME_PROBE_FAILED"]
    assert "confidential" not in json.dumps(safe.__dict__)


def test_expired_oauth_token_is_refreshed_and_reported(
    tmp_path,
    monkeypatch,
) -> None:
    tokens = {
        "access_token": "old-access",
        "refresh_token": "refresh",
        "obtained_at": 1,
        "expires_in": 1,
        "accessible_resources": [
            {
                "id": "cloud-990001",
                "url": "https://atlas.example.invalid",
            }
        ],
    }
    refresh_calls = []
    refresh_observations = []
    saved_tokens = []

    class FakeResponse:
        status_code = 200

        @staticmethod
        def raise_for_status():
            return None

    class FakeSession:
        def __init__(self):
            self.verify = True
            self.headers = {}

        @staticmethod
        def get(*_args, **_kwargs):
            return FakeResponse()

    def refresh(*_args, **_kwargs):
        refresh_calls.append(True)
        return {
            "access_token": "new-access",
            "expires_in": 3600,
            "obtained_at": time.time(),
        }

    def save(updated):
        saved_tokens.append(dict(updated))
        return tmp_path / "tokens.json"

    monkeypatch.setattr(atlassian, "_refresh_access_token", refresh)
    monkeypatch.setattr(
        atlassian,
        "_fetch_accessible_resources",
        lambda *_args, **_kwargs: tokens["accessible_resources"],
    )
    monkeypatch.setattr(atlassian, "_save_tokens", save)
    monkeypatch.setattr(atlassian.requests, "Session", FakeSession)

    auth = atlassian._build_oauth_session(
        "jira",
        "https://atlas.example.invalid",
        True,
        "cloud-990001",
        "client",
        "secret",
        "refresh",
        tokens,
        tmp_path / "tokens.json",
        lambda: refresh_observations.append(True),
    )

    assert refresh_calls == [True]
    assert refresh_observations == [True]
    assert saved_tokens
    assert saved_tokens[-1]["access_token"] == "new-access"
    assert auth.token_refreshed is True
    assert auth.session.headers["Authorization"] == "Bearer new-access"
