from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from pm_agent.database.bootstrap import main as init_db
from pm_agent.project_health.configuration import confirm, preview
from pm_agent.project_health.evaluation import evaluate


def _project(db: Path) -> None:
    with sqlite3.connect(db) as conn:
        conn.execute("INSERT INTO projects (id,name) VALUES ('project-synthetic-b','Synthetic B')")


def _parameters(*, tolerance: int = 0, scope_minimum: int = 100) -> dict[str, int]:
    return {
        "critical_milestone_tolerance_days": tolerance,
        "scope_completion_green_minimum": scope_minimum,
    }


def test_configuration_preview_confirm_replay_and_project_validation(isolated_db: Path) -> None:
    init_db(quiet=True)
    _project(isolated_db)
    proposed = preview(parameters=_parameters(tolerance=3), project_id="project-synthetic-b", db_path=isolated_db)
    confirmed = confirm(proposed["operation_id"], proposed["confirmation_token"], db_path=isolated_db)
    assert confirmed["status"] == "confirmed"
    assert confirm(proposed["operation_id"], proposed["confirmation_token"], db_path=isolated_db)["idempotent"]
    assert confirmed["effective"] == _parameters(tolerance=3)
    assert preview(parameters=_parameters(tolerance=3), project_id="project-synthetic-b", db_path=isolated_db)["status"] == "no_op"
    with pytest.raises(ValueError, match="PROJECT_NOT_FOUND"):
        preview(parameters=_parameters(tolerance=1), project_id="missing", db_path=isolated_db)
    with pytest.raises(ValueError, match="HEALTH_CONFIGURATION_INVALID"):
        preview(parameters={"arbitrary_expression": "x"}, db_path=isolated_db)


