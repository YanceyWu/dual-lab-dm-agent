"""Persistence helpers for repo-scoped Copilot interaction memory."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from pm_agent.config import settings
from pm_agent.interaction_memory.schema import INTERACTION_MEMORY_DDL

_READY_DATABASES: set[str] = set()
_SCHEMA_TABLES = {
    "interaction_memory_scopes",
    "interaction_memory_entries",
    "interaction_memory_audit",
}


def now_utc() -> str:
    """Return the canonical UTC timestamp string used by the capability."""
    return datetime.now(timezone.utc).isoformat()


def json_value(value: Any) -> str:
    """Serialize JSON deterministically for storage and fingerprints."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    """Hash a structured value deterministically."""
    raw = value if isinstance(value, str) else json_value(value)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@contextmanager
def connection(db_path: str | Path | None = None) -> Iterator[sqlite3.Connection]:
    """Open a capability-local SQLite connection."""
    database = sqlite3.connect(Path(db_path or settings.database_path))
    database.row_factory = sqlite3.Row
    database.execute("PRAGMA foreign_keys = ON")
    database.execute("PRAGMA busy_timeout = 10000")
    try:
        yield database
        database.commit()
    except Exception:
        database.rollback()
        raise
    finally:
        database.close()


def _row_to_scope(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "scope_id": row["scope_id"],
        "scope_source": row["scope_source"],
        "scope_key": row["scope_key"],
        "scope_display_name": row["scope_display_name"],
        "enabled": bool(row["enabled"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _row_to_entry(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "entry_id": row["entry_id"],
        "scope_id": row["scope_id"],
        "memory_kind": row["memory_kind"],
        "category": row["category"],
        "title": row["title"],
        "summary": row["summary"],
        "state": row["state"],
        "confidence": row["confidence"],
        "weight": row["weight"],
        "metadata": json.loads(row["metadata_json"]),
        "interaction_event_ref": json.loads(row["interaction_event_ref_json"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def ensure_schema(*, db_path: str | Path | None = None) -> None:
    """Create capability-local tables on first use for the selected database."""
    database_path = Path(db_path or settings.database_path).resolve()
    database_key = str(database_path)
    if database_key in _READY_DATABASES and database_path.exists():
        return
    with connection(database_path) as database:
        database.executescript(INTERACTION_MEMORY_DDL)
    _READY_DATABASES.add(database_key)


def schema_ready(*, db_path: str | Path | None = None) -> bool:
    """Return whether the capability tables already exist without mutating state."""
    database_path = Path(db_path or settings.database_path)
    if not database_path.exists():
        return False
    with connection(db_path) as database:
        rows = database.execute(
            """
            SELECT name
              FROM sqlite_master
             WHERE type='table'
               AND name LIKE 'interaction_memory_%'
            """
        ).fetchall()
    table_names = {str(row[0]) for row in rows}
    return _SCHEMA_TABLES.issubset(table_names)


def load_scope(scope_id: str, *, db_path: str | Path | None = None) -> dict[str, Any] | None:
    """Load one stored memory scope."""
    with connection(db_path) as database:
        row = database.execute(
            "SELECT * FROM interaction_memory_scopes WHERE scope_id=?",
            [scope_id],
        ).fetchone()
    return _row_to_scope(row)


def ensure_scope(
    *,
    scope_id: str,
    scope_source: str,
    scope_key: str,
    scope_display_name: str,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Insert a scope if needed and refresh its display metadata."""
    now = now_utc()
    with connection(db_path) as database:
        database.execute(
            """
            INSERT INTO interaction_memory_scopes(
                scope_id, scope_source, scope_key, scope_display_name, enabled,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, 1, ?, ?)
            ON CONFLICT(scope_id) DO UPDATE SET
                scope_display_name=excluded.scope_display_name,
                updated_at=excluded.updated_at
            """,
            [scope_id, scope_source, scope_key, scope_display_name, now, now],
        )
        row = database.execute(
            "SELECT * FROM interaction_memory_scopes WHERE scope_id=?",
            [scope_id],
        ).fetchone()
    return _row_to_scope(row) or {
        "scope_id": scope_id,
        "scope_source": scope_source,
        "scope_key": scope_key,
        "scope_display_name": scope_display_name,
        "enabled": True,
        "created_at": now,
        "updated_at": now,
    }


