from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from pm_agent.database.bootstrap import main as init_db
from pm_agent.project_health.service import catalog_projection, confirm_reimport, preview_reimport


def _package() -> dict[str, object]:
    return {"package_id": "phase4-synthetic-package-001", "schema_version": "project-health-reimport-v1", "inputs": []}


def test_clean_bootstrap_seeds_fixed_catalog_and_no_mutable_configuration(isolated_db: Path) -> None:
    init_db(quiet=True)
    projection = catalog_projection(db_path=isolated_db)
    assert [item["dimension"] for item in projection["factors"]] == [
        "delivery", "delivery", "dependency", "governance", "quality", "resource", "schedule", "schedule", "scope",
    ]
    assert projection["override_state"] == "not_available"
    assert projection["configuration_mutation"] == "not_available"
    with sqlite3.connect(isolated_db) as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"project_health_factor_catalog", "project_health_default_conditions", "project_health_input_observations", "project_health_reimport_sessions", "project_health_reimport_runs"} <= tables


def test_reimport_preview_confirm_is_audited_idempotent_and_reports_not_available(isolated_db: Path) -> None:
    init_db(quiet=True)
    with sqlite3.connect(isolated_db) as connection:
        connection.execute("INSERT INTO projects (id,name) VALUES ('project-synthetic-001','Synthetic Project')")
    preview = preview_reimport(_package(), db_path=isolated_db)
    assert preview["status"] == "previewed"
    confirmed = confirm_reimport(preview["session_id"], db_path=isolated_db)
    assert confirmed["status"] == "completed"
    assert confirmed["report"]["assessment_state"] == "not_available"
    assert confirmed["report"]["dimensions"]["project-synthetic-001"] == {
        "schedule": "unknown", "delivery": "not_available", "scope": "unknown", "quality": "not_available", "resource": "not_available", "dependency": "unknown", "governance": "not_available",
    }
    assert confirm_reimport(preview["session_id"], db_path=isolated_db)["idempotent"] is True
    assert preview_reimport(_package(), db_path=isolated_db)["status"] == "already_completed"
    with sqlite3.connect(isolated_db) as connection:
        assert connection.execute("SELECT COUNT(*) FROM project_health_reimport_runs").fetchone()[0] == 3


def test_invalid_or_unapproved_structured_input_creates_no_session(isolated_db: Path) -> None:
    init_db(quiet=True)
    with pytest.raises(ValueError, match="HEALTH_INPUT_PRODUCER_NOT_AVAILABLE"):
        preview_reimport({**_package(), "inputs": [{"input_kind": "quality_gate"}]}, db_path=isolated_db)
    with pytest.raises(ValueError, match="HEALTH_REIMPORT_PACKAGE_VERSION_INVALID"):
        preview_reimport({**_package(), "schema_version": "unknown"}, db_path=isolated_db)
    with sqlite3.connect(isolated_db) as connection:
        assert connection.execute("SELECT COUNT(*) FROM project_health_reimport_sessions").fetchone()[0] == 0


def test_catalog_project_scope_requires_existing_stable_project(isolated_db: Path) -> None:
    init_db(quiet=True)
    with pytest.raises(ValueError, match="PROJECT_NOT_FOUND"):
        catalog_projection(project_id="missing-synthetic", db_path=isolated_db)


def test_reimport_failure_is_audited_without_a_partial_coverage_view(
    isolated_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    init_db(quiet=True)
    preview = preview_reimport(_package(), db_path=isolated_db)
    monkeypatch.setattr("pm_agent.project_health.service._coverage", lambda _connection: (_ for _ in ()).throw(RuntimeError("synthetic failure")))
    with pytest.raises(RuntimeError, match="synthetic failure"):
        confirm_reimport(preview["session_id"], db_path=isolated_db)
    with sqlite3.connect(isolated_db) as connection:
        session = connection.execute("SELECT status,report_json FROM project_health_reimport_sessions").fetchone()
        run = connection.execute("SELECT status,warnings_json FROM project_health_reimport_runs").fetchone()
    assert session == ("failed", "{}")
    assert run == ("failed", '["HEALTH_REIMPORT_PARTIAL_FAILURE"]')
