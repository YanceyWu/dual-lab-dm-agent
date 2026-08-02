"""Persisted compatibility marker for capacity-aware Staffing writes."""

from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from pm_agent.config import settings

STAFFING_CAPACITY_POLICY_DDL = """
CREATE TABLE IF NOT EXISTS staffing_capacity_policy (
    policy_key TEXT PRIMARY KEY CHECK(policy_key='effective_capacity_required'),
    capacity_required INTEGER NOT NULL CHECK(capacity_required IN (0,1)),
    policy_version TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

STAFFING_CAPACITY_OPERATIONS_DDL = """
CREATE TABLE IF NOT EXISTS staffing_capacity_operations (
    operation_id TEXT PRIMARY KEY,
    action TEXT NOT NULL CHECK(action IN ('enable')),
    actor TEXT NOT NULL,
    status TEXT NOT NULL CHECK(
        status IN ('proposed', 'claimed', 'confirmed', 'expired', 'rejected')
    ),
    token_hash TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    preconditions_json TEXT NOT NULL CHECK(json_valid(preconditions_json)),
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    confirmed_at TEXT NOT NULL DEFAULT '',
    result_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(result_json))
);
"""


def install_or_validate_policy(
    database: sqlite3.Connection, *, table_preexisting: bool
) -> None:
    """Install disabled once; never repair a missing existing marker to disabled."""
    row = database.execute(
        """SELECT capacity_required FROM staffing_capacity_policy
           WHERE policy_key='effective_capacity_required'"""
    ).fetchone()
    if row:
        return
    if table_preexisting:
        raise ValueError("STAFFING_CAPACITY_POLICY_NOT_FOUND")
    database.execute(
        """INSERT INTO staffing_capacity_policy
           (policy_key,capacity_required,policy_version,updated_at)
           VALUES ('effective_capacity_required',0,'staffing-capacity-policy-v1',datetime('now'))"""
    )
    database.commit()


def policy_state(
    *,
    connection: sqlite3.Connection | None = None,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Return the current marker state through the public reader."""
    if connection is None:
        database = sqlite3.connect(Path(db_path or settings.database_path))
        database.row_factory = sqlite3.Row
        try:
            return policy_state(connection=database)
        finally:
            database.close()
    row = connection.execute(
        """SELECT policy_key, capacity_required, policy_version, updated_at
           FROM staffing_capacity_policy
           WHERE policy_key='effective_capacity_required'"""
    ).fetchone()
    if not row:
        raise ValueError("STAFFING_CAPACITY_POLICY_NOT_FOUND")
    return {
        "policy_key": row["policy_key"],
        "capacity_required": bool(row["capacity_required"]),
        "policy_version": row["policy_version"],
        "updated_at": row["updated_at"],
    }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _current_publication_id(
    database: sqlite3.Connection,
) -> str | None:
    row = database.execute(
        """SELECT publication_id FROM resource_capacity_publications
           WHERE is_current=1"""
    ).fetchone()
    return str(row[0]) if row else None


def _enable_in_transaction(database: sqlite3.Connection) -> dict[str, Any]:
    """Apply the enable inside a caller-owned write transaction."""
    current = _current_publication_id(database)
    if not current:
        raise ValueError("STAFFING_CAPACITY_PUBLICATION_REQUIRED")
    updated = database.execute(
        """UPDATE staffing_capacity_policy
           SET capacity_required=1,policy_version='staffing-capacity-policy-v1',
               updated_at=datetime('now')
           WHERE policy_key='effective_capacity_required'"""
    )
    if updated.rowcount != 1:
        raise ValueError("STAFFING_CAPACITY_POLICY_NOT_FOUND")
    return {
        "capacity_required": True,
        "policy_version": "staffing-capacity-policy-v1",
        "capacity_publication_id": current,
    }


def capacity_required(
    *,
    connection: sqlite3.Connection | None = None,
    db_path: str | Path | None = None,
) -> bool:
    if connection is not None:
        row = connection.execute(
            """SELECT capacity_required FROM staffing_capacity_policy
               WHERE policy_key='effective_capacity_required'"""
        ).fetchone()
        if not row:
            raise ValueError("STAFFING_CAPACITY_POLICY_NOT_FOUND")
        return bool(row[0])
    database = sqlite3.connect(Path(db_path or settings.database_path))
    try:
        return capacity_required(connection=database)
    finally:
        database.close()


def enable_capacity_requirement(*, db_path: str | Path | None = None) -> dict[str, object]:
    """Enable fail-closed consumption only after a complete current publication exists."""
    database = sqlite3.connect(Path(db_path or settings.database_path), isolation_level=None)
    database.execute("PRAGMA foreign_keys = ON")
    try:
        database.execute("BEGIN IMMEDIATE")
        result = _enable_in_transaction(database)
        database.commit()
        return result
    except Exception:
        database.rollback()
        raise
    finally:
        database.close()


