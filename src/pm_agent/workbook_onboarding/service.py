"""Workbook onboarding orchestration service."""

from __future__ import annotations

from datetime import date
import hashlib
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from openpyxl import Workbook

from pm_agent.contract_coverage.service import (
    confirm_import as confirm_contract_coverage_import,
)
from pm_agent.contract_coverage.service import (
    preview_import as preview_contract_coverage_import,
)
from pm_agent.contract_coverage.service import (
    validate_package as validate_contract_coverage_package,
)
from pm_agent.resource_intelligence.service import (
    confirm_import as confirm_capacity_import,
)
from pm_agent.resource_intelligence.service import (
    preview_import as preview_capacity_import,
)
from pm_agent.resource_intelligence.service import (
    validate_package as validate_capacity_package,
)
from pm_agent.current_state_staffing.service import (
    confirm_import as confirm_current_state_staffing_import,
)
from pm_agent.current_state_staffing.service import (
    preview_import as preview_current_state_staffing_import,
)
from pm_agent.current_state_staffing.service import (
    validate_package as validate_current_state_staffing_package,
)
from pm_agent.workbook_onboarding.contract_coverage_adapter import (
    build_contract_coverage_package,
)
from pm_agent.workbook_onboarding.current_state_staffing_adapter import (
    build_current_state_staffing_package,
)
from pm_agent.workbook_onboarding.capacity_adapter import build_capacity_package
from pm_agent.workbook_onboarding.confirmed_adjustments import scan_workbook_conflicts
from pm_agent.workbook_onboarding.hiref_bridge import (
    build_hiref_bridge_payload,
    export_snapshot as hiref_export_snapshot,
    persist_hiref_bridge_payload,
)
from pm_agent.workbook_onboarding.models import ValidationIssue
from pm_agent.workbook_onboarding.parser import WorkbookParseError, parse_workbook
from pm_agent.workbook_onboarding.presets import (
    DEFAULT_WORKBOOK_MAPPING_PRESET_ID,
    build_source_contract,
    get_workbook_preset,
    serialize_workbook_preset_lookup,
)
from pm_agent.resource_intelligence.read_model import source_capacity_export_snapshot
from pm_agent.data_onboarding.source_context import latest_workbook_source_context
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
from pm_agent.workforce_planning_import.read_model import source_export_snapshot
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


