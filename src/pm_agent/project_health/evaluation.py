"""Deterministic internal seven-dimension assessment persistence."""

from __future__ import annotations
import json
import uuid
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from pm_agent.project_health.service import CATALOG_VERSION, _connection, _json, _now
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
        factor_states = {
            "schedule_critical_milestone_adherence": schedule,
            "schedule_target_change": "unknown",
            "delivery_sprint_completion": "not_available",
            "delivery_carry_over": "not_available",
            "scope_release_readiness": "unknown",
            "quality_readiness_gate": "not_available",
            "resource_capacity_coverage": "not_available",
            "dependency_readiness": "unknown",
            "governance_decision_readiness": "not_available",
        }
        legacy_rows = conn.execute(
            """SELECT h.overall_grade, cs.rag_status FROM jira_board_configs b
               LEFT JOIN jira_health_snapshots h ON h.id=(SELECT id FROM jira_health_snapshots WHERE board_id=b.id ORDER BY snapshot_date DESC,id DESC LIMIT 1)
               LEFT JOIN confluence_status_snapshots cs ON cs.id=(SELECT id FROM confluence_status_snapshots WHERE board_id=b.id ORDER BY snapshot_date DESC,id DESC LIMIT 1)
               WHERE b.pm_project_id=? AND b.active=1""", [project_id]
        ).fetchall()
        legacy_states = sorted({str(row["overall_grade"] or row["rag_status"] or "").lower() for row in legacy_rows if row["overall_grade"] or row["rag_status"]})
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
        for factor_id, state in factor_states.items():
            conn.execute(
                "INSERT INTO project_health_factor_results VALUES (?,?,?,?)",
                [run, factor_id, state, _json({"source": "canonical"})],
            )
        conn.commit()
    return {
        "assessment_run_id": run,
        "project_id": project_id,
        "dimensions": dimensions,
        "overall_state": overall,
        "configuration_version_id": config["configuration_version_id"],
        "legacy_comparison": {"states": legacy_states, "state": "not_available" if not legacy_states else "available"},
    }
