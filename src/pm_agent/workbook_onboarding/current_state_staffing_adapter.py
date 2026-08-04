"""Adapter from workbook-native validated data to current-state staffing packages."""

from __future__ import annotations

from typing import Any

from pm_agent.current_state_staffing.service import PACKAGE_SCHEMA_VERSION
from pm_agent.rules.identity import slugify_text
from pm_agent.workbook_onboarding.models import ValidatedWorkbook

DATASET_MARKER = "WORKBOOK_ONBOARDING_V1"
SOURCE_ID = "source-workbook-current-state-staffing"
SCOPE_KEY = "workbook-current-state-staffing"


def build_current_state_staffing_package(
    workbook: ValidatedWorkbook,
    *,
    version_name: str,
    as_of_date: str,
    revision: int,
) -> dict[str, Any]:
    package_slug = slugify_text(version_name) or "baseline"
    effective_year, effective_month = _effective_period(workbook, as_of_date)
    members = [
        {
            "member_id": member.member_key,
            "display_name": member.display_name,
            "status": member.status,
            "role": member.role or "unspecified",
            "level": str(member.level) if member.level is not None else "unknown",
            "resource_type": member.fte_type,
            "current_hiref_id": member.current_hiref_id,
            "hiref_end_date": member.hiref_end_date,
        }
        for member in workbook.members
    ]
    projects = [
        {
            "project_id": project.project_key,
            "display_name": project.display_name,
            "status": project.status,
            "priority": project.priority,
        }
        for project in workbook.projects
    ]
    assignments = [
        {
            "member_id": allocation.member_key,
            "project_id": allocation.project_key,
            "allocation": allocation.allocation,
        }
        for allocation in workbook.allocations
        if allocation.year == effective_year
        and allocation.month_number == effective_month
        and allocation.allocation > 0
    ]
    assignments.sort(key=lambda item: (item["member_id"], item["project_id"]))
    return {
        "dataset_marker": DATASET_MARKER,
        "package_id": f"package-workbook-current-state-{package_slug}-r{revision}",
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "generated_at": f"{as_of_date}T00:00:00+00:00",
        "source_id": SOURCE_ID,
        "publication_scope": {
            "scope_key": SCOPE_KEY,
            "as_of_date": as_of_date,
            "effective_year": effective_year,
            "effective_month": effective_month,
        },
        "manifest": {
            "member_ids": [member["member_id"] for member in members],
            "project_ids": [project["project_id"] for project in projects],
            "assignment_keys": [
                {
                    "member_id": assignment["member_id"],
                    "project_id": assignment["project_id"],
                }
                for assignment in assignments
            ],
        },
        "members": members,
        "projects": projects,
        "assignments": assignments,
    }


def _effective_period(workbook: ValidatedWorkbook, as_of_date: str) -> tuple[int, int]:
    as_of_month = as_of_date[:7]
    for year, month in workbook.setup.covered_months:
        if as_of_month == f"{year:04d}-{month:02d}":
            return year, month
    return workbook.setup.covered_months[0]
