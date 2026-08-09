from __future__ import annotations

from pathlib import Path
import os
import shutil
import subprocess
import sys

import pytest

from pm_agent.config import PROJECT_ROOT, Settings, get_database_path, settings
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


def test_settings_loads_the_runtime_root_env_file_not_the_caller_cwd() -> None:
    assert Settings.model_config["env_file"] == PROJECT_ROOT / ".env"


def test_bundle_root_and_src_cwd_share_env_with_process_env_precedence(tmp_path: Path) -> None:
    """A staged runtime reads src/.env regardless of invocation cwd."""
    runtime = tmp_path / "bundle" / "src"
    shutil.copytree(PROJECT_ROOT / "pm_agent", runtime / "pm_agent")
    (runtime / ".env").write_text("DATABASE_PATH=selected.db\n", encoding="utf-8")
    code = "from pm_agent.config import get_database_path; print(get_database_path())"
    base_env = {key: value for key, value in os.environ.items() if key != "DATABASE_PATH"}
    base_env["PYTHONPATH"] = str(runtime)
    root_result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=runtime.parent,
        env=base_env,
        text=True,
        capture_output=True,
        check=True,
    )
    src_result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=runtime,
        env=base_env,
        text=True,
        capture_output=True,
        check=True,
    )
    selected = (runtime / "selected.db").resolve()
    override = tmp_path / "override.db"
    override_result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=runtime.parent,
        env={**base_env, "DATABASE_PATH": str(override)},
        text=True,
        capture_output=True,
        check=True,
    )
    assert root_result.stdout.strip() == str(selected)
    assert src_result.stdout.strip() == str(selected)
    assert override_result.stdout.strip() == str(override.resolve())


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
