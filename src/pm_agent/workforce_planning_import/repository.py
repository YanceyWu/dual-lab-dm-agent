"""Persistence boundary for atomic workforce/planning clean import."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from pm_agent.config import settings


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


@contextmanager
def connection(db_path: str | Path | None = None) -> Iterator[sqlite3.Connection]:
    database = sqlite3.connect(Path(db_path or settings.database_path), isolation_level=None)
    database.row_factory = sqlite3.Row
    database.execute("PRAGMA foreign_keys = ON")
    database.execute("PRAGMA busy_timeout = 10000")
    try:
        yield database
    finally:
        database.close()


def session_by_fingerprint(
    package_fingerprint: str, *, db_path: str | Path | None = None
) -> dict[str, Any] | None:
    with connection(db_path) as database:
        row = database.execute(
            "SELECT * FROM workforce_planning_import_sessions WHERE package_fingerprint=?",
            [package_fingerprint],
        ).fetchone()
    return dict(row) if row else None


def completed_session_for_package(
    package_id: str, *, db_path: str | Path | None = None
) -> dict[str, Any] | None:
    with connection(db_path) as database:
        row = database.execute(
            """
            SELECT * FROM workforce_planning_import_sessions
            WHERE package_id=? AND status='completed'
            ORDER BY completed_at DESC LIMIT 1
            """,
            [package_id],
        ).fetchone()
    return dict(row) if row else None


def create_session(
    *,
    session_id: str,
    package_id: str,
    schema_version: str,
    package_fingerprint: str,
    package: dict[str, Any],
    status: str,
    created_at: str,
    failure_code: str = "",
    db_path: str | Path | None = None,
) -> None:
    with connection(db_path) as database:
        database.execute("BEGIN IMMEDIATE")
        database.execute(
            """
            INSERT INTO workforce_planning_import_sessions
                (session_id,package_id,schema_version,package_fingerprint,package_json,
                 status,created_at,completed_at,failure_code)
            VALUES (?,?,?,?,?,?,?,?,?)
            """,
            [
                session_id,
                package_id,
                schema_version,
                package_fingerprint,
                _json(package),
                status,
                created_at,
                created_at if status == "rejected" else "",
                failure_code,
            ],
        )
        database.commit()


def record_run(
    *,
    session_id: str,
    attempt_id: str | None,
    step_key: str,
    status: str,
    counts: dict[str, int],
    warning_codes: list[str],
    created_at: str,
    db_path: str | Path | None = None,
) -> str:
    run_id = f"workforce-planning-run-{uuid4().hex}"
    with connection(db_path) as database:
        database.execute(
            """
            INSERT INTO workforce_planning_import_runs
                (run_id,session_id,attempt_id,step_key,status,counts_json,
                 warning_codes_json,created_at)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            [
                run_id,
                session_id,
                attempt_id,
                step_key,
                status,
                _json(counts),
                _json(warning_codes),
                created_at,
            ],
        )
    return run_id


def load_session(session_id: str, *, db_path: str | Path | None = None) -> dict[str, Any] | None:
    with connection(db_path) as database:
        row = database.execute(
            "SELECT * FROM workforce_planning_import_sessions WHERE session_id=?",
            [session_id],
        ).fetchone()
    return dict(row) if row else None


def start_attempt(
    session_id: str, *, started_at: str, db_path: str | Path | None = None
) -> str:
    attempt_id = f"workforce-planning-attempt-{uuid4().hex}"
    with connection(db_path) as database:
        database.execute("BEGIN IMMEDIATE")
        claimed = database.execute(
            """
            UPDATE workforce_planning_import_sessions
            SET status='running',failure_code=''
            WHERE session_id=? AND status IN ('previewed','failed')
            """,
            [session_id],
        )
        if claimed.rowcount != 1:
            raise ValueError("WORKFORCE_PLANNING_SESSION_NOT_CONFIRMABLE")
        database.execute(
            """
            INSERT INTO workforce_planning_import_attempts
                (attempt_id,session_id,status,started_at)
            VALUES (?,?,'running',?)
            """,
            [attempt_id, session_id, started_at],
        )
        database.commit()
    return attempt_id


