"""Workbook onboarding orchestration service."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any
from uuid import uuid4

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
from pm_agent.workbook_onboarding.parser import WorkbookParseError, parse_workbook
from pm_agent.workbook_onboarding.presets import (
    DEFAULT_WORKBOOK_MAPPING_PRESET_ID,
    build_source_contract,
    serialize_workbook_preset_lookup,
)
from pm_agent.workbook_onboarding.repository import (
    advance_profile_revision,
    ensure_default_onboarding_profile,
    next_profile_revision,
    release_plan_identity,
    resolve_plan_identity,
    restore_profile_revision,
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
    mapping_preset_id: str = DEFAULT_WORKBOOK_MAPPING_PRESET_ID,
    profile_key: str = "default",
    run_id: str | None = None,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    candidate = _build_candidate(
        workbook_path,
        mapping_preset_id=mapping_preset_id,
        reserve_revision=False,
        profile_key=profile_key,
        run_id=run_id,
        db_path=db_path,
    )
    return candidate


def import_workbook(
    workbook_path: str | Path,
    *,
    mapping_preset_id: str = DEFAULT_WORKBOOK_MAPPING_PRESET_ID,
    profile_key: str = "default",
    run_id: str | None = None,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    effective_run_id = run_id or f"workbook-import-run-{uuid4().hex}"
    candidate = _build_candidate(
        workbook_path,
        mapping_preset_id=mapping_preset_id,
        reserve_revision=True,
        profile_key=profile_key,
        run_id=effective_run_id,
        db_path=db_path,
    )
    if candidate["status"] == "rejected":
        _rollback_rejected_import_candidate(
            profile_key=profile_key,
            candidate=candidate,
            run_id=effective_run_id,
            db_path=db_path,
        )
        return candidate
    try:
        result = confirm_workbook_candidate(candidate, db_path=db_path)
    except RuntimeError as exc:
        if str(exc) == "WORKBOOK_ONBOARDING_WORKFORCE_IN_PROGRESS":
            _rollback_rejected_import_candidate(
                profile_key=profile_key,
                candidate=candidate,
                run_id=effective_run_id,
                db_path=db_path,
            )
        raise
    if result["status"] == "rejected":
        _rollback_rejected_import_candidate(
            profile_key=profile_key,
            candidate=candidate,
            run_id=effective_run_id,
            db_path=db_path,
        )
        return result
    if result["status"] in {"completed", "partially_completed"}:
        release_plan_identity(run_id=effective_run_id, db_path=db_path)
    return result


def confirm_workbook_candidate(
    candidate: dict[str, Any],
    *,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    if candidate["status"] == "rejected":
        return candidate
    workforce_result = _resolve_workforce_result(candidate, db_path=db_path)
    if workforce_result["status"] == "in_progress":
        raise RuntimeError("WORKBOOK_ONBOARDING_WORKFORCE_IN_PROGRESS")
    if workforce_result["status"] != "completed":
        return {
            **candidate,
            "status": "rejected",
            "workforce_result": workforce_result,
            "capacity_result": None,
        }

    capacity_result: dict[str, Any] | None = None
    if candidate["capacity_package"] is not None:
        capacity_preview = preview_capacity_import(
            candidate["capacity_package"],
            db_path=db_path,
        )
        try:
            capacity_result = _resolve_capacity_result(capacity_preview, db_path=db_path)
        except Exception as exc:
            capacity_result = {
                "status": "failed",
                "failure_code": str(exc),
                "session_id": (
                    capacity_preview["session_id"]
                    if isinstance(capacity_preview, dict)
                    and "session_id" in capacity_preview
                    else ""
                ),
            }
        if capacity_result["status"] != "completed":
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


def _resolve_workforce_result(
    candidate: dict[str, Any],
    *,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    workforce_preview = preview_workforce_import(
        candidate["workforce_package"],
        db_path=db_path,
    )
    status = workforce_preview["status"]
    if status in {"previewed", "retryable"}:
        return confirm_workforce_import(
            workforce_preview["session_id"],
            replace_current=True,
            db_path=db_path,
        )
    if status == "already_completed":
        return {
            "status": "completed",
            "session_id": workforce_preview["session_id"],
            "idempotent": True,
            "report": workforce_preview["report"],
        }
    return workforce_preview


def _resolve_capacity_result(
    capacity_preview: dict[str, Any],
    *,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    status = capacity_preview["status"]
    if status in {"previewed", "retryable"}:
        return confirm_capacity_import(
            capacity_preview["session_id"],
            db_path=db_path,
        )
    if status == "already_completed":
        return {
            "status": "completed",
            "session_id": capacity_preview["session_id"],
            "idempotent": True,
            "report": capacity_preview["report"],
        }
    return capacity_preview


def _build_candidate(
    workbook_path: str | Path,
    *,
    mapping_preset_id: str,
    reserve_revision: bool,
    profile_key: str,
    run_id: str | None,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    workbook_file = Path(workbook_path)
    effective_preset_id = mapping_preset_id.strip() or DEFAULT_WORKBOOK_MAPPING_PRESET_ID
    try:
        parsed = parse_workbook(
            workbook_file,
            mapping_preset_id=effective_preset_id,
        )
    except WorkbookParseError as exc:
        return {
            "status": "rejected",
            "workbook_path": str(workbook_file),
            "source_contract": (
                build_source_contract(exc.preset_resolution)
                if exc.preset_resolution is not None
                else None
            ),
            "blockers": [_serialize_issue(_parse_error(exc))],
            "warnings": [],
            "conflicts": [],
        }
    except ValueError as exc:
        if str(exc) != "WORKBOOK_MAPPING_PRESET_UNKNOWN":
            raise
        return {
            "status": "rejected",
            "workbook_path": str(workbook_file),
            "source_contract": {
                "mapping_preset": serialize_workbook_preset_lookup(effective_preset_id),
                "resolution": None,
            },
            "blockers": [
                _serialize_issue(
                    ValidationIssue(
                        severity="blocker",
                        code="WORKBOOK_MAPPING_PRESET_UNKNOWN",
                        message=f"Unknown workbook mapping preset: {effective_preset_id}.",
                        location="mapping_preset_id",
                    )
                )
            ],
            "warnings": [],
            "conflicts": [],
        }
    validation = validate_workbook(parsed)
    source_contract = build_source_contract(parsed.preset_resolution)
    blockers = [_serialize_issue(item) for item in validation.blockers]
    warnings = [_serialize_issue(item) for item in validation.warnings]
    if validation.workbook is None:
        return {
            "status": "rejected",
            "workbook_path": str(workbook_file),
            "source_contract": source_contract,
            "blockers": blockers,
            "warnings": warnings,
            "conflicts": [],
        }

    if profile_key == "default":
        ensure_default_onboarding_profile(db_path=db_path)
    revision = (
        advance_profile_revision(profile_key=profile_key, db_path=db_path)
        if reserve_revision
        else next_profile_revision(profile_key=profile_key, db_path=db_path)
    )
    resolved_plan = resolve_plan_identity(
        validation.workbook.setup.plan_version_name,
        profile_key=profile_key,
        run_id=run_id,
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
            "source_contract": source_contract,
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
            "source_contract": source_contract,
            "blockers": blockers + [_serialize_issue(_import_error(str(exc)))],
            "warnings": warnings,
            "conflicts": conflicts,
            "plan_version": resolved_plan,
            "revision": revision,
        }
    return {
        "status": "previewed",
        "workbook_path": str(workbook_file),
        "source_contract": source_contract,
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


def _parse_error(error: WorkbookParseError) -> ValidationIssue:
    return ValidationIssue(
        severity="blocker",
        code=error.code,
        message=error.message,
        location=error.location,
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


def _rollback_rejected_import_candidate(
    *,
    profile_key: str,
    candidate: dict[str, Any],
    run_id: str,
    db_path: str | Path | None = None,
) -> None:
    revision = candidate.get("revision")
    if isinstance(revision, int):
        restore_profile_revision(
            profile_key=profile_key,
            claimed_revision=revision,
            db_path=db_path,
        )
    release_plan_identity(run_id=run_id, db_path=db_path)
