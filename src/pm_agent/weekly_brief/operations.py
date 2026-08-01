"""C-layer controlled capture facade; never a generic read query operation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pm_agent.weekly_brief.composer import WeeklyBriefQueryAdapter
from pm_agent.weekly_brief.snapshots import WeeklyBriefSnapshotService


def preview_capture(*, candidate: dict[str, Any], actor_id: str, idempotency_key: str, expires_in_seconds: int = 600, db_path: str | Path | None = None) -> dict[str, Any]:
    adapter = WeeklyBriefQueryAdapter(db_path=db_path)
    service = WeeklyBriefSnapshotService(
        query_lookup=lambda execution_id: adapter.recompose(candidate) if execution_id == candidate.get("execution_id") else None,
        recompose=adapter.recompose,
        db_path=db_path,
    )
    return service.preview(candidate=candidate, actor_id=actor_id, idempotency_key=idempotency_key, expires_in_seconds=expires_in_seconds)


def confirm_capture(*, operation_id: str, confirmation_token: str, db_path: str | Path | None = None) -> dict[str, Any]:
    adapter = WeeklyBriefQueryAdapter(db_path=db_path)
    service = WeeklyBriefSnapshotService(query_lookup=lambda _execution_id: None, recompose=adapter.recompose, db_path=db_path)
    return service.confirm(operation_id=operation_id, confirmation_token=confirmation_token)
