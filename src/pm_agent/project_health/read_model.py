"""Read-only projection of persisted layered Project Health assessments."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pm_agent.project_health.service import _connection


def latest_assessments(
    *, project_id: str | None = None, db_path: str | Path | None = None
) -> list[dict[str, Any]]:
    """Return only persisted latest assessments; never evaluate or reconcile."""
    with _connection(db_path) as connection:
        if project_id and not connection.execute(
            "SELECT 1 FROM projects WHERE id=?", [project_id]
        ).fetchone():
            raise ValueError("PROJECT_NOT_FOUND")
        rows = connection.execute(
            """SELECT ar.assessment_run_id,ar.project_id,ar.catalog_version,ar.state,ar.created_at,
                      ad.configuration_version_id,ad.guard_outcomes_json,ad.legacy_comparison_json
               FROM project_health_assessment_runs ar
               JOIN project_health_assessment_details ad ON ad.assessment_run_id=ar.assessment_run_id
               WHERE (? IS NULL OR ar.project_id=?)
                 AND NOT EXISTS (
                     SELECT 1 FROM project_health_assessment_runs later
                     WHERE later.project_id=ar.project_id
                       AND (later.created_at>ar.created_at OR (
                           later.created_at=ar.created_at AND later.assessment_run_id>ar.assessment_run_id))
                 )
               ORDER BY ar.project_id""",
            [project_id, project_id],
        ).fetchall()
        result = []
        for row in rows:
            assessment = dict(row)
            assessment["guard_outcomes"] = json.loads(assessment.pop("guard_outcomes_json"))
            assessment["legacy_comparison"] = json.loads(
                assessment.pop("legacy_comparison_json")
            )
            dimensions = connection.execute(
                "SELECT dimension,state FROM project_health_dimension_results WHERE assessment_run_id=? ORDER BY dimension",
                [assessment["assessment_run_id"]],
            ).fetchall()
            factors = connection.execute(
                "SELECT factor_id,state,evidence_json FROM project_health_factor_results WHERE assessment_run_id=? ORDER BY factor_id",
                [assessment["assessment_run_id"]],
            ).fetchall()
            assessment["dimensions"] = {item["dimension"]: item["state"] for item in dimensions}
            assessment["factors"] = [
                {"factor_id": item["factor_id"], "state": item["state"], "detail": json.loads(item["evidence_json"])}
                for item in factors
            ]
            result.append(assessment)
        return result
