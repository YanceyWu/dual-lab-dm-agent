"""Phase 3 B2 internal services; no public use-case registration in this batch."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pm_agent.database import execution


class ExecutionFoundationService:
    """Deterministic canonicalization and controlled Milestone import boundary."""

    def derive(self, board_id: str, *, db_path: str | Path | None = None) -> dict[str, Any]:
        return execution.derive_board(board_id, db_path=db_path)

    def preview_milestone_import(
        self,
        payload: dict[str, Any],
        *,
        db_path: str | Path | None = None,
        ttl_minutes: int = 30,
    ) -> dict[str, Any]:
        return execution.preview_milestone_import(
            payload,
            db_path=db_path,
            ttl_minutes=ttl_minutes,
        )

    def confirm_milestone_import(
        self,
        operation_id: str,
        confirmation_token: str,
        *,
        db_path: str | Path | None = None,
    ) -> dict[str, Any]:
        return execution.confirm_milestone_import(
            operation_id,
            confirmation_token,
            db_path=db_path,
        )
