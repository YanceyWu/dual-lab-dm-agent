"""Bounded JSON source handlers for retained domain importers."""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from pm_agent.data_onboarding import repository as onboarding_repository
from pm_agent.data_onboarding.models import (
    DomainLinkRecord,
    SourceProfileRecord,
    SourceProfileUpsert,
)
from pm_agent.database.execution import (
    confirm_milestone_import,
    preview_milestone_import,
)
from pm_agent.project_health.service import confirm_reimport, preview_reimport
from pm_agent.resource_intelligence.service import (
    confirm_import as confirm_capacity_import,
    preview_import as preview_capacity_import,
)
from pm_agent.workforce_planning_import.service import (
    confirm_import as confirm_workforce_import,
    preview_import as preview_workforce_import,
)

WORKFORCE_PLANNING_JSON_SOURCE_TYPE = "workforce-planning-json"
RESOURCE_CAPACITY_JSON_SOURCE_TYPE = "resource-capacity-json"
MILESTONE_JSON_SOURCE_TYPE = "milestone-json"
PROJECT_HEALTH_REIMPORT_JSON_SOURCE_TYPE = "project-health-reimport-json"


@dataclass(frozen=True)
class JsonDomainSourceDefinition:
    source_type: str
    display_name: str
    capability_key: str
    expected_schema_version: str
    preview_domain: Callable[..., dict[str, Any]]
    confirm_domain: Callable[..., dict[str, Any]]
    count_summary: Callable[[dict[str, Any]], dict[str, Any]]
    coverage_from_preview: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]
    planned_operation: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]
    plan_version: Callable[[dict[str, Any]], dict[str, Any] | None]
    domain_link: Callable[[dict[str, Any], dict[str, Any]], DomainLinkRecord]


_DEFAULT_WARNING_LIMIT = 1


