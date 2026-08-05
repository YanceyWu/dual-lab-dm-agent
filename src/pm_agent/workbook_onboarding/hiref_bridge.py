"""Workbook onboarding bridge for legacy HIREF slot/result surfaces."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pm_agent.workbook_onboarding.models import ValidatedWorkbook
from pm_agent.workbook_onboarding.repository import connection

SOURCE_SYSTEM = "workbook_onboarding"


def build_hiref_bridge_payload(
    workbook: ValidatedWorkbook,
    *,
    plan_version_id: str,
    snapshot_present: bool,
) -> dict[str, Any] | None:
    if not snapshot_present and (
        not workbook.hiref_members
        and not workbook.hiref_slots
        and not workbook.hiref_placeholders
        and not workbook.hiref_placeholder_allocations
    ):
        return None
    next_hiref_by_member = {
        item.member_key: item.next_hiref_id for item in workbook.hiref_members
    }
    return {
        "member_next_hiref": [
            {
                "member_id": member.member_key,
                "next_hiref_id": next_hiref_by_member.get(member.member_key, ""),
            }
            for member in workbook.members
        ],
        "slots": [
            {
                "id": item.hiref_id,
                "project": item.project,
                "request_type": item.request_type,
                "start_date": item.start_date,
                "end_date": item.end_date,
                "notes": item.notes or "",
            }
            for item in workbook.hiref_slots
        ],
        "placeholders": [
            {
                "placeholder_id": item.placeholder_id,
                "display_name": item.display_name,
                "source_system": SOURCE_SYSTEM,
                "source_employee_id": "",
                "hiref_id": item.hiref_id or "",
                "linked_employee_id": item.linked_member_key,
                "resource_type": item.resource_type or "",
                "status": item.status,
                "notes": item.notes or "",
                "metadata": "{}",
            }
            for item in workbook.hiref_placeholders
        ],
        "placeholder_allocations": [
            {
                "placeholder_id": item.placeholder_id,
                "project_id": item.project_key,
                "year": item.year,
                "month": item.month_number,
                "allocation": item.allocation,
                "plan_version_id": plan_version_id,
            }
            for item in workbook.hiref_placeholder_allocations
        ],
    }


def persist_hiref_bridge_payload(
    payload: dict[str, Any],
    *,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    with connection(db_path) as database:
        database.execute("BEGIN IMMEDIATE")
        try:
            member_ids = [
                str(item["member_id"]) for item in payload["member_next_hiref"]
            ]
            if member_ids:
                placeholders = ",".join("?" for _ in member_ids)
                database.execute(
                    f"UPDATE employees SET next_hiref='' WHERE id IN ({placeholders})",
                    member_ids,
                )
                database.executemany(
                    "UPDATE employees SET next_hiref=? WHERE id=?",
                    [
                        (str(item["next_hiref_id"]), str(item["member_id"]))
                        for item in payload["member_next_hiref"]
                    ],
                )
            database.execute("DELETE FROM placeholder_monthly_allocations")
            database.execute("DELETE FROM staffing_placeholders")
            database.execute("DELETE FROM hiref")
            if payload["slots"]:
                database.executemany(
                    """
                    INSERT INTO hiref
                        (id, project, request_type, start_date, end_date, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            str(item["id"]),
                            str(item["project"]),
                            str(item["request_type"]),
                            str(item["start_date"]),
                            str(item["end_date"]),
                            str(item["notes"]),
                        )
                        for item in payload["slots"]
                    ],
                )
            if payload["placeholders"]:
                database.executemany(
                    """
                    INSERT INTO staffing_placeholders
                        (placeholder_id, display_name, source_system, source_employee_id,
                         hiref_id, linked_employee_id, resource_type, status, notes, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            str(item["placeholder_id"]),
                            str(item["display_name"]),
                            str(item["source_system"]),
                            str(item["source_employee_id"]),
                            str(item["hiref_id"]),
                            item["linked_employee_id"],
                            str(item["resource_type"] or ""),
                            str(item["status"]),
                            str(item["notes"] or ""),
                            str(item["metadata"]),
                        )
                        for item in payload["placeholders"]
                    ],
                )
            if payload["placeholder_allocations"]:
                database.executemany(
                    """
                    INSERT INTO placeholder_monthly_allocations
                        (placeholder_id, project_id, year, month, allocation, plan_version_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            str(item["placeholder_id"]),
                            str(item["project_id"]),
                            int(item["year"]),
                            int(item["month"]),
                            float(item["allocation"]),
                            str(item["plan_version_id"]),
                        )
                        for item in payload["placeholder_allocations"]
                    ],
                )
            database.commit()
        except Exception:
            database.rollback()
            raise
    return {
        "status": "completed",
        "report": {
            "member_next_hiref_rows": len(payload["member_next_hiref"]),
            "hiref_slot_rows": len(payload["slots"]),
            "placeholder_rows": len(payload["placeholders"]),
            "placeholder_allocation_rows": len(payload["placeholder_allocations"]),
        },
    }
