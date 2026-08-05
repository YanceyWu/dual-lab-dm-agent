"""Thin onboarding wrappers for retained project-profile and change-request files."""

from __future__ import annotations

import copy
import hashlib
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
from pm_agent.project_profile_import import (
    EXPECTED_HEADERS as PROJECT_PROFILE_EXPECTED_HEADERS,
)
from pm_agent.project_profile_import import (
    WORKSHEET_NAME as PROJECT_PROFILE_WORKSHEET_NAME,
)
from pm_agent.project_profile_import import (
    apply_project_profile_import,
    preview_project_profile_import,
)
from pm_agent.sync.servicenow.cr_import import apply_cr_import, preview_cr_import

PROJECT_PROFILE_WORKBOOK_SOURCE_TYPE = "project-profile-workbook"
SERVICENOW_CHANGE_REQUEST_CSV_SOURCE_TYPE = "servicenow-change-request-csv"


@dataclass(frozen=True)
class AuxiliaryFileSourceDefinition:
    source_type: str
    display_name: str
    capability_key: str
    file_format: str
    suffix: str
    source_options: dict[str, Any]
    preview_domain: Callable[..., dict[str, Any]]
    confirm_domain: Callable[..., dict[str, Any]]


PROJECT_PROFILE_WORKBOOK_DEFINITION = AuxiliaryFileSourceDefinition(
    source_type=PROJECT_PROFILE_WORKBOOK_SOURCE_TYPE,
    display_name="Project profile workbook",
    capability_key="project_profile_import",
    file_format="xlsx",
    suffix=".xlsx",
    source_options={
        "worksheet": PROJECT_PROFILE_WORKSHEET_NAME,
        "header_row": 4,
        "expected_headers": list(PROJECT_PROFILE_EXPECTED_HEADERS),
    },
    preview_domain=preview_project_profile_import,
    confirm_domain=apply_project_profile_import,
)

SERVICENOW_CHANGE_REQUEST_CSV_DEFINITION = AuxiliaryFileSourceDefinition(
    source_type=SERVICENOW_CHANGE_REQUEST_CSV_SOURCE_TYPE,
    display_name="ServiceNow change-request CSV",
    capability_key="change_request_import",
    file_format="csv",
    suffix=".csv",
    source_options={
        "source_system": "servicenow",
        "reconciliation_mode": "upsert_only",
        "audit_source_id": "servicenow-change-requests",
    },
    preview_domain=preview_cr_import,
    confirm_domain=apply_cr_import,
)


def validate_profile(
    definition: AuxiliaryFileSourceDefinition,
    profile: SourceProfileUpsert,
) -> SourceProfileUpsert:
    if profile.source_type != definition.source_type:
        raise ValueError("DATA_ONBOARDING_SOURCE_TYPE_UNSUPPORTED")
    source_locator = profile.source_locator.strip()
    if not source_locator:
        raise ValueError("DATA_ONBOARDING_SOURCE_LOCATOR_REQUIRED")
    normalized_path = str(Path(source_locator).expanduser().resolve(strict=False))
    if Path(normalized_path).suffix.lower() != definition.suffix:
        if definition.file_format == "xlsx":
            raise ValueError("DATA_ONBOARDING_PROJECT_PROFILE_SOURCE_LOCATOR_INVALID")
        raise ValueError("DATA_ONBOARDING_CHANGE_REQUEST_SOURCE_LOCATOR_INVALID")
    _require_blank(
        profile.mapping_preset_id,
        f"{definition.capability_key.upper()}_MAPPING_PRESET_UNSUPPORTED",
    )
    _require_blank(
        profile.member_key_type,
        f"{definition.capability_key.upper()}_MEMBER_KEY_TYPE_UNSUPPORTED",
    )
    _require_blank(
        profile.project_key_type,
        f"{definition.capability_key.upper()}_PROJECT_KEY_TYPE_UNSUPPORTED",
    )
    _require_blank(
        profile.baseline_source,
        f"{definition.capability_key.upper()}_BASELINE_SOURCE_UNSUPPORTED",
    )
    _require_blank(
        profile.adjustment_source,
        f"{definition.capability_key.upper()}_ADJUSTMENT_SOURCE_UNSUPPORTED",
    )
    _require_blank(
        profile.conflict_policy,
        f"{definition.capability_key.upper()}_CONFLICT_POLICY_UNSUPPORTED",
    )
    _require_blank(
        profile.plan_naming_policy,
        f"{definition.capability_key.upper()}_PLAN_NAMING_POLICY_UNSUPPORTED",
    )
    return replace(
        profile,
        display_name=profile.display_name.strip() or definition.display_name,
        source_locator=normalized_path,
        source_options={
            "file_format": definition.file_format,
            "domain_capability": definition.capability_key,
            **copy.deepcopy(definition.source_options),
        },
    )


