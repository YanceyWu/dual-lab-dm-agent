from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from pm_agent.database.bootstrap import main as init_db
from pm_agent.project_health.configuration import confirm, preview
from pm_agent.project_health.evaluation import evaluate


def _project(db: Path) -> None:
    with sqlite3.connect(db) as conn:
        conn.execute("INSERT INTO projects (id,name) VALUES ('project-synthetic-b','Synthetic B')")


def test_configuration_preview_confirm_replay_and_project_validation(isolated_db: Path) -> None:
    init_db(quiet=True)
    _project(isolated_db)
    proposed = preview(parameters={"critical_milestone_tolerance_days": 3}, project_id="project-synthetic-b", db_path=isolated_db)
    confirmed = confirm(proposed["operation_id"], proposed["confirmation_token"], db_path=isolated_db)
    assert confirmed["status"] == "confirmed"
    assert confirm(proposed["operation_id"], proposed["confirmation_token"], db_path=isolated_db)["idempotent"]
    assert preview(parameters={"critical_milestone_tolerance_days": 3}, project_id="project-synthetic-b", db_path=isolated_db)["status"] == "no_op"
    with pytest.raises(ValueError, match="PROJECT_NOT_FOUND"):
        preview(parameters={"critical_milestone_tolerance_days": 1}, project_id="missing", db_path=isolated_db)


def test_critical_overdue_milestone_is_not_averaged_away(isolated_db: Path) -> None:
    init_db(quiet=True)
    _project(isolated_db)
    with sqlite3.connect(isolated_db) as conn:
        conn.execute("""INSERT INTO execution_milestones
          (milestone_id,project_id,milestone_type,criticality,lifecycle_state,planned_date,authority,completeness_state,observed_at,schema_version)
          VALUES ('milestone-synthetic-b','project-synthetic-b','release','critical','in_progress','2020-01-01','synthetic','known','2026-01-01T00:00:00+00:00','synthetic-v1')""")
    result = evaluate("project-synthetic-b", db_path=isolated_db)
    assert result["dimensions"]["schedule"] == "red"
    assert result["overall_state"] == "red"
    with sqlite3.connect(isolated_db) as conn:
        assert conn.execute("SELECT state FROM project_health_assessment_runs").fetchone()[0] == "red"
