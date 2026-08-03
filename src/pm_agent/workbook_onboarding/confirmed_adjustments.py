"""Stable read surface for confirmed Copilot staffing adjustments."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pm_agent.workbook_onboarding import repository
from pm_agent.workforce_planning_import import repository as workforce_repository


def list_confirmed_staffing_adjustments(
    *,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    current = workforce_repository.current_publication(db_path=db_path)
    if not current:
        return []
    package = json.loads(current["package_json"])
    current_plan_ids = {
        item["plan_version_id"] for item in package.get("plan_versions", [])
    }
    if not current_plan_ids:
        return []
    baseline_allocations = {
        (
            row["member_id"],
            row["project_id"],
            int(row["year"]),
            int(row["month"]),
            row["plan_version_id"],
        ): float(row["allocation"])
        for row in package.get("monthly_allocations", [])
    }
    with repository.connection(db_path) as database:
        rows = database.execute(
            """
            SELECT proposal_id,request_json,proposal_json,confirmed_at,decision_id
            FROM staffing_proposals
            WHERE status='confirmed' AND decision_id IS NOT NULL
            ORDER BY confirmed_at,proposal_id
            """
        ).fetchall()
        results_by_key: dict[tuple[str, str, int, int], dict[str, Any]] = {}
        for row in rows:
            request = json.loads(row["request_json"] or "{}")
            proposal = json.loads(row["proposal_json"] or "{}")
            plan_version_id = str(proposal.get("plan_version_id") or "")
            if plan_version_id not in current_plan_ids:
                continue
            project_id = str(request.get("project_id") or "")
            if not project_id:
                continue
            for selection in proposal.get("selections", []):
                member_id = str(selection.get("member_id") or "")
                if not member_id:
                    continue
                for period in proposal.get("periods", []):
                    year = int(period["year"])
                    month = int(period["month"])
                    business_key = (member_id, project_id, year, month)
                    effective_allocation = database.execute(
                        """
                        SELECT COALESCE(SUM(allocation), 0.0)
                        FROM monthly_allocations
                        WHERE employee_id=? AND project_id=? AND year=? AND month=? AND plan_version_id=?
                        """,
                        [member_id, project_id, year, month, plan_version_id],
                    ).fetchone()[0]
                    results_by_key[business_key] = {
                        "member_id": member_id,
                        "project_id": project_id,
                        "year": year,
                        "month": month,
                        "plan_version_id": plan_version_id,
                        "baseline_allocation": baseline_allocations.get(
                            (member_id, project_id, year, month, plan_version_id), 0.0
                        ),
                        "effective_allocation": float(effective_allocation or 0.0),
                        "decision_id": int(row["decision_id"]),
                        "proposal_id": row["proposal_id"],
                        "confirmed_at": row["confirmed_at"],
                    }
        return sorted(
            results_by_key.values(),
            key=lambda item: (
                item["member_id"],
                item["project_id"],
                item["year"],
                item["month"],
            ),
        )


def scan_workbook_conflicts(
    candidate_allocations: list[dict[str, Any]],
    covered_months: set[tuple[int, int]],
    *,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    candidate_map = {
        (
            str(row["member_id"]),
            str(row["project_id"]),
            int(row["year"]),
            int(row["month"]),
        ): float(row["allocation"])
        for row in candidate_allocations
    }
    conflicts = []
    for item in list_confirmed_staffing_adjustments(db_path=db_path):
        key = (item["member_id"], item["project_id"], item["year"], item["month"])
        if (item["year"], item["month"]) not in covered_months:
            continue
        candidate_value = candidate_map.get(key)
        effective_value = float(item["effective_allocation"])
        if candidate_value is None or abs(candidate_value - effective_value) > 1e-9:
            conflicts.append(
                {
                    **item,
                    "candidate_allocation": candidate_value,
                    "conflict_code": "WORKBOOK_ONBOARDING_CONFIRMED_ADJUSTMENT_CONFLICT",
                }
            )
    return conflicts
