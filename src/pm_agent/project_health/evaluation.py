"""Deterministic internal seven-dimension assessment persistence."""

from __future__ import annotations
import json
import uuid
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from pm_agent.project_health.service import CATALOG_VERSION, _connection, _now
from pm_agent.project_health.configuration import _current


def evaluate(project_id: str, *, db_path: str | Path | None = None) -> dict[str, Any]:
    with _connection(db_path) as conn:
        if not conn.execute("SELECT 1 FROM projects WHERE id=?", [project_id]).fetchone():
            raise ValueError("PROJECT_NOT_FOUND")
        config = _current(conn, "project", project_id)
        if config["configuration_version_id"] == "catalog-default-v1":
            config = _current(conn, "default", "")
        tolerance = json.loads(config["parameters_json"])["critical_milestone_tolerance_days"]
        milestones = conn.execute(
            "SELECT planned_date,lifecycle_state FROM execution_milestones WHERE project_id=? AND criticality='critical'",
            [project_id],
        ).fetchall()
        schedule = (
            "red"
            if any(
                r["planned_date"]
                and r["lifecycle_state"] not in {"achieved", "cancelled"}
                and date.fromisoformat(r["planned_date"]) < date.today() - timedelta(days=tolerance)
                for r in milestones
            )
            else "unknown"
        )
        dimensions = {
            "schedule": schedule,
            "delivery": "not_available",
            "scope": "unknown",
            "quality": "not_available",
            "resource": "not_available",
            "dependency": "unknown",
            "governance": "not_available",
        }
        overall = "red" if schedule == "red" else "unknown"
        run = f"health-assessment-{uuid.uuid4().hex}"
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "INSERT INTO project_health_assessment_runs VALUES (?,?,?,?,?)",
            [run, project_id, CATALOG_VERSION, overall, _now()],
        )
        for dimension, state in dimensions.items():
            conn.execute(
                "INSERT INTO project_health_dimension_results VALUES (?,?,?)",
                [run, dimension, state],
            )
        conn.commit()
    return {
        "assessment_run_id": run,
        "project_id": project_id,
        "dimensions": dimensions,
        "overall_state": overall,
        "configuration_version_id": config["configuration_version_id"],
        "legacy_comparison": "not_available",
    }
