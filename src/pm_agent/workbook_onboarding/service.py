"""Workbook onboarding orchestration service."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from pm_agent.resource_intelligence.service import (
    confirm_import as confirm_capacity_import,
)
from pm_agent.resource_intelligence.service import (
    preview_import as preview_capacity_import,
)
from pm_agent.resource_intelligence.service import (
    validate_package as validate_capacity_package,
)
from pm_agent.workbook_onboarding.capacity_adapter import build_capacity_package
from pm_agent.workbook_onboarding.confirmed_adjustments import scan_workbook_conflicts
from pm_agent.workbook_onboarding.models import ValidationIssue
from pm_agent.workbook_onboarding.parser import parse_workbook
from pm_agent.workbook_onboarding.repository import (
    advance_profile_revision,
    ensure_default_onboarding_profile,
    next_profile_revision,
    resolve_plan_identity,
)
from pm_agent.workbook_onboarding.validator import validate_workbook
from pm_agent.workbook_onboarding.workforce_adapter import build_workforce_package
from pm_agent.workforce_planning_import.service import (
    confirm_import as confirm_workforce_import,
)
from pm_agent.workforce_planning_import.service import (
    preview_import as preview_workforce_import,
)
from pm_agent.workforce_planning_import.service import (
    validate_package as validate_workforce_package,
)


def preview_workbook_import(
    workbook_path: str | Path,
    *,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    candidate = _build_candidate(
        workbook_path,
        reserve_revision=False,
        db_path=db_path,
    )
    return candidate


def import_workbook(
    workbook_path: str | Path,
    *,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    candidate = _build_candidate(
        workbook_path,
        reserve_revision=True,
        db_path=db_path,
    )
    if candidate["status"] == "rejected":
        return candidate

    workforce_preview = preview_workforce_import(
        candidate["workforce_package"],
        db_path=db_path,
    )
    workforce_result: dict[str, Any]
    if workforce_preview["status"] == "previewed":
        workforce_result = confirm_workforce_import(
            workforce_preview["session_id"],
            replace_current=True,
            db_path=db_path,
        )
    else:
        return {
            **candidate,
            "status": "rejected",
            "workforce_result": workforce_preview,
            "capacity_result": None,
        }

    capacity_result: dict[str, Any] | None = None
    if candidate["capacity_package"] is not None:
        capacity_preview = preview_capacity_import(
            candidate["capacity_package"],
            db_path=db_path,
        )
        if capacity_preview["status"] == "previewed":
            capacity_result = confirm_capacity_import(
                capacity_preview["session_id"],
                db_path=db_path,
            )
        else:
            capacity_result = capacity_preview
        if capacity_result["status"] == "rejected":
            return {
                **candidate,
                "status": "partially_completed",
                "workforce_result": workforce_result,
                "capacity_result": capacity_result,
            }

    return {
        **candidate,
        "status": "completed",
        "workforce_result": workforce_result,
        "capacity_result": capacity_result,
    }


def _build_candidate(
    workbook_path: str | Path,
    *,
    reserve_revision: bool,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    workbook_file = Path(workbook_path)
    try:
        parsed = parse_workbook(workbook_file)
    except ValueError as exc:
        return {
            "status": "rejected",
            "workbook_path": str(workbook_file),
            "blockers": [_serialize_issue(_parse_error(str(exc)))],
            "warnings": [],
            "conflicts": [],
        }
    validation = validate_workbook(parsed)
    blockers = [_serialize_issue(item) for item in validation.blockers]
    warnings = [_serialize_issue(item) for item in validation.warnings]
    if validation.workbook is None:
        return {
            "status": "rejected",
            "workbook_path": str(workbook_file),
            "blockers": blockers,
            "warnings": warnings,
            "conflicts": [],
        }

    ensure_default_onboarding_profile(db_path=db_path)
    revision = (
        advance_profile_revision(db_path=db_path)
        if reserve_revision
        else next_profile_revision(db_path=db_path)
    )
    resolved_plan = resolve_plan_identity(
        validation.workbook.setup.plan_version_name,
        db_path=db_path,
    )
    as_of_date = validation.workbook.setup.as_of_date or date.today().isoformat()
    assessment_time = f"{as_of_date}T00:00:00+00:00"
    workforce_package = build_workforce_package(
        validation.workbook,
        plan_version_id=resolved_plan["plan_version_id"],
        version_name=resolved_plan["version_name"],
        as_of_date=as_of_date,
        revision=revision,
    )
    conflicts = scan_workbook_conflicts(
        workforce_package["monthly_allocations"],
        set(validation.workbook.setup.covered_months),
        db_path=db_path,
    )
    if conflicts:
        return {
            "status": "rejected",
            "workbook_path": str(workbook_file),
            "blockers": blockers,
            "warnings": warnings,
            "conflicts": conflicts,
            "plan_version": resolved_plan,
            "revision": revision,
        }
    capacity_package = build_capacity_package(
        validation.workbook,
        plan_version_id=resolved_plan["plan_version_id"],
        version_name=resolved_plan["version_name"],
        assessment_time=assessment_time,
        revision=revision,
    )
    try:
        validate_workforce_package(workforce_package)
        if capacity_package is not None:
            validate_capacity_package(capacity_package)
    except ValueError as exc:
        return {
            "status": "rejected",
            "workbook_path": str(workbook_file),
            "blockers": blockers + [_serialize_issue(_import_error(str(exc)))],
            "warnings": warnings,
            "conflicts": conflicts,
            "plan_version": resolved_plan,
            "revision": revision,
        }
    return {
        "status": "previewed",
        "workbook_path": str(workbook_file),
        "blockers": blockers,
        "warnings": warnings,
        "conflicts": conflicts,
        "plan_version": resolved_plan,
        "revision": revision,
        "counts": {
            "members": len(validation.workbook.members),
            "projects": len(validation.workbook.projects),
            "allocation_rows": len(validation.workbook.allocations),
            "capacity_rows": len(validation.workbook.capacity_rows),
            "expanded_allocation_records": len(workforce_package["monthly_allocations"]),
        },
        "workforce_package": workforce_package,
        "capacity_package": capacity_package,
    }


def _parse_error(message: str) -> ValidationIssue:
    return ValidationIssue(
        severity="blocker",
        code="WORKBOOK_ONBOARDING_PARSE_ERROR",
        message=message,
        location="workbook",
    )


def _import_error(message: str) -> ValidationIssue:
    return ValidationIssue(
        severity="blocker",
        code="WORKBOOK_ONBOARDING_IMPORT_PACKAGE_INVALID",
        message=message,
        location="workbook",
    )


def _serialize_issue(issue: ValidationIssue) -> dict[str, str]:
    return {
        "severity": issue.severity,
        "code": issue.code,
        "message": issue.message,
        "location": issue.location,
    }
