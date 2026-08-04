from __future__ import annotations

import sqlite3
from pathlib import Path

from pm_agent.current_state_staffing import service


def publish_current_state_staffing_from_legacy(
    db_path: Path,
    *,
    package_id: str = "package-test-current-state-r1",
) -> dict:
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        members = []
        for row in connection.execute(
            """
            SELECT e.id,e.name,e.status,e.role,e.level,e.resource_type,e.current_hiref,
                   COALESCE(h.end_date, e.billing_end_date) AS current_hiref_end_date
            FROM employees e
            LEFT JOIN hiref h ON h.id = e.current_hiref
            WHERE e.status='active'
            ORDER BY e.id
            """
        ).fetchall():
            current_hiref_id = str(row["current_hiref"] or "") or None
            hiref_end_date = str(row["current_hiref_end_date"] or "") or None
            if not current_hiref_id or not hiref_end_date:
                current_hiref_id = None
                hiref_end_date = None
            members.append(
                {
                    "member_id": str(row["id"]),
                    "display_name": str(row["name"]),
                    "status": "active" if str(row["status"]) == "active" else "inactive",
                    "role": str(row["role"] or "unspecified"),
                    "level": str(row["level"] or "unknown"),
                    "resource_type": str(row["resource_type"] or ""),
                    "current_hiref_id": current_hiref_id,
                    "hiref_end_date": hiref_end_date,
                }
            )
        projects = [
            {
                "project_id": str(row["id"]),
                "display_name": str(row["name"]),
                "status": str(row["status"]),
                "priority": int(row["priority"] or 3),
            }
            for row in connection.execute(
                """
                SELECT id,name,status,priority
                FROM projects
                WHERE status IN ('planning','active','done')
                ORDER BY id
                """
            ).fetchall()
        ]
        assignments = [
            {
                "member_id": str(row["employee_id"]),
                "project_id": str(row["project_id"]),
                "allocation": float(row["allocation"]),
            }
            for row in connection.execute(
                """
                SELECT employee_id,project_id,allocation
                FROM assignments
                WHERE status='active'
                ORDER BY employee_id,project_id
                """
            ).fetchall()
        ]

    package = {
        "dataset_marker": "TEST_CURRENT_STATE_STAFFING",
        "package_id": package_id,
        "schema_version": service.PACKAGE_SCHEMA_VERSION,
        "generated_at": "2026-08-15T00:00:00+00:00",
        "source_id": "source-test-current-state-staffing",
        "publication_scope": {
            "scope_key": "test-current-state-staffing",
            "as_of_date": "2026-08-15",
            "effective_year": 2026,
            "effective_month": 8,
        },
        "manifest": {
            "member_ids": [member["member_id"] for member in members],
            "project_ids": [project["project_id"] for project in projects],
            "assignment_keys": [
                {
                    "member_id": item["member_id"],
                    "project_id": item["project_id"],
                }
                for item in assignments
            ],
        },
        "members": members,
        "projects": projects,
        "assignments": assignments,
    }
    preview = service.preview_import(package, db_path=db_path)
    return service.confirm_import(preview["session_id"], db_path=db_path)
