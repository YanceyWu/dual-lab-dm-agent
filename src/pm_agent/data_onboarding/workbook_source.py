"""Workbook source registration for the structured onboarding framework."""

from __future__ import annotations

import copy
import hashlib
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pm_agent.data_onboarding.models import DomainLinkRecord, SourceProfileRecord, SourceProfileUpsert
from pm_agent.data_onboarding.workbook_contract import (
    WORKBOOK_ADJUSTMENT_SOURCE,
    WORKBOOK_BASELINE_SOURCE,
    WORKBOOK_CONFLICT_POLICY,
    WORKBOOK_DEFAULT_DISPLAY_NAME,
    WORKBOOK_MAPPING_PRESET_ID,
    WORKBOOK_MEMBER_KEY_TYPE,
    WORKBOOK_PLAN_NAMING_POLICY,
    WORKBOOK_PROJECT_KEY_TYPE,
    WORKBOOK_SOURCE_TYPE,
)
from pm_agent.workbook_onboarding.presets import (
    default_source_options,
    get_workbook_preset,
    serialize_workbook_preset_lookup,
    serialize_workbook_preset_summary,
)
from pm_agent.workbook_onboarding.repository import release_plan_identity
from pm_agent.workbook_onboarding.service import (
    confirm_workbook_candidate,
    preview_workbook_import,
)


def validate_profile(profile: SourceProfileUpsert) -> SourceProfileUpsert:
    if profile.source_type != WORKBOOK_SOURCE_TYPE:
        raise ValueError("DATA_ONBOARDING_SOURCE_TYPE_UNSUPPORTED")
    source_locator = profile.source_locator.strip()
    if not source_locator:
        raise ValueError("DATA_ONBOARDING_SOURCE_LOCATOR_REQUIRED")
    normalized_path = str(Path(source_locator).expanduser().resolve(strict=False))
    if Path(normalized_path).suffix.lower() != ".xlsx":
        raise ValueError("DATA_ONBOARDING_WORKBOOK_SOURCE_LOCATOR_INVALID")
    mapping_preset_id = profile.mapping_preset_id.strip() or WORKBOOK_MAPPING_PRESET_ID
    try:
        get_workbook_preset(mapping_preset_id)
    except ValueError as exc:
        if str(exc) == "WORKBOOK_MAPPING_PRESET_UNKNOWN":
            raise ValueError("DATA_ONBOARDING_WORKBOOK_MAPPING_PRESET_INVALID") from exc
        raise ValueError("DATA_ONBOARDING_WORKBOOK_MAPPING_PRESET_INVALID")
    member_key_type = profile.member_key_type.strip() or WORKBOOK_MEMBER_KEY_TYPE
    if member_key_type != WORKBOOK_MEMBER_KEY_TYPE:
        raise ValueError("DATA_ONBOARDING_WORKBOOK_MEMBER_KEY_TYPE_INVALID")
    project_key_type = profile.project_key_type.strip() or WORKBOOK_PROJECT_KEY_TYPE
    if project_key_type != WORKBOOK_PROJECT_KEY_TYPE:
        raise ValueError("DATA_ONBOARDING_WORKBOOK_PROJECT_KEY_TYPE_INVALID")
    baseline_source = profile.baseline_source.strip() or WORKBOOK_BASELINE_SOURCE
    if baseline_source != WORKBOOK_BASELINE_SOURCE:
        raise ValueError("DATA_ONBOARDING_WORKBOOK_BASELINE_SOURCE_INVALID")
    adjustment_source = profile.adjustment_source.strip() or WORKBOOK_ADJUSTMENT_SOURCE
    if adjustment_source != WORKBOOK_ADJUSTMENT_SOURCE:
        raise ValueError("DATA_ONBOARDING_WORKBOOK_ADJUSTMENT_SOURCE_INVALID")
    conflict_policy = profile.conflict_policy.strip() or WORKBOOK_CONFLICT_POLICY
    if conflict_policy != WORKBOOK_CONFLICT_POLICY:
        raise ValueError("DATA_ONBOARDING_WORKBOOK_CONFLICT_POLICY_INVALID")
    plan_naming_policy = profile.plan_naming_policy.strip() or WORKBOOK_PLAN_NAMING_POLICY
    if plan_naming_policy != WORKBOOK_PLAN_NAMING_POLICY:
        raise ValueError("DATA_ONBOARDING_WORKBOOK_PLAN_NAMING_POLICY_INVALID")
    display_name = profile.display_name.strip() or WORKBOOK_DEFAULT_DISPLAY_NAME
    return replace(
        profile,
        display_name=display_name,
        source_locator=normalized_path,
        mapping_preset_id=mapping_preset_id,
        member_key_type=member_key_type,
        project_key_type=project_key_type,
        baseline_source=baseline_source,
        adjustment_source=adjustment_source,
        conflict_policy=conflict_policy,
        plan_naming_policy=plan_naming_policy,
        source_options=default_source_options(mapping_preset_id),
    )


