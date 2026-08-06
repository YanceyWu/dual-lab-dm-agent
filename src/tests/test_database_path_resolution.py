from __future__ import annotations

from pathlib import Path

import pytest

from pm_agent.config import get_database_path, settings
from pm_agent.dashboard import server as dashboard_server
from pm_agent.sync.jira import health_sync


def test_database_path_is_resolved_at_call_time(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = tmp_path / "first.db"
    second = tmp_path / "second.db"

    monkeypatch.setattr(settings, "database_path", str(first))
    assert get_database_path() == first.resolve()

    monkeypatch.setattr(settings, "database_path", str(second))
    assert get_database_path() == second.resolve()


def test_dashboard_connection_honors_setting_changed_after_import(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected = tmp_path / "dashboard.db"
    monkeypatch.setattr(settings, "database_path", str(selected))
    monkeypatch.setattr(dashboard_server, "DB", None)

    connection = dashboard_server.db()
    try:
        connection.execute("CREATE TABLE selected_path_test (id INTEGER)")
        connection.commit()
    finally:
        connection.close()

    assert selected.exists()


def test_database_consumers_share_call_time_resolver() -> None:
    assert dashboard_server.get_database_path is get_database_path
    assert health_sync.get_database_path is get_database_path