def _insert_core_records(database: sqlite3.Connection, package: dict[str, Any]) -> None:
    for member in package["members"]:
        database.execute(
            """
            INSERT INTO employees
                (id,wd_id,name,role,level,status,notes,skills,metadata)
            VALUES (?,?,?,?,?,?,?,'{}',?)
            """,
            [
                member["member_id"],
                member["member_id"],
                member["display_name"],
                member["role"],
                member["level"],
                member["status"],
                "SYNTHETIC_DATASET_V1 workforce planning clean import",
                _json(
                    {
                        "effective_start": member["effective_start"],
                        "effective_end": member["effective_end"],
                        "source_id": package["source_id"],
                    }
                ),
            ],
        )
    for project in package["projects"]:
        database.execute(
            """
            INSERT INTO projects
                (id,name,status,priority,start_date,target_end,tech_stack,notes)
            VALUES (?,?,?,?,?,?,'[]',?)
            """,
            [
                project["project_id"],
                project["display_name"],
                project["status"],
                project["priority"],
                project["start_date"],
                project["target_end"],
                "SYNTHETIC_DATASET_V1 workforce planning clean import",
            ],
        )
    for plan in package["plan_versions"]:
        database.execute(
            """
            INSERT INTO plan_versions
                (plan_version_id,version_name,scenario_type,as_of_date,version_status,notes)
            VALUES (?,?,?,?,?,?)
            """,
            [
                plan["plan_version_id"],
                plan["version_name"],
                plan["scenario_type"],
                plan["as_of_date"],
                plan["status"],
                "SYNTHETIC_DATASET_V1 workforce planning clean import",
            ],
        )
    for allocation in package["monthly_allocations"]:
        database.execute(
            """
            INSERT INTO monthly_allocations
                (employee_id,project_id,year,month,allocation,plan_version_id)
            VALUES (?,?,?,?,?,?)
            """,
            [
                allocation["member_id"],
                allocation["project_id"],
                allocation["year"],
                allocation["month"],
                allocation["allocation"],
                allocation["plan_version_id"],
            ],
        )


def _integrity_report(database: sqlite3.Connection) -> dict[str, Any]:
    integrity_rows = [row[0] for row in database.execute("PRAGMA integrity_check")]
    foreign_key_rows = database.execute("PRAGMA foreign_key_check").fetchall()
    return {
        "sqlite_integrity": "ok" if integrity_rows == ["ok"] else "failed",
        "foreign_key_violations": len(foreign_key_rows),
        "state": "passed" if integrity_rows == ["ok"] and not foreign_key_rows else "failed",
    }


def _target_counts(database: sqlite3.Connection) -> dict[str, int]:
    return {
        table: database.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        for table in ("employees", "projects", "plan_versions", "monthly_allocations")
    }


def _rollback_compatibility_report(
    database: sqlite3.Connection, counts: dict[str, int]
) -> dict[str, Any]:
    """Prove the imported facts remain readable without the additive audit tables."""
    legacy_rows = database.execute(
        """
        SELECT e.id,ma.project_id,ma.plan_version_id,ma.year,ma.month,ma.allocation
        FROM employees e
        JOIN monthly_allocations ma ON ma.employee_id=e.id
        JOIN projects p ON p.id=ma.project_id
        JOIN plan_versions pv ON pv.plan_version_id=ma.plan_version_id
        ORDER BY e.id,ma.project_id,ma.plan_version_id,ma.year,ma.month
        """
    ).fetchall()
    if len(legacy_rows) != counts["monthly_allocations"]:
        raise RuntimeError("WORKFORCE_PLANNING_ROLLBACK_COMPATIBILITY_FAILED")
    return {
        "state": "passed",
        "strategy": "phase4_runtime_ignores_additive_import_audit",
        "core_tables_preserved": True,
        "legacy_read_row_count": len(legacy_rows),
    }


