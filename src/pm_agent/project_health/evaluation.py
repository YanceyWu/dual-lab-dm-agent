"""Deterministic, evidence-bounded seven-dimension health assessment."""

from __future__ import annotations

import json
import uuid
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from pm_agent.project_health.configuration import _params, effective_current
from pm_agent.project_health.service import CATALOG_VERSION, _connection, _json, _now


_FACTOR_DEFINITIONS = {
    "schedule_critical_milestone_adherence": ("schedule", ("milestone_adherence",)),
    "schedule_target_change": ("schedule", ("release_target_date_change",)),
    "delivery_sprint_completion": ("delivery", ("sprint_completion",)),
    "delivery_carry_over": ("delivery", ("sprint_carry_over",)),
    "scope_release_readiness": ("scope", ("release_scope_count",)),
    "quality_readiness_gate": ("quality", ("quality_readiness_gate",)),
    "resource_capacity_coverage": ("resource", ("capacity_coverage",)),
    "dependency_readiness": ("dependency", ("dependency_readiness",)),
    "governance_decision_readiness": ("governance", ("governance_decision_gate",)),
}
_DIMENSIONS = ("schedule", "delivery", "scope", "quality", "resource", "dependency", "governance")
def _limited_state(rows: list[dict[str, Any]], unavailable: str) -> str | None:
    if not rows:
        return unavailable
    if any(row["value_state"] == "conflicting" for row in rows):
        return "conflicting"
    if any(row["freshness_state"] in {"failed", "partial", "never_observed"} for row in rows):
        return "unknown"
    if any(row["freshness_state"] == "stale" for row in rows):
        return "stale"
    if any(row["value_state"] == "unavailable" for row in rows):
        return "not_available"
    if any(row["value_state"] != "known" for row in rows):
        return "unknown"
    return None


def _fact_evidence(rows: list[dict[str, Any]], allowed: tuple[str, ...]) -> list[dict[str, Any]]:
    return [
        {
            "fact_id": row["fact_id"],
            "fact_key": row["fact_key"],
            "subject_kind": row["subject_kind"],
            "subject_id": row["subject_id"],
            "value_state": row["value_state"],
            "freshness_state": row["freshness_state"],
            "evidence": json.loads(row["evidence_json"]),
        }
        for row in rows
        if row["fact_key"] in allowed
    ]


def _factor_state(
    factor_id: str, rows: list[dict[str, Any]], parameters: dict[str, int], critical_overdue: bool
) -> tuple[str, list[str], list[str]]:
    """Return state, deterministic reason codes, and warnings for one fixed factor."""
    if factor_id == "schedule_critical_milestone_adherence":
        if critical_overdue:
            return "red", ["CRITICAL_MILESTONE_OVERDUE"], []
        limited = _limited_state(rows, "unknown")
        if limited:
            return limited, ["MILESTONE_ADHERENCE_" + limited.upper()], []
        values = [json.loads(row["value_json"]) for row in rows]
        if any(value in {"overdue", "achieved_late"} for value in values):
            return "red", ["CRITICAL_MILESTONE_ADHERENCE_RED"], []
        return "green", ["CRITICAL_MILESTONE_ADHERENCE_OK"], []
    if factor_id == "schedule_target_change":
        limited = _limited_state(rows, "unknown")
        if limited:
            return limited, ["TARGET_CHANGE_" + limited.upper()], []
        changed = any(
            isinstance((value := json.loads(row["value_json"])), dict)
            and value.get("first") and value.get("latest") and value["first"] != value["latest"]
            for row in rows
        )
        return ("amber", ["RELEASE_TARGET_CHANGED"], []) if changed else ("green", ["RELEASE_TARGET_UNCHANGED"], [])
    if factor_id == "scope_release_readiness":
        limited = _limited_state(rows, "unknown")
        if limited:
            return limited, ["RELEASE_SCOPE_" + limited.upper()], []
        values = [json.loads(row["value_json"]) for row in rows]
        if not all(isinstance(value, dict) and isinstance(value.get("total"), int) and isinstance(value.get("done"), int) and value["total"] > 0 and 0 <= value["done"] <= value["total"] for value in values):
            return "unknown", ["RELEASE_SCOPE_VALUE_INVALID"], ["RELEASE_SCOPE_VALUE_INVALID"]
        completion = min(value["done"] * 100 / value["total"] for value in values)
        return (
            ("green", ["RELEASE_SCOPE_COMPLETION_MET"], [])
            if completion >= parameters["scope_completion_green_minimum"]
            else ("amber", ["RELEASE_SCOPE_COMPLETION_BELOW_THRESHOLD"], [])
        )
    if factor_id == "dependency_readiness":
        limited = _limited_state(rows, "unknown")
        if limited:
            return limited, ["DEPENDENCY_READINESS_" + limited.upper()], []
        # Phase 3 currently proves an active link, not whether its prerequisite is ready.
        return "unknown", ["DEPENDENCY_READINESS_SEMANTICS_NOT_AVAILABLE"], []
    return "not_available", ["APPROVED_SOURCE_FACT_NOT_AVAILABLE"], []


def _aggregate_dimension(factor_states: list[str], guards: list[dict[str, Any]]) -> str:
    if any(guard["state"] == "red" for guard in guards) or "red" in factor_states:
        return "red"
    if "amber" in factor_states:
        return "amber"
    if factor_states and all(state == "green" for state in factor_states):
        return "green"
    if "conflicting" in factor_states:
        return "conflicting"
    if "stale" in factor_states:
        return "stale"
    if "not_available" in factor_states and all(state == "not_available" for state in factor_states):
        return "not_available"
    return "unknown"


