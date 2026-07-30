"""Controlled health-condition configuration; no public transport."""

from __future__ import annotations
import hashlib
import json
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from pm_agent.project_health.service import _connection, _json, _now


DEFAULT_PARAMETERS = {
    "critical_milestone_tolerance_days": 0,
    "scope_completion_green_minimum": 100,
}


def _params(value: object) -> dict[str, int]:
    if not isinstance(value, dict) or set(value) - set(DEFAULT_PARAMETERS):
        raise ValueError("HEALTH_CONFIGURATION_INVALID")
    normalized = {**DEFAULT_PARAMETERS, **value}
    days = normalized["critical_milestone_tolerance_days"]
    if not isinstance(days, int) or not 0 <= days <= 90:
        raise ValueError("HEALTH_CONFIGURATION_INVALID")
    completion = normalized["scope_completion_green_minimum"]
    if not isinstance(completion, int) or not 0 <= completion <= 100:
        raise ValueError("HEALTH_CONFIGURATION_INVALID")
    return normalized


def _current(conn, scope: str, project: str):
    row = conn.execute(
        "SELECT * FROM project_health_configuration_versions WHERE scope=? AND project_id=? AND is_current=1",
        [scope, project],
    ).fetchone()
    return (
        dict(row)
        if row
        else {
            "parameters_json": _json(DEFAULT_PARAMETERS),
            "configuration_version_id": "catalog-default-v1",
        }
    )


def effective_current(conn, project_id: str | None = None):
    """Resolve the bounded default plus an existing-project replacement override."""
    if project_id:
        project = _current(conn, "project", project_id)
        if project["configuration_version_id"] != "catalog-default-v1":
            return project
    return _current(conn, "default", "")


def _fingerprint(scope: str, project: str, effective_parameters: dict[str, int]) -> str:
    return hashlib.sha256(_json([scope, project, effective_parameters]).encode()).hexdigest()


def preview(
    *, parameters: object, project_id: str | None = None, db_path: str | Path | None = None
) -> dict[str, Any]:
    proposed = _params(parameters)
    scope, project = (
        ("project", project_id.strip())
        if isinstance(project_id, str) and project_id.strip()
        else ("default", "")
    )
    with _connection(db_path) as conn:
        if (
            scope == "project"
            and not conn.execute("SELECT 1 FROM projects WHERE id=?", [project]).fetchone()
        ):
            raise ValueError("PROJECT_NOT_FOUND")
        prior = _current(conn, scope, project)
        prior_parameters = _params(json.loads(prior["parameters_json"]))
        effective_prior = _params(json.loads(effective_current(conn, project if scope == "project" else None)["parameters_json"]))
        if (scope == "default" and prior_parameters == proposed) or (
            scope == "project" and effective_prior == proposed
        ):
            return {"status": "no_op", "changes": []}
        fingerprint = _fingerprint(scope, project, effective_prior)
        token = secrets.token_urlsafe(32)
        oid = f"health-config-{uuid.uuid4().hex}"
        expires = datetime.now(timezone.utc) + timedelta(minutes=30)
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "INSERT INTO project_health_configuration_changes VALUES (?,?,?,'proposed',?,?,?,?,?, '{}')",
            [
                oid,
                scope,
                project,
                hashlib.sha256(token.encode()).hexdigest(),
                fingerprint,
                _json(proposed),
                _now(),
                expires.isoformat(timespec="seconds"),
            ],
        )
        conn.commit()
    return {
        "status": "proposed",
        "operation_id": oid,
        "confirmation_token": token,
        "prior": prior_parameters,
        "proposed": proposed,
        "effective": proposed,
        "prior_configuration_version_id": prior["configuration_version_id"],
        "effective_configuration_version_id": "pending_confirmation",
        "expires_at": expires.isoformat(timespec="seconds"),
    }


def confirm(
    operation_id: str, confirmation_token: str, *, db_path: str | Path | None = None
) -> dict[str, Any]:
    with _connection(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        op = conn.execute(
            "SELECT * FROM project_health_configuration_changes WHERE operation_id=?",
            [operation_id],
        ).fetchone()
        if not op or not secrets.compare_digest(
            op["token_hash"], hashlib.sha256(confirmation_token.encode()).hexdigest()
        ):
            raise ValueError("HEALTH_CONFIGURATION_CONFIRMATION_INVALID")
        if op["status"] == "confirmed":
            conn.commit()
            return {**json.loads(op["result_json"]), "idempotent": True}
        if op["status"] != "proposed" or datetime.fromisoformat(op["expires_at"]) <= datetime.now(
            timezone.utc
        ):
            conn.execute(
                "UPDATE project_health_configuration_changes SET status='expired' WHERE operation_id=?",
                [operation_id],
            )
            conn.commit()
            return {"status": "expired"}
        claimed = conn.execute(
            "UPDATE project_health_configuration_changes SET status='claimed' WHERE operation_id=? AND status='proposed'",
            [operation_id],
        ).rowcount
        if claimed != 1:
            conn.rollback()
            raise ValueError("HEALTH_CONFIGURATION_CONFIRMATION_INVALID")
        effective_prior = _params(json.loads(effective_current(conn, op["project_id"] if op["scope"] == "project" else None)["parameters_json"]))
        fp = _fingerprint(op["scope"], op["project_id"], effective_prior)
        if fp != op["fingerprint"]:
            conn.execute(
                "UPDATE project_health_configuration_changes SET status='rejected' WHERE operation_id=?",
                [operation_id],
            )
            conn.commit()
            return {"status": "rejected", "reason": "STALE_FINGERPRINT"}
        conn.execute(
            "UPDATE project_health_configuration_versions SET is_current=0 WHERE scope=? AND project_id=?",
            [op["scope"], op["project_id"]],
        )
        vid = f"health-condition-{uuid.uuid4().hex}"
        conn.execute(
            "INSERT INTO project_health_configuration_versions VALUES (?,?,?,?,?,?)",
            [vid, op["project_id"], op["scope"], op["proposed_json"], 1, _now()],
        )
        result = {
            "status": "confirmed",
            "configuration_version_id": vid,
            "scope": op["scope"],
            "project_id": op["project_id"] or None,
            "effective": _params(json.loads(op["proposed_json"])),
        }
        conn.execute(
            "UPDATE project_health_configuration_changes SET status='confirmed',result_json=? WHERE operation_id=?",
            [_json(result), operation_id],
        )
        conn.commit()
        return result
