from __future__ import annotations

import inspect
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from pm_agent.dashboard import server as dashboard_server
from pm_agent.cli.commands.dashboard import dashboard_serve
from pm_agent.database.bootstrap import main as init_db


def _insert_board(con: sqlite3.Connection, board_id: str, name: str) -> None:
    con.execute(
        """
        INSERT INTO jira_board_configs
            (id, name, project_key, base_jql, active)
        VALUES (?, ?, 'ATL', 'project = ATL', 1)
        """,
        [board_id, name],
    )


def _insert_data_source(con: sqlite3.Connection, source_id: str) -> None:
    con.execute(
        """
        INSERT INTO data_sources
            (id, source_type, source_name, ingestion_mode, refresh_sla_hours, active, config_json, notes)
        VALUES (?, 'jira', ?, 'api', 24, 1, '{}', '')
        """,
        [source_id, source_id],
    )


def test_dashboard_defaults_to_loopback_only(monkeypatch: pytest.MonkeyPatch) -> None:
    started: dict[str, object] = {}
    monkeypatch.setattr(dashboard_server.app, "run", lambda **kwargs: started.update(kwargs))

    dashboard_server.serve()

    assert started["host"] == "127.0.0.1"
    assert inspect.signature(dashboard_serve).parameters["host"].default.default == "127.0.0.1"


def test_project_health_sync_endpoint_triggers_release_and_health_for_one_board(
    isolated_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    init_db(quiet=True)
    con = sqlite3.connect(isolated_db)
    try:
        _insert_board(con, "atlas-board", "Atlas Board")
        con.commit()
    finally:
        con.close()

    monkeypatch.setattr(dashboard_server, "DB", str(isolated_db))
    calls: list[tuple[str, str, bool]] = []
    monkeypatch.setattr(
        dashboard_server.jira_connector,
        "sync_releases",
        lambda board="", project="", dry_run=False: calls.append(("release", board, dry_run)),
    )
    monkeypatch.setattr(
        dashboard_server.jira_connector,
        "sync_health",
        lambda board=None, dry_run=False: calls.append(("health", board or "", dry_run)),
    )

    client = dashboard_server.app.test_client()
    response = client.post("/api/project-health/sync", json={"board_id": "atlas-board"})

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert "Atlas Board" in payload["message"]
    assert calls == [
        ("release", "atlas-board", False),
        ("health", "atlas-board", False),
    ]


def test_project_health_sync_endpoint_targets_only_stale_boards(
    isolated_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    init_db(quiet=True)
    con = sqlite3.connect(isolated_db)
    try:
        _insert_board(con, "stale-board", "Stale Board")
        _insert_board(con, "fresh-board", "Fresh Board")
        _insert_data_source(con, "jira-release-stale-board")
        _insert_data_source(con, "jira-health-stale-board")
        _insert_data_source(con, "jira-release-fresh-board")
        _insert_data_source(con, "jira-health-fresh-board")
        fresh_finished_at = datetime.now().replace(microsecond=0)
        fresh_started_at = fresh_finished_at - timedelta(minutes=1)
        con.executemany(
            """
            INSERT INTO sync_runs
                (id, source_id, run_type, started_at, finished_at, status, rows_in, rows_changed, target_tables_json, notes)
            VALUES (?, ?, 'incremental', ?, ?, 'success', 1, 1, '[]', '')
            """,
            [
                (
                    "run-release-fresh",
                    "jira-release-fresh-board",
                    fresh_started_at.isoformat(sep=" "),
                    fresh_finished_at.isoformat(sep=" "),
                ),
                (
                    "run-health-fresh",
                    "jira-health-fresh-board",
                    fresh_started_at.isoformat(sep=" "),
                    fresh_finished_at.isoformat(sep=" "),
                ),
            ],
        )
        con.commit()
    finally:
        con.close()

    monkeypatch.setattr(dashboard_server, "DB", str(isolated_db))
    calls: list[tuple[str, str, bool]] = []
    monkeypatch.setattr(
        dashboard_server.jira_connector,
        "sync_releases",
        lambda board="", project="", dry_run=False: calls.append(("release", board, dry_run)),
    )
    monkeypatch.setattr(
        dashboard_server.jira_connector,
        "sync_health",
        lambda board=None, dry_run=False: calls.append(("health", board or "", dry_run)),
    )

    client = dashboard_server.app.test_client()
    response = client.post("/api/project-health/sync", json={"stale_only": True})

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert calls == [
        ("release", "stale-board", False),
        ("health", "stale-board", False),
    ]