def evaluate(project_id: str, *, db_path: str | Path | None = None) -> dict[str, Any]:
    """Persist a new assessment. It neither changes configuration nor legacy health."""
    with _connection(db_path) as conn:
        if not conn.execute("SELECT 1 FROM projects WHERE id=?", [project_id]).fetchone():
            raise ValueError("PROJECT_NOT_FOUND")
        config = effective_current(conn, project_id)
        parameters = _params(json.loads(config["parameters_json"]))
        milestones = conn.execute(
            "SELECT milestone_id,planned_date,lifecycle_state,completeness_state,observed_at FROM execution_milestones WHERE project_id=? AND criticality='critical'",
            [project_id],
        ).fetchall()
        critical_milestone_ids = {row["milestone_id"] for row in milestones}
        cutoff = date.today() - timedelta(days=parameters["critical_milestone_tolerance_days"])
        overdue = [row for row in milestones if row["planned_date"] and row["lifecycle_state"] not in {"achieved", "cancelled"} and row["completeness_state"] == "known" and date.fromisoformat(row["planned_date"]) < cutoff]
        guards = ([{"guard_id": "critical_milestone_overdue", "dimension": "schedule", "state": "red", "reason_code": "CRITICAL_MILESTONE_OVERDUE", "evidence_refs": [row["milestone_id"] for row in overdue]}] if overdue else [])
        latest_facts = conn.execute(
            """SELECT f.fact_id,f.subject_kind,f.subject_id,f.fact_key,f.value_json,f.value_state,
                      f.freshness_state,f.evidence_json
               FROM execution_facts f JOIN execution_derivation_runs r ON r.derivation_run_id=f.derivation_run_id
               WHERE f.project_id=? AND r.completeness_state='complete'
                 AND NOT EXISTS (SELECT 1 FROM execution_derivation_runs later
                     WHERE later.project_id=r.project_id AND later.board_id=r.board_id
                       AND (later.finished_at>r.finished_at OR (later.finished_at=r.finished_at AND later.derivation_run_id>r.derivation_run_id)))""",
            [project_id],
        ).fetchall()
        by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in latest_facts:
            by_key[row["fact_key"]].append(dict(row))
        factor_results: dict[str, dict[str, Any]] = {}
        for factor_id, (dimension, allowed) in _FACTOR_DEFINITIONS.items():
            rows = [row for key in allowed for row in by_key[key]]
            if factor_id == "schedule_critical_milestone_adherence":
                rows = [row for row in rows if row["subject_id"] in critical_milestone_ids]
            state, reasons, warnings = _factor_state(factor_id, rows, parameters, bool(overdue))
            factor_results[factor_id] = {
                "factor_id": factor_id,
                "catalog_version": CATALOG_VERSION,
                "dimension": dimension,
                "state": state,
                "severity": state if state in {"red", "amber"} else None,
                "allowed_source_fact_keys": list(allowed),
                "evidence_refs": _fact_evidence(rows, allowed),
                "guard_evidence_refs": [
                    reference
                    for guard in guards
                    if factor_id == "schedule_critical_milestone_adherence" and guard["dimension"] == dimension
                    for reference in guard["evidence_refs"]
                ],
                "completeness": "complete" if rows and all(row["value_state"] == "known" for row in rows) else "limited",
                "freshness": "fresh" if rows and all(row["freshness_state"] == "fresh" for row in rows) else "limited",
                "warnings": warnings,
                "reason_codes": reasons,
            }
        dimensions = {
            dimension: _aggregate_dimension(
                [result["state"] for result in factor_results.values() if result["dimension"] == dimension],
                [guard for guard in guards if guard["dimension"] == dimension],
            )
            for dimension in _DIMENSIONS
        }
        overall = "red" if "red" in dimensions.values() else "amber" if "amber" in dimensions.values() else "green" if all(state == "green" for state in dimensions.values()) else "unknown"
        legacy_rows = conn.execute(
            """SELECT h.overall_grade, cs.rag_status FROM jira_board_configs b
               LEFT JOIN jira_health_snapshots h ON h.id=(SELECT id FROM jira_health_snapshots WHERE board_id=b.id ORDER BY snapshot_date DESC,id DESC LIMIT 1)
               LEFT JOIN confluence_status_snapshots cs ON cs.id=(SELECT id FROM confluence_status_snapshots WHERE board_id=b.id ORDER BY snapshot_date DESC,id DESC LIMIT 1)
               WHERE b.pm_project_id=? AND b.active=1""", [project_id]
        ).fetchall()
        legacy_states = sorted({str(row["overall_grade"] or row["rag_status"] or "").lower() for row in legacy_rows if row["overall_grade"] or row["rag_status"]})
        legacy = {"states": legacy_states, "state": "not_available" if not legacy_states else "available"}
        run = f"health-assessment-{uuid.uuid4().hex}"
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("INSERT INTO project_health_assessment_runs VALUES (?,?,?,?,?)", [run, project_id, CATALOG_VERSION, overall, _now()])
        conn.execute("INSERT INTO project_health_assessment_details VALUES (?,?,?,?)", [run, config["configuration_version_id"], _json(guards), _json(legacy)])
        for dimension, state in dimensions.items():
            conn.execute("INSERT INTO project_health_dimension_results VALUES (?,?,?)", [run, dimension, state])
        for factor_id, result in factor_results.items():
            conn.execute("INSERT INTO project_health_factor_results VALUES (?,?,?,?)", [run, factor_id, result["state"], _json(result)])
        conn.commit()
    return {"assessment_run_id": run, "project_id": project_id, "dimensions": dimensions, "overall_state": overall, "configuration_version_id": config["configuration_version_id"], "guard_outcomes": guards, "legacy_comparison": legacy}
