from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from pm_agent.database import repository as legacy_repository
from pm_agent.database.bootstrap import main as init_db
from pm_agent.workforce_planning_import import repository as import_repository
from pm_agent.workforce_planning_import.service import confirm_import, preview_import

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "sample-data" / "json" / "workforce_planning_import.sample.json"


def _package() -> dict[str, object]:
    return json.loads(SAMPLE.read_text(encoding="utf-8"))


def test_clean_bootstrap_is_idempotent_and_composes_capability_schema(isolated_db: Path) -> None:
    init_db(quiet=True)
    init_db(quiet=True)
    with sqlite3.connect(isolated_db) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert {
        "workforce_planning_import_sessions",
        "workforce_planning_import_attempts",
        "workforce_planning_import_runs",
        "workforce_planning_publications",
        "workforce_member_period_coverage",
        "monthly_project_allocation_coverage",
    } <= tables


def test_preview_confirm_publishes_complete_audited_package(isolated_db: Path) -> None:
    init_db(quiet=True)
    preview = preview_import(_package(), db_path=isolated_db)
    assert preview == {
        "status": "previewed",
        "session_id": preview["session_id"],
        "idempotent": False,
        "package_fingerprint": preview["package_fingerprint"],
        "counts": {
            "members": 2,
            "projects": 1,
            "plan_versions": 1,
            "monthly_allocations": 2,
            "workforce_periods": 2,
            "allocation_keys": 2,
            "explicit_zero_allocations": 1,
        },
        "coverage": {"authoritative_manifest": True, "missing_record_count": 0},
        "confirmation_required": True,
    }

    result = confirm_import(preview["session_id"], db_path=isolated_db)
    assert result["status"] == "completed"
    assert result["idempotent"] is False
    assert result["report"]["counts"] == {
        "employees": 2,
        "projects": 1,
        "plan_versions": 1,
        "monthly_allocations": 2,
    }
    assert result["report"]["coverage"] == {
        "state": "complete",
        "authoritative_manifest": True,
        "member_count": 2,
        "project_count": 1,
        "plan_version_count": 1,
        "workforce_period_count": 2,
        "allocation_key_count": 2,
        "explicit_zero_count": 1,
        "missing_record_count": 0,
    }
    assert result["report"]["integrity"] == {
        "sqlite_integrity": "ok",
        "foreign_key_violations": 0,
        "state": "passed",
    }
    assert result["report"]["software_rollback"]["state"] == "passed"

    with sqlite3.connect(isolated_db) as connection:
        connection.row_factory = sqlite3.Row
        allocations = connection.execute(
            """
            SELECT employee_id,allocation FROM monthly_allocations
            ORDER BY employee_id
            """
        ).fetchall()
        audit = {
            "sessions": connection.execute(
                "SELECT COUNT(*) FROM workforce_planning_import_sessions"
            ).fetchone()[0],
            "attempts": connection.execute(
                "SELECT COUNT(*) FROM workforce_planning_import_attempts"
            ).fetchone()[0],
            "runs": connection.execute(
                "SELECT COUNT(*) FROM workforce_planning_import_runs"
            ).fetchone()[0],
            "coverage": connection.execute(
                "SELECT COUNT(*) FROM monthly_project_allocation_coverage"
            ).fetchone()[0],
        }
    assert [(row["employee_id"], row["allocation"]) for row in allocations] == [
        ("member-synthetic-001", 0.5),
        ("member-synthetic-002", 0.0),
    ]
    assert audit == {"sessions": 1, "attempts": 1, "runs": 4, "coverage": 2}


def test_identical_replay_is_idempotent_without_duplicate_audit_attempt(isolated_db: Path) -> None:
    init_db(quiet=True)
    first = preview_import(_package(), db_path=isolated_db)
    confirm_import(first["session_id"], db_path=isolated_db)

    replay = preview_import(_package(), db_path=isolated_db)
    assert replay["status"] == "already_completed"
    assert replay["idempotent"] is True
    confirmed = confirm_import(replay["session_id"], db_path=isolated_db)
    assert confirmed["idempotent"] is True
    with sqlite3.connect(isolated_db) as connection:
        assert connection.execute("SELECT COUNT(*) FROM monthly_allocations").fetchone()[0] == 2
        assert connection.execute(
            "SELECT COUNT(*) FROM workforce_planning_import_attempts"
        ).fetchone()[0] == 1


def test_conflicting_replay_is_rejected_and_preserves_current_publication(isolated_db: Path) -> None:
    init_db(quiet=True)
    package = _package()
    first = preview_import(package, db_path=isolated_db)
    first_result = confirm_import(first["session_id"], db_path=isolated_db)

    conflict = deepcopy(package)
    conflict["monthly_allocations"][0]["allocation"] = 0.75
    rejected = preview_import(conflict, db_path=isolated_db)
    assert rejected["status"] == "rejected"
    assert rejected["failure_code"] == "WORKFORCE_PLANNING_PACKAGE_REPLAY_CONFLICT"
    with pytest.raises(ValueError, match="SESSION_NOT_CONFIRMABLE"):
        confirm_import(rejected["session_id"], db_path=isolated_db)

    with sqlite3.connect(isolated_db) as connection:
        current = connection.execute(
            """
            SELECT package_fingerprint FROM workforce_planning_publications
            WHERE is_current=1
            """
        ).fetchone()[0]
        allocation = connection.execute(
            """
            SELECT allocation FROM monthly_allocations
            WHERE employee_id='member-synthetic-001'
            """
        ).fetchone()[0]
        rejected_attempts = connection.execute(
            """
            SELECT COUNT(*) FROM workforce_planning_import_attempts
            WHERE session_id=?
            """,
            [rejected["session_id"]],
        ).fetchone()[0]
    assert first_result["report"]["publication_id"].startswith(
        "workforce-planning-publication-"
    )
    assert current == first["package_fingerprint"]
    assert allocation == 0.5
    assert rejected_attempts == 0