def _require_blank(value: str, code: str) -> None:
    if value.strip():
        raise ValueError(code)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _local_file_identity(path: Path, source_type: str) -> dict[str, Any]:
    identity: dict[str, Any] = {
        "kind": "local_file",
        "source_type": source_type,
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


def _schema_version(payload: dict[str, Any]) -> str | None:
    value = payload.get("schema_version")
    return value.strip() if isinstance(value, str) and value.strip() else None


def _rejected_preview(
    definition: JsonDomainSourceDefinition,
    payload: dict[str, Any] | None,
    *,
    code: str,
    message: str,
    location: str,
    revision: int | None = None,
) -> dict[str, Any]:
    return {
        "status": "rejected",
        "revision": revision,
        "source_contract": _source_contract(definition, payload),
        "plan_version": definition.plan_version(payload or {}),
        "blockers": [
            {
                "severity": "blocker",
                "code": code,
                "message": message,
                "location": location,
            }
        ],
        "warnings": [],
        "conflicts": [],
        "counts": {},
        "domain_preview": {
            "capability": definition.capability_key,
            "status": "rejected",
        },
    }


def _source_contract(
    definition: JsonDomainSourceDefinition,
    payload: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "source_type": definition.source_type,
        "display_name": definition.display_name,
        "file_format": "json",
        "domain_capability": definition.capability_key,
        "expected_schema_version": definition.expected_schema_version,
        "resolved_schema_version": _schema_version(payload or {}),
    }


def _domain_preview_status(
    definition: JsonDomainSourceDefinition,
    result: dict[str, Any],
) -> str:
    status = str(result.get("status", "failed"))
    if definition.source_type == MILESTONE_JSON_SOURCE_TYPE:
        if status == "proposed":
            return "previewed"
        if status == "no_op":
            return "already_completed"
    if status in {"previewed", "already_completed", "retryable", "in_progress"}:
        return status
    if status == "rejected":
        return "rejected"
    return "failed"


def _domain_preview_identifiers(result: dict[str, Any]) -> dict[str, Any]:
    identifiers: dict[str, Any] = {
        "status": str(result.get("status", "")),
    }
    for key in ("session_id", "operation_id", "confirmation_token", "expires_at"):
        value = result.get(key)
        if value not in (None, ""):
            identifiers[key] = value
    return identifiers


def _domain_warning_code(result: dict[str, Any], fallback: str) -> str:
    for key in ("failure_code", "reason"):
        value = result.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return fallback


def _failed_source_result(
    definition: JsonDomainSourceDefinition,
    source_preview: dict[str, Any],
    *,
    failure_code: str,
    warning_message: str,
) -> dict[str, Any]:
    warnings = list(source_preview.get("warnings", []))
    warnings.append(
        {
            "severity": "warning",
            "code": failure_code,
            "message": warning_message,
            "location": "confirm",
        }
    )
    return {
        "status": "failed",
        "failure_code": failure_code,
        "source_contract": copy.deepcopy(source_preview.get("source_contract")),
        "plan_version": copy.deepcopy(source_preview.get("plan_version")),
        "blockers": list(source_preview.get("blockers", [])),
        "warnings": warnings,
        "conflicts": list(source_preview.get("conflicts", [])),
        "domain_preview": copy.deepcopy(source_preview.get("domain_preview")),
        "domain_payload": copy.deepcopy(source_preview.get("domain_payload", {})),
        "domain_result": {
            "status": "failed",
            "failure_code": failure_code,
        },
        "capability": definition.capability_key,
    }


def _successful_source_result(
    definition: JsonDomainSourceDefinition,
    source_preview: dict[str, Any],
    domain_result: dict[str, Any],
) -> dict[str, Any]:
    domain_status = str(domain_result.get("status", "failed"))
    if definition.source_type == MILESTONE_JSON_SOURCE_TYPE:
        final_status = "completed" if domain_status == "confirmed" else "rejected"
    elif domain_status == "completed":
        final_status = "completed"
    elif domain_status == "failed":
        final_status = "failed"
    elif domain_status == "rejected":
        final_status = "rejected"
    elif domain_status == "expired":
        final_status = "rejected"
    else:
        final_status = "failed"
    warnings = list(source_preview.get("warnings", []))
    blockers = list(source_preview.get("blockers", []))
    if final_status == "rejected":
        code = _domain_warning_code(
            domain_result,
            f"{definition.capability_key.upper()}_CONFIRM_REJECTED",
        )
        blockers.append(
            {
                "severity": "blocker",
                "code": code,
                "message": f"{definition.display_name} confirmation was rejected.",
                "location": "confirm",
            }
        )
    return {
        "status": final_status,
        "failure_code": (
            _domain_warning_code(domain_result, "DATA_ONBOARDING_DOMAIN_CONFIRMATION_FAILED")
            if final_status != "completed"
            else ""
        ),
        "source_contract": copy.deepcopy(source_preview.get("source_contract")),
        "plan_version": copy.deepcopy(source_preview.get("plan_version")),
        "blockers": blockers,
        "warnings": warnings,
        "conflicts": list(source_preview.get("conflicts", [])),
        "domain_preview": copy.deepcopy(source_preview.get("domain_preview")),
        "domain_payload": copy.deepcopy(source_preview.get("domain_payload", {})),
        "domain_result": copy.deepcopy(domain_result),
        "capability": definition.capability_key,
    }


def validate_profile(
    definition: JsonDomainSourceDefinition,
    profile: SourceProfileUpsert,
) -> SourceProfileUpsert:
    if profile.source_type != definition.source_type:
        raise ValueError("DATA_ONBOARDING_SOURCE_TYPE_UNSUPPORTED")
    source_locator = profile.source_locator.strip()
    if not source_locator:
        raise ValueError("DATA_ONBOARDING_SOURCE_LOCATOR_REQUIRED")
    normalized_path = str(Path(source_locator).expanduser().resolve(strict=False))
    if Path(normalized_path).suffix.lower() != ".json":
        raise ValueError("DATA_ONBOARDING_JSON_SOURCE_LOCATOR_INVALID")
    _require_blank(
        profile.mapping_preset_id,
        "DATA_ONBOARDING_JSON_MAPPING_PRESET_UNSUPPORTED",
    )
    _require_blank(
        profile.member_key_type,
        "DATA_ONBOARDING_JSON_MEMBER_KEY_TYPE_UNSUPPORTED",
    )
    _require_blank(
        profile.project_key_type,
        "DATA_ONBOARDING_JSON_PROJECT_KEY_TYPE_UNSUPPORTED",
    )
    _require_blank(
        profile.baseline_source,
        "DATA_ONBOARDING_JSON_BASELINE_SOURCE_UNSUPPORTED",
    )
    _require_blank(
        profile.adjustment_source,
        "DATA_ONBOARDING_JSON_ADJUSTMENT_SOURCE_UNSUPPORTED",
    )
    _require_blank(
        profile.conflict_policy,
        "DATA_ONBOARDING_JSON_CONFLICT_POLICY_UNSUPPORTED",
    )
    _require_blank(
        profile.plan_naming_policy,
        "DATA_ONBOARDING_JSON_PLAN_NAMING_POLICY_UNSUPPORTED",
    )
    return replace(
        profile,
        display_name=profile.display_name.strip() or definition.display_name,
        source_locator=normalized_path,
        source_options={
            "file_format": "json",
            "domain_capability": definition.capability_key,
            "expected_schema_version": definition.expected_schema_version,
        },
    )


def profile_metadata(
    definition: JsonDomainSourceDefinition,
    profile: SourceProfileRecord,
) -> dict[str, Any]:
    return {
        "source_options": copy.deepcopy(profile.source_options),
        "source_family": {
            "source_type": definition.source_type,
            "display_name": definition.display_name,
            "file_format": "json",
            "domain_capability": definition.capability_key,
            "expected_schema_version": definition.expected_schema_version,
        },
    }


def build_source_identity(
    definition: JsonDomainSourceDefinition,
    profile: SourceProfileRecord,
) -> dict[str, Any]:
    return _local_file_identity(Path(profile.source_locator), definition.source_type)


def preview(
    definition: JsonDomainSourceDefinition,
    profile: SourceProfileRecord,
    *,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    revision = onboarding_repository.next_profile_revision(
        profile_key=profile.profile_key,
        db_path=db_path,
    )
    path = Path(profile.source_locator)
    if not path.is_file():
        return _rejected_preview(
            definition,
            None,
            code="DATA_ONBOARDING_SOURCE_LOCATOR_NOT_FOUND",
            message=f"Source file not found: {path}",
            location="source_locator",
            revision=revision,
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return _rejected_preview(
            definition,
            None,
            code="DATA_ONBOARDING_SOURCE_JSON_INVALID",
            message=f"JSON source is invalid: {exc.msg}.",
            location="source_locator",
            revision=revision,
        )
    if not isinstance(payload, dict):
        return _rejected_preview(
            definition,
            None,
            code="DATA_ONBOARDING_SOURCE_JSON_OBJECT_REQUIRED",
            message="JSON source must contain one top-level object.",
            location="source_locator",
            revision=revision,
        )
    try:
        domain_preview = definition.preview_domain(payload, db_path=db_path)
    except ValueError as exc:
        return _rejected_preview(
            definition,
            payload,
            code=str(exc),
            message=f"{definition.display_name} preview rejected: {exc}",
            location="source",
            revision=revision,
        )
    status = _domain_preview_status(definition, domain_preview)
    warnings: list[dict[str, Any]] = []
    if status not in {"previewed", "already_completed", "retryable", "in_progress"}:
        status = "rejected"
    if status in {"retryable", "in_progress"}:
        warnings.append(
            {
                "severity": "warning",
                "code": _domain_warning_code(
                    domain_preview,
                    f"{definition.capability_key.upper()}_REQUIRES_ATTENTION",
                ),
                "message": (
                    f"{definition.display_name} preview returned "
                    f"{status.replace('_', ' ')}; confirm can retry the retained domain session."
                    if status == "retryable"
                    else f"{definition.display_name} preview is already running in the retained domain owner."
                ),
                "location": "source",
            }
        )
    if status == "already_completed":
        warnings.append(
            {
                "severity": "warning",
                "code": f"{definition.capability_key.upper()}_ALREADY_COMPLETED",
                "message": (
                    f"{definition.display_name} already completed in its domain owner; "
                    "confirm reuses that authoritative result without publishing a duplicate."
                ),
                "location": "source",
            }
        )
    return {
        "status": status,
        "revision": revision,
        "source_contract": _source_contract(definition, payload),
        "plan_version": definition.plan_version(payload),
        "blockers": [],
        "warnings": warnings[:_DEFAULT_WARNING_LIMIT],
        "conflicts": [],
        "counts": definition.count_summary(payload),
        "domain_preview": _domain_preview_identifiers(domain_preview),
        "domain_payload": copy.deepcopy(payload),
        "domain_report": copy.deepcopy(
            domain_preview.get("proposed", domain_preview.get("report", {}))
        ),
        "domain_coverage": copy.deepcopy(
            domain_preview.get("coverage", domain_preview.get("report", {}).get("coverage", {}))
        ),
    }


def confirm(
    definition: JsonDomainSourceDefinition,
    profile: SourceProfileRecord,
    source_preview: dict[str, Any],
    *,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    del profile
    preview_state = str(source_preview.get("status", "rejected"))
    domain_preview = source_preview.get("domain_preview", {})
    if not isinstance(domain_preview, dict):
        return _failed_source_result(
            definition,
            source_preview,
            failure_code="DATA_ONBOARDING_DOMAIN_PREVIEW_MISSING",
            warning_message="Onboarding preview is missing retained-domain replay identity.",
        )
    try:
        if definition.source_type == MILESTONE_JSON_SOURCE_TYPE:
            if preview_state == "already_completed":
                return _successful_source_result(
                    definition,
                    source_preview,
                    {
                        "status": "confirmed",
                        "operation_id": "",
                        "milestone_count": source_preview.get("counts", {}).get(
                            "milestones", 0
                        ),
                        "idempotent": True,
                        "changes": [],
                    },
                )
            operation_id = str(domain_preview.get("operation_id", ""))
            confirmation_token = str(domain_preview.get("confirmation_token", ""))
            domain_result = definition.confirm_domain(
                operation_id,
                confirmation_token,
                db_path=db_path,
            )
        else:
            session_id = str(domain_preview.get("session_id", ""))
            if not session_id:
                return _failed_source_result(
                    definition,
                    source_preview,
                    failure_code="DATA_ONBOARDING_DOMAIN_SESSION_ID_MISSING",
                    warning_message="Retained-domain session identity is missing.",
                )
            domain_result = definition.confirm_domain(session_id, db_path=db_path)
    except ValueError as exc:
        return _failed_source_result(
            definition,
            source_preview,
            failure_code=str(exc),
            warning_message=f"{definition.display_name} confirmation failed: {exc}",
        )
    except RuntimeError as exc:
        return _failed_source_result(
            definition,
            source_preview,
            failure_code=str(exc),
            warning_message=f"{definition.display_name} confirmation failed: {exc}",
        )
    return _successful_source_result(definition, source_preview, domain_result)


def release_run(
    definition: JsonDomainSourceDefinition,
    run_id: str,
    *,
    db_path: str | Path | None = None,
) -> None:
    del definition, run_id, db_path


def planned_operations(
    definition: JsonDomainSourceDefinition,
    source_preview: dict[str, Any],
) -> list[dict[str, Any]]:
    payload = source_preview.get("domain_payload")
    if not isinstance(payload, dict):
        return []
    operation = definition.planned_operation(payload, source_preview)
    operation["status"] = (
        "planned"
        if str(source_preview.get("status")) == "previewed"
        else str(source_preview.get("status"))
    )
    return [operation]


def coverage_summary(
    definition: JsonDomainSourceDefinition,
    source_preview: dict[str, Any],
) -> dict[str, Any]:
    payload = source_preview.get("domain_payload")
    if not isinstance(payload, dict):
        return {"state": "not_available"}
    return definition.coverage_from_preview(payload, source_preview)


def publication_links(
    definition: JsonDomainSourceDefinition,
    source_result: dict[str, Any],
) -> list[DomainLinkRecord]:
    return [definition.domain_link(source_result, source_result.get("domain_payload", {}))]


def _workforce_counts(payload: dict[str, Any]) -> dict[str, Any]:
    manifest = payload.get("manifest", {})
    allocations = payload.get("monthly_allocations", [])
    return {
        "members": len(payload.get("members", [])),
        "projects": len(payload.get("projects", [])),
        "plan_versions": len(payload.get("plan_versions", [])),
        "monthly_allocations": len(allocations),
        "workforce_periods": len(manifest.get("workforce_periods", [])),
        "allocation_keys": len(manifest.get("allocation_keys", [])),
        "explicit_zero_allocations": sum(
            isinstance(item, dict) and item.get("allocation") == 0
            for item in allocations
        ),
    }


def _workforce_coverage(payload: dict[str, Any], source_preview: dict[str, Any]) -> dict[str, Any]:
    coverage = source_preview.get("domain_coverage")
    if isinstance(coverage, dict) and coverage:
        return coverage
    counts = _workforce_counts(payload)
    return {
        "state": "complete",
        "authoritative_manifest": True,
        "member_count": counts["members"],
        "project_count": counts["projects"],
        "plan_version_count": counts["plan_versions"],
        "workforce_period_count": counts["workforce_periods"],
        "allocation_key_count": counts["allocation_keys"],
        "explicit_zero_count": counts["explicit_zero_allocations"],
        "missing_record_count": 0,
    }


def _workforce_operation(payload: dict[str, Any], _source_preview: dict[str, Any]) -> dict[str, Any]:
    counts = _workforce_counts(payload)
    plan_version_id = ""
    plan_versions = payload.get("plan_versions", [])
    if isinstance(plan_versions, list) and plan_versions:
        first = plan_versions[0]
        if isinstance(first, dict):
            plan_version_id = str(first.get("plan_version_id", ""))
    return {
        "capability": "workforce_planning_import",
        "package_id": str(payload.get("package_id", "")),
        "schema_version": str(payload.get("schema_version", "")),
        "plan_version_id": plan_version_id,
        "counts": counts,
    }


def _workforce_plan_version(payload: dict[str, Any]) -> dict[str, Any] | None:
    plan_versions = payload.get("plan_versions")
    if not isinstance(plan_versions, list) or not plan_versions:
        return None
    first = plan_versions[0]
    if not isinstance(first, dict):
        return None
    return {
        "plan_version_id": str(first.get("plan_version_id", "")),
        "version_name": str(first.get("version_name", "")),
    }


def _workforce_link(source_result: dict[str, Any], _payload: dict[str, Any]) -> DomainLinkRecord:
    domain_result = source_result.get("domain_result", {})
    report = domain_result.get("report", {}) if isinstance(domain_result, dict) else {}
    domain_preview = source_result.get("domain_preview", {})
    plan_version = source_result.get("plan_version", {})
    payload = source_result.get("domain_payload", {})
    return DomainLinkRecord(
        capability_key="workforce_planning_import",
        status=str(source_result.get("status", "")),
        domain_session_id=str(
            (domain_result or {}).get("session_id")
            or (domain_preview or {}).get("session_id")
            or ""
        ),
        domain_publication_id=str((report or {}).get("publication_id", "")),
        domain_plan_version_id=str((plan_version or {}).get("plan_version_id", "")),
        details={
            "package_id": str((payload or {}).get("package_id", "")),
            "failure_code": str(source_result.get("failure_code", "")),
            "report": copy.deepcopy(report) if isinstance(report, dict) else {},
        },
    )


def _capacity_counts(payload: dict[str, Any]) -> dict[str, Any]:
    manifest = payload.get("manifest", {})
    observations = payload.get("observations", [])
    return {
        "member_periods": len(manifest.get("member_periods", [])),
        "coverage_keys": len(manifest.get("coverage_keys", [])),
        "observations": len(observations),
        "explicit_zero_observations": sum(
            isinstance(item, dict) and item.get("fraction") == 0 for item in observations
        ),
    }


def _capacity_coverage(payload: dict[str, Any], source_preview: dict[str, Any]) -> dict[str, Any]:
    coverage = source_preview.get("domain_coverage")
    if isinstance(coverage, dict) and coverage:
        return coverage
    counts = _capacity_counts(payload)
    return {
        "state": "complete",
        "authoritative_manifest": True,
        "missing_record_count": 0,
        "explicit_zero_count": counts["explicit_zero_observations"],
    }


def _capacity_operation(payload: dict[str, Any], _source_preview: dict[str, Any]) -> dict[str, Any]:
    return {
        "capability": "resource_intelligence",
        "package_id": str(payload.get("package_id", "")),
        "schema_version": str(payload.get("schema_version", "")),
        "plan_version_id": str(payload.get("plan_version_id", "")),
        "counts": _capacity_counts(payload),
    }


def _capacity_plan_version(payload: dict[str, Any]) -> dict[str, Any] | None:
    plan_version_id = payload.get("plan_version_id")
    if not isinstance(plan_version_id, str) or not plan_version_id.strip():
        return None
    return {
        "plan_version_id": plan_version_id.strip(),
        "version_name": "",
    }


def _capacity_link(source_result: dict[str, Any], _payload: dict[str, Any]) -> DomainLinkRecord:
    domain_result = source_result.get("domain_result", {})
    report = domain_result.get("report", {}) if isinstance(domain_result, dict) else {}
    domain_preview = source_result.get("domain_preview", {})
    plan_version = source_result.get("plan_version", {})
    payload = source_result.get("domain_payload", {})
    return DomainLinkRecord(
        capability_key="resource_intelligence",
        status=str(source_result.get("status", "")),
        domain_session_id=str(
            (domain_result or {}).get("session_id")
            or (domain_preview or {}).get("session_id")
            or ""
        ),
        domain_publication_id=str((report or {}).get("publication_id", "")),
        domain_plan_version_id=str((plan_version or {}).get("plan_version_id", "")),
        details={
            "package_id": str((payload or {}).get("package_id", "")),
            "failure_code": str(source_result.get("failure_code", "")),
            "report": copy.deepcopy(report) if isinstance(report, dict) else {},
        },
    )


def _milestone_counts(payload: dict[str, Any]) -> dict[str, Any]:
    milestones = payload.get("milestones", [])
    project_ids = {
        item.get("project_id")
        for item in milestones
        if isinstance(item, dict) and isinstance(item.get("project_id"), str)
    }
    return {
        "milestones": len(milestones),
        "projects": len(project_ids),
    }


def _milestone_coverage(payload: dict[str, Any], source_preview: dict[str, Any]) -> dict[str, Any]:
    counts = _milestone_counts(payload)
    proposed = (
        source_preview.get("domain_report")
        if isinstance(source_preview.get("domain_report"), dict)
        else {}
    )
    change_count = len(proposed.get("changes", []))
    state = "already_applied" if str(source_preview.get("status")) == "already_completed" else "changes_detected"
    return {
        "state": state,
        "milestone_count": counts["milestones"],
        "project_count": counts["projects"],
        "changed_milestone_count": change_count,
    }


def _milestone_operation(payload: dict[str, Any], source_preview: dict[str, Any]) -> dict[str, Any]:
    proposed = source_preview.get("domain_report", {})
    return {
        "capability": "execution_milestones",
        "schema_version": _schema_version(payload) or "milestone-import-v1",
        "counts": _milestone_counts(payload),
        "changed_milestone_count": len(
            proposed.get("changes", []) if isinstance(proposed, dict) else []
        ),
    }


def _milestone_plan_version(_payload: dict[str, Any]) -> dict[str, Any] | None:
    return None


def _milestone_link(source_result: dict[str, Any], _payload: dict[str, Any]) -> DomainLinkRecord:
    domain_result = source_result.get("domain_result", {})
    domain_preview = source_result.get("domain_preview", {})
    payload = source_result.get("domain_payload", {})
    operation_id = str(
        (domain_result or {}).get("operation_id")
        or (domain_preview or {}).get("operation_id")
        or ""
    )
    return DomainLinkRecord(
        capability_key="execution_milestones",
        status=str(source_result.get("status", "")),
        domain_session_id=operation_id,
        domain_publication_id="",
        domain_plan_version_id="",
        details={
            "operation_id": operation_id or None,
            "milestone_count": _milestone_counts(payload)["milestones"],
            "failure_code": str(source_result.get("failure_code", "")),
            "report": copy.deepcopy(domain_result) if isinstance(domain_result, dict) else {},
        },
    )


def _health_counts(payload: dict[str, Any]) -> dict[str, Any]:
    board_ids = payload.get("board_ids", [])
    return {
        "boards": len(board_ids),
        "structured_inputs": len(payload.get("inputs", [])),
    }


def _health_coverage(payload: dict[str, Any], source_preview: dict[str, Any]) -> dict[str, Any]:
    report = source_preview.get("domain_report")
    if isinstance(report, dict) and report:
        return {
            "assessment_state": report.get("assessment_state"),
            "project_count": report.get("project_count"),
            "reason_codes": copy.deepcopy(report.get("reason_codes", [])),
        }
    counts = _health_counts(payload)
    return {
        "state": "planned",
        "board_count": counts["boards"],
    }


def _health_operation(payload: dict[str, Any], _source_preview: dict[str, Any]) -> dict[str, Any]:
    counts = _health_counts(payload)
    operation: dict[str, Any] = {
        "capability": "project_health",
        "package_id": str(payload.get("package_id", "")),
        "schema_version": str(payload.get("schema_version", "")),
        "counts": counts,
    }
    capacity_scope = payload.get("capacity_scope")
    if isinstance(capacity_scope, dict):
        operation["capacity_scope"] = copy.deepcopy(capacity_scope)
    return operation


def _health_plan_version(payload: dict[str, Any]) -> dict[str, Any] | None:
    capacity_scope = payload.get("capacity_scope")
    if not isinstance(capacity_scope, dict):
        return None
    plan_version_id = capacity_scope.get("plan_version_id")
    if not isinstance(plan_version_id, str) or not plan_version_id.strip():
        return None
    return {
        "plan_version_id": plan_version_id.strip(),
        "version_name": "",
    }


def _health_link(source_result: dict[str, Any], _payload: dict[str, Any]) -> DomainLinkRecord:
    domain_result = source_result.get("domain_result", {})
    report = domain_result.get("report", {}) if isinstance(domain_result, dict) else {}
    domain_preview = source_result.get("domain_preview", {})
    plan_version = source_result.get("plan_version", {})
    payload = source_result.get("domain_payload", {})
    return DomainLinkRecord(
        capability_key="project_health",
        status=str(source_result.get("status", "")),
        domain_session_id=str(
            (domain_result or {}).get("session_id")
            or (domain_preview or {}).get("session_id")
            or ""
        ),
        domain_publication_id="",
        domain_plan_version_id=str((plan_version or {}).get("plan_version_id", "")),
        details={
            "package_id": str((payload or {}).get("package_id", "")),
            "failure_code": str(source_result.get("failure_code", "")),
            "report": copy.deepcopy(report) if isinstance(report, dict) else {},
        },
    )


WORKFORCE_PLANNING_JSON_DEFINITION = JsonDomainSourceDefinition(
    source_type=WORKFORCE_PLANNING_JSON_SOURCE_TYPE,
    display_name="Workforce planning JSON",
    capability_key="workforce_planning_import",
    expected_schema_version="workforce-planning-import-v1",
    preview_domain=preview_workforce_import,
    confirm_domain=confirm_workforce_import,
    count_summary=_workforce_counts,
    coverage_from_preview=_workforce_coverage,
    planned_operation=_workforce_operation,
    plan_version=_workforce_plan_version,
    domain_link=_workforce_link,
)

RESOURCE_CAPACITY_JSON_DEFINITION = JsonDomainSourceDefinition(
    source_type=RESOURCE_CAPACITY_JSON_SOURCE_TYPE,
    display_name="Resource capacity JSON",
    capability_key="resource_intelligence",
    expected_schema_version="resource-capacity-import-v1",
    preview_domain=preview_capacity_import,
    confirm_domain=confirm_capacity_import,
    count_summary=_capacity_counts,
    coverage_from_preview=_capacity_coverage,
    planned_operation=_capacity_operation,
    plan_version=_capacity_plan_version,
    domain_link=_capacity_link,
)

MILESTONE_JSON_DEFINITION = JsonDomainSourceDefinition(
    source_type=MILESTONE_JSON_SOURCE_TYPE,
    display_name="Milestone JSON",
    capability_key="execution_milestones",
    expected_schema_version="milestone-import-v1",
    preview_domain=preview_milestone_import,
    confirm_domain=confirm_milestone_import,
    count_summary=_milestone_counts,
    coverage_from_preview=_milestone_coverage,
    planned_operation=_milestone_operation,
    plan_version=_milestone_plan_version,
    domain_link=_milestone_link,
)

PROJECT_HEALTH_REIMPORT_JSON_DEFINITION = JsonDomainSourceDefinition(
    source_type=PROJECT_HEALTH_REIMPORT_JSON_SOURCE_TYPE,
    display_name="Project Health re-import JSON",
    capability_key="project_health",
    expected_schema_version="project-health-reimport-v1",
    preview_domain=preview_reimport,
    confirm_domain=confirm_reimport,
    count_summary=_health_counts,
    coverage_from_preview=_health_coverage,
    planned_operation=_health_operation,
    plan_version=_health_plan_version,
    domain_link=_health_link,
)