def export_current_state_workbook(
    output_path: str | Path,
    *,
    plan_version_id: str | None = None,
    overwrite: bool = False,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Export maintained planning source facts using the v1 workbook contract.

    This is a read-only portability snapshot. It fails closed for missing or
    ambiguous source facts, never because a derived publication is stale or
    absent.
    """
    target = Path(output_path).expanduser()
    if target.suffix.lower() != ".xlsx":
        return _export_failed("WORKBOOK_EXPORT_OUTPUT_EXTENSION_INVALID")
    if target.exists() and not overwrite:
        return _export_failed("WORKBOOK_EXPORT_OUTPUT_EXISTS")
    if not target.parent.exists() or not target.parent.is_dir():
        return _export_failed("WORKBOOK_EXPORT_OUTPUT_PARENT_MISSING")

    try:
        snapshot = _export_snapshot(plan_version_id=plan_version_id, db_path=db_path)
    except ValueError as exc:
        return _export_failed(str(exc))

    temporary = target.with_name(f".{target.name}.{uuid4().hex}.tmp.xlsx")
    try:
        _write_export_workbook(temporary, snapshot)
        parsed = parse_workbook(temporary, mapping_preset_id=DEFAULT_WORKBOOK_MAPPING_PRESET_ID)
        validation = validate_workbook(parsed)
        if validation.workbook is None:
            raise ValueError("WORKBOOK_EXPORT_ROUNDTRIP_REJECTED")
        if overwrite:
            os.replace(temporary, target)
        else:
            # ``exists`` followed by replace is a TOCTOU overwrite.  link(2)
            # creates the final name only if it still does not exist.
            os.link(temporary, target)
    except FileExistsError:
        temporary.unlink(missing_ok=True)
        return _export_failed("WORKBOOK_EXPORT_OUTPUT_EXISTS")
    except ValueError as exc:
        temporary.unlink(missing_ok=True)
        code = str(exc)
        if code.startswith("WORKBOOK_EXPORT_"):
            return _export_failed(code)
        return _export_failed("WORKBOOK_EXPORT_WRITE_FAILED")
    except OSError:
        temporary.unlink(missing_ok=True)
        return _export_failed("WORKBOOK_EXPORT_WRITE_FAILED")
    finally:
        temporary.unlink(missing_ok=True)

    return {
        "status": "success",
        "output_path": str(target.resolve()),
        "sha256": _sha256(target),
        "plan_version": snapshot["plan_version"],
        "counts": snapshot["counts"],
        "warnings": [],
        "evidence": snapshot["evidence"],
    }


def _export_failed(code: str) -> dict[str, Any]:
    return {"status": "failed", "warnings": [code]}


def _export_snapshot(
    *, plan_version_id: str | None, db_path: str | Path | None
) -> dict[str, Any]:
    """Read maintained source facts and turn them into v1 workbook rows."""
    workforce = source_export_snapshot(plan_version_id=plan_version_id, db_path=db_path)
    plan = workforce["plan_version"]
    context = latest_workbook_source_context(
        plan_version_id=str(plan["plan_version_id"]), db_path=db_path
    )
    member_records = workforce["members"]
    project_records = workforce["projects"]
    allocation_rows = workforce["allocations"]
    member_ids = [str(row["id"]) for row in member_records]
    project_ids = [str(row["id"]) for row in project_records]
    capacity = source_capacity_export_snapshot(
        plan_version_id=plan["plan_version_id"],
        capacity_context=context["capacity"],
        db_path=db_path,
    )
    capacity_member_ids = {str(fact["member_id"]) for fact in capacity["facts"]}
    if not capacity_member_ids <= set(member_ids):
        raise ValueError("WORKBOOK_EXPORT_CAPACITY_SOURCE_MEMBER_INCOMPLETE")

    capacity_rows = [
        [fact["member_id"], f"{fact['year']:04d}-{fact['month']:02d}",
         fact["leave_fraction"], fact["bau_fraction"], fact["non_project_fraction"]]
        for fact in capacity["facts"]
    ]

    allocations = [
        [str(row["employee_id"]), str(row["project_id"]), f"{int(row['year']):04d}-{int(row['month']):02d}", float(row["allocation"]), ""]
        for row in allocation_rows
    ]
    hiref = hiref_export_snapshot(
        plan_version_id=plan["plan_version_id"], member_ids=member_ids, db_path=db_path
    )
    allocations.extend(hiref["open_demand_allocations"])
    _validate_horizon_rows(
        start_month=context["start_month"], end_month=context["end_month"],
        allocations=allocations, capacity_facts=capacity["facts"],
    )
    row_by_member = {str(row["id"]): row for row in member_records}
    row_by_project = {str(row["id"]): row for row in project_records}
    request_ids = {str(row[0]) for row in hiref["hiref_requests"]}
    members = []
    for member_id in member_ids:
        row = row_by_member[member_id]
        metadata = _metadata_dict(row["metadata"])
        current_hiref = str(row["current_hiref"] or "")
        hiref_end_date = str(row["billing_end_date"] or "")
        if str(row["resource_type"]) == "STFTE" and (
            not current_hiref or not hiref_end_date
        ):
            raise ValueError("WORKBOOK_EXPORT_STFTE_HIREF_REQUIRED")
        if current_hiref and current_hiref not in request_ids:
            raise ValueError("WORKBOOK_EXPORT_HIREF_REFERENCE_INCOMPLETE")
        status = str(row["status"])
        if status not in {"active", "inactive"}:
            raise ValueError("WORKBOOK_EXPORT_MEMBER_STATUS_UNSUPPORTED")
        members.append([
            member_id, str(row["name"]), str(row["resource_type"]),
            status,
            current_hiref, hiref_end_date,
            str(row["role"] or ""), _level_as_int(row["level"]),
            metadata.get("effective_start") or "", metadata.get("effective_end") or "",
            hiref["member_next_hiref"][member_id],
        ])
    projects = [
        [project_id, str(row_by_project[project_id]["name"]), str(row_by_project[project_id]["status"]),
         int(row_by_project[project_id]["priority"]), row_by_project[project_id]["start_date"] or "", row_by_project[project_id]["target_end"] or ""]
        for project_id in project_ids
    ]
    start_month, end_month = context["start_month"], context["end_month"]
    return {
        "plan_version": {"plan_version_id": str(plan["plan_version_id"]), "version_name": str(plan["version_name"])},
        "setup": [[str(plan["version_name"]), str(plan["as_of_date"] or ""), start_month, end_month]],
        "members": members, "projects": projects, "allocations": allocations, "capacity": capacity_rows,
        "hiref_requests": hiref["hiref_requests"],
        "counts": {"setup": 1, "members": len(members), "projects": len(projects), "allocations": len(allocations), "capacity": len(capacity_rows), "hiref_requests": len(hiref["hiref_requests"])},
        "evidence": {"plan_version_id": str(plan["plan_version_id"]),
                     "capacity_source": capacity["source"], "hiref_bridge": hiref["evidence"]},
    }


def _validate_horizon_rows(
    *, start_month: str, end_month: str, allocations: list[list[Any]],
    capacity_facts: list[dict[str, Any]],
) -> None:
    """Reject source facts that cannot be re-imported under their Setup range."""
    months = [str(row[2]) for row in allocations]
    months.extend(f"{int(row['year']):04d}-{int(row['month']):02d}" for row in capacity_facts)
    if any(month < start_month or month > end_month for month in months):
        raise ValueError("WORKBOOK_EXPORT_SOURCE_HORIZON_SCOPE_INCOMPLETE")


def _metadata_dict(value: Any) -> dict[str, Any]:
    import json
    try:
        result = json.loads(value or "{}")
    except (TypeError, ValueError):
        return {}
    return result if isinstance(result, dict) else {}


def _level_as_int(value: Any) -> int:
    try:
        level = int(value)
    except (TypeError, ValueError):
        aliases = {"junior": 5, "mid": 6, "senior": 7, "lead": 8}
        level = aliases.get(str(value or "").strip().lower())
        if level is None:
            raise ValueError("WORKBOOK_EXPORT_MEMBER_LEVEL_INVALID") from None
    if not 5 <= level <= 10:
        raise ValueError("WORKBOOK_EXPORT_MEMBER_LEVEL_INVALID")
    return level


def _write_export_workbook(path: Path, snapshot: dict[str, Any]) -> None:
    preset = get_workbook_preset(DEFAULT_WORKBOOK_MAPPING_PRESET_ID)
    rows = {"setup": snapshot["setup"], "members": snapshot["members"], "projects": snapshot["projects"], "allocations": snapshot["allocations"], "capacity": snapshot["capacity"], "hiref_requests": snapshot["hiref_requests"]}
    workbook = Workbook()
    workbook.remove(workbook.active)
    for section in preset.sections:
        sheet = workbook.create_sheet(section.primary_sheet_name)
        sheet.append([field.header_name for field in section.fields])
        for row in rows[section.section_key]:
            sheet.append(row)
        sheet.freeze_panes = "A2"
    workbook.save(path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    current_state_result = _resolve_current_state_staffing_result(candidate, db_path=db_path)
    if current_state_result["status"] != "completed":
        return {
            **candidate,
            "status": "rejected",
            "workforce_result": workforce_result,
            "current_state_staffing_result": current_state_result,
            "capacity_result": None,
        }

    contract_coverage_result: dict[str, Any] | None = None
    if candidate.get("contract_coverage_package") is not None:
        contract_coverage_result = _resolve_contract_coverage_result(candidate, db_path=db_path)
        if contract_coverage_result["status"] != "completed":
            return {
                **candidate,
                "status": "partially_completed",
                "workforce_result": workforce_result,
                "current_state_staffing_result": current_state_result,
                "contract_coverage_result": contract_coverage_result,
                "capacity_result": None,
            }

    hiref_bridge_result: dict[str, Any] | None = None
    if candidate.get("hiref_bridge_payload") is not None:
        try:
            hiref_bridge_result = persist_hiref_bridge_payload(
                candidate["hiref_bridge_payload"],
                db_path=db_path,
            )
        except Exception as exc:
            hiref_bridge_result = {
                "status": "failed",
                "failure_code": str(exc),
            }
        if hiref_bridge_result["status"] != "completed":
            return {
                **candidate,
                "status": "partially_completed",
                "workforce_result": workforce_result,
                "current_state_staffing_result": current_state_result,
                "contract_coverage_result": contract_coverage_result,
                "hiref_bridge_result": hiref_bridge_result,
                "capacity_result": None,
            }

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
                "current_state_staffing_result": current_state_result,
                "contract_coverage_result": contract_coverage_result,
                "hiref_bridge_result": hiref_bridge_result,
                "capacity_result": capacity_result,
            }

    return {
        **candidate,
        "status": "completed",
        "workforce_result": workforce_result,
        "current_state_staffing_result": current_state_result,
        "contract_coverage_result": contract_coverage_result,
        "hiref_bridge_result": hiref_bridge_result,
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


def _resolve_current_state_staffing_result(
    candidate: dict[str, Any],
    *,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    current_state_preview = preview_current_state_staffing_import(
        candidate["current_state_staffing_package"],
        db_path=db_path,
    )
    status = current_state_preview["status"]
    if status in {"previewed", "retryable"}:
        return confirm_current_state_staffing_import(
            current_state_preview["session_id"],
            db_path=db_path,
        )
    if status == "already_completed":
        return {
            "status": "completed",
            "session_id": current_state_preview["session_id"],
            "idempotent": True,
            "report": current_state_preview["report"],
        }
    return current_state_preview


def _resolve_contract_coverage_result(
    candidate: dict[str, Any],
    *,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    contract_coverage_preview = preview_contract_coverage_import(
        candidate["contract_coverage_package"],
        db_path=db_path,
    )
    status = contract_coverage_preview["status"]
    if status in {"previewed", "retryable"}:
        return confirm_contract_coverage_import(
            contract_coverage_preview["session_id"],
            db_path=db_path,
        )
    if status == "already_completed":
        return {
            "status": "completed",
            "session_id": contract_coverage_preview["session_id"],
            "idempotent": True,
            "report": contract_coverage_preview["report"],
        }
    return contract_coverage_preview


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
    current_state_staffing_package = build_current_state_staffing_package(
        validation.workbook,
        version_name=resolved_plan["version_name"],
        as_of_date=as_of_date,
        revision=revision,
    )
    contract_coverage_package = build_contract_coverage_package(
        validation.workbook,
        version_name=resolved_plan["version_name"],
        as_of_date=as_of_date,
        revision=revision,
    )
    hiref_snapshot_present = any(
        section.section_key == "hiref_requests"
        and section.resolved_sheet_name is not None
        for section in parsed.preset_resolution.sections
    )
    hiref_bridge_payload = build_hiref_bridge_payload(
        validation.workbook,
        plan_version_id=resolved_plan["plan_version_id"],
        snapshot_present=hiref_snapshot_present,
    )
    try:
        validate_workforce_package(workforce_package)
        validate_current_state_staffing_package(current_state_staffing_package)
        validate_contract_coverage_package(contract_coverage_package)
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
        "workbook_export_metadata": {
            "plan_version_id": resolved_plan["plan_version_id"],
            "setup": {"start_month": validation.workbook.setup.start_month,
                      "end_month": validation.workbook.setup.end_month},
            "capacity": {
                "row_count": len(validation.workbook.capacity_rows),
                "package_id": capacity_package["package_id"] if capacity_package else None,
            },
        },
        "counts": {
            "members": len(validation.workbook.members),
            "projects": len(validation.workbook.projects),
            "allocation_rows": len(validation.workbook.allocations),
            "capacity_rows": len(validation.workbook.capacity_rows),
            "expanded_allocation_records": len(workforce_package["monthly_allocations"]),
            "current_state_assignment_records": len(
                current_state_staffing_package["assignments"]
            ),
            "contract_coverage_member_records": len(contract_coverage_package["members"]),
            "hiref_request_rows": len(validation.workbook.hiref_requests),
            "hiref_next_assignment_rows": sum(
                1 for member in validation.workbook.members if member.next_hiref_id
            ),
            "hiref_slot_rows": len(validation.workbook.hiref_requests),
            "hiref_open_demand_rows": len(
                validation.workbook.hiref_demand_allocations
            ),
            "hiref_placeholder_rows": len(
                {
                    allocation.hiref_id
                    for allocation in validation.workbook.hiref_demand_allocations
                }
            ),
            "hiref_placeholder_allocation_rows": len(
                validation.workbook.hiref_demand_allocations
            ),
        },
        "workforce_package": workforce_package,
        "current_state_staffing_package": current_state_staffing_package,
        "contract_coverage_package": contract_coverage_package,
        "hiref_bridge_payload": hiref_bridge_payload,
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
