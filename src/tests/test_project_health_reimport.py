from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from pm_agent.database.bootstrap import main as init_db
from pm_agent.project_health import service
from pm_agent.project_health.evaluation import evaluate
from pm_agent.project_health.service import catalog_projection, confirm_reimport, preview_reimport
from pm_agent.use_cases.layered_project_health import execute_layered_project_health_review
from pm_agent.use_cases.service import UseCaseRequest


def _package() -> dict[str, object]:
    return {"package_id": "project-health-synthetic-package-001", "schema_version": "project-health-reimport-v1", "board_ids": [], "inputs": []}


def _seed_board(db_path: Path) -> None:
    with sqlite3.connect(db_path) as connection:
        connection.execute("INSERT INTO projects (id,name) VALUES ('project-synthetic-001','Synthetic Project')")
        connection.execute("""INSERT INTO jira_board_configs
            (id,name,project_key,base_jql,pm_project_id,active)
            VALUES ('board-synthetic','Synthetic Board','SYN','project = SYN','project-synthetic-001',1)""")


def test_clean_bootstrap_seeds_fixed_catalog_and_no_mutable_configuration(isolated_db: Path) -> None:
    init_db(quiet=True)
    projection = catalog_projection(db_path=isolated_db)
    assert [item["dimension"] for item in projection["factors"]] == [
        "delivery", "delivery", "dependency", "governance", "quality", "resource", "schedule", "schedule", "scope",
    ]
    assert projection["override_state"] == "not_available"
    assert projection["configuration_mutation"] == "internal_controlled_preview_confirm"
    assert projection["effective_configuration"] == {
        "critical_milestone_tolerance_days": 0,
        "scope_completion_green_minimum": 100,
    }
    with sqlite3.connect(isolated_db) as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"project_health_factor_catalog", "project_health_default_conditions", "project_health_input_observations", "project_health_reimport_sessions", "project_health_reimport_runs", "project_health_reimport_attempts", "project_health_reimport_assessments", "project_health_configuration_operations", "project_health_assessment_runs", "project_health_dimension_results", "project_health_factor_results"} <= tables


def test_reimport_preview_confirm_runs_assessment_and_is_audited_idempotent(isolated_db: Path) -> None:
    init_db(quiet=True)
    _seed_board(isolated_db)
    preview = preview_reimport({**_package(), "board_ids": ["board-synthetic"]}, db_path=isolated_db)
    assert preview["status"] == "previewed"
    assert preview["planned_steps"] == ["validate", "canonical_derivation", "health_assessment", "health_coverage"]
    confirmed = confirm_reimport(preview["session_id"], db_path=isolated_db)
    assert confirmed["status"] == "completed"
    assert confirmed["report"]["assessment_state"] == "completed"
    assert confirmed["report"]["dimensions"]["project-synthetic-001"] == {
        "schedule": "unknown", "delivery": "not_available", "scope": "unknown", "quality": "not_available", "resource": "not_available", "dependency": "unknown", "governance": "not_available",
    }
    assert confirmed["report"]["assessments"][0]["project_id"] == "project-synthetic-001"
    assert confirmed["report"]["assessments"][0]["state"] == "unknown"
    assert confirmed["report"]["assessments"][0]["dimensions"] == confirmed["report"]["dimensions"]["project-synthetic-001"]
    assert confirmed["report"]["canonical_derivations"][0]["board_id"] == "board-synthetic"
    assert confirmed["report"]["integrity"] == {"sqlite_integrity": "ok", "foreign_key_violations": 0, "state": "passed"}
    with sqlite3.connect(isolated_db) as connection:
        assert connection.execute("SELECT COUNT(*) FROM project_health_assessment_runs").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM project_health_reimport_assessments").fetchone()[0] == 1
        health_coverage = connection.execute(
            "SELECT counts_json FROM project_health_reimport_runs WHERE step_key='health_coverage'"
        ).fetchone()[0]
    assert json.loads(health_coverage)["assessment_run_count"] == 1
    assert confirm_reimport(preview["session_id"], db_path=isolated_db)["idempotent"] is True
    assert preview_reimport({**_package(), "board_ids": ["board-synthetic"]}, db_path=isolated_db)["status"] == "already_completed"
    with sqlite3.connect(isolated_db) as connection:
        assert connection.execute("SELECT COUNT(*) FROM project_health_reimport_runs").fetchone()[0] == 3
        assert connection.execute("SELECT COUNT(*) FROM project_health_assessment_runs").fetchone()[0] == 1


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
    monkeypatch.setattr("pm_agent.project_health.service._coverage", lambda *_args: (_ for _ in ()).throw(RuntimeError("synthetic failure")))
    with pytest.raises(RuntimeError, match="synthetic failure"):
        confirm_reimport(preview["session_id"], db_path=isolated_db)
    with sqlite3.connect(isolated_db) as connection:
        session = connection.execute("SELECT status,report_json FROM project_health_reimport_sessions").fetchone()
        run = connection.execute("SELECT status,warnings_json FROM project_health_reimport_runs").fetchone()
        attempt = connection.execute("SELECT status,warning_codes_json FROM project_health_reimport_attempts").fetchone()
    assert session == ("failed", "{}")
    assert run == ("failed", '["HEALTH_REIMPORT_PARTIAL_FAILURE"]')
    assert attempt == ("failed", '["HEALTH_REIMPORT_PARTIAL_FAILURE"]')


