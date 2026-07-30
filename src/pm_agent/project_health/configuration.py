"""Controlled Phase 4 health-condition configuration; no public transport."""

from __future__ import annotations
import hashlib
import json
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from pm_agent.project_health.service import _connection, _json, _now


def _params(value: object) -> dict[str, int]:
    if not isinstance(value, dict) or set(value) != {"critical_milestone_tolerance_days"}:
        raise ValueError("HEALTH_CONFIGURATION_INVALID")
    days = value["critical_milestone_tolerance_days"]
    if not isinstance(days, int) or not 0 <= days <= 90:
        raise ValueError("HEALTH_CONFIGURATION_INVALID")
    return {"critical_milestone_tolerance_days": days}


def _current(conn, scope: str, project: str):
    row = conn.execute(
        "SELECT * FROM project_health_configuration_versions WHERE scope=? AND project_id=? AND is_current=1",
        [scope, project],
    ).fetchone()
    return (
        dict(row)
        if row
        else {
            "parameters_json": _json({"critical_milestone_tolerance_days": 0}),
            "configuration_version_id": "catalog-default-v1",
        }
    )


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
        if json.loads(prior["parameters_json"]) == proposed:
            return {"status": "no_op", "changes": []}
        fingerprint = hashlib.sha256(
            _json([scope, project, prior["parameters_json"]]).encode()
        ).hexdigest()
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
        "prior": json.loads(prior["parameters_json"]),
        "proposed": proposed,
        "effective": proposed,
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
        prior = _current(conn, op["scope"], op["project_id"])
        fp = hashlib.sha256(
            _json([op["scope"], op["project_id"], prior["parameters_json"]]).encode()
        ).hexdigest()
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
        result = {"status": "confirmed", "configuration_version_id": vid}
        conn.execute(
            "UPDATE project_health_configuration_changes SET status='confirmed',result_json=? WHERE operation_id=?",
            [_json(result), operation_id],
        )
        conn.commit()
        return result
