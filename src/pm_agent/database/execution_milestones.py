"""Controlled milestone preview/confirm operations for Phase 3 execution facts."""

from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from pm_agent.database.execution_common import (
    VALUE_STATES,
    connection_scope,
    json_dumps,
    now_utc,
    stable_id,
)


def _validate_milestones(payload: dict[str, Any]) -> list[dict[str, Any]]:
    records = payload.get("milestones") if isinstance(payload, dict) else None
    if not isinstance(records, list) or not records or len(records) > 100:
        raise ValueError("milestones must contain between 1 and 100 structured records")
    required = {"milestone_id", "project_id", "milestone_type", "criticality", "lifecycle_state", "authority", "completeness_state", "observed_at", "schema_version"}
    allowed = required | {"planned_date", "source_target_date", "forecast_date", "actual_date", "release_ids"}
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for record in records:
        if not isinstance(record, dict) or not required <= set(record):
            raise ValueError("Milestone record is missing required structured fields")
        if set(record) - allowed:
            raise ValueError("Milestone record contains unsupported fields")
        item = {key: str(record.get(key, "")).strip() for key in required | {"planned_date", "source_target_date", "forecast_date", "actual_date"}}
        if any(not item[key] or len(item[key]) > 200 for key in required):
            raise ValueError("Milestone required fields must be bounded non-empty strings")
        if item["milestone_id"] in seen:
            raise ValueError("Milestone IDs must be unique within one import")
        if item["criticality"] not in {"critical", "high", "medium", "low", "unknown"}:
            raise ValueError("Milestone criticality is invalid")
        if item["lifecycle_state"] not in {"planned", "in_progress", "achieved", "cancelled", "unknown"}:
            raise ValueError("Milestone lifecycle state is invalid")
        if item["completeness_state"] not in VALUE_STATES:
            raise ValueError("Milestone completeness state is invalid")
        for key in ("planned_date", "source_target_date", "forecast_date", "actual_date"):
            if item[key]:
                try:
                    date.fromisoformat(item[key])
                except ValueError as exc:
                    raise ValueError(f"Milestone {key} must be an ISO date") from exc
        try:
            datetime.fromisoformat(item["observed_at"].replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("Milestone observed_at must be an ISO timestamp") from exc
        release_ids = record.get("release_ids", [])
        if not isinstance(release_ids, list) or len(release_ids) > 50 or not all(
            isinstance(value, str) and value.strip() and len(value.strip()) <= 200
            for value in release_ids
        ):
            raise ValueError("Milestone release_ids must be a bounded string list")
        item["release_ids"] = sorted(set(value.strip() for value in release_ids))
        seen.add(item["milestone_id"])
        normalized.append(item)
    return sorted(normalized, key=lambda item: item["milestone_id"])


def _milestone_state(connection: sqlite3.Connection, milestone_id: str) -> dict[str, Any]:
    row = connection.execute(
        "SELECT * FROM execution_milestones WHERE milestone_id = ?", [milestone_id]
    ).fetchone()
    release_ids = [
        item[0] for item in connection.execute(
            "SELECT release_id FROM execution_milestone_release_links WHERE milestone_id = ? ORDER BY release_id",
            [milestone_id],
        )
    ]
    return {"milestone": dict(row) if row else {}, "release_ids": release_ids}


def _validate_release_references(connection: sqlite3.Connection, release_ids: list[str]) -> None:
    for release_id in release_ids:
        if not connection.execute(
            "SELECT 1 FROM execution_release_commitments WHERE release_id = ?", [release_id]
        ).fetchone():
            raise ValueError("Milestone release reference does not exist")


def preview_milestone_import(payload: dict[str, Any], *, db_path: str | Path | None = None, ttl_minutes: int = 30) -> dict[str, Any]:
    records = _validate_milestones(payload)
    if not 1 <= ttl_minutes <= 60:
        raise ValueError("ttl_minutes must be between 1 and 60")
    with connection_scope(db_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        current = []
        for record in records:
            if not connection.execute("SELECT 1 FROM projects WHERE id = ?", [record["project_id"]]).fetchone():
                raise ValueError("Milestone project does not exist")
            _validate_release_references(connection, record["release_ids"])
            current.append(_milestone_state(connection, record["milestone_id"]))
        fingerprint = hashlib.sha256(json_dumps({"records": records, "current": current}).encode()).hexdigest()
        changes = [
            record["milestone_id"] for record, existing in zip(records, current)
            if not existing["milestone"]
            or any(
                existing["milestone"].get(key, "") != record[key]
                for key in record if key != "release_ids"
            )
            or existing["release_ids"] != record["release_ids"]
        ]
        if not changes:
            connection.rollback()
            return {"status": "no_op", "changes": []}
        operation_id, token = f"milestone-op-{uuid4().hex}", secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        expires = now + timedelta(minutes=ttl_minutes)
        proposed = {"milestones": records, "changes": changes}
        connection.execute(
            """
            INSERT INTO milestone_import_operations
                (operation_id, status, token_hash, request_json, proposed_json, fingerprint, created_at, expires_at)
            VALUES (?, 'proposed', ?, ?, ?, ?, ?, ?)
            """,
            [operation_id, hashlib.sha256(token.encode()).hexdigest(), json_dumps(payload), json_dumps(proposed), fingerprint,
             now.isoformat(timespec="seconds"), expires.isoformat(timespec="seconds")],
        )
        connection.commit()
    return {"status": "proposed", "operation_id": operation_id, "confirmation_token": token, "expires_at": expires.isoformat(timespec="seconds"), "proposed": proposed}


def confirm_milestone_import(operation_id: str, confirmation_token: str, *, db_path: str | Path | None = None) -> dict[str, Any]:
    with connection_scope(db_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute("SELECT * FROM milestone_import_operations WHERE operation_id = ?", [operation_id]).fetchone()
        if not row:
            raise ValueError("Unknown Milestone import operation")
        operation = dict(row)
        supplied = hashlib.sha256(confirmation_token.encode()).hexdigest()
        if not secrets.compare_digest(operation["token_hash"], supplied):
            raise ValueError("Invalid confirmation token")
        if operation["status"] == "confirmed":
            connection.commit()
            result = json.loads(operation["result_json"] or "{}")
            return {
                **result,
                "status": "confirmed",
                "operation_id": operation_id,
                "idempotent": True,
            }
        if operation["status"] != "proposed":
            raise ValueError("Milestone import is not confirmable")
        if datetime.fromisoformat(operation["expires_at"]) <= datetime.now(timezone.utc):
            connection.execute("UPDATE milestone_import_operations SET status='expired' WHERE operation_id = ?", [operation_id])
            connection.commit()
            return {"status": "expired", "operation_id": operation_id}
        claimed = connection.execute("UPDATE milestone_import_operations SET status='claimed' WHERE operation_id = ? AND status = 'proposed'", [operation_id])
        if claimed.rowcount != 1:
            raise ValueError("Milestone import was already claimed")
        proposed = json.loads(operation["proposed_json"])
        records = proposed["milestones"]
        current = []
        for record in records:
            if not connection.execute("SELECT 1 FROM projects WHERE id = ?", [record["project_id"]]).fetchone():
                raise ValueError("Milestone project no longer exists")
            _validate_release_references(connection, record["release_ids"])
            current.append(_milestone_state(connection, record["milestone_id"]))
        fingerprint = hashlib.sha256(json_dumps({"records": records, "current": current}).encode()).hexdigest()
        if fingerprint != operation["fingerprint"]:
            connection.execute("UPDATE milestone_import_operations SET status='rejected', failure_code='STALE_FINGERPRINT' WHERE operation_id = ?", [operation_id])
            connection.commit()
            return {"status": "rejected", "operation_id": operation_id, "reason": "STALE_FINGERPRINT"}
        for record in records:
            first_target = record["source_target_date"]
            existing = connection.execute("SELECT first_observed_target_date FROM execution_milestones WHERE milestone_id = ?", [record["milestone_id"]]).fetchone()
            if existing and existing["first_observed_target_date"]:
                first_target = existing["first_observed_target_date"]
            connection.execute(
                """
                INSERT INTO execution_milestones
                    (milestone_id, project_id, milestone_type, criticality, lifecycle_state,
                     planned_date, source_target_date, forecast_date, actual_date,
                     first_observed_target_date, authority, completeness_state, observed_at,
                     schema_version, latest_operation_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(milestone_id) DO UPDATE SET
                    project_id=excluded.project_id, milestone_type=excluded.milestone_type,
                    criticality=excluded.criticality, lifecycle_state=excluded.lifecycle_state,
                    planned_date=excluded.planned_date, source_target_date=excluded.source_target_date,
                    forecast_date=excluded.forecast_date, actual_date=excluded.actual_date,
                    authority=excluded.authority, completeness_state=excluded.completeness_state,
                    observed_at=excluded.observed_at, schema_version=excluded.schema_version,
                    latest_operation_id=excluded.latest_operation_id
                """,
                [record["milestone_id"], record["project_id"], record["milestone_type"], record["criticality"],
                 record["lifecycle_state"], record["planned_date"], record["source_target_date"],
                 record["forecast_date"], record["actual_date"], first_target, record["authority"],
                 record["completeness_state"], record["observed_at"], record["schema_version"], operation_id],
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO execution_milestone_observations
                    (observation_id, milestone_id, planned_date, source_target_date, forecast_date,
                     actual_date, lifecycle_state, authority, completeness_state, observed_at, operation_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [stable_id("milestone-observation", record["milestone_id"], record["observed_at"], operation_id),
                 record["milestone_id"], record["planned_date"], record["source_target_date"],
                 record["forecast_date"], record["actual_date"], record["lifecycle_state"], record["authority"],
                 record["completeness_state"], record["observed_at"], operation_id],
            )
            if record["release_ids"]:
                placeholders = ",".join("?" for _ in record["release_ids"])
                connection.execute(
                    f"DELETE FROM execution_milestone_release_links WHERE milestone_id = ? AND release_id NOT IN ({placeholders})",
                    [record["milestone_id"], *record["release_ids"]],
                )
            else:
                connection.execute(
                    "DELETE FROM execution_milestone_release_links WHERE milestone_id = ?",
                    [record["milestone_id"]],
                )
            for release_id in record["release_ids"]:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO execution_milestone_release_links
                        (milestone_id, release_id, operation_id)
                    VALUES (?, ?, ?)
                    """,
                    [record["milestone_id"], release_id, operation_id],
                )
        result = {"status": "confirmed", "operation_id": operation_id, "milestone_count": len(records), "idempotent": False}
        connection.execute("UPDATE milestone_import_operations SET status='confirmed', confirmed_at=?, result_json=? WHERE operation_id = ?", [now_utc(), json_dumps(result), operation_id])
        connection.commit()
    return result
