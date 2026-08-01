"""Read-only queries for the Phase 3 execution-review capability."""

from __future__ import annotations

import json
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any

from pm_agent.config import settings


def list_latest_execution_facts(
    project_id: str,
    *,
    layer: str,
    subject_kind: str | None,
    subject_id: str | None,
    since: str,
    limit: int,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Return bounded facts from the newest completed derivation per board."""
    connection = sqlite3.connect(Path(db_path or settings.database_path))
    connection.row_factory = sqlite3.Row
    try:
        if not connection.execute("SELECT 1 FROM projects WHERE id = ?", [project_id]).fetchone():
            raise ValueError("PROJECT_NOT_FOUND")
        kinds = ("sprint",) if layer == "sprint" else (
            "release", "milestone", "dependency",
        ) if layer == "release_milestone" else ("sprint", "release", "milestone", "dependency")
        placeholders = ", ".join("?" for _ in kinds)
        clauses = [
            "f.project_id = ?",
            f"f.subject_kind IN ({placeholders})",
            "dr.finished_at >= ?",
            "NOT EXISTS (SELECT 1 FROM execution_derivation_runs later "
            "WHERE later.project_id = dr.project_id AND later.board_id = dr.board_id "
            "AND (later.finished_at > dr.finished_at OR "
            "(later.finished_at = dr.finished_at AND later.derivation_run_id > dr.derivation_run_id)))",
        ]
        values: list[Any] = [project_id, *kinds, since]
        if subject_kind:
            clauses.append("f.subject_kind = ?")
            values.append(subject_kind)
        if subject_id:
            clauses.append("f.subject_id = ?")
            values.append(subject_id)
        values.append(limit)
        rows = connection.execute(
            f"""
            SELECT f.*, dr.board_id, dr.rule_version, dr.completeness_state,
                   dr.freshness_state AS run_freshness_state, dr.warning_codes_json,
                   dr.started_at, dr.finished_at
            FROM execution_facts f
            JOIN execution_derivation_runs dr ON dr.derivation_run_id = f.derivation_run_id
            WHERE {' AND '.join(clauses)}
            ORDER BY dr.finished_at DESC, f.subject_kind, f.subject_id, f.fact_key
            LIMIT ?
            """,
            values,
        ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["value"] = json.loads(item.pop("value_json"))
            item["evidence"] = json.loads(item.pop("evidence_json"))
            item["warning_codes"] = json.loads(item.pop("warning_codes_json"))
            item["fact_observed_at"] = item["finished_at"] or item["started_at"]
            is_achievement = (
                item["subject_kind"] == "milestone"
                and item["fact_key"] == "milestone_adherence"
                and item["value_state"] == "known"
                and item["value"] in {"achieved_on_time", "achieved_late"}
            )
            event_date = (
                item["evidence"].get("actual_date")
                if is_achievement and isinstance(item["evidence"], dict)
                else ""
            )
            try:
                item["event_occurred_at"] = (
                    date.fromisoformat(event_date).isoformat()
                    if isinstance(event_date, str) and event_date
                    else ""
                )
            except ValueError:
                item["event_occurred_at"] = ""
            item["event_time_precision"] = (
                "date" if item["event_occurred_at"] else "not_available"
            )
            item["event_time_state"] = (
                "known" if item["event_occurred_at"] else "not_available"
            )
            item["event_time_basis"] = (
                "fact_derivation_evidence" if item["event_occurred_at"] else ""
            )
            if is_achievement and not item["event_occurred_at"]:
                item["warning_codes"].append("EXECUTION_EVENT_TIME_NOT_AVAILABLE")
            item["input_ids"] = [
                dict(input_row)
                for input_row in connection.execute(
                    """
                    SELECT input_kind, input_id FROM execution_derivation_inputs
                    WHERE derivation_run_id = ? ORDER BY input_kind, input_id
                    """,
                    [item["derivation_run_id"]],
                )
            ]
            result.append(item)
        return result
    finally:
        connection.close()