def profile_metadata(profile: SourceProfileRecord) -> dict[str, Any]:
    mapping_preset_id = profile.mapping_preset_id or WORKBOOK_MAPPING_PRESET_ID
    try:
        preset = get_workbook_preset(mapping_preset_id)
    except ValueError as exc:
        if str(exc) != "WORKBOOK_MAPPING_PRESET_UNKNOWN":
            raise
        return {
            "mapping_preset": serialize_workbook_preset_lookup(mapping_preset_id),
            "source_options": copy.deepcopy(profile.source_options),
        }
    return {
        "mapping_preset": serialize_workbook_preset_summary(preset),
        "source_options": default_source_options(mapping_preset_id),
    }


def build_source_identity(profile: SourceProfileRecord) -> dict[str, Any]:
    path = Path(profile.source_locator)
    identity: dict[str, Any] = {
        "kind": "local_file",
        "source_type": WORKBOOK_SOURCE_TYPE,
        "locator": str(path),
        "exists": path.is_file(),
    }
    if path.is_file():
        stat = path.stat()
        identity.update(
            {
                "size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(
                    stat.st_mtime, tz=timezone.utc
                ).isoformat(timespec="seconds"),
                "sha256": _sha256(path),
            }
        )
    return identity


def preview(
    profile: SourceProfileRecord,
    *,
    run_id: str,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    mapping_preset_id = profile.mapping_preset_id.strip() or WORKBOOK_MAPPING_PRESET_ID
    try:
        preset = get_workbook_preset(mapping_preset_id)
    except ValueError as exc:
        if str(exc) != "WORKBOOK_MAPPING_PRESET_UNKNOWN":
            raise
        return {
            "status": "rejected",
            "source_contract": {
                "mapping_preset": serialize_workbook_preset_lookup(mapping_preset_id),
                "resolution": None,
            },
            "blockers": [
                {
                    "severity": "blocker",
                    "code": "WORKBOOK_MAPPING_PRESET_UNKNOWN",
                    "message": f"Unknown workbook mapping preset: {mapping_preset_id}.",
                    "location": "mapping_preset_id",
                }
            ],
            "warnings": [],
            "conflicts": [],
        }
    source_contract = {
        "mapping_preset": serialize_workbook_preset_summary(preset),
        "resolution": None,
    }
    path = Path(profile.source_locator)
    if not path.is_file():
        return {
            "status": "rejected",
            "source_contract": source_contract,
            "blockers": [
                {
                    "severity": "blocker",
                    "code": "DATA_ONBOARDING_SOURCE_LOCATOR_NOT_FOUND",
                    "message": f"Workbook source file not found: {path}",
                    "location": "source_locator",
                }
            ],
            "warnings": [],
            "conflicts": [],
        }
    return preview_workbook_import(
        path,
        mapping_preset_id=mapping_preset_id,
        profile_key=profile.profile_key,
        run_id=run_id,
        db_path=db_path,
    )


def confirm(
    profile: SourceProfileRecord,
    source_preview: dict[str, Any],
    *,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    del profile
    return confirm_workbook_candidate(source_preview, db_path=db_path)


def release_run(
    run_id: str,
    *,
    db_path: str | Path | None = None,
) -> None:
    release_plan_identity(run_id=run_id, db_path=db_path)


def planned_operations(source_preview: dict[str, Any]) -> list[dict[str, Any]]:
    workforce_package = source_preview.get("workforce_package")
    if not isinstance(workforce_package, dict):
        return []
    manifest = workforce_package["manifest"]
    operations = [
        {
            "capability": "workforce_planning_import",
            "status": "planned",
            "package_id": workforce_package["package_id"],
            "schema_version": workforce_package["schema_version"],
            "plan_version_id": workforce_package["plan_versions"][0]["plan_version_id"],
            "counts": {
                "members": len(workforce_package["members"]),
                "projects": len(workforce_package["projects"]),
                "plan_versions": len(workforce_package["plan_versions"]),
                "monthly_allocations": len(workforce_package["monthly_allocations"]),
                "workforce_periods": len(manifest["workforce_periods"]),
                "allocation_keys": len(manifest["allocation_keys"]),
            },
        }
    ]
    current_state_package = source_preview.get("current_state_staffing_package")
    if isinstance(current_state_package, dict):
        scope = current_state_package["publication_scope"]
        assigned_members = {
            item["member_id"] for item in current_state_package["assignments"]
        }
        operations.append(
            {
                "capability": "current_state_staffing",
                "status": "planned",
                "package_id": current_state_package["package_id"],
                "schema_version": current_state_package["schema_version"],
                "counts": {
                    "members": len(current_state_package["members"]),
                    "projects": len(current_state_package["projects"]),
                    "assignments": len(current_state_package["assignments"]),
                    "assigned_members": len(assigned_members),
                    "unassigned_members": len(current_state_package["members"])
                    - len(assigned_members),
                },
                "publication_scope": {
                    "scope_key": scope["scope_key"],
                    "as_of_date": scope["as_of_date"],
                    "effective_year": scope["effective_year"],
                    "effective_month": scope["effective_month"],
                },
            }
        )
    capacity_package = source_preview.get("capacity_package")
    if isinstance(capacity_package, dict):
        operations.append(
            {
                "capability": "resource_intelligence",
                "status": "planned",
                "depends_on": "workforce_planning_import",
                "package_id": capacity_package["package_id"],
                "schema_version": capacity_package["schema_version"],
                "plan_version_id": capacity_package["plan_version_id"],
                "counts": {
                    "member_periods": len(capacity_package["manifest"]["member_periods"]),
                    "coverage_keys": len(capacity_package["manifest"]["coverage_keys"]),
                    "observations": len(capacity_package["observations"]),
                    "explicit_zero_observations": sum(
                        item["fraction"] == 0 for item in capacity_package["observations"]
                    ),
                },
            }
        )
    return operations


def coverage_summary(source_preview: dict[str, Any]) -> dict[str, Any]:
    workforce_package = source_preview.get("workforce_package")
    if not isinstance(workforce_package, dict):
        return {
            "workforce": {"state": "not_available"},
            "current_state_staffing": {"state": "not_available"},
            "capacity": {"state": "not_available"},
        }
    workforce_period_count = len(workforce_package["manifest"]["workforce_periods"])
    current_state_package = source_preview.get("current_state_staffing_package")
    current_state_coverage = {"state": "not_available"}
    if isinstance(current_state_package, dict):
        scope = current_state_package["publication_scope"]
        assigned_members = {
            item["member_id"] for item in current_state_package["assignments"]
        }
        current_state_coverage = {
            "state": "complete",
            "member_count": len(current_state_package["members"]),
            "project_count": len(current_state_package["projects"]),
            "assignment_count": len(current_state_package["assignments"]),
            "assigned_member_count": len(assigned_members),
            "unassigned_member_count": len(current_state_package["members"])
            - len(assigned_members),
            "effective_period": {
                "year": scope["effective_year"],
                "month": scope["effective_month"],
                "as_of_date": scope["as_of_date"],
            },
        }
    capacity_package = source_preview.get("capacity_package")
    if not isinstance(capacity_package, dict):
        return {
            "workforce": {
                "state": "complete",
                "authoritative_manifest": True,
                "member_period_count": workforce_period_count,
                "missing_record_count": 0,
            },
            "current_state_staffing": current_state_coverage,
            "capacity": {
                "state": "not_provided",
                "known_member_period_count": 0,
                "unknown_member_period_count": workforce_period_count,
                "explicit_zero_observation_count": 0,
            },
        }
    known_member_period_count = len(capacity_package["manifest"]["member_periods"])
    unknown_member_period_count = max(workforce_period_count - known_member_period_count, 0)
    return {
        "workforce": {
            "state": "complete",
            "authoritative_manifest": True,
            "member_period_count": workforce_period_count,
            "missing_record_count": 0,
        },
        "capacity": {
            "state": "complete" if unknown_member_period_count == 0 else "partial",
            "known_member_period_count": known_member_period_count,
            "unknown_member_period_count": unknown_member_period_count,
            "explicit_zero_observation_count": sum(
                item["fraction"] == 0 for item in capacity_package["observations"]
            ),
        },
        "current_state_staffing": current_state_coverage,
    }


def publication_links(source_result: dict[str, Any]) -> list[DomainLinkRecord]:
    links: list[DomainLinkRecord] = []
    workforce_result = source_result.get("workforce_result")
    if isinstance(workforce_result, dict):
        links.append(
            DomainLinkRecord(
                capability_key="workforce_planning_import",
                status=str(workforce_result.get("status", "")),
                domain_session_id=str(workforce_result.get("session_id", "")),
                domain_publication_id=str(
                    workforce_result.get("report", {}).get("publication_id", "")
                ),
                domain_plan_version_id=str(
                    source_result.get("plan_version", {}).get("plan_version_id", "")
                ),
                details={
                    "package_id": source_result.get("workforce_package", {}).get("package_id", ""),
                    "failure_code": workforce_result.get("failure_code", ""),
                    "report": workforce_result.get("report", {}),
                },
            )
        )
    current_state_result = source_result.get("current_state_staffing_result")
    if isinstance(current_state_result, dict):
        links.append(
            DomainLinkRecord(
                capability_key="current_state_staffing",
                status=str(current_state_result.get("status", "")),
                domain_session_id=str(current_state_result.get("session_id", "")),
                domain_publication_id=str(
                    current_state_result.get("report", {}).get("publication_id", "")
                ),
                domain_plan_version_id="",
                details={
                    "package_id": source_result.get("current_state_staffing_package", {}).get(
                        "package_id", ""
                    ),
                    "failure_code": current_state_result.get("failure_code", ""),
                    "report": current_state_result.get("report", {}),
                },
            )
        )
    capacity_result = source_result.get("capacity_result")
    if isinstance(capacity_result, dict):
        links.append(
            DomainLinkRecord(
                capability_key="resource_intelligence",
                status=str(capacity_result.get("status", "")),
                domain_session_id=str(capacity_result.get("session_id", "")),
                domain_publication_id=str(
                    capacity_result.get("report", {}).get("publication_id", "")
                ),
                domain_plan_version_id=str(
                    source_result.get("plan_version", {}).get("plan_version_id", "")
                ),
                details={
                    "package_id": source_result.get("capacity_package", {}).get("package_id", ""),
                    "failure_code": capacity_result.get("failure_code", ""),
                    "report": capacity_result.get("report", {}),
                },
            )
        )
    return links


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()
