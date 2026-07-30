"""System-owned C2 reconciliation for the single approved Phase 3 rule."""

import json
import sqlite3
from pathlib import Path

from pm_agent.attention.rules import CRITICAL_MILESTONE_RULE
from pm_agent.attention.service import AttentionService
from pm_agent.config import settings
from pm_agent.database.execution import derive_board


def reconcile_after_execution_change(
    board_id: str,
    *,
    db_path: str | Path | None = None,
) -> dict:
    """Derive then reconcile; published evidence remains valid if this fails."""
    derive_board(board_id, db_path=db_path)
    service = AttentionService(db_path=db_path)
    preview = service.preview_reconciliation(
        actor="system",
        rule_keys=[CRITICAL_MILESTONE_RULE],
    )
    if preview.get("status") != "proposed":
        return preview
    confirmed = service.confirm(
        operation_id=preview["operation_id"],
        confirmation_token=preview["confirmation_token"],
    )
    if confirmed.get("status") != "success":
        raise RuntimeError("Phase 3 Attention reconciliation did not complete")
    return confirmed


def reconcile_after_evidence_publication(
    board_id: str,
    *,
    db_path: str | Path | None = None,
) -> dict:
    """Wait for the complete history-and-links evidence pair before deriving."""
    with sqlite3.connect(Path(db_path or settings.database_path)) as connection:
        datasets = {
            row[0]
            for row in connection.execute(
                """
                SELECT DISTINCT dataset FROM source_evidence_runs
                WHERE board_id = ? AND publication_status = 'published'
                  AND coverage_status = 'complete'
                """,
                [board_id],
            )
        }
    if datasets != {"jira_issue_history", "jira_issue_links"}:
        return {"status": "deferred"}
    return reconcile_after_execution_change(board_id, db_path=db_path)


def reconcile_after_milestone_import(
    operation_id: str,
    *,
    db_path: str | Path | None = None,
) -> list[dict]:
    """Refresh every configured board affected by a confirmed milestone import."""
    with sqlite3.connect(Path(db_path or settings.database_path)) as connection:
        row = connection.execute(
            "SELECT proposed_json FROM milestone_import_operations WHERE operation_id = ?",
            [operation_id],
        ).fetchone()
        if row is None:
            raise ValueError("Unknown Milestone import operation")
        project_ids = sorted({
            item["project_id"] for item in json.loads(row[0])["milestones"]
        })
        placeholders = ",".join("?" for _ in project_ids)
        boards = connection.execute(
            f"SELECT id FROM jira_board_configs WHERE pm_project_id IN ({placeholders}) AND active = 1",
            project_ids,
        ).fetchall()
    return [
        reconcile_after_execution_change(board_id, db_path=db_path)
        for (board_id,) in boards
    ]