def test_running_session_can_be_replayed_after_interruption(isolated_db: Path) -> None:
    init_db(quiet=True)
    _seed_board(isolated_db)
    package = {**_package(), "board_ids": ["board-synthetic"]}
    preview = preview_reimport(package, db_path=isolated_db)
    with sqlite3.connect(isolated_db) as connection:
        connection.execute("UPDATE project_health_reimport_sessions SET status='running' WHERE session_id=?", [preview["session_id"]])
    assert preview_reimport(package, db_path=isolated_db)["status"] == "retryable"
    replayed = confirm_reimport(preview["session_id"], db_path=isolated_db)
    assert replayed["status"] == "completed"
    with sqlite3.connect(isolated_db) as connection:
        assert connection.execute("SELECT COUNT(*) FROM project_health_reimport_attempts").fetchone()[0] == 1


def test_interrupted_reimport_replays_assessments_without_duplicates(
    isolated_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    init_db(quiet=True)
    _seed_board(isolated_db)
    preview = preview_reimport({**_package(), "board_ids": ["board-synthetic"]}, db_path=isolated_db)

    from pm_agent.project_health import evaluation as evaluation_module

    calls = {"count": 0}
    original_evaluate = evaluation_module.evaluate

    def counting_evaluate(project_id: str, **kwargs: object) -> dict[str, object]:
        calls["count"] += 1
        return original_evaluate(project_id, **kwargs)

    monkeypatch.setattr(evaluation_module, "evaluate", counting_evaluate)
    real_coverage = service._coverage
    monkeypatch.setattr(
        "pm_agent.project_health.service._coverage",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("synthetic interruption after assessment")),
    )
    with pytest.raises(RuntimeError, match="synthetic interruption"):
        confirm_reimport(preview["session_id"], db_path=isolated_db)
    assert calls["count"] == 1
    with sqlite3.connect(isolated_db) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM project_health_reimport_assessments"
        ).fetchone()[0] == 1

    monkeypatch.setattr("pm_agent.project_health.service._coverage", real_coverage)
    replayed = confirm_reimport(preview["session_id"], db_path=isolated_db)
    assert replayed["status"] == "completed"
    assert calls["count"] == 1
    with sqlite3.connect(isolated_db) as connection:
        assert connection.execute("SELECT COUNT(*) FROM project_health_assessment_runs").fetchone()[0] == 1


