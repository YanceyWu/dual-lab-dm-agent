"""Persisted compatibility marker for capacity-aware Staffing writes."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from pm_agent.config import settings

STAFFING_CAPACITY_POLICY_DDL = """
CREATE TABLE IF NOT EXISTS staffing_capacity_policy (
    policy_key TEXT PRIMARY KEY CHECK(policy_key='effective_capacity_required'),
    capacity_required INTEGER NOT NULL CHECK(capacity_required IN (0,1)),
    policy_version TEXT NOT NULL,
    updated_at TEXT NOT NULL
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
        current = database.execute(
            """SELECT publication_id FROM resource_capacity_publications
               WHERE is_current=1"""
        ).fetchone()
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
        database.commit()
        return {
            "capacity_required": True,
            "policy_version": "staffing-capacity-policy-v1",
            "capacity_publication_id": current[0],
        }
    except Exception:
        database.rollback()
        raise
    finally:
        database.close()
