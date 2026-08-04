"""Persistence boundary for canonical current-state staffing publication."""

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
            """
            SELECT * FROM current_state_staffing_import_sessions
            WHERE package_fingerprint=?
            """,
            [package_fingerprint],
        ).fetchone()
    return dict(row) if row else None


def latest_session_for_package(
    package_id: str, *, db_path: str | Path | None = None
) -> dict[str, Any] | None:
    with connection(db_path) as database:
        row = database.execute(
            """
            SELECT * FROM current_state_staffing_import_sessions
            WHERE package_id=?
            ORDER BY created_at DESC, rowid DESC
            LIMIT 1
            """,
            [package_id],
        ).fetchone()
    return dict(row) if row else None


def load_session(session_id: str, *, db_path: str | Path | None = None) -> dict[str, Any] | None:
    with connection(db_path) as database:
        row = database.execute(
            """
            SELECT * FROM current_state_staffing_import_sessions
            WHERE session_id=?
            """,
            [session_id],
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
    report: dict[str, Any] | None = None,
    db_path: str | Path | None = None,
) -> None:
    with connection(db_path) as database:
        database.execute("BEGIN IMMEDIATE")
        database.execute(
            """
            INSERT INTO current_state_staffing_import_sessions
                (session_id,package_id,schema_version,package_fingerprint,package_json,
                 status,created_at,completed_at,failure_code,report_json)
            VALUES (?,?,?,?,?,?,?,?,?,?)
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
                _json(report or {}),
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
    run_id = f"current-state-staffing-run-{uuid4().hex}"
    with connection(db_path) as database:
        database.execute(
            """
            INSERT INTO current_state_staffing_import_runs
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


def start_attempt(
    session_id: str, *, started_at: str, db_path: str | Path | None = None
) -> str:
    attempt_id = f"current-state-staffing-attempt-{uuid4().hex}"
    with connection(db_path) as database:
        database.execute("BEGIN IMMEDIATE")
        claimed = database.execute(
            """
            UPDATE current_state_staffing_import_sessions
            SET status='running',failure_code='',completed_at=''
            WHERE session_id=? AND status IN ('previewed','failed')
            """,
            [session_id],
        )
        if claimed.rowcount != 1:
            database.commit()
            raise ValueError("CURRENT_STATE_STAFFING_SESSION_NOT_CONFIRMABLE")
        database.execute(
            """
            INSERT INTO current_state_staffing_import_attempts
                (attempt_id,session_id,status,started_at)
            VALUES (?,?,'running',?)
            """,
            [attempt_id, session_id, started_at],
        )
        database.commit()
    return attempt_id


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
            UPDATE current_state_staffing_import_attempts
            SET status='failed', finished_at=?, failure_code=?
            WHERE attempt_id=?
            """,
            [finished_at, failure_code, attempt_id],
        )
        database.execute(
            """
            UPDATE current_state_staffing_import_sessions
            SET status='failed', completed_at=?, failure_code=?
            WHERE session_id=?
            """,
            [finished_at, failure_code, session_id],
        )
        database.commit()


def current_publication(
    scope_key: str, *, db_path: str | Path | None = None
) -> dict[str, Any] | None:
    with connection(db_path) as database:
        row = database.execute(
            """
            SELECT * FROM current_state_staffing_publications
            WHERE scope_key=? AND is_current=1
            """,
            [scope_key],
        ).fetchone()
    return dict(row) if row else None


def current_publication_any_scope(*, db_path: str | Path | None = None) -> dict[str, Any] | None:
    with connection(db_path) as database:
        row = database.execute(
            """
            SELECT * FROM current_state_staffing_publications
            WHERE is_current=1
            ORDER BY published_at DESC
            LIMIT 1
            """
        ).fetchone()
    return dict(row) if row else None


def publish(
    *,
    session_id: str,
    attempt_id: str,
    package_fingerprint: str,
    package: dict[str, Any],
    published_at: str,
    replace_current: bool,
    report: dict[str, Any],
    counts: dict[str, int],
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    publication_id = f"current-state-staffing-publication-{uuid4().hex}"
    scope = package["publication_scope"]
    final_report = {
        **report,
        "publication_id": publication_id,
    }
    with connection(db_path) as database:
        database.execute("BEGIN IMMEDIATE")
        current = database.execute(
            """
            SELECT publication_id
            FROM current_state_staffing_publications
            WHERE scope_key=? AND is_current=1
            """,
            [scope["scope_key"]],
        ).fetchone()
        if current and not replace_current:
            raise ValueError("CURRENT_STATE_STAFFING_CURRENT_PUBLICATION_EXISTS")
        if current:
            database.execute(
                """
                UPDATE current_state_staffing_publications
                SET is_current=0
                WHERE publication_id=?
                """,
                [current["publication_id"]],
            )
        database.execute(
            """
            INSERT INTO current_state_staffing_publications
                (publication_id,session_id,package_id,package_fingerprint,schema_version,
                 scope_key,as_of_date,effective_year,effective_month,published_at,
                 is_current,report_json)
            VALUES (?,?,?,?,?,?,?,?,?,?,1,?)
            """,
            [
                publication_id,
                session_id,
                package["package_id"],
                package_fingerprint,
                package["schema_version"],
                scope["scope_key"],
                scope["as_of_date"],
                scope["effective_year"],
                scope["effective_month"],
                published_at,
                _json(
                    {
                        **final_report,
                        "replaced_publication_id": (
                            str(current["publication_id"]) if current is not None else None
                        ),
                    }
                ),
            ],
        )
        for member in package["members"]:
            database.execute(
                """
                INSERT INTO current_state_staffing_members
                    (publication_id,member_id,display_name,employment_status,role,level,
                     resource_type,current_hiref_id,hiref_end_date)
                VALUES (?,?,?,?,?,?,?,?,?)
                """,
                [
                    publication_id,
                    member["member_id"],
                    member["display_name"],
                    member["status"],
                    member["role"],
                    member["level"],
                    member["resource_type"] or "",
                    member["current_hiref_id"] or "",
                    member["hiref_end_date"] or "",
                ],
            )
        for project in package["projects"]:
            database.execute(
                """
                INSERT INTO current_state_staffing_projects
                    (publication_id,project_id,display_name,project_status,priority)
                VALUES (?,?,?,?,?)
                """,
                [
                    publication_id,
                    project["project_id"],
                    project["display_name"],
                    project["status"],
                    project["priority"],
                ],
            )
        load_index = {
            member["member_id"]: {
                "current_load": 0.0,
                "active_project_count": 0,
            }
            for member in package["members"]
        }
        for assignment in package["assignments"]:
            database.execute(
                """
                INSERT INTO current_state_staffing_assignments
                    (publication_id,member_id,project_id,allocation)
                VALUES (?,?,?,?)
                """,
                [
                    publication_id,
                    assignment["member_id"],
                    assignment["project_id"],
                    assignment["allocation"],
                ],
            )
            load = load_index[assignment["member_id"]]
            load["current_load"] = round(load["current_load"] + float(assignment["allocation"]), 10)
            load["active_project_count"] += 1
        for member_id, load in load_index.items():
            database.execute(
                """
                INSERT INTO current_state_staffing_member_loads
                    (publication_id,member_id,current_load,active_project_count,assignment_state)
                VALUES (?,?,?,?,?)
                """,
                [
                    publication_id,
                    member_id,
                    load["current_load"],
                    load["active_project_count"],
                    "assigned" if load["active_project_count"] else "unassigned",
                ],
            )
        database.execute(
            """
            UPDATE current_state_staffing_import_attempts
            SET status='completed', finished_at=?, failure_code=''
            WHERE attempt_id=?
            """,
            [published_at, attempt_id],
        )
        database.execute(
            """
            INSERT INTO current_state_staffing_import_runs
                (run_id,session_id,attempt_id,step_key,status,counts_json,
                 warning_codes_json,created_at)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            [
                f"current-state-staffing-run-{uuid4().hex}",
                session_id,
                attempt_id,
                "publication",
                "completed",
                _json(counts),
                "[]",
                published_at,
            ],
        )
        database.execute(
            """
            UPDATE current_state_staffing_import_sessions
            SET status='completed', completed_at=?, failure_code='', report_json=?
            WHERE session_id=?
            """,
            [published_at, _json(final_report), session_id],
        )
        database.commit()
    return final_report