def test_reimport_links_assessment_left_by_crashed_attempt(
    isolated_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    init_db(quiet=True)
    _seed_board(isolated_db)
    preview = preview_reimport({**_package(), "board_ids": ["board-synthetic"]}, db_path=isolated_db)

    from pm_agent.project_health import evaluation as evaluation_module
    from pm_agent.project_health.evaluation import evaluate as run_assessment

    crashed = run_assessment("project-synthetic-001", db_path=isolated_db)
    calls = {"count": 0}
    original_evaluate = evaluation_module.evaluate

    def counting_evaluate(project_id: str, **kwargs: object) -> dict[str, object]:
        calls["count"] += 1
        return original_evaluate(project_id, **kwargs)

    monkeypatch.setattr(evaluation_module, "evaluate", counting_evaluate)
    confirmed = confirm_reimport(preview["session_id"], db_path=isolated_db)
    assert confirmed["status"] == "completed"
    assert confirmed["report"]["assessments"][0]["assessment_run_id"] == crashed["assessment_run_id"]
    assert calls["count"] == 0
    with sqlite3.connect(isolated_db) as connection:
        assert connection.execute("SELECT COUNT(*) FROM project_health_assessment_runs").fetchone()[0] == 1


def test_reimport_assessment_is_readable_through_layered_review(isolated_db: Path) -> None:
    init_db(quiet=True)
    _seed_board(isolated_db)
    preview = preview_reimport({**_package(), "board_ids": ["board-synthetic"]}, db_path=isolated_db)
    assert confirm_reimport(preview["session_id"], db_path=isolated_db)["status"] == "completed"

    result = execute_layered_project_health_review(
        UseCaseRequest(
            use_case_id="layered-project-health-review",
            parameters={"project_id": "project-synthetic-001"},
        )
    )
    assert result.status == "success"
    assert result.data["assessments"][0]["project_id"] == "project-synthetic-001"
    assert result.data["assessments"][0]["state"] == "unknown"


def test_integrity_failure_is_not_published_as_completed(isolated_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    init_db(quiet=True)
    preview = preview_reimport(_package(), db_path=isolated_db)
    monkeypatch.setattr("pm_agent.project_health.service._integrity", lambda _connection: {"sqlite_integrity": "failed", "foreign_key_violations": 1, "state": "failed"})
    result = confirm_reimport(preview["session_id"], db_path=isolated_db)
    assert result["status"] == "failed"
    assert result["report"]["integrity"]["state"] == "failed"


def test_assessment_reads_newest_derivation_when_runs_finish_same_second(
    isolated_db: Path,
) -> None:
    """A later-created derivation run must win even when its UUID sorts first."""
    init_db(quiet=True)
    _seed_board(isolated_db)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with sqlite3.connect(isolated_db) as connection:
        for run_id in ("zzz-run-old", "aaa-run-new"):
            connection.execute(
                """
                INSERT INTO execution_derivation_runs
                    (derivation_run_id, project_id, board_id, rule_version,
                     input_fingerprint, completeness_state, freshness_state,
                     started_at, finished_at)
                VALUES (?, 'project-synthetic-001', 'board-synthetic',
                        'execution-foundation-v1', ?, 'complete', 'fresh', ?, ?)
                """,
                [run_id, f"synthetic-{run_id}", now, now],
            )
        connection.execute(
            """
            INSERT INTO execution_facts
                (fact_id, derivation_run_id, project_id, subject_kind, subject_id,
                 fact_key, value_json, value_state, freshness_state, evidence_json)
            VALUES ('fact-scope-new', 'aaa-run-new', 'project-synthetic-001',
                    'release', 'release-new', 'release_scope_count',
                    '{"total": 1, "done": 1}', 'known', 'fresh', '{}')
            """
        )
    result = evaluate("project-synthetic-001", db_path=isolated_db)
    assert result["dimensions"]["scope"] == "green"
