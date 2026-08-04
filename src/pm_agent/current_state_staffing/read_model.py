"""Public read-contract skeleton for canonical current-state staffing."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from pm_agent.config import settings
from pm_agent.current_state_staffing.schema import CURRENT_STATE_STAFFING_REQUIRED_TABLES


def _connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    database = sqlite3.connect(Path(db_path or settings.database_path))
    database.row_factory = sqlite3.Row
    database.execute("PRAGMA foreign_keys = ON")
    return database


def _schema_available(database: sqlite3.Connection) -> bool:
    rows = database.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
          AND name IN ({})
        """.format(",".join("?" for _ in CURRENT_STATE_STAFFING_REQUIRED_TABLES)),
        sorted(CURRENT_STATE_STAFFING_REQUIRED_TABLES),
    ).fetchall()
    return {str(row["name"]) for row in rows} == CURRENT_STATE_STAFFING_REQUIRED_TABLES


def current_publication_state(*, db_path: str | Path | None = None) -> dict[str, Any]:
    database = _connect(db_path)
    try:
        if not _schema_available(database):
            return {
                "state": "unavailable",
                "state_reason": "current_state_staffing_schema_missing",
                "publication": None,
            }
        publication = database.execute(
            """
            SELECT publication_id,package_id,package_fingerprint,scope_key,
                   as_of_date,effective_year,effective_month,published_at,report_json
            FROM current_state_staffing_publications
            WHERE is_current=1
            ORDER BY published_at DESC
            LIMIT 1
            """
        ).fetchone()
        if publication is None:
            return {
                "state": "unknown",
                "state_reason": "current_state_staffing_publication_not_found",
                "publication": None,
            }
        return {
            "state": "known",
            "state_reason": "current_state_staffing_current_publication_available",
            "publication": {
                "publication_id": str(publication["publication_id"]),
                "package_id": str(publication["package_id"]),
                "package_fingerprint": str(publication["package_fingerprint"]),
                "scope_key": str(publication["scope_key"]),
                "as_of_date": str(publication["as_of_date"]),
                "effective_year": int(publication["effective_year"]),
                "effective_month": int(publication["effective_month"]),
                "published_at": str(publication["published_at"]),
                "report": json.loads(str(publication["report_json"])),
            },
        }
    finally:
        database.close()


def member_load_snapshot(
    member_id: str, *, db_path: str | Path | None = None
) -> dict[str, Any]:
    publication_state = current_publication_state(db_path=db_path)
    base = {
        "member_id": member_id,
        "state": publication_state["state"],
        "state_reason": publication_state["state_reason"],
        "publication": publication_state["publication"],
        "member": None,
        "current_load": None,
        "active_project_count": None,
        "assignment_state": None,
        "assignments": [],
    }
    if publication_state["state"] != "known":
        return base
    publication = publication_state["publication"]
    assert isinstance(publication, dict)
    database = _connect(db_path)
    try:
        member = database.execute(
            """
            SELECT m.display_name,m.employment_status,m.role,m.level,m.resource_type,
                   m.current_hiref_id,m.hiref_end_date,l.current_load,l.active_project_count,
                   l.assignment_state
            FROM current_state_staffing_members m
            JOIN current_state_staffing_member_loads l
              ON l.publication_id=m.publication_id AND l.member_id=m.member_id
            WHERE m.publication_id=? AND m.member_id=?
            """,
            [publication["publication_id"], member_id],
        ).fetchone()
        if member is None:
            return {
                **base,
                "state": "unknown",
                "state_reason": "member_not_in_current_state_staffing_publication",
            }
        assignments = database.execute(
            """
            SELECT a.project_id,p.display_name,a.allocation
            FROM current_state_staffing_assignments a
            JOIN current_state_staffing_projects p
              ON p.publication_id=a.publication_id AND p.project_id=a.project_id
            WHERE a.publication_id=? AND a.member_id=?
            ORDER BY a.project_id
            """,
            [publication["publication_id"], member_id],
        ).fetchall()
        return {
            **base,
            "state": "known",
            "state_reason": "member_load_available_from_current_state_staffing_publication",
            "member": {
                "display_name": str(member["display_name"]),
                "employment_status": str(member["employment_status"]),
                "role": str(member["role"]),
                "level": str(member["level"]),
                "resource_type": str(member["resource_type"]) or None,
                "current_hiref_id": str(member["current_hiref_id"]) or None,
                "hiref_end_date": str(member["hiref_end_date"]) or None,
            },
            "current_load": float(member["current_load"]),
            "active_project_count": int(member["active_project_count"]),
            "assignment_state": str(member["assignment_state"]),
            "assignments": [
                {
                    "project_id": str(row["project_id"]),
                    "project_name": str(row["display_name"]),
                    "allocation": float(row["allocation"]),
                }
                for row in assignments
            ],
        }
    finally:
        database.close()


def project_team_snapshot(
    project_id: str, *, db_path: str | Path | None = None
) -> dict[str, Any]:
    publication_state = current_publication_state(db_path=db_path)
    base = {
        "project_id": project_id,
        "state": publication_state["state"],
        "state_reason": publication_state["state_reason"],
        "publication": publication_state["publication"],
        "project": None,
        "assignment_state": None,
        "assignments": [],
    }
    if publication_state["state"] != "known":
        return base
    publication = publication_state["publication"]
    assert isinstance(publication, dict)
    database = _connect(db_path)
    try:
        project = database.execute(
            """
            SELECT display_name,project_status,priority
            FROM current_state_staffing_projects
            WHERE publication_id=? AND project_id=?
            """,
            [publication["publication_id"], project_id],
        ).fetchone()
        if project is None:
            return {
                **base,
                "state": "unknown",
                "state_reason": "project_not_in_current_state_staffing_publication",
            }
        assignments = database.execute(
            """
            SELECT a.member_id,m.display_name,m.employment_status,a.allocation
            FROM current_state_staffing_assignments a
            JOIN current_state_staffing_members m
              ON m.publication_id=a.publication_id AND m.member_id=a.member_id
            WHERE a.publication_id=? AND a.project_id=?
            ORDER BY a.member_id
            """,
            [publication["publication_id"], project_id],
        ).fetchall()
        return {
            **base,
            "state": "known",
            "state_reason": "project_team_available_from_current_state_staffing_publication",
            "project": {
                "display_name": str(project["display_name"]),
                "project_status": str(project["project_status"]),
                "priority": int(project["priority"]),
            },
            "assignment_state": "assigned" if assignments else "empty",
            "assignments": [
                {
                    "member_id": str(row["member_id"]),
                    "display_name": str(row["display_name"]),
                    "employment_status": str(row["employment_status"]),
                    "allocation": float(row["allocation"]),
                }
                for row in assignments
            ],
        }
    finally:
        database.close()