def preview_enable_capacity_requirement(
    *,
    actor: str,
    db_path: str | Path | None = None,
    ttl_minutes: int = 30,
) -> dict[str, Any]:
    """Preview the controlled enable; writes only an expiring operation row."""
    if not isinstance(actor, str) or not actor.strip() or len(actor.strip()) > 128:
        raise ValueError("STAFFING_CAPACITY_ACTOR_INVALID")
    if not isinstance(ttl_minutes, int) or not 1 <= ttl_minutes <= 60:
        raise ValueError("STAFFING_CAPACITY_TTL_INVALID")
    database = sqlite3.connect(Path(db_path or settings.database_path), isolation_level=None)
    database.row_factory = sqlite3.Row
    database.execute("PRAGMA foreign_keys = ON")
    try:
        database.execute("BEGIN IMMEDIATE")
        publication_id = _current_publication_id(database)
        if not publication_id:
            raise ValueError("STAFFING_CAPACITY_PUBLICATION_REQUIRED")
        state = policy_state(connection=database)
        if state["capacity_required"]:
            return {
                "status": "no_op",
                "changes": [],
                "policy": state,
            }
        now = _now()
        expires = (
            datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
        ).isoformat(timespec="seconds")
        fingerprint = hashlib.sha256(
            _json(
                {
                    "publication_id": publication_id,
                    "policy": state,
                }
            ).encode()
        ).hexdigest()
        token = secrets.token_urlsafe(32)
        operation_id = f"staffing-capacity-op-{uuid4().hex}"
        database.execute(
            """
            INSERT INTO staffing_capacity_operations
                (operation_id, action, actor, status, token_hash, fingerprint,
                 preconditions_json, created_at, expires_at)
            VALUES (?, 'enable', ?, 'proposed', ?, ?, ?, ?, ?)
            """,
            [
                operation_id,
                actor.strip(),
                hashlib.sha256(token.encode()).hexdigest(),
                fingerprint,
                _json({"publication_id": publication_id, "policy": state}),
                now,
                expires,
            ],
        )
        database.commit()
        return {
            "status": "proposed",
            "operation_id": operation_id,
            "confirmation_token": token,
            "actor": actor.strip(),
            "expires_at": expires,
            "policy": state,
            "publication_id": publication_id,
            "changes": ["enable_capacity_requirement"],
        }
    except Exception:
        database.rollback()
        raise
    finally:
        database.close()


def confirm_enable_capacity_requirement(
    *,
    operation_id: str,
    confirmation_token: str,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Confirm one exact preview after revalidating its fingerprint."""
    database = sqlite3.connect(Path(db_path or settings.database_path), isolation_level=None)
    database.row_factory = sqlite3.Row
    database.execute("PRAGMA foreign_keys = ON")
    try:
        database.execute("BEGIN IMMEDIATE")
        row = database.execute(
            "SELECT * FROM staffing_capacity_operations WHERE operation_id=?",
            [operation_id],
        ).fetchone()
        if not row or not secrets.compare_digest(
            row["token_hash"],
            hashlib.sha256(confirmation_token.encode()).hexdigest(),
        ):
            raise ValueError("STAFFING_CAPACITY_CONFIRMATION_INVALID")
        operation = dict(row)
        if operation["status"] == "confirmed":
            result = json.loads(operation["result_json"])
            return {**result, "idempotent": True}
        if operation["status"] != "proposed":
            raise ValueError("STAFFING_CAPACITY_OPERATION_NOT_CONFIRMABLE")
        if datetime.fromisoformat(operation["expires_at"]) <= datetime.now(timezone.utc):
            database.execute(
                """UPDATE staffing_capacity_operations SET status='expired'
                   WHERE operation_id=?""",
                [operation_id],
            )
            database.commit()
            return {"status": "expired", "operation_id": operation_id}
        current_fingerprint = hashlib.sha256(
            _json(
                {
                    "publication_id": _current_publication_id(database),
                    "policy": policy_state(connection=database),
                }
            ).encode()
        ).hexdigest()
        if current_fingerprint != operation["fingerprint"]:
            database.execute(
                """UPDATE staffing_capacity_operations SET status='rejected'
                   WHERE operation_id=?""",
                [operation_id],
            )
            database.commit()
            return {
                "status": "rejected",
                "operation_id": operation_id,
                "reason": "STALE_FINGERPRINT",
            }
        try:
            result = _enable_in_transaction(database)
        except ValueError as exc:
            database.execute(
                """UPDATE staffing_capacity_operations SET status='rejected',
                       result_json=? WHERE operation_id=?""",
                [_json({"reason": str(exc)}), operation_id],
            )
            database.commit()
            return {
                "status": "rejected",
                "operation_id": operation_id,
                "reason": str(exc),
            }
        result.update(
            {
                "status": "confirmed",
                "operation_id": operation_id,
                "actor": operation["actor"],
            }
        )
        database.execute(
            """UPDATE staffing_capacity_operations
               SET status='confirmed', confirmed_at=?, result_json=?
               WHERE operation_id=?""",
            [_now(), _json(result), operation_id],
        )
        database.commit()
        return result
    except Exception:
        database.rollback()
        raise
    finally:
        database.close()
