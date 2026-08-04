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


def current_staffing_snapshot(*, db_path: str | Path | None = None) -> dict[str, Any]:
    publication_state = current_publication_state(db_path=db_path)
    base = {
        "state": publication_state["state"],
        "state_reason": publication_state["state_reason"],
        "publication": publication_state["publication"],
        "members": [],
        "projects": [],
    }
    if publication_state["state"] != "known":
        return base
    publication = publication_state["publication"]
    assert isinstance(publication, dict)
    database = _connect(db_path)
    try:
        member_rows = database.execute(
            """
            SELECT m.member_id,m.display_name,m.employment_status,m.role,m.level,
                   m.resource_type,m.current_hiref_id,m.hiref_end_date,
                   l.current_load,l.active_project_count,l.assignment_state
            FROM current_state_staffing_members m
            JOIN current_state_staffing_member_loads l
              ON l.publication_id=m.publication_id AND l.member_id=m.member_id
            WHERE m.publication_id=?
            ORDER BY m.member_id
            """,
            [publication["publication_id"]],
        ).fetchall()
        project_rows = database.execute(
            """
            SELECT project_id,display_name,project_status,priority
            FROM current_state_staffing_projects
            WHERE publication_id=?
            ORDER BY project_id
            """,
            [publication["publication_id"]],
        ).fetchall()
        assignment_rows = database.execute(
            """
            SELECT a.member_id,m.display_name AS member_name,m.employment_status,
                   a.project_id,p.display_name AS project_name,a.allocation
            FROM current_state_staffing_assignments a
            JOIN current_state_staffing_members m
              ON m.publication_id=a.publication_id AND m.member_id=a.member_id
            JOIN current_state_staffing_projects p
              ON p.publication_id=a.publication_id AND p.project_id=a.project_id
            WHERE a.publication_id=?
            ORDER BY a.member_id,a.project_id
            """,
            [publication["publication_id"]],
        ).fetchall()
    finally:
        database.close()

    member_assignments: dict[str, list[dict[str, Any]]] = {}
    project_assignments: dict[str, list[dict[str, Any]]] = {}
    for row in assignment_rows:
        member_assignments.setdefault(str(row["member_id"]), []).append(
            {
                "project_id": str(row["project_id"]),
                "project_name": str(row["project_name"]),
                "allocation": float(row["allocation"]),
            }
        )
        project_assignments.setdefault(str(row["project_id"]), []).append(
            {
                "member_id": str(row["member_id"]),
                "display_name": str(row["member_name"]),
                "employment_status": str(row["employment_status"]),
                "allocation": float(row["allocation"]),
            }
        )

    members = [
        {
            "member_id": str(row["member_id"]),
            "display_name": str(row["display_name"]),
            "employment_status": str(row["employment_status"]),
            "role": str(row["role"]),
            "level": str(row["level"]),
            "resource_type": str(row["resource_type"]) or None,
            "current_hiref_id": str(row["current_hiref_id"]) or None,
            "hiref_end_date": str(row["hiref_end_date"]) or None,
            "current_load": float(row["current_load"]),
            "active_project_count": int(row["active_project_count"]),
            "assignment_state": str(row["assignment_state"]),
            "assignments": list(member_assignments.get(str(row["member_id"]), [])),
        }
        for row in member_rows
    ]
    projects = [
        {
            "project_id": str(row["project_id"]),
            "display_name": str(row["display_name"]),
            "project_status": str(row["project_status"]),
            "priority": int(row["priority"]),
            "assignment_state": "assigned"
            if project_assignments.get(str(row["project_id"]))
            else "empty",
            "assignments": list(project_assignments.get(str(row["project_id"]), [])),
        }
        for row in project_rows
    ]
    return {**base, "members": members, "projects": projects}


def member_load_snapshot(
    member_id: str, *, db_path: str | Path | None = None
) -> dict[str, Any]:
    snapshot = current_staffing_snapshot(db_path=db_path)
    base = {
        "member_id": member_id,
        "state": snapshot["state"],
        "state_reason": snapshot["state_reason"],
        "publication": snapshot["publication"],
        "member": None,
        "current_load": None,
        "active_project_count": None,
        "assignment_state": None,
        "assignments": [],
    }
    if snapshot["state"] != "known":
        return base
    member = next(
        (item for item in snapshot["members"] if item["member_id"] == member_id),
        None,
    )
    if member is None:
        return {
            **base,
            "state": "unknown",
            "state_reason": "member_not_in_current_state_staffing_publication",
        }
    return {
        **base,
        "state": "known",
        "state_reason": "member_load_available_from_current_state_staffing_publication",
        "member": {
            "display_name": member["display_name"],
            "employment_status": member["employment_status"],
            "role": member["role"],
            "level": member["level"],
            "resource_type": member["resource_type"],
            "current_hiref_id": member["current_hiref_id"],
            "hiref_end_date": member["hiref_end_date"],
        },
        "current_load": member["current_load"],
        "active_project_count": member["active_project_count"],
        "assignment_state": member["assignment_state"],
        "assignments": list(member["assignments"]),
    }


def project_team_snapshot(
    project_id: str, *, db_path: str | Path | None = None
) -> dict[str, Any]:
    snapshot = current_staffing_snapshot(db_path=db_path)
    base = {
        "project_id": project_id,
        "state": snapshot["state"],
        "state_reason": snapshot["state_reason"],
        "publication": snapshot["publication"],
        "project": None,
        "assignment_state": None,
        "assignments": [],
    }
    if snapshot["state"] != "known":
        return base
    project = next(
        (item for item in snapshot["projects"] if item["project_id"] == project_id),
        None,
    )
    if project is None:
        return {
            **base,
            "state": "unknown",
            "state_reason": "project_not_in_current_state_staffing_publication",
        }
    return {
        **base,
        "state": "known",
        "state_reason": "project_team_available_from_current_state_staffing_publication",
        "project": {
            "display_name": project["display_name"],
            "project_status": project["project_status"],
            "priority": project["priority"],
        },
        "assignment_state": project["assignment_state"],
        "assignments": list(project["assignments"]),
    }
