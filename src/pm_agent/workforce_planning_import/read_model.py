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


def project_allocation_snapshot(
    project_id: str,
    year: int,
    month: int,
    plan_version_id: str,
    *,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Return the authoritative human assignment set for one project/month.

    Explicit zero allocations prove non-assignment. Missing publication,
    manifest scope, or coverage remains unknown rather than becoming empty.
    """
    database = sqlite3.connect(Path(db_path or settings.database_path))
    database.row_factory = sqlite3.Row
    database.execute("PRAGMA foreign_keys = ON")
    try:
        publication = database.execute(
            """SELECT p.publication_id,p.package_fingerprint,s.package_json
               FROM workforce_planning_publications p
               JOIN workforce_planning_import_sessions s ON s.session_id=p.session_id
               WHERE p.is_current=1"""
        ).fetchone()
        base = {
            "project_id": project_id,
            "year": year,
            "month": month,
            "plan_version_id": plan_version_id,
            "state": "unknown",
            "assignments": [],
        }
        if not publication:
            return {**base, "state_reason": "current_workforce_publication_not_found"}
        package = json.loads(publication["package_json"])
        manifest = package["manifest"]
        if (
            project_id not in manifest["project_ids"]
            or plan_version_id not in manifest["plan_version_ids"]
        ):
            return {
                **base,
                "publication_id": publication["publication_id"],
                "package_fingerprint": publication["package_fingerprint"],
                "state_reason": "project_or_plan_not_in_authoritative_manifest",
            }
        covered_members = sorted(
            item["member_id"]
            for item in manifest["workforce_periods"]
            if item["year"] == year and item["month"] == month
        )
        if not covered_members:
            return {
                **base,
                "publication_id": publication["publication_id"],
                "package_fingerprint": publication["package_fingerprint"],
                "state_reason": "period_not_in_authoritative_manifest",
            }
        rows = database.execute(
            """SELECT c.member_id,ma.allocation
               FROM monthly_project_allocation_coverage c
               JOIN monthly_allocations ma
                 ON ma.employee_id=c.member_id AND ma.project_id=c.project_id
                AND ma.plan_version_id=c.plan_version_id
                AND ma.year=c.year AND ma.month=c.month
               WHERE c.publication_id=? AND c.project_id=?
                 AND c.plan_version_id=? AND c.year=? AND c.month=?
               ORDER BY c.member_id""",
            [publication["publication_id"], project_id, plan_version_id, year, month],
        ).fetchall()
        if [row["member_id"] for row in rows] != covered_members:
            return {
                **base,
                "publication_id": publication["publication_id"],
                "package_fingerprint": publication["package_fingerprint"],
                "state_reason": "project_allocation_coverage_incomplete",
            }
        allocations = [
            {"member_id": row["member_id"], "allocation": float(row["allocation"])}
            for row in rows
        ]
        return {
            **base,
            "publication_id": publication["publication_id"],
            "package_fingerprint": publication["package_fingerprint"],
            "state": "known",
            "state_reason": "authoritative_project_allocation_coverage",
            "assignment_state": (
                "assigned" if any(item["allocation"] > 0 for item in allocations) else "empty"
            ),
            "assignments": [item for item in allocations if item["allocation"] > 0],
            "explicit_zero_member_ids": [
                item["member_id"] for item in allocations if item["allocation"] == 0
            ],
        }
    finally:
        database.close()
