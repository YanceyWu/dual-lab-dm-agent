"""Project Health catalog projection and clean structured re-import contract."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from pm_agent.config import settings
from pm_agent.database import execution

CATALOG_VERSION = "project-health-catalog-v1"
PACKAGE_VERSION = "project-health-reimport-v1"
_FACTORS = (
    ("schedule_critical_milestone_adherence", "schedule", "canonical_milestone_release", "unknown"),
    ("schedule_target_change", "schedule", "canonical_milestone_release", "unknown"),
    ("delivery_sprint_completion", "delivery", "canonical_sprint", "not_available"),
    ("delivery_carry_over", "delivery", "canonical_sprint", "not_available"),
    ("scope_release_readiness", "scope", "canonical_release_scope", "unknown"),
    ("quality_readiness_gate", "quality", "structured_quality_gate", "not_available"),
    ("resource_capacity_coverage", "resource", "structured_capacity_coverage", "not_available"),
    ("dependency_readiness", "dependency", "canonical_dependency", "unknown"),
    ("governance_decision_readiness", "governance", "structured_governance_gate", "not_available"),
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


@contextmanager
def _connection(db_path: str | Path | None = None) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(Path(db_path or settings.database_path), isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 10000")
    try:
        yield connection
    finally:
        connection.close()


def seed_catalog(connection: sqlite3.Connection) -> None:
    """Seed the immutable Project Health catalogue and default read projection."""
    for factor_id, dimension, boundary, policy in _FACTORS:
        connection.execute(
            """INSERT OR IGNORE INTO project_health_factor_catalog
               (factor_id,catalog_version,dimension,evidence_boundary,availability_policy)
               VALUES (?,?,?,?,?)""",
            [factor_id, CATALOG_VERSION, dimension, boundary, policy],
        )
        condition = {"version": "default-v1", "operators": ["in", "equals", "less_than", "less_than_or_equal", "greater_than", "greater_than_or_equal", "days_before", "days_after"], "state": "fixed_catalog_only"}
        connection.execute(
            """INSERT OR IGNORE INTO project_health_default_conditions
               (condition_id,factor_id,condition_version,condition_json)
               VALUES (?,?,?,?)""",
            [f"condition-{factor_id}-v1", factor_id, "default-v1", _json(condition)],
        )


def catalog_projection(*, project_id: str | None = None, db_path: str | Path | None = None) -> dict[str, Any]:
    """Read the fixed catalogue and the current bounded configuration projection."""
    with _connection(db_path) as connection:
        if project_id is not None and not connection.execute("SELECT 1 FROM projects WHERE id = ?", [project_id]).fetchone():
            raise ValueError("PROJECT_NOT_FOUND")
        rows = connection.execute(
            """SELECT c.factor_id,c.catalog_version,c.dimension,c.evidence_boundary,
                      c.availability_policy,d.condition_version,d.condition_json
                 FROM project_health_factor_catalog c
                 JOIN project_health_default_conditions d ON d.factor_id=c.factor_id AND d.active=1
                WHERE c.active=1 ORDER BY c.dimension,c.factor_id"""
        ).fetchall()
        # Local import avoids a configuration/service import cycle while keeping this
        # catalogue read model independent from the controlled-write owner.
        from pm_agent.project_health.configuration import _params, effective_current

        configuration = effective_current(connection, project_id)
        effective_configuration = _params(json.loads(configuration["parameters_json"]))
    factors = []
    for row in rows:
        item = dict(row)
        item["condition"] = json.loads(item.pop("condition_json"))
        factors.append(item)
    return {
        "catalog_version": CATALOG_VERSION,
        "project_id": project_id,
        "factors": factors,
        "effective_configuration": effective_configuration,
        "configuration_version_id": configuration["configuration_version_id"],
        "override_state": "available" if project_id and configuration["configuration_version_id"] != "catalog-default-v1" and configuration["scope"] == "project" else "not_available",
        "configuration_mutation": "internal_controlled_preview_confirm",
    }


def _validate_package(payload: object) -> dict[str, Any]:
    allowed = {"dataset_marker", "package_id", "schema_version", "board_ids", "inputs"}
    required = {"package_id", "schema_version", "board_ids", "inputs"}
    if not isinstance(payload, dict) or not required <= set(payload) or set(payload) - allowed:
        raise ValueError("HEALTH_REIMPORT_PACKAGE_INVALID")
    package_id = payload["package_id"]
    if not isinstance(package_id, str) or not package_id.strip() or len(package_id.strip()) > 128:
        raise ValueError("HEALTH_REIMPORT_PACKAGE_INVALID")
    if payload["schema_version"] != PACKAGE_VERSION or not isinstance(payload["inputs"], list):
        raise ValueError("HEALTH_REIMPORT_PACKAGE_VERSION_INVALID")
    board_ids = payload["board_ids"]
    if not isinstance(board_ids, list) or not all(
        isinstance(item, str) and item.strip() and len(item.strip()) <= 200 for item in board_ids
    ):
        raise ValueError("HEALTH_REIMPORT_BOARD_IDS_INVALID")
    # The structured-input family is reserved until an approved producer exists.
    if payload["inputs"]:
        raise ValueError("HEALTH_INPUT_PRODUCER_NOT_AVAILABLE")
    return {"package_id": package_id.strip(), "schema_version": PACKAGE_VERSION, "board_ids": sorted(set(item.strip() for item in board_ids)), "inputs": []}


def _validate_boards(connection: sqlite3.Connection, board_ids: list[str]) -> None:
    for board_id in board_ids:
        row = connection.execute(
            "SELECT pm_project_id FROM jira_board_configs WHERE id = ?", [board_id]
        ).fetchone()
        if not row or not row["pm_project_id"]:
            raise ValueError("HEALTH_REIMPORT_BOARD_NOT_FOUND")


def preview_reimport(payload: object, *, db_path: str | Path | None = None) -> dict[str, Any]:
    package = _validate_package(payload)
    fingerprint = hashlib.sha256(_json(package).encode()).hexdigest()
    with _connection(db_path) as connection:
        _validate_boards(connection, package["board_ids"])
        existing = connection.execute("SELECT * FROM project_health_reimport_sessions WHERE package_fingerprint=?", [fingerprint]).fetchone()
        if existing and existing["status"] == "completed":
            return {"status": "already_completed", "session_id": existing["session_id"], "idempotent": True, "report": json.loads(existing["report_json"])}
        if existing:
            return {"status": "retryable", "session_id": existing["session_id"], "idempotent": False}
        session_id = f"health-reimport-{uuid.uuid4().hex}"
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            """INSERT INTO project_health_reimport_sessions
               (session_id,package_id,package_version,package_fingerprint,package_json,status,created_at)
               VALUES (?,?,?,?,?, 'previewed', ?)""",
            [session_id, package["package_id"], PACKAGE_VERSION, fingerprint, _json(package), _now()],
        )
        connection.commit()
    return {"status": "previewed", "session_id": session_id, "package": package, "planned_steps": ["validate", "canonical_derivation", "health_coverage"]}


def _coverage(connection: sqlite3.Connection, derivations: list[dict[str, Any]]) -> dict[str, Any]:
    projects = sorted({item["project_id"] for item in derivations})
    dimensions: dict[str, dict[str, str]] = {}
    for project_id in projects:
        dimensions[project_id] = {
            "schedule": "unknown", "delivery": "not_available", "scope": "unknown",
            "quality": "not_available", "resource": "not_available", "dependency": "unknown", "governance": "not_available",
        }
    return {"project_count": len(projects), "dimensions": dimensions, "assessment_state": "not_available", "reason_codes": ["PROJECT_HEALTH_ASSESSMENT_NOT_RUN", "QUALITY_INPUT_NOT_AVAILABLE", "RESOURCE_INPUT_NOT_AVAILABLE", "GOVERNANCE_INPUT_NOT_AVAILABLE"], "canonical_derivations": derivations}


def _integrity(connection: sqlite3.Connection) -> dict[str, Any]:
    integrity_rows = [row[0] for row in connection.execute("PRAGMA integrity_check")]
    foreign_key_rows = [tuple(row) for row in connection.execute("PRAGMA foreign_key_check")]
    return {"sqlite_integrity": "ok" if integrity_rows == ["ok"] else "failed", "foreign_key_violations": len(foreign_key_rows), "state": "passed" if integrity_rows == ["ok"] and not foreign_key_rows else "failed"}


def confirm_reimport(session_id: str, *, db_path: str | Path | None = None) -> dict[str, Any]:
    with _connection(db_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute("SELECT * FROM project_health_reimport_sessions WHERE session_id=?", [session_id]).fetchone()
        if not row:
            raise ValueError("HEALTH_REIMPORT_SESSION_NOT_FOUND")
        if row["status"] == "completed":
            connection.commit()
            return {"status": "completed", "session_id": session_id, "idempotent": True, "report": json.loads(row["report_json"])}
        if row["status"] not in {"previewed", "running", "failed"}:
            raise ValueError("HEALTH_REIMPORT_SESSION_NOT_CONFIRMABLE")
        connection.execute("UPDATE project_health_reimport_sessions SET status='running' WHERE session_id=?", [session_id])
        attempt_id = f"health-attempt-{uuid.uuid4().hex}"
        connection.execute("INSERT INTO project_health_reimport_attempts (attempt_id,session_id,status,started_at) VALUES (?,?,'running',?)", [attempt_id, session_id, _now()])
        connection.commit()
        try:
            package = json.loads(row["package_json"])
            derivation_results = [execution.derive_board(board_id, db_path=db_path) for board_id in package["board_ids"]]
            connection.execute("BEGIN IMMEDIATE")
            now = _now()
            derivations = []
            for result in derivation_results:
                details = connection.execute("SELECT project_id,board_id,completeness_state,freshness_state,warning_codes_json FROM execution_derivation_runs WHERE derivation_run_id=?", [result["derivation_run_id"]]).fetchone()
                derivations.append({"derivation_run_id": result["derivation_run_id"], "project_id": details["project_id"], "board_id": details["board_id"], "idempotent": result["idempotent"], "fact_count": result["fact_count"], "completeness_state": details["completeness_state"], "freshness_state": details["freshness_state"], "warning_codes": json.loads(details["warning_codes_json"])})
            _record_step(connection, session_id, "validate", "completed", {"input_count": 0, "board_count": len(package["board_ids"])}, [])
            _record_step(connection, session_id, "canonical_derivation", "completed", {"derivation_run_count": len(derivations)}, [])
            report = _coverage(connection, derivations)
            integrity = _integrity(connection)
            _record_step(connection, session_id, "health_coverage", "completed" if integrity["state"] == "passed" else "failed", {"project_count": report["project_count"]}, report["reason_codes"])
            final_status = "completed" if integrity["state"] == "passed" else "failed"
            warnings = report["reason_codes"] + ([] if final_status == "completed" else ["HEALTH_REIMPORT_INTEGRITY_FAILED"])
            final_report = {**report, "integrity": integrity, "reconciliation_state": "not_available", "attempt_id": attempt_id}
            connection.execute("UPDATE project_health_reimport_sessions SET status=?,completed_at=?,warning_codes_json=?,integrity_json=?,report_json=? WHERE session_id=?", [final_status, now, _json(warnings), _json(integrity), _json(final_report), session_id])
            connection.execute("UPDATE project_health_reimport_attempts SET status=?,finished_at=?,warning_codes_json=? WHERE attempt_id=?", [final_status, now, _json(warnings), attempt_id])
            connection.commit()
        except Exception:
            connection.rollback()
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("UPDATE project_health_reimport_sessions SET status='failed',completed_at=?,warning_codes_json=? WHERE session_id=?", [_now(), _json(["HEALTH_REIMPORT_PARTIAL_FAILURE"]), session_id])
            _record_step(connection, session_id, "validate", "failed", {}, ["HEALTH_REIMPORT_PARTIAL_FAILURE"])
            connection.execute("UPDATE project_health_reimport_attempts SET status='failed',finished_at=?,warning_codes_json=? WHERE attempt_id=?", [_now(), _json(["HEALTH_REIMPORT_PARTIAL_FAILURE"]), attempt_id])
            connection.commit()
            raise
    return {"status": final_status, "session_id": session_id, "idempotent": False, "report": final_report}


def _record_step(connection: sqlite3.Connection, session_id: str, step_key: str, status: str, counts: dict[str, Any], warnings: list[str]) -> None:
    connection.execute("""INSERT INTO project_health_reimport_runs (import_run_id,session_id,step_key,status,counts_json,warnings_json,created_at) VALUES (?,?,?,?,?,?,?) ON CONFLICT(session_id,step_key) DO UPDATE SET status=excluded.status,counts_json=excluded.counts_json,warnings_json=excluded.warnings_json,created_at=excluded.created_at""", [f"health-run-{uuid.uuid4().hex}", session_id, step_key, status, _json(counts), _json(warnings), _now()])