def set_scope_enabled(
    *,
    scope_id: str,
    enabled: bool,
    db_path: str | Path | None = None,
) -> dict[str, Any] | None:
    """Enable or disable one stored scope."""
    now = now_utc()
    with connection(db_path) as database:
        database.execute(
            """
            UPDATE interaction_memory_scopes
               SET enabled=?,
                   updated_at=?
             WHERE scope_id=?
            """,
            [1 if enabled else 0, now, scope_id],
        )
        row = database.execute(
            "SELECT * FROM interaction_memory_scopes WHERE scope_id=?",
            [scope_id],
        ).fetchone()
    return _row_to_scope(row)


def set_scope_enabled_with_audit(
    *,
    scope_id: str,
    enabled: bool,
    operation_type: str,
    interaction_event_ref: dict[str, Any],
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Enable or disable one stored scope and append an audit row atomically."""
    now = now_utc()
    audit_id = "ima-" + digest(
        {
            "scope_id": scope_id,
            "entry_id": "",
            "operation_type": operation_type,
            "interaction_event_ref": interaction_event_ref,
            "created_at": now,
        }
    )[:24]
    with connection(db_path) as database:
        prior_row = database.execute(
            "SELECT * FROM interaction_memory_scopes WHERE scope_id=?",
            [scope_id],
        ).fetchone()
        database.execute(
            """
            UPDATE interaction_memory_scopes
               SET enabled=?,
                   updated_at=?
             WHERE scope_id=?
            """,
            [1 if enabled else 0, now, scope_id],
        )
        row = database.execute(
            "SELECT * FROM interaction_memory_scopes WHERE scope_id=?",
            [scope_id],
        ).fetchone()
        if row is None:
            raise RuntimeError("INTERACTION_MEMORY_SCOPE_ENABLE_UPDATE_FAILED")
        prior_state = (
            {"enabled": bool(prior_row["enabled"])} if prior_row is not None else {}
        )
        new_state = {"enabled": bool(row["enabled"])}
        database.execute(
            """
            INSERT INTO interaction_memory_audit(
                audit_id, scope_id, entry_id, operation_type,
                interaction_event_ref_json, prior_state_json, new_state_json,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                audit_id,
                scope_id,
                "",
                operation_type,
                json_value(interaction_event_ref),
                json_value(prior_state),
                json_value(new_state),
                now,
            ],
        )
    return {
        "scope": _row_to_scope(row),
        "prior_state": prior_state,
        "new_state": new_state,
        "audit_id": audit_id,
        "created_at": now,
    }