def publish(
    *,
    session_id: str,
    attempt_id: str,
    package_fingerprint: str,
    package: dict[str, Any],
    published_at: str,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    publication_id = f"workforce-planning-publication-{uuid4().hex}"
    with connection(db_path) as database:
        database.execute("BEGIN IMMEDIATE")
        if database.execute(
            "SELECT 1 FROM workforce_planning_publications WHERE is_current=1"
        ).fetchone():
            raise ValueError("WORKFORCE_PLANNING_CURRENT_PUBLICATION_EXISTS")
        counts_before = _target_counts(database)
        if any(counts_before.values()):
            raise ValueError("WORKFORCE_PLANNING_TARGET_NOT_EMPTY")

        _insert_core_records(database, package)
        database.execute(
            """
            INSERT INTO workforce_planning_publications
                (publication_id,session_id,package_id,package_fingerprint,schema_version,
                 published_at,is_current,report_json)
            VALUES (?,?,?,?,?,?,1,'{}')
            """,
            [
                publication_id,
                session_id,
                package["package_id"],
                package_fingerprint,
                package["schema_version"],
                published_at,
            ],
        )
        member_status = {item["member_id"]: item["status"] for item in package["members"]}
        database.executemany(
            """
            INSERT INTO workforce_member_period_coverage
                (publication_id,member_id,year,month,employment_status)
            VALUES (?,?,?,?,?)
            """,
            [
                (
                    publication_id,
                    item["member_id"],
                    item["year"],
                    item["month"],
                    member_status[item["member_id"]],
                )
                for item in package["manifest"]["workforce_periods"]
            ],
        )
        database.executemany(
            """
            INSERT INTO monthly_project_allocation_coverage
                (publication_id,member_id,project_id,plan_version_id,year,month,value_state)
            VALUES (?,?,?,?,?,?,'known')
            """,
            [
                (
                    publication_id,
                    item["member_id"],
                    item["project_id"],
                    item["plan_version_id"],
                    item["year"],
                    item["month"],
                )
                for item in package["manifest"]["allocation_keys"]
            ],
        )

        counts = _target_counts(database)
        integrity = _integrity_report(database)
        if integrity["state"] != "passed":
            raise RuntimeError("WORKFORCE_PLANNING_INTEGRITY_FAILED")
        rollback_compatibility = _rollback_compatibility_report(database, counts)
        explicit_zero_count = sum(
            item["allocation"] == 0 for item in package["monthly_allocations"]
        )
        report = {
            "publication_id": publication_id,
            "package_id": package["package_id"],
            "schema_version": package["schema_version"],
            "counts": counts,
            "coverage": {
                "state": "complete",
                "authoritative_manifest": True,
                "member_count": len(package["manifest"]["member_ids"]),
                "project_count": len(package["manifest"]["project_ids"]),
                "plan_version_count": len(package["manifest"]["plan_version_ids"]),
                "workforce_period_count": len(package["manifest"]["workforce_periods"]),
                "allocation_key_count": len(package["manifest"]["allocation_keys"]),
                "explicit_zero_count": explicit_zero_count,
                "missing_record_count": 0,
            },
            "integrity": integrity,
            "reconciliation_state": "not_required_clean_import",
            "software_rollback": rollback_compatibility,
            "attempt_id": attempt_id,
        }
        database.execute(
            "UPDATE workforce_planning_publications SET report_json=? WHERE publication_id=?",
            [_json(report), publication_id],
        )
        for step_key, step_counts in (
            ("publication", counts),
            ("integrity", {"foreign_key_violations": integrity["foreign_key_violations"]}),
            ("rollback_compatibility", {"core_table_count": len(counts)}),
        ):
            database.execute(
                """
                INSERT INTO workforce_planning_import_runs
                    (run_id,session_id,attempt_id,step_key,status,counts_json,
                     warning_codes_json,created_at)
                VALUES (?,?,?,?, 'completed',?,'[]',?)
                """,
                [
                    f"workforce-planning-run-{uuid4().hex}",
                    session_id,
                    attempt_id,
                    step_key,
                    _json(step_counts),
                    published_at,
                ],
            )
        database.execute(
            """
            UPDATE workforce_planning_import_attempts
            SET status='completed',finished_at=? WHERE attempt_id=?
            """,
            [published_at, attempt_id],
        )
        database.execute(
            """
            UPDATE workforce_planning_import_sessions
            SET status='completed',completed_at=?,failure_code='',report_json=?
            WHERE session_id=?
            """,
            [published_at, _json(report), session_id],
        )
        database.commit()
    return report


def fail_attempt(
    *,
    session_id: str,
    attempt_id: str,
    failure_code: str,
    finished_at: str,
    db_path: str | Path | None = None,
) -> None:
    with connection(db_path) as database:
        database.execute("BEGIN IMMEDIATE")
        database.execute(
            """
            UPDATE workforce_planning_import_attempts
            SET status='failed',finished_at=?,failure_code=? WHERE attempt_id=?
            """,
            [finished_at, failure_code, attempt_id],
        )
        database.execute(
            """
            UPDATE workforce_planning_import_sessions
            SET status='failed',completed_at=?,failure_code=? WHERE session_id=?
            """,
            [finished_at, failure_code, session_id],
        )
        database.execute(
            """
            INSERT INTO workforce_planning_import_runs
                (run_id,session_id,attempt_id,step_key,status,counts_json,
                 warning_codes_json,created_at)
            VALUES (?,?,?,'publication','failed','{}',?,?)
            """,
            [
                f"workforce-planning-run-{uuid4().hex}",
                session_id,
                attempt_id,
                _json([failure_code]),
                finished_at,
            ],
        )
        database.commit()
