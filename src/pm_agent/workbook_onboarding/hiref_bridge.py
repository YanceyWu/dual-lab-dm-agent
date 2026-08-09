"""Workbook onboarding bridge for legacy HIREF slot/result surfaces."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from pm_agent.rules.identity import slugify_text
from pm_agent.workbook_onboarding.models import ValidatedWorkbook
from pm_agent.workbook_onboarding.repository import connection

SOURCE_SYSTEM = "workbook_onboarding"


def export_snapshot(
    *, plan_version_id: str, member_ids: list[str], db_path: str | Path | None = None
) -> dict[str, Any]:
    """Expose the retained HIREF bridge as one complete export contract.

    Workbook orchestration must not reach into legacy bridge tables.  This
    owner validates that requests, member next-HIREF references, and open
    demand allocations describe one internally consistent bridge generation.
    """
    with connection(db_path) as database:
        requests = database.execute(
            "SELECT id,project,request_type,start_date,end_date,notes FROM hiref ORDER BY id"
        ).fetchall()
        request_ids = {str(row["id"]) for row in requests}
        project_ids = {
            str(row["id"])
            for row in database.execute("SELECT id FROM projects").fetchall()
        }
        if member_ids:
            placeholders = ",".join("?" for _ in member_ids)
            members = database.execute(
                f"SELECT id,next_hiref FROM employees WHERE id IN ({placeholders}) ORDER BY id",
                member_ids,
            ).fetchall()
        else:
            members = []
        if [str(row["id"]) for row in members] != sorted(member_ids):
            raise ValueError("WORKBOOK_EXPORT_HIREF_MEMBERS_INCOMPLETE")
        open_demand = database.execute(
            """SELECT pma.project_id,pma.year,pma.month,pma.allocation,sp.hiref_id,
                      sp.status,sp.source_system
               FROM placeholder_monthly_allocations pma
               JOIN staffing_placeholders sp ON sp.placeholder_id=pma.placeholder_id
               WHERE pma.plan_version_id=? ORDER BY sp.hiref_id,pma.project_id,pma.year,pma.month""",
            [plan_version_id],
        ).fetchall()
    next_hiref = {str(row["id"]): str(row["next_hiref"] or "") for row in members}
    referenced = {value for value in next_hiref.values() if value}
    referenced.update(str(row["hiref_id"] or "") for row in open_demand)
    if "" in referenced or not referenced <= request_ids:
        raise ValueError("WORKBOOK_EXPORT_HIREF_REFERENCE_INCOMPLETE")
    if any(
        str(row["status"]) != "planned" or str(row["source_system"]) != SOURCE_SYSTEM
        for row in open_demand
    ):
        raise ValueError("WORKBOOK_EXPORT_HIREF_OPEN_DEMAND_INVALID")
    request_rows = []
    for row in requests:
        project = str(row["project"])
        if " (" in project and project.endswith(")"):
            project_id = project.rsplit(" (", 1)[1][:-1]
        else:
            # Older synthetic/legacy source rows retain the canonical project
            # ID directly. This is a storage compatibility representation of
            # the same user-maintained HIREF fact, not a derived projection.
            project_id = project
        if project_id not in project_ids:
            raise ValueError("WORKBOOK_EXPORT_HIREF_REQUEST_PROJECT_INVALID")
        request_rows.append([
            str(row["id"]), project_id, str(row["request_type"]),
            str(row["start_date"]), str(row["end_date"]), str(row["notes"] or ""),
        ])
    open_rows = [
        ["", str(row["project_id"]), f"{int(row['year']):04d}-{int(row['month']):02d}",
         float(row["allocation"]), str(row["hiref_id"])]
        for row in open_demand
    ]
    material = {"member_next_hiref": next_hiref, "requests": request_rows, "open_demand": open_rows}
    generation = hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "member_next_hiref": next_hiref,
        "hiref_requests": request_rows,
        "open_demand_allocations": open_rows,
        "evidence": {"bridge_generation": generation, "plan_version_id": plan_version_id},
    }


def build_hiref_bridge_payload(
    workbook: ValidatedWorkbook,
    *,
    plan_version_id: str,
    snapshot_present: bool,
) -> dict[str, Any] | None:
    if not snapshot_present and (
        not any(member.next_hiref_id for member in workbook.members)
        and not workbook.hiref_requests
        and not workbook.hiref_demand_allocations
    ):
        return None
    project_by_key = {
        project.project_key: project.display_name for project in workbook.projects
    }
    request_by_id = {request.hiref_id: request for request in workbook.hiref_requests}
    return {
        "member_next_hiref": [
            {
                "member_id": member.member_key,
                "next_hiref_id": member.next_hiref_id or "",
            }
            for member in workbook.members
        ],
        "slots": [
            {
                "id": item.hiref_id,
                "project": _project_display(
                    item.project_key,
                    project_by_key=project_by_key,
                ),
                "request_type": item.request_type,
                "start_date": item.start_date,
                "end_date": item.end_date,
                "notes": item.notes or "",
            }
            for item in workbook.hiref_requests
        ],
        "placeholders": _build_placeholder_rows(
            workbook=workbook,
            request_by_id=request_by_id,
            project_by_key=project_by_key,
        ),
        "placeholder_allocations": [
            {
                "placeholder_id": _placeholder_id(item.hiref_id),
                "project_id": item.project_key,
                "year": item.year,
                "month": item.month_number,
                "allocation": item.allocation,
                "plan_version_id": plan_version_id,
            }
            for item in workbook.hiref_demand_allocations
        ],
    }


def _build_placeholder_rows(
    *,
    workbook: ValidatedWorkbook,
    request_by_id: dict[str, Any],
    project_by_key: dict[str, str],
) -> list[dict[str, Any]]:
    placeholders: list[dict[str, Any]] = []
    seen_hiref_ids: set[str] = set()
    for allocation in sorted(
        workbook.hiref_demand_allocations,
        key=lambda item: (item.hiref_id, item.project_key, item.month),
    ):
        if allocation.hiref_id in seen_hiref_ids:
            continue
        seen_hiref_ids.add(allocation.hiref_id)
        request = request_by_id.get(allocation.hiref_id)
        project_display_name = project_by_key.get(allocation.project_key, allocation.project_key)
        notes = ""
        if request is not None and request.notes:
            notes = request.notes
        placeholders.append(
            {
                "placeholder_id": _placeholder_id(allocation.hiref_id),
                "display_name": f"Open demand for {project_display_name}",
                "source_system": SOURCE_SYSTEM,
                "source_employee_id": "",
                "hiref_id": allocation.hiref_id,
                "linked_employee_id": None,
                "resource_type": "STFTE",
                "status": "planned",
                "notes": notes,
                "metadata": "{}",
            }
        )
    return placeholders


def _project_display(project_key: str, *, project_by_key: dict[str, str]) -> str:
    project_name = project_by_key.get(project_key, project_key)
    return f"{project_name} ({project_key})"


def _placeholder_id(hiref_id: str) -> str:
    suffix = slugify_text(hiref_id) or hiref_id.lower()
    return f"placeholder-{suffix}"


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
