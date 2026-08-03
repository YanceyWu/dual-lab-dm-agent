"""Adapter from workbook-native validated data to workforce import packages."""

from __future__ import annotations

from typing import Any

from pm_agent.rules.identity import slugify_text
from pm_agent.workbook_onboarding.models import (
    ValidatedCapacityRow,
    ValidatedWorkbook,
)

DATASET_MARKER = "WORKBOOK_ONBOARDING_V1"
SOURCE_ID = "source-workbook-team-project-capacity"


def build_workforce_package(
    workbook: ValidatedWorkbook,
    *,
    plan_version_id: str,
    version_name: str,
    as_of_date: str,
    revision: int,
) -> dict[str, Any]:
    package_slug = slugify_text(version_name) or "baseline"
    members = _build_members(workbook, workbook.capacity_rows)
    member_periods = _build_member_periods(workbook, members)
    projects = [
        {
            "project_id": project.project_key,
            "display_name": project.display_name,
            "status": project.status,
            "priority": project.priority,
            "start_date": project.start_date,
            "target_end": project.target_end,
        }
        for project in workbook.projects
    ]
    allocation_map = {
        (allocation.member_key, allocation.project_key, allocation.year, allocation.month_number): allocation.allocation
        for allocation in workbook.allocations
    }
    monthly_allocations = []
    allocation_keys = []
    for member_id, year, month in member_periods:
        for project in workbook.projects:
            allocation_keys.append(
                {
                    "member_id": member_id,
                    "project_id": project.project_key,
                    "plan_version_id": plan_version_id,
                    "year": year,
                    "month": month,
                }
            )
            monthly_allocations.append(
                {
                    "member_id": member_id,
                    "project_id": project.project_key,
                    "plan_version_id": plan_version_id,
                    "year": year,
                    "month": month,
                    "allocation": float(
                        allocation_map.get((member_id, project.project_key, year, month), 0.0)
                    ),
                }
            )
    return {
        "dataset_marker": DATASET_MARKER,
        "package_id": f"package-workbook-workforce-{package_slug}-r{revision}",
        "schema_version": "workforce-planning-import-v1",
        "generated_at": f"{as_of_date}T00:00:00+00:00",
        "source_id": SOURCE_ID,
        "manifest": {
            "member_ids": [member["member_id"] for member in members],
            "project_ids": [project["project_id"] for project in projects],
            "plan_version_ids": [plan_version_id],
            "workforce_periods": [
                {"member_id": member_id, "year": year, "month": month}
                for member_id, year, month in member_periods
            ],
            "allocation_keys": allocation_keys,
        },
        "members": members,
        "projects": projects,
        "plan_versions": [
            {
                "plan_version_id": plan_version_id,
                "version_name": version_name,
                "scenario_type": "baseline",
                "as_of_date": as_of_date,
                "status": "active",
            }
        ],
        "monthly_allocations": monthly_allocations,
    }


def _build_members(
    workbook: ValidatedWorkbook, capacity_rows: list[ValidatedCapacityRow]
) -> list[dict[str, Any]]:
    allocation_months: dict[str, set[str]] = {}
    for allocation in workbook.allocations:
        allocation_months.setdefault(allocation.member_key, set()).add(allocation.month)
    capacity_month_map: dict[str, set[str]] = {}
    for row in capacity_rows:
        capacity_month_map.setdefault(row.member_key, set()).add(row.month)
    members = []
    for member in workbook.members:
        effective_start = member.effective_start or _derive_member_start(
            member.member_key,
            workbook.setup.start_month,
            allocation_months.get(member.member_key, set()),
            capacity_month_map.get(member.member_key, set()),
        )
        members.append(
            {
                "member_id": member.member_key,
                "display_name": member.display_name,
                "role": member.role or "unspecified",
                "level": str(member.level) if member.level is not None else "unknown",
                "status": member.status,
                "effective_start": effective_start,
                "effective_end": member.effective_end,
                "resource_type": member.fte_type,
                "current_hiref_id": member.current_hiref_id,
                "hiref_end_date": member.hiref_end_date,
            }
        )
    return members


def _build_member_periods(
    workbook: ValidatedWorkbook, members: list[dict[str, Any]]
) -> list[tuple[str, int, int]]:
    periods: list[tuple[str, int, int]] = []
    for member in members:
        start = member["effective_start"][:7]
        end = member["effective_end"][:7] if member["effective_end"] else workbook.setup.end_month
        for year, month in workbook.setup.covered_months:
            month_text = f"{year:04d}-{month:02d}"
            if start <= month_text <= end:
                periods.append((member["member_id"], year, month))
    periods.sort()
    return periods


def _derive_member_start(
    member_key: str,
    default_month: str,
    allocation_months: set[str],
    capacity_months: set[str],
) -> str:
    candidate_months = sorted(allocation_months | capacity_months)
    month_text = candidate_months[0] if candidate_months else default_month
    return f"{month_text}-01"
