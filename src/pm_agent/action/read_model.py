"""Read-only current and completion facts for recorded Actions."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from pm_agent.config import settings

_STATUSES = {"open", "done", "cancelled"}
_PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}


def list_action_records(
    *,
    statuses: list[str] | None = None,
    completed_since: str | None = None,
    through: str | None = None,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Return current Action facts without inferring a project association."""
    normalized_statuses = _statuses(statuses)
    since = (
        _timestamp(completed_since, "ACTION_COMPLETED_SINCE_INVALID")
        if completed_since
        else None
    )
    boundary = (
        _timestamp(through, "ACTION_THROUGH_INVALID")
        if through
        else datetime.now(timezone.utc)
    )
    if since and since > boundary:
        raise ValueError("ACTION_COMPLETION_WINDOW_INVALID")
    database = sqlite3.connect(Path(db_path or settings.database_path))
    database.row_factory = sqlite3.Row
    try:
        placeholders = ",".join("?" for _ in normalized_statuses)
        rows = database.execute(
            f"""SELECT ai.*
                FROM action_items ai
                WHERE ai.status IN ({placeholders})
                ORDER BY ai.id""",
            normalized_statuses,
        ).fetchall()
    finally:
        database.close()

    today = boundary.date()
    items = []
    coverage_limitations: set[str] = set()
    for raw in rows:
        row = dict(raw)
        completed_at = _optional_timestamp(row.get("completed_at"))
        reasons, limitations = _follow_up(row, today)
        completion_state = "not_applicable"
        if row["status"] == "done":
            if completed_at is None:
                completion_state = "unavailable"
                limitations.append("ACTION_COMPLETION_TIME_INVALID")
            elif completed_at > boundary:
                completion_state = "unavailable"
                limitations.append("ACTION_COMPLETION_AFTER_BOUNDARY")
            elif since and completed_at <= since:
                continue
            else:
                completion_state = "known"
        coverage_limitations.update(limitations)
        items.append(
            {
                "action_id": str(row["id"]),
                "title": row["title"],
                "status": row["status"],
                "priority": row["priority"],
                "owner_id": row["owner_id"],
                "owner_state": "known" if row["owner_id"] else "missing",
                "due_date": row["due_date"],
                "created_at": row["created_at"],
                "completed_at": row["completed_at"],
                "completion_state": completion_state,
                "follow_up_reasons": reasons,
                "severity": (
                    "high"
                    if "overdue" in reasons and row["priority"] == "high"
                    else "medium"
                    if reasons
                    else "none"
                ),
                "project_association": {
                    "state": "unavailable",
                    "project_id": None,
                    "reason": "action_project_association_not_recorded",
                },
                "limitations": limitations,
            }
        )
    items.sort(
        key=lambda item: (
            _PRIORITY_RANK.get(str(item["priority"]), 9),
            str(item["due_date"] or "9999-12-31"),
            item["action_id"],
        )
    )
    return {
        "contract_version": "action-read-model-v1",
        "items": items,
        "coverage": {
            "state": "partial" if coverage_limitations else "complete",
            "basis": "recorded_action_items",
            "record_count": len(items),
            "limitation_codes": sorted(coverage_limitations),
        },
        "filters": {
            "statuses": normalized_statuses,
            "completed_since": completed_since,
            "through": boundary.isoformat(timespec="seconds"),
        },
    }


def _statuses(value: list[str] | None) -> list[str]:
    normalized = ["open", "done"] if value is None else value
    if (
        not isinstance(normalized, list)
        or not normalized
        or any(not isinstance(item, str) or item not in _STATUSES for item in normalized)
        or len(normalized) != len(set(normalized))
    ):
        raise ValueError("ACTION_STATUSES_INVALID")
    return sorted(normalized)


def _timestamp(value: str, error_code: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError(error_code) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _optional_timestamp(value: object) -> datetime | None:
    if not value:
        return None
    try:
        return _timestamp(str(value), "ACTION_COMPLETION_TIME_INVALID")
    except ValueError:
        return None


def _follow_up(row: dict[str, Any], today: date) -> tuple[list[str], list[str]]:
    if row["status"] != "open":
        return [], []
    reasons = []
    limitations = []
    due_date = row.get("due_date")
    if due_date:
        try:
            if date.fromisoformat(str(due_date)) < today:
                reasons.append("overdue")
        except ValueError:
            limitations.append("ACTION_DUE_DATE_INVALID")
    if not row.get("owner_id"):
        reasons.append("missing_owner")
    if not due_date:
        reasons.append("missing_due_date")
    return reasons, limitations
