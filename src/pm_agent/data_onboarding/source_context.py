"""Read the retained Workbook source context needed for portable export."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from pm_agent.config import settings


def latest_workbook_source_context(
    *, plan_version_id: str, db_path: str | Path | None = None
) -> dict[str, Any]:
    """Return the latest completed Workbook source context for one plan.

    The onboarding run is the owner-recorded origin of the Setup horizon and
    optional Capacity input.  This reader deliberately does not inspect
    publication links or any derived product.
    """
    database = sqlite3.connect(Path(db_path or settings.database_path))
    database.row_factory = sqlite3.Row
    try:
        rows = database.execute(
            """SELECT run_id,source_preview_json FROM data_onboarding_runs
               WHERE source_type='workbook' AND status='completed'
               ORDER BY completed_at DESC,created_at DESC,rowid DESC"""
        ).fetchall()
    finally:
        database.close()

    for row in rows:
        try:
            preview = json.loads(str(row["source_preview_json"]))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            raise ValueError("WORKBOOK_EXPORT_SOURCE_CONTEXT_INVALID") from None
        try:
            metadata = preview["workbook_export_metadata"]
            plan = metadata["plan_version_id"]
        except (KeyError, TypeError):
            raise ValueError("WORKBOOK_EXPORT_SOURCE_CONTEXT_INVALID") from None
        if str(plan) != plan_version_id:
            continue
        try:
            horizon = metadata["setup"]
            start_month = _month(horizon["start_month"])
            end_month = _month(horizon["end_month"])
            capacity = metadata["capacity"]
            row_count = capacity["row_count"]
            if type(row_count) is not int or row_count < 0 or start_month > end_month:
                raise ValueError
            package_id = capacity.get("package_id")
            if row_count == 0 and package_id is not None:
                raise ValueError
            if row_count > 0 and not isinstance(package_id, str):
                raise ValueError
        except (KeyError, TypeError, ValueError):
            raise ValueError("WORKBOOK_EXPORT_SOURCE_CONTEXT_INVALID") from None
        return {
            "run_id": str(row["run_id"]),
            "start_month": start_month,
            "end_month": end_month,
            "capacity": {"row_count": row_count, "package_id": package_id},
        }
    raise ValueError("WORKBOOK_EXPORT_HORIZON_UNAVAILABLE")


def _month(value: Any) -> str:
    text = str(value)
    if len(text) != 7 or text[4] != "-" or not text[:4].isdigit() or not text[5:].isdigit():
        raise ValueError
    month = int(text[5:])
    if not 1 <= month <= 12:
        raise ValueError
    return text
