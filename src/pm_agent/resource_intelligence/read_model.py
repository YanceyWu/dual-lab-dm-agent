"""Immutable public reader for the current canonical capacity fact."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from pm_agent.config import settings


def list_effective_capacity(
    year: int,
    month: int,
    plan_version_id: str,
    *,
    member_ids: list[str] | None = None,
    states: list[str] | None = None,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Return current persisted derivations without recalculating capacity."""
    database = sqlite3.connect(Path(db_path or settings.database_path))
    database.row_factory = sqlite3.Row
    try:
        clauses = [
            "p.is_current=1",
            "d.year=?",
            "d.month=?",
            "d.plan_version_id=?",
        ]
        parameters: list[Any] = [year, month, plan_version_id]
        if member_ids:
            clauses.append(f"d.member_id IN ({','.join('?' for _ in member_ids)})")
            parameters.extend(member_ids)
        if states:
            clauses.append(f"d.state IN ({','.join('?' for _ in states)})")
            parameters.extend(states)
        rows = database.execute(
            f"""SELECT d.*,p.package_id,p.package_fingerprint,p.published_at
                FROM resource_capacity_derivations d
                JOIN resource_capacity_publications p
                  ON p.publication_id=d.publication_id
                WHERE {' AND '.join(clauses)}
                ORDER BY d.member_id""",
            parameters,
        ).fetchall()
        results = []
        for row in rows:
            item = dict(row)
            item["evidence"] = json.loads(item.pop("evidence_json"))
            results.append(item)
        return results
    finally:
        database.close()


def get_effective_capacity(
    member_id: str, year: int, month: int, plan_version_id: str, *,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Return one member/month fact; absence is explicit unknown, never zero."""
    database = sqlite3.connect(Path(db_path or settings.database_path))
    database.row_factory = sqlite3.Row
    try:
        row = database.execute(
            """SELECT d.*,p.package_id,p.package_fingerprint,p.published_at
               FROM resource_capacity_derivations d
               JOIN resource_capacity_publications p ON p.publication_id=d.publication_id
               WHERE p.is_current=1 AND d.member_id=? AND d.year=? AND d.month=?
                 AND d.plan_version_id=?""",
            [member_id, year, month, plan_version_id],
        ).fetchone()
        if not row:
            return {
                "member_id": member_id, "year": year, "month": month,
                "plan_version_id": plan_version_id, "state": "unknown",
                "state_reason": "current_capacity_publication_or_period_not_found",
                "effective_capacity": None, "available_capacity": None,
                "overload_amount": None, "overload_state": None, "evidence": {},
            }
        result = dict(row)
        result["evidence"] = json.loads(result.pop("evidence_json"))
        return result
    finally:
        database.close()


def get_effective_capacity_in_transaction(
    database: sqlite3.Connection,
    member_id: str,
    year: int,
    month: int,
    plan_version_id: str,
) -> dict[str, Any] | None:
    """Load the current derivation using a caller-owned write transaction."""
    prior_factory = database.row_factory
    database.row_factory = sqlite3.Row
    try:
        row = database.execute(
            """SELECT d.*,p.package_id,p.package_fingerprint,p.published_at
               FROM resource_capacity_derivations d
               JOIN resource_capacity_publications p ON p.publication_id=d.publication_id
               WHERE p.is_current=1 AND d.member_id=? AND d.year=? AND d.month=?
                 AND d.plan_version_id=?""",
            [member_id, year, month, plan_version_id],
        ).fetchone()
        if not row:
            return None
        result = dict(row)
        result["evidence"] = json.loads(result.pop("evidence_json"))
        return result
    finally:
        database.row_factory = prior_factory
