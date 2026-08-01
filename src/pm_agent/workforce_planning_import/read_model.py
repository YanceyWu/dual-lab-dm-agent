"""Public dependency reader for workforce/planning consumers.

Consumers receive canonical member/month and allocation coverage facts without
reading this capability's audit or coverage tables directly.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from pm_agent.config import settings


def dependency_snapshot(
    periods: list[dict[str, int | str]],
    plan_version_id: str,
    *,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    database = sqlite3.connect(Path(db_path or settings.database_path))
    database.row_factory = sqlite3.Row
    database.execute("PRAGMA foreign_keys = ON")
    try:
        publication = database.execute(
            """
            SELECT p.publication_id,p.package_fingerprint,s.package_json
            FROM workforce_planning_publications p
            JOIN workforce_planning_import_sessions s ON s.session_id=p.session_id
            WHERE p.is_current=1
            """
        ).fetchone()
        if not publication:
            raise ValueError("WORKFORCE_PLANNING_CURRENT_PUBLICATION_NOT_FOUND")
        plan = database.execute(
            """
            SELECT plan_version_id,version_status,updated_at
            FROM plan_versions WHERE plan_version_id=?
            """,
            [plan_version_id],
        ).fetchone()
        if not plan:
            raise ValueError("WORKFORCE_PLANNING_PLAN_VERSION_NOT_FOUND")

        package = json.loads(publication["package_json"])
        members = {item["member_id"]: item for item in package["members"]}
        projects = set(package["manifest"]["project_ids"])
        results: list[dict[str, Any]] = []
        for requested in periods:
            member_id = str(requested["member_id"])
            year = int(requested["year"])
            month = int(requested["month"])
            member = members.get(member_id)
            coverage = database.execute(
                """
                SELECT employment_status FROM workforce_member_period_coverage
                WHERE publication_id=? AND member_id=? AND year=? AND month=?
                """,
                [publication["publication_id"], member_id, year, month],
            ).fetchone()
            allocation_rows = database.execute(
                """
                SELECT c.project_id,ma.allocation
                FROM monthly_project_allocation_coverage c
                JOIN monthly_allocations ma
                  ON ma.employee_id=c.member_id
                 AND ma.project_id=c.project_id
                 AND ma.plan_version_id=c.plan_version_id
                 AND ma.year=c.year AND ma.month=c.month
                WHERE c.publication_id=? AND c.member_id=?
                  AND c.plan_version_id=? AND c.year=? AND c.month=?
                ORDER BY c.project_id
                """,
                [publication["publication_id"], member_id, plan_version_id, year, month],
            ).fetchall()
            covered_projects = {row["project_id"] for row in allocation_rows}
            complete = bool(member and coverage and covered_projects == projects)
            results.append(
                {
                    "member_id": member_id,
                    "year": year,
                    "month": month,
                    "state": "known" if complete else "unknown",
                    "employment_status": coverage["employment_status"] if coverage else None,
                    "effective_start": member["effective_start"] if member else None,
                    "effective_end": member["effective_end"] if member else None,
                    "planned_project_allocation": (
                        sum(float(row["allocation"]) for row in allocation_rows)
                        if complete
                        else None
                    ),
                    "allocation_evidence": [
                        {
                            "project_id": row["project_id"],
                            "allocation": float(row["allocation"]),
                        }
                        for row in allocation_rows
                    ],
                }
            )
        return {
            "publication_id": publication["publication_id"],
            "package_fingerprint": publication["package_fingerprint"],
            "plan_version_id": plan["plan_version_id"],
            "plan_version_status": plan["version_status"],
            "plan_updated_at": plan["updated_at"],
            "periods": results,
        }
    finally:
        database.close()
