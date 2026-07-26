"""Short-lived, auditable confirmation boundary for Dashboard write actions."""

from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4


SYNC_ACTION = "jira_project_health_sync"
TOKEN_TTL_SECONDS = 300


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.isoformat(timespec="seconds")


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_sync_preview(
    connection: sqlite3.Connection,
    *,
    targets: list[dict[str, Any]],
    actor: str,
) -> dict[str, Any]:
    operation_id = str(uuid4())
    created_at = _utc_now()
    expires_at = created_at + timedelta(seconds=TOKEN_TTL_SECONDS)
    token = secrets.token_urlsafe(32)
    scope = {
        "board_ids": [str(target["id"]) for target in targets],
        "board_names": [str(target["name"]) for target in targets],
        "network_access": True,
        "local_updates": ["jira_release_snapshots", "jira_health_snapshots"],
        "remote_writes": False,
    }
    connection.execute(
        """
        INSERT INTO dashboard_operations
            (operation_id, action, actor, status, scope_json, token_hash,
             created_at, expires_at)
        VALUES (?, ?, ?, 'proposed', ?, ?, ?, ?)
        """,
        [
            operation_id,
            SYNC_ACTION,
            actor,
            json.dumps(scope, ensure_ascii=False, sort_keys=True),
            _token_hash(token),
            _iso(created_at),
            _iso(expires_at),
        ],
    )
    connection.commit()
    return {
        "operation_id": operation_id,
        "confirmation_token": token,
        "expires_at": _iso(expires_at),
        "actor": actor,
        "scope": scope,
    }


def claim_sync_operation(
    connection: sqlite3.Connection,
    *,
    operation_id: str,
    confirmation_token: str,
) -> tuple[dict[str, Any] | None, str | None]:
    row = connection.execute(
        """
        SELECT operation_id, action, actor, status, scope_json, token_hash,
               expires_at
        FROM dashboard_operations
        WHERE operation_id = ?
        """,
        [operation_id],
    ).fetchone()
    if row is None or row["action"] != SYNC_ACTION:
        return None, "SYNC_OPERATION_NOT_FOUND"
    if row["status"] != "proposed":
        return None, "SYNC_OPERATION_ALREADY_USED"
    try:
        expires_at = datetime.fromisoformat(row["expires_at"])
    except (TypeError, ValueError):
        return None, "SYNC_OPERATION_INVALID"
    if expires_at <= _utc_now():
        connection.execute(
            """
            UPDATE dashboard_operations
            SET status = 'expired', failure_code = 'SYNC_CONFIRMATION_EXPIRED'
            WHERE operation_id = ? AND status = 'proposed'
            """,
            [operation_id],
        )
        connection.commit()
        return None, "SYNC_CONFIRMATION_EXPIRED"
    if not secrets.compare_digest(row["token_hash"], _token_hash(confirmation_token)):
        return None, "SYNC_CONFIRMATION_INVALID"

    claimed = connection.execute(
        """
        UPDATE dashboard_operations
        SET status = 'executing', confirmed_at = ?
        WHERE operation_id = ? AND status = 'proposed'
        """,
        [_iso(_utc_now()), operation_id],
    )
    connection.commit()
    if claimed.rowcount != 1:
        return None, "SYNC_OPERATION_ALREADY_USED"
    return {
        "operation_id": row["operation_id"],
        "actor": row["actor"],
        "scope": json.loads(row["scope_json"]),
    }, None


def finish_sync_operation(
    connection: sqlite3.Connection,
    *,
    operation_id: str,
    success: bool,
    result: dict[str, Any],
    failure_code: str = "",
) -> None:
    connection.execute(
        """
        UPDATE dashboard_operations
        SET status = ?, result_json = ?, failure_code = ?, finished_at = ?
        WHERE operation_id = ? AND status = 'executing'
        """,
        [
            "success" if success else "failed",
            json.dumps(result, ensure_ascii=False, sort_keys=True),
            failure_code,
            _iso(_utc_now()),
            operation_id,
        ],
    )
    connection.commit()
