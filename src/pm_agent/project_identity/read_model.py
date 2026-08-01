"""Read-only manifest for the canonical local project catalog."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

from pm_agent.config import settings

_STABLE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
MAX_PROJECTS = 200


def active_project_manifest(
    *,
    project_ids: list[str] | None = None,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Return the complete active-project set, or an exact validated subset."""
    normalized_ids = _project_ids(project_ids)
    database = sqlite3.connect(Path(db_path or settings.database_path))
    database.row_factory = sqlite3.Row
    try:
        active_count = database.execute(
            "SELECT COUNT(*) FROM projects WHERE status='active'"
        ).fetchone()[0]
        if normalized_ids is None and active_count > MAX_PROJECTS:
            return {
                "contract_version": "active-project-manifest-v1",
                "scope": {"kind": "global", "project_ids": []},
                "projects": [],
                "coverage": {
                    "state": "unavailable",
                    "basis": "canonical_local_project_catalog",
                    "active_project_count": active_count,
                    "selected_project_count": 0,
                    "limit": MAX_PROJECTS,
                },
                "limitations": ["PROJECT_MANIFEST_LIMIT_EXCEEDED"],
            }
        if normalized_ids is None:
            rows = database.execute(
                """SELECT id,status,priority,updated_at
                   FROM projects
                   WHERE status='active'
                   ORDER BY priority,id"""
            ).fetchall()
        else:
            placeholders = ",".join("?" for _ in normalized_ids)
            rows = database.execute(
                f"""SELECT id,status,priority,updated_at
                    FROM projects
                    WHERE status='active' AND id IN ({placeholders})
                    ORDER BY priority,id""",
                normalized_ids,
            ).fetchall()
    finally:
        database.close()

    active_by_id = {row["id"]: dict(row) for row in rows}
    if normalized_ids is not None:
        missing = sorted(set(normalized_ids) - set(active_by_id))
        if missing:
            raise ValueError("PROJECT_NOT_FOUND")
        selected = [active_by_id[project_id] for project_id in normalized_ids]
        scope = {"kind": "projects", "project_ids": normalized_ids}
    else:
        selected = [dict(row) for row in rows]
        scope = {"kind": "global", "project_ids": sorted(active_by_id)}

    projects = [
        {
            "project_id": row["id"],
            "status": row["status"],
            "priority": row["priority"],
            "observed_at": row["updated_at"],
        }
        for row in selected
    ]
    return {
        "contract_version": "active-project-manifest-v1",
        "scope": scope,
        "projects": projects,
        "coverage": {
            "state": "complete" if rows else "absent",
            "basis": "canonical_local_project_catalog",
            "active_project_count": active_count,
            "selected_project_count": len(projects),
        },
        "limitations": [],
    }


def _project_ids(value: list[str] | None) -> list[str] | None:
    if value is None:
        return None
    if (
        not isinstance(value, list)
        or not value
        or len(value) > MAX_PROJECTS
        or any(not isinstance(item, str) or not _STABLE_ID.fullmatch(item) for item in value)
    ):
        raise ValueError("PROJECT_IDS_INVALID")
    if len(value) != len(set(value)):
        raise ValueError("PROJECT_IDS_DUPLICATE")
    return sorted(value)
