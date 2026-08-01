"""Immutable public reader for the current canonical capacity fact."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from pm_agent.config import settings


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
