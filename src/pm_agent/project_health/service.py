"""Batch A catalog projection and clean structured re-import contract."""

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
    """Seed the immutable Batch A catalogue and default read projection."""
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
    """Read the fixed catalogue and effective defaults; overrides are intentionally absent."""
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
    factors = []
    for row in rows:
        item = dict(row)
        item["condition"] = json.loads(item.pop("condition_json"))
        factors.append(item)
    return {"catalog_version": CATALOG_VERSION, "project_id": project_id, "factors": factors, "override_state": "not_available", "configuration_mutation": "not_available"}


def _validate_package(payload: object) -> dict[str, Any]:
    allowed = {"dataset_marker", "package_id", "schema_version", "inputs"}
    if not isinstance(payload, dict) or not {"package_id", "schema_version", "inputs"} <= set(payload) or set(payload) - allowed:
        raise ValueError("HEALTH_REIMPORT_PACKAGE_INVALID")
    package_id = payload["package_id"]
    if not isinstance(package_id, str) or not package_id.strip() or len(package_id.strip()) > 128:
        raise ValueError("HEALTH_REIMPORT_PACKAGE_INVALID")
    if payload["schema_version"] != PACKAGE_VERSION or not isinstance(payload["inputs"], list):
        raise ValueError("HEALTH_REIMPORT_PACKAGE_VERSION_INVALID")
    # Batch A reserves the structured-input family but deliberately has no approved producer.
    if payload["inputs"]:
        raise ValueError("HEALTH_INPUT_PRODUCER_NOT_AVAILABLE")
    return {"package_id": package_id.strip(), "schema_version": PACKAGE_VERSION, "inputs": []}


def preview_reimport(payload: object, *, db_path: str | Path | None = None) -> dict[str, Any]:
    package = _validate_package(payload)
    fingerprint = hashlib.sha256(_json(package).encode()).hexdigest()
    with _connection(db_path) as connection:
        existing = connection.execute("SELECT * FROM project_health_reimport_sessions WHERE package_fingerprint=?", [fingerprint]).fetchone()
        if existing and existing["status"] == "completed":
            return {"status": "already_completed", "session_id": existing["session_id"], "idempotent": True, "report": json.loads(existing["report_json"])}
        if existing:
            return {"status": existing["status"], "session_id": existing["session_id"], "idempotent": False}
        session_id = f"health-reimport-{uuid.uuid4().hex}"
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            """INSERT INTO project_health_reimport_sessions
               (session_id,package_id,package_version,package_fingerprint,status,created_at)
               VALUES (?,?,?,?, 'previewed', ?)""",
            [session_id, package["package_id"], PACKAGE_VERSION, fingerprint, _now()],
        )
        connection.commit()
    return {"status": "previewed", "session_id": session_id, "package": package, "planned_steps": ["validate", "canonical_derivation", "health_coverage"]}


def _coverage(connection: sqlite3.Connection) -> dict[str, Any]:
    projects = [row[0] for row in connection.execute("SELECT id FROM projects ORDER BY id")]
    dimensions: dict[str, dict[str, str]] = {}
    for project_id in projects:
        dimensions[project_id] = {
            "schedule": "unknown", "delivery": "not_available", "scope": "unknown",
            "quality": "not_available", "resource": "not_available", "dependency": "unknown", "governance": "not_available",
        }
    return {"project_count": len(projects), "dimensions": dimensions, "assessment_state": "not_available", "reason_codes": ["PHASE4_ASSESSMENT_BATCH_B_NOT_IMPLEMENTED", "QUALITY_INPUT_NOT_AVAILABLE", "RESOURCE_INPUT_NOT_AVAILABLE", "GOVERNANCE_INPUT_NOT_AVAILABLE"]}


def confirm_reimport(session_id: str, *, db_path: str | Path | None = None) -> dict[str, Any]:
    with _connection(db_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute("SELECT * FROM project_health_reimport_sessions WHERE session_id=?", [session_id]).fetchone()
        if not row:
            raise ValueError("HEALTH_REIMPORT_SESSION_NOT_FOUND")
        if row["status"] == "completed":
            connection.commit()
            return {"status": "completed", "session_id": session_id, "idempotent": True, "report": json.loads(row["report_json"])}
        if row["status"] != "previewed":
            raise ValueError("HEALTH_REIMPORT_SESSION_NOT_CONFIRMABLE")
        connection.execute("UPDATE project_health_reimport_sessions SET status='running' WHERE session_id=?", [session_id])
        connection.commit()
        connection.execute("BEGIN IMMEDIATE")
        now = _now()
        try:
            connection.execute("INSERT INTO project_health_reimport_runs (import_run_id,session_id,step_key,status,counts_json,warnings_json,created_at) VALUES (?,?,?,?,?,?,?)", [f"health-run-{uuid.uuid4().hex}", session_id, "validate", "completed", _json({"input_count": 0}), "[]", now])
            # Derivation is deliberately not run implicitly. Batch A reports its persisted state.
            derivation_count = connection.execute("SELECT COUNT(*) FROM execution_derivation_runs WHERE finished_at != ''").fetchone()[0]
            connection.execute("INSERT INTO project_health_reimport_runs (import_run_id,session_id,step_key,status,counts_json,warnings_json,created_at) VALUES (?,?,?,?,?,?,?)", [f"health-run-{uuid.uuid4().hex}", session_id, "canonical_derivation", "completed" if derivation_count else "skipped", _json({"derivation_run_count": derivation_count}), _json([] if derivation_count else ["CANONICAL_DERIVATION_NOT_AVAILABLE"]), now])
            report = _coverage(connection)
            connection.execute("INSERT INTO project_health_reimport_runs (import_run_id,session_id,step_key,status,counts_json,warnings_json,created_at) VALUES (?,?,?,?,?,?,?)", [f"health-run-{uuid.uuid4().hex}", session_id, "health_coverage", "completed", _json({"project_count": report["project_count"]}), _json(report["reason_codes"]), now])
            connection.execute("UPDATE project_health_reimport_sessions SET status='completed',completed_at=?,warning_codes_json=?,report_json=? WHERE session_id=?", [now, _json(report["reason_codes"]), _json(report), session_id])
            connection.commit()
        except Exception:
            connection.rollback()
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("UPDATE project_health_reimport_sessions SET status='failed',completed_at=?,warning_codes_json=? WHERE session_id=?", [_now(), _json(["HEALTH_REIMPORT_PARTIAL_FAILURE"]), session_id])
            connection.execute("INSERT INTO project_health_reimport_runs (import_run_id,session_id,step_key,status,counts_json,warnings_json,created_at) VALUES (?,?,?,?,?,?,?)", [f"health-run-{uuid.uuid4().hex}", session_id, "validate", "failed", "{}", _json(["HEALTH_REIMPORT_PARTIAL_FAILURE"]), _now()])
            connection.commit()
            raise
    return {"status": "completed", "session_id": session_id, "idempotent": False, "report": report}
