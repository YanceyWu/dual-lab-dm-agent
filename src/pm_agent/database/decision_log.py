"""
database/decision_log.py — Append-only decision recorder.

Contract:
- Historical records are NEVER modified (only outcome fields can be set once).
- Every allocation confirmation writes a record automatically.
- Follow-up analysis uses the indexes created in database/bootstrap.py.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import sqlite3

from pm_agent.config import settings


def _conn() -> sqlite3.Connection:
    con = sqlite3.connect(Path(settings.database_path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def record_allocation(
    project_id: str,
    project_name: str,
    requirement: dict,
    all_candidates: list[dict],  # [{member_id, name, score, breakdown, blocked}]
    chosen_members: list[dict],  # [{member_id, name}]
    alternatives: list[dict],    # [{label, members}]
) -> int:
    """
    Write one immutable decision record.
    Returns the new row id (stored on ServiceResponse.decision_id).
    """
    member_ids = [m["member_id"] for m in chosen_members]
    names = [m["name"] for m in chosen_members]
    description = (
        f"为 [{project_name}] 分配 {', '.join(names)}"
        f"（{requirement.get('role', '未指定角色')}）"
    )

    row = {
        "type": "allocation",
        "description": description,
        "context": json.dumps(
            {
                "project_id": project_id,
                "project_name": project_name,
                "task_type": requirement.get("task_type", ""),
                "role": requirement.get("role", ""),
                "count": requirement.get("count", 1),
                "recorded_at": datetime.now().isoformat(),
            },
            ensure_ascii=False,
        ),
        "candidates": json.dumps(all_candidates, ensure_ascii=False),
        "chosen": json.dumps(
            {"members": chosen_members}, ensure_ascii=False
        ),
        "alternatives": json.dumps(alternatives, ensure_ascii=False),
        "project_id": project_id,
        "member_ids": json.dumps(member_ids, ensure_ascii=False),
    }

    con = _conn()
    try:
        cur = con.execute(
            """
            INSERT INTO decision_log
                (type, description, context, candidates, chosen,
                 alternatives, project_id, member_ids)
            VALUES
                (:type,:description,:context,:candidates,:chosen,
                 :alternatives,:project_id,:member_ids)
            """,
            row,
        )
        row_id: int = cur.lastrowid  # type: ignore[assignment]
        con.commit()
        return row_id
    finally:
        con.close()


def set_outcome(decision_id: int, outcome: str, note: str = "") -> None:
    """
    Fill in the result after the fact.
    outcome: 'success' | 'delayed' | 'failed' | 'cancelled'
    Only works if current outcome is 'pending' (prevents accidental overwrite).
    """
    valid = {"success", "delayed", "failed", "cancelled"}
    if outcome not in valid:
        raise ValueError(f"outcome must be one of {valid}, got '{outcome}'")

    con = _conn()
    try:
        con.execute(
            """
            UPDATE decision_log
            SET outcome=?, outcome_note=?, outcome_at=datetime('now')
            WHERE id=? AND outcome='pending'
            """,
            [outcome, note, decision_id],
        )
        con.commit()
    finally:
        con.close()


def record_manual(type_: str, description: str, context: dict, chosen: dict) -> int:
    """Generic log entry for non-allocation decisions (priority change, risk accept, etc.)."""
    row = {
        "type": type_,
        "description": description,
        "context": json.dumps(context, ensure_ascii=False),
        "candidates": None,
        "chosen": json.dumps(chosen, ensure_ascii=False),
        "alternatives": None,
        "project_id": context.get("project_id"),
        "member_ids": json.dumps([]),
        "created_by": "manual",
    }
    con = _conn()
    try:
        cur = con.execute(
            """
            INSERT INTO decision_log
                (type, description, context, candidates, chosen,
                 alternatives, project_id, member_ids, created_by)
            VALUES
                (:type,:description,:context,:candidates,:chosen,
                 :alternatives,:project_id,:member_ids,:created_by)
            """,
            row,
        )
        row_id: int = cur.lastrowid  # type: ignore[assignment]
        con.commit()
        return row_id
    finally:
        con.close()