def test_configuration_rejects_stale_and_expired_preview_without_new_version(isolated_db: Path) -> None:
    init_db(quiet=True)
    first = preview(parameters=_parameters(tolerance=1), db_path=isolated_db)
    second = preview(parameters=_parameters(tolerance=2), db_path=isolated_db)
    assert confirm(second["operation_id"], second["confirmation_token"], db_path=isolated_db)["status"] == "confirmed"
    assert confirm(first["operation_id"], first["confirmation_token"], db_path=isolated_db) == {"status": "rejected", "reason": "STALE_FINGERPRINT"}
    expired = preview(parameters=_parameters(tolerance=3), db_path=isolated_db)
    with sqlite3.connect(isolated_db) as conn:
        conn.execute("UPDATE project_health_configuration_changes SET expires_at='2000-01-01T00:00:00+00:00' WHERE operation_id=?", [expired["operation_id"]])
    assert confirm(expired["operation_id"], expired["confirmation_token"], db_path=isolated_db) == {"status": "expired"}
    with sqlite3.connect(isolated_db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM project_health_configuration_versions WHERE is_current=1").fetchone()[0] == 1


def test_configuration_confirmation_is_atomic_under_replay_race(isolated_db: Path) -> None:
    init_db(quiet=True)
    proposed = preview(parameters=_parameters(tolerance=4), db_path=isolated_db)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(
            lambda _: confirm(proposed["operation_id"], proposed["confirmation_token"], db_path=isolated_db),
            range(2),
        ))
    assert {result["status"] for result in results} == {"confirmed"}
    assert sum(bool(result.get("idempotent")) for result in results) == 1
    with sqlite3.connect(isolated_db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM project_health_configuration_versions").fetchone()[0] == 1


def test_project_evaluation_uses_current_default_until_override_is_confirmed(isolated_db: Path) -> None:
    init_db(quiet=True)
    _project(isolated_db)
    default = preview(parameters=_parameters(scope_minimum=80), db_path=isolated_db)
    default_version = confirm(default["operation_id"], default["confirmation_token"], db_path=isolated_db)["configuration_version_id"]
    result = evaluate("project-synthetic-b", db_path=isolated_db)
    assert result["configuration_version_id"] == default_version
    assert preview(parameters=_parameters(scope_minimum=80), project_id="project-synthetic-b", db_path=isolated_db)["status"] == "no_op"
    override = preview(parameters=_parameters(scope_minimum=90), project_id="project-synthetic-b", db_path=isolated_db)
    override_version = confirm(override["operation_id"], override["confirmation_token"], db_path=isolated_db)["configuration_version_id"]
    assert evaluate("project-synthetic-b", db_path=isolated_db)["configuration_version_id"] == override_version


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
        assert conn.execute("SELECT COUNT(*) FROM project_health_factor_results").fetchone()[0] == 9
        evidence = conn.execute("SELECT evidence_json FROM project_health_factor_results WHERE factor_id='schedule_critical_milestone_adherence'").fetchone()[0]
        assert "CRITICAL_MILESTONE_OVERDUE" in evidence


def test_assessment_compares_stored_legacy_grade_without_changing_it(isolated_db: Path) -> None:
    init_db(quiet=True)
    _project(isolated_db)
    with sqlite3.connect(isolated_db) as conn:
        conn.execute("INSERT INTO jira_board_configs (id,name,project_key,base_jql,pm_project_id,active) VALUES ('board-b','Synthetic','SYN','project=SYN','project-synthetic-b',1)")
        conn.execute("INSERT INTO jira_health_snapshots (board_id,snapshot_date,overall_grade) VALUES ('board-b','2026-01-01','AMBER')")
    result = evaluate("project-synthetic-b", db_path=isolated_db)
    assert result["legacy_comparison"] == {"states": ["amber"], "state": "available"}
    with sqlite3.connect(isolated_db) as conn:
        assert '"states":["amber"]' in conn.execute("SELECT legacy_comparison_json FROM project_health_assessment_details").fetchone()[0]


def test_canonical_scope_and_dependency_facts_are_reflected_fail_closed(isolated_db: Path) -> None:
    init_db(quiet=True)
    _project(isolated_db)
    with sqlite3.connect(isolated_db) as conn:
        conn.execute("INSERT INTO execution_derivation_runs VALUES ('run-b','project-synthetic-b','board-b','v1','fingerprint-b','complete','fresh','[]',0,'2026-01-01T00:00:00+00:00','2026-01-01T00:00:01+00:00')")
        conn.execute("INSERT INTO execution_facts VALUES ('fact-scope','run-b','project-synthetic-b','release','release-b','release_scope_count','{\"total\":1,\"done\":1}','known','fresh','{}')")
        conn.execute("INSERT INTO execution_facts VALUES ('fact-dependency','run-b','project-synthetic-b','dependency','dependency-b','dependency_readiness','{\"state\":\"active\"}','known','fresh','{}')")
    result = evaluate("project-synthetic-b", db_path=isolated_db)
    assert result["dimensions"]["scope"] == "green"
    assert result["dimensions"]["dependency"] == "unknown"


def test_partial_or_stale_canonical_fact_never_implies_green(isolated_db: Path) -> None:
    init_db(quiet=True)
    _project(isolated_db)
    with sqlite3.connect(isolated_db) as conn:
        conn.execute("INSERT INTO execution_derivation_runs VALUES ('run-partial','project-synthetic-b','board-b','v1','fingerprint-partial','complete','partial','[]',0,'2026-01-01T00:00:00+00:00','2026-01-01T00:00:01+00:00')")
        conn.execute("INSERT INTO execution_facts VALUES ('fact-partial','run-partial','project-synthetic-b','release','release-b','release_scope_count','{\"total\":1,\"done\":1}','known','partial','{}')")
    result = evaluate("project-synthetic-b", db_path=isolated_db)
    assert result["dimensions"]["scope"] == "unknown"
    with sqlite3.connect(isolated_db) as conn:
        evidence = conn.execute("SELECT evidence_json FROM project_health_factor_results WHERE factor_id='scope_release_readiness'").fetchone()[0]
    assert '"state":"unknown"' in evidence