@pytest.mark.parametrize(
    ("mutate", "error_code"),
    [
        (
            lambda package: package["monthly_allocations"].pop(),
            "WORKFORCE_ALLOCATION_MANIFEST_INCOMPLETE",
        ),
        (
            lambda package: (
                package["monthly_allocations"].pop(),
                package["manifest"]["allocation_keys"].pop(),
            ),
            "WORKFORCE_ALLOCATION_COVERAGE_INCOMPLETE",
        ),
        (
            lambda package: package["monthly_allocations"][0].update(month=13),
            "WORKFORCE_ALLOCATION_MONTH_INVALID",
        ),
        (
            lambda package: package["monthly_allocations"][0].update(month=True),
            "WORKFORCE_ALLOCATION_MONTH_INVALID",
        ),
        (
            lambda package: package["monthly_allocations"][0].update(allocation=1.5),
            "WORKFORCE_ALLOCATION_RANGE_INVALID",
        ),
        (
            lambda package: package["monthly_allocations"][0].update(
                project_id="project-synthetic-missing"
            ),
            "WORKFORCE_ALLOCATION_MANIFEST_INCOMPLETE",
        ),
        (
            lambda package: package["members"][0].update(role="arbitrary narrative"),
            "WORKFORCE_MEMBER_ROLE_INVALID",
        ),
        (
            lambda package: package["members"][0].update(status=["active"]),
            "WORKFORCE_MEMBER_STATUS_INVALID",
        ),
        (
            lambda package: package["projects"][0].update(status=["active"]),
            "WORKFORCE_PROJECT_STATUS_INVALID",
        ),
        (
            lambda package: package["plan_versions"][0].update(scenario_type=["baseline"]),
            "WORKFORCE_PLAN_SCENARIO_INVALID",
        ),
    ],
)
def test_validation_fails_before_session_creation(
    isolated_db: Path, mutate, error_code: str
) -> None:
    init_db(quiet=True)
    package = _package()
    mutate(package)
    with pytest.raises(ValueError, match=error_code):
        preview_import(package, db_path=isolated_db)
    with sqlite3.connect(isolated_db) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM workforce_planning_import_sessions"
        ).fetchone()[0] == 0


def test_publication_failure_is_atomic_audited_and_retryable(
    isolated_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    init_db(quiet=True)
    preview = preview_import(_package(), db_path=isolated_db)
    original_integrity = import_repository._integrity_report
    monkeypatch.setattr(
        import_repository,
        "_integrity_report",
        lambda _database: {
            "sqlite_integrity": "failed",
            "foreign_key_violations": 1,
            "state": "failed",
        },
    )
    with pytest.raises(RuntimeError, match="WORKFORCE_PLANNING_INTEGRITY_FAILED"):
        confirm_import(preview["session_id"], db_path=isolated_db)
    with sqlite3.connect(isolated_db) as connection:
        counts = [
            connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            for table in ("employees", "projects", "plan_versions", "monthly_allocations")
        ]
        attempt = connection.execute(
            "SELECT status,failure_code FROM workforce_planning_import_attempts"
        ).fetchone()
        publication_count = connection.execute(
            "SELECT COUNT(*) FROM workforce_planning_publications"
        ).fetchone()[0]
    assert counts == [0, 0, 0, 0]
    assert attempt == ("failed", "WORKFORCE_PLANNING_INTEGRITY_FAILED")
    assert publication_count == 0

    monkeypatch.setattr(import_repository, "_integrity_report", original_integrity)
    retry = confirm_import(preview["session_id"], db_path=isolated_db)
    assert retry["status"] == "completed"
    with sqlite3.connect(isolated_db) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM workforce_planning_import_attempts"
        ).fetchone()[0] == 2


def test_phase4_read_contract_remains_usable_as_software_rollback_target(
    isolated_db: Path,
) -> None:
    init_db(quiet=True)
    preview = preview_import(_package(), db_path=isolated_db)
    confirm_import(preview["session_id"], db_path=isolated_db)

    rows, plan = legacy_repository.get_capacity_rows(
        2026, 8, "plan-synthetic-baseline-001"
    )
    assert plan is not None
    assert plan["plan_version_id"] == "plan-synthetic-baseline-001"
    assert [(row["id"], row["month_load"]) for row in rows] == [
        ("member-synthetic-002", 0.0),
        ("member-synthetic-001", 0.5),
    ]


def test_non_interactive_command_requires_preview_or_explicit_confirm(
    isolated_db: Path,
) -> None:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT)
    environment["DATABASE_PATH"] = str(isolated_db)
    command = [
        sys.executable,
        str(ROOT / "scripts" / "import_workforce_planning.py"),
        "--file",
        str(SAMPLE),
    ]
    missing_action = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
    )
    assert missing_action.returncode == 2
    assert "--dry-run | --confirm" in missing_action.stderr

    preview = subprocess.run(
        [*command, "--dry-run"],
        cwd=ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(preview.stdout)["status"] == "previewed"
    confirmed = subprocess.run(
        [*command, "--confirm"],
        cwd=ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(confirmed.stdout)["status"] == "completed"