def count_entries(
    scope_id: str,
    *,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Return grouped entry counts for one scope."""
    with connection(db_path) as database:
        grouped = database.execute(
            """
            SELECT memory_kind, state, COUNT(*) AS entry_count
              FROM interaction_memory_entries
             WHERE scope_id=?
             GROUP BY memory_kind, state
            """,
            [scope_id],
        ).fetchall()
        audit_count = database.execute(
            """
            SELECT COUNT(*)
              FROM interaction_memory_audit
             WHERE scope_id=?
            """,
            [scope_id],
        ).fetchone()[0]
    by_kind: dict[str, int] = {}
    by_state: dict[str, int] = {}
    for row in grouped:
        by_kind[row["memory_kind"]] = by_kind.get(row["memory_kind"], 0) + int(
            row["entry_count"]
        )
        by_state[row["state"]] = by_state.get(row["state"], 0) + int(
            row["entry_count"]
        )
    return {
        "total_entries": sum(by_kind.values()),
        "by_kind": by_kind,
        "by_state": by_state,
        "audit_event_count": int(audit_count),
    }


def list_entries(
    scope_id: str,
    *,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Return all interaction-memory entries for one scope."""
    with connection(db_path) as database:
        rows = database.execute(
            """
            SELECT *
              FROM interaction_memory_entries
             WHERE scope_id=?
             ORDER BY
                 CASE memory_kind
                     WHEN 'preference' THEN 0
                     WHEN 'context' THEN 1
                     WHEN 'follow_up' THEN 2
                     ELSE 3
                 END,
                 weight DESC,
                 confidence DESC,
                 updated_at DESC,
                 entry_id
            """,
            [scope_id],
        ).fetchall()
    return [_row_to_entry(row) for row in rows]


def upsert_entry(
    *,
    scope_id: str,
    memory_kind: str,
    category: str,
    title: str,
    summary: str,
    state: str,
    confidence: float,
    weight: float,
    metadata: dict[str, Any],
    interaction_event_ref: dict[str, Any],
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Insert or replace one normalized memory entry."""
    normalized_title = title.strip()
    normalized_category = category.strip()
    entry_id = "im-" + digest(
        {
            "scope_id": scope_id,
            "memory_kind": memory_kind,
            "category": normalized_category,
            "title": normalized_title,
        }
    )[:24]
    now = now_utc()
    with connection(db_path) as database:
        database.execute(
            """
            INSERT INTO interaction_memory_entries(
                entry_id, scope_id, memory_kind, category, title, summary, state,
                confidence, weight, metadata_json, interaction_event_ref_json,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(scope_id, memory_kind, category, title) DO UPDATE SET
                entry_id=excluded.entry_id,
                summary=excluded.summary,
                state=excluded.state,
                confidence=excluded.confidence,
                weight=excluded.weight,
                metadata_json=excluded.metadata_json,
                interaction_event_ref_json=excluded.interaction_event_ref_json,
                updated_at=excluded.updated_at
            """,
            [
                entry_id,
                scope_id,
                memory_kind,
                normalized_category,
                normalized_title,
                summary,
                state,
                confidence,
                weight,
                json_value(metadata),
                json_value(interaction_event_ref),
                now,
                now,
            ],
        )
        row = database.execute(
            "SELECT * FROM interaction_memory_entries WHERE entry_id=?",
            [entry_id],
        ).fetchone()
    if row is None:
        raise RuntimeError("INTERACTION_MEMORY_ENTRY_UPSERT_FAILED")
    return _row_to_entry(row)


def insert_audit(
    *,
    scope_id: str,
    entry_id: str,
    operation_type: str,
    interaction_event_ref: dict[str, Any],
    prior_state: dict[str, Any],
    new_state: dict[str, Any],
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Append one bounded audit row."""
    now = now_utc()
    audit_id = "ima-" + digest(
        {
            "scope_id": scope_id,
            "entry_id": entry_id,
            "operation_type": operation_type,
            "interaction_event_ref": interaction_event_ref,
            "created_at": now,
        }
    )[:24]
    with connection(db_path) as database:
        database.execute(
            """
            INSERT INTO interaction_memory_audit(
                audit_id, scope_id, entry_id, operation_type,
                interaction_event_ref_json, prior_state_json, new_state_json,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                audit_id,
                scope_id,
                entry_id,
                operation_type,
                json_value(interaction_event_ref),
                json_value(prior_state),
                json_value(new_state),
                now,
            ],
        )
    return {
        "audit_id": audit_id,
        "scope_id": scope_id,
        "entry_id": entry_id,
        "operation_type": operation_type,
        "created_at": now,
    }


def integrity_report(*, db_path: str | Path | None = None) -> dict[str, Any]:
    """Return a small integrity report for the capability store."""
    with connection(db_path) as database:
        integrity = [row[0] for row in database.execute("PRAGMA integrity_check")]
        foreign_keys = database.execute("PRAGMA foreign_key_check").fetchall()
        scope_count = database.execute(
            "SELECT COUNT(*) FROM interaction_memory_scopes"
        ).fetchone()[0]
        entry_count = database.execute(
            "SELECT COUNT(*) FROM interaction_memory_entries"
        ).fetchone()[0]
        audit_count = database.execute(
            "SELECT COUNT(*) FROM interaction_memory_audit"
        ).fetchone()[0]
    return {
        "state": "passed"
        if integrity == ["ok"] and not foreign_keys
        else "failed",
        "sqlite_integrity": "ok" if integrity == ["ok"] else "failed",
        "foreign_key_violations": len(foreign_keys),
        "scope_count": int(scope_count),
        "entry_count": int(entry_count),
        "audit_count": int(audit_count),
    }