def profile_metadata(
    definition: AuxiliaryFileSourceDefinition,
    profile: SourceProfileRecord,
) -> dict[str, Any]:
    return {
        "source_options": copy.deepcopy(profile.source_options),
        "source_family": {
            "source_type": definition.source_type,
            "display_name": definition.display_name,
            "file_format": definition.file_format,
            "domain_capability": definition.capability_key,
            **copy.deepcopy(definition.source_options),
        },
    }


def build_source_identity(
    definition: AuxiliaryFileSourceDefinition,
    profile: SourceProfileRecord,
) -> dict[str, Any]:
    path = Path(profile.source_locator)
    identity: dict[str, Any] = {
        "kind": "local_file",
        "source_type": definition.source_type,
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
    definition: AuxiliaryFileSourceDefinition,
    profile: SourceProfileRecord,
    *,
    run_id: str,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    del run_id
    revision = onboarding_repository.next_profile_revision(
        profile_key=profile.profile_key,
        db_path=db_path,
    )
    path = Path(profile.source_locator)
    if not path.is_file():
        return _rejected_preview(
            definition,
            revision=revision,
            code="DATA_ONBOARDING_SOURCE_LOCATOR_NOT_FOUND",
            message=f"Source file not found: {path}",
            location="source_locator",
        )
    domain_preview = definition.preview_domain(path, db_path=db_path)
    status = str(domain_preview.get("status", "rejected"))
    if status not in {"previewed", "already_completed", "rejected"}:
        status = "rejected"
    warnings = list(domain_preview.get("warnings", []))
    if status == "already_completed":
        warnings.append(
            {
                "severity": "warning",
                "code": f"{definition.capability_key.upper()}_ALREADY_COMPLETED",
                "message": (
                    f"{definition.display_name} already matches the retained local state; "
                    "confirm records an idempotent completion without replaying writes."
                ),
                "location": "source",
            }
        )
    return {
        "status": status,
        "revision": revision,
        "source_contract": _source_contract(definition),
        "plan_version": None,
        "blockers": list(domain_preview.get("blockers", [])),
        "warnings": warnings,
        "conflicts": list(domain_preview.get("conflicts", [])),
        "counts": dict(domain_preview.get("counts", {})),
        "domain_payload": copy.deepcopy(domain_preview.get("payload", {})),
        "domain_report": copy.deepcopy(domain_preview.get("report", {})),
    }


def confirm(
    definition: AuxiliaryFileSourceDefinition,
    profile: SourceProfileRecord,
    source_preview: dict[str, Any],
    *,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    preview_state = str(source_preview.get("status", "rejected"))
    if preview_state == "already_completed":
        return _successful_source_result(
            definition,
            source_preview,
            {
                "status": "completed",
                "idempotent": True,
                "payload": copy.deepcopy(source_preview.get("domain_payload", {})),
                "report": copy.deepcopy(source_preview.get("domain_report", {})),
            },
        )
    domain_result = definition.confirm_domain(
        Path(profile.source_locator),
        db_path=db_path,
    )
    return _successful_source_result(definition, source_preview, domain_result)


def release_run(
    definition: AuxiliaryFileSourceDefinition,
    run_id: str,
    *,
    db_path: str | Path | None = None,
) -> None:
    del definition, run_id, db_path


def planned_operations(
    definition: AuxiliaryFileSourceDefinition,
    source_preview: dict[str, Any],
) -> list[dict[str, Any]]:
    operation = {
        "capability": definition.capability_key,
        "counts": dict(source_preview.get("counts", {})),
        "publication_id": (
            source_preview.get("domain_payload", {}).get("publication_id") or None
        ),
    }
    operation["status"] = (
        "planned"
        if str(source_preview.get("status")) == "previewed"
        else str(source_preview.get("status"))
    )
    return [operation]


def coverage_summary(
    definition: AuxiliaryFileSourceDefinition,
    source_preview: dict[str, Any],
) -> dict[str, Any]:
    del definition
    report = source_preview.get("domain_report", {})
    if not isinstance(report, dict):
        return {"state": "not_available"}
    coverage = report.get("coverage", {})
    if not isinstance(coverage, dict):
        return {"state": "not_available"}
    return copy.deepcopy(coverage)


def publication_links(
    definition: AuxiliaryFileSourceDefinition,
    source_result: dict[str, Any],
) -> list[DomainLinkRecord]:
    payload = source_result.get("domain_result", {}).get("payload", {})
    if not isinstance(payload, dict):
        payload = {}
    preview_payload = source_result.get("domain_payload", {})
    if not isinstance(preview_payload, dict):
        preview_payload = {}
    publication_id = str(
        preview_payload.get("publication_id") or payload.get("publication_id") or ""
    )
    sync_run_id = str(payload.get("sync_run_id") or "")
    return [
        DomainLinkRecord(
            capability_key=definition.capability_key,
            status=str(source_result.get("status", "failed")),
            domain_session_id=sync_run_id,
            domain_publication_id=publication_id,
            domain_plan_version_id="",
            details={
                "report": copy.deepcopy(source_result.get("domain_report", {})),
                "counts": dict(source_result.get("counts", {})),
                "source_contract": copy.deepcopy(source_result.get("source_contract")),
                "replay": {
                    "idempotent": bool(
                        source_result.get("domain_result", {}).get("idempotent", False)
                    )
                },
            },
        )
    ]


def _require_blank(value: str, code: str) -> None:
    if value.strip():
        raise ValueError(code)


def _rejected_preview(
    definition: AuxiliaryFileSourceDefinition,
    *,
    revision: int,
    code: str,
    message: str,
    location: str,
) -> dict[str, Any]:
    return {
        "status": "rejected",
        "revision": revision,
        "source_contract": _source_contract(definition),
        "plan_version": None,
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
        "domain_payload": {},
        "domain_report": {"coverage": {"state": "not_available"}},
    }


def _source_contract(definition: AuxiliaryFileSourceDefinition) -> dict[str, Any]:
    return {
        "source_type": definition.source_type,
        "display_name": definition.display_name,
        "file_format": definition.file_format,
        "domain_capability": definition.capability_key,
        **copy.deepcopy(definition.source_options),
    }


def _successful_source_result(
    definition: AuxiliaryFileSourceDefinition,
    source_preview: dict[str, Any],
    domain_result: dict[str, Any],
) -> dict[str, Any]:
    domain_status = str(domain_result.get("status", "failed"))
    final_status = "completed" if domain_status == "completed" else domain_status
    warnings = list(source_preview.get("warnings", []))
    blockers = list(source_preview.get("blockers", []))
    if final_status == "rejected":
        blockers.append(
            {
                "severity": "blocker",
                "code": f"{definition.capability_key.upper()}_CONFIRM_REJECTED",
                "message": f"{definition.display_name} confirmation was rejected.",
                "location": "confirm",
            }
        )
    return {
        "status": final_status,
        "failure_code": "" if final_status == "completed" else definition.capability_key.upper(),
        "source_contract": copy.deepcopy(source_preview.get("source_contract")),
        "plan_version": None,
        "blockers": blockers,
        "warnings": warnings,
        "conflicts": list(source_preview.get("conflicts", [])),
        "counts": dict(source_preview.get("counts", {})),
        "domain_payload": copy.deepcopy(source_preview.get("domain_payload", {})),
        "domain_report": copy.deepcopy(
            domain_result.get("report", source_preview.get("domain_report", {}))
        ),
        "domain_result": copy.deepcopy(domain_result),
        "capability": definition.capability_key,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()
