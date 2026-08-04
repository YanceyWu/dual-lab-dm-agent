"""Workbook source registration for the structured onboarding framework."""

from __future__ import annotations

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
    WORKBOOK_DEFAULT_SOURCE_OPTIONS,
    WORKBOOK_MAPPING_PRESET_ID,
    WORKBOOK_MEMBER_KEY_TYPE,
    WORKBOOK_PLAN_NAMING_POLICY,
    WORKBOOK_PROJECT_KEY_TYPE,
    WORKBOOK_SOURCE_TYPE,
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
    if mapping_preset_id != WORKBOOK_MAPPING_PRESET_ID:
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
        source_options=dict(WORKBOOK_DEFAULT_SOURCE_OPTIONS),
    )


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
    path = Path(profile.source_locator)
    if not path.is_file():
        return {
            "status": "rejected",
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
            "capacity": {"state": "not_available"},
        }
    workforce_period_count = len(workforce_package["manifest"]["workforce_periods"])
    capacity_package = source_preview.get("capacity_package")
    if not isinstance(capacity_package, dict):
        return {
            "workforce": {
                "state": "complete",
                "authoritative_manifest": True,
                "member_period_count": workforce_period_count,
                "missing_record_count": 0,
            },
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
