"""Thin onboarding wrappers for retained registry CSV import sources."""

from __future__ import annotations

import copy
import hashlib
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from pm_agent.connectors.confluence.page_registry import (
    OPTIONAL_COLUMNS as CONFLUENCE_PAGE_OPTIONAL_COLUMNS,
)
from pm_agent.connectors.confluence.page_registry import (
    REQUIRED_COLUMNS as CONFLUENCE_PAGE_REQUIRED_COLUMNS,
)
from pm_agent.connectors.confluence.page_registry import (
    apply_registry_import as apply_confluence_page_registry_import,
)
from pm_agent.connectors.confluence.page_registry import (
    preview_registry_import as preview_confluence_page_registry_import,
)
from pm_agent.connectors.jira.board_registry import (
    OPTIONAL_COLUMNS as JIRA_BOARD_OPTIONAL_COLUMNS,
)
from pm_agent.connectors.jira.board_registry import (
    REQUIRED_COLUMNS as JIRA_BOARD_REQUIRED_COLUMNS,
)
from pm_agent.connectors.jira.board_registry import (
    apply_registry_import as apply_jira_board_registry_import,
)
from pm_agent.connectors.jira.board_registry import (
    preview_registry_import as preview_jira_board_registry_import,
)
from pm_agent.data_onboarding import repository as onboarding_repository
from pm_agent.data_onboarding.models import (
    DomainLinkRecord,
    SourceProfileRecord,
    SourceProfileUpsert,
)

JIRA_BOARD_REGISTRY_SOURCE_TYPE = "jira-board-registry-csv"
CONFLUENCE_PAGE_REGISTRY_SOURCE_TYPE = "confluence-page-registry-csv"


@dataclass(frozen=True)
class CsvRegistrySourceDefinition:
    source_type: str
    display_name: str
    capability_key: str
    required_columns: tuple[str, ...]
    optional_columns: tuple[str, ...]
    preview_domain: Callable[..., dict[str, Any]]
    confirm_domain: Callable[..., dict[str, Any]]


JIRA_BOARD_REGISTRY_DEFINITION = CsvRegistrySourceDefinition(
    source_type=JIRA_BOARD_REGISTRY_SOURCE_TYPE,
    display_name="JIRA board registry",
    capability_key="jira_board_registry",
    required_columns=JIRA_BOARD_REQUIRED_COLUMNS,
    optional_columns=JIRA_BOARD_OPTIONAL_COLUMNS,
    preview_domain=preview_jira_board_registry_import,
    confirm_domain=apply_jira_board_registry_import,
)

CONFLUENCE_PAGE_REGISTRY_DEFINITION = CsvRegistrySourceDefinition(
    source_type=CONFLUENCE_PAGE_REGISTRY_SOURCE_TYPE,
    display_name="Confluence page registry",
    capability_key="confluence_page_registry",
    required_columns=CONFLUENCE_PAGE_REQUIRED_COLUMNS,
    optional_columns=CONFLUENCE_PAGE_OPTIONAL_COLUMNS,
    preview_domain=preview_confluence_page_registry_import,
    confirm_domain=apply_confluence_page_registry_import,
)


def validate_profile(
    definition: CsvRegistrySourceDefinition,
    profile: SourceProfileUpsert,
) -> SourceProfileUpsert:
    if profile.source_type != definition.source_type:
        raise ValueError("DATA_ONBOARDING_SOURCE_TYPE_UNSUPPORTED")
    source_locator = profile.source_locator.strip()
    if not source_locator:
        raise ValueError("DATA_ONBOARDING_SOURCE_LOCATOR_REQUIRED")
    normalized_path = str(Path(source_locator).expanduser().resolve(strict=False))
    if Path(normalized_path).suffix.lower() != ".csv":
        raise ValueError("DATA_ONBOARDING_CSV_SOURCE_LOCATOR_INVALID")
    _require_blank(
        profile.mapping_preset_id,
        "DATA_ONBOARDING_REGISTRY_MAPPING_PRESET_UNSUPPORTED",
    )
    _require_blank(
        profile.member_key_type,
        "DATA_ONBOARDING_REGISTRY_MEMBER_KEY_TYPE_UNSUPPORTED",
    )
    _require_blank(
        profile.project_key_type,
        "DATA_ONBOARDING_REGISTRY_PROJECT_KEY_TYPE_UNSUPPORTED",
    )
    _require_blank(
        profile.baseline_source,
        "DATA_ONBOARDING_REGISTRY_BASELINE_SOURCE_UNSUPPORTED",
    )
    _require_blank(
        profile.adjustment_source,
        "DATA_ONBOARDING_REGISTRY_ADJUSTMENT_SOURCE_UNSUPPORTED",
    )
    _require_blank(
        profile.conflict_policy,
        "DATA_ONBOARDING_REGISTRY_CONFLICT_POLICY_UNSUPPORTED",
    )
    _require_blank(
        profile.plan_naming_policy,
        "DATA_ONBOARDING_REGISTRY_PLAN_NAMING_POLICY_UNSUPPORTED",
    )
    return replace(
        profile,
        display_name=profile.display_name.strip() or definition.display_name,
        source_locator=normalized_path,
        source_options={
            "file_format": "csv",
            "domain_capability": definition.capability_key,
            "required_columns": list(definition.required_columns),
            "optional_columns": list(definition.optional_columns),
            "reconciliation_mode": "full_sync",
        },
    )


def profile_metadata(
    definition: CsvRegistrySourceDefinition,
    profile: SourceProfileRecord,
) -> dict[str, Any]:
    return {
        "source_options": copy.deepcopy(profile.source_options),
        "source_family": {
            "source_type": definition.source_type,
            "display_name": definition.display_name,
            "file_format": "csv",
            "domain_capability": definition.capability_key,
            "required_columns": list(definition.required_columns),
            "optional_columns": list(definition.optional_columns),
            "reconciliation_mode": "full_sync",
        },
    }


def build_source_identity(
    definition: CsvRegistrySourceDefinition,
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
    definition: CsvRegistrySourceDefinition,
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
                    f"{definition.display_name} already matches the retained registry state; "
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
    definition: CsvRegistrySourceDefinition,
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
    definition: CsvRegistrySourceDefinition,
    run_id: str,
    *,
    db_path: str | Path | None = None,
) -> None:
    del definition, run_id, db_path


def planned_operations(
    definition: CsvRegistrySourceDefinition,
    source_preview: dict[str, Any],
) -> list[dict[str, Any]]:
    operation = {
        "capability": definition.capability_key,
        "counts": dict(source_preview.get("counts", {})),
        "publication_id": (
            source_preview.get("domain_payload", {}).get("publication_id") or None
        ),
        "reconciliation_mode": "full_sync",
    }
    operation["status"] = (
        "planned"
        if str(source_preview.get("status")) == "previewed"
        else str(source_preview.get("status"))
    )
    return [operation]


def coverage_summary(
    definition: CsvRegistrySourceDefinition,
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
    definition: CsvRegistrySourceDefinition,
    source_result: dict[str, Any],
) -> list[DomainLinkRecord]:
    publication_id = str(
        source_result.get("domain_payload", {}).get("publication_id")
        or source_result.get("domain_result", {}).get("payload", {}).get("publication_id")
        or ""
    )
    return [
        DomainLinkRecord(
            capability_key=definition.capability_key,
            status=str(source_result.get("status", "failed")),
            domain_session_id="",
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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_contract(definition: CsvRegistrySourceDefinition) -> dict[str, Any]:
    return {
        "source_type": definition.source_type,
        "display_name": definition.display_name,
        "file_format": "csv",
        "domain_capability": definition.capability_key,
        "required_columns": list(definition.required_columns),
        "optional_columns": list(definition.optional_columns),
        "reconciliation_mode": "full_sync",
    }


def _rejected_preview(
    definition: CsvRegistrySourceDefinition,
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


def _failed_source_result(
    definition: CsvRegistrySourceDefinition,
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
        "source_contract": _source_contract(definition),
        "plan_version": None,
        "blockers": list(source_preview.get("blockers", [])),
        "warnings": warnings,
        "conflicts": list(source_preview.get("conflicts", [])),
        "counts": dict(source_preview.get("counts", {})),
        "domain_payload": copy.deepcopy(source_preview.get("domain_payload", {})),
        "domain_report": copy.deepcopy(source_preview.get("domain_report", {})),
        "domain_result": {
            "status": "failed",
            "failure_code": failure_code,
            "idempotent": False,
        },
    }


def _successful_source_result(
    definition: CsvRegistrySourceDefinition,
    source_preview: dict[str, Any],
    domain_result: dict[str, Any],
) -> dict[str, Any]:
    domain_payload = copy.deepcopy(
        domain_result.get("payload", source_preview.get("domain_payload", {}))
    )
    domain_report = copy.deepcopy(
        domain_result.get("report", source_preview.get("domain_report", {}))
    )
    return {
        "status": "completed",
        "failure_code": "",
        "source_contract": _source_contract(definition),
        "plan_version": None,
        "blockers": list(source_preview.get("blockers", [])),
        "warnings": list(source_preview.get("warnings", [])),
        "conflicts": list(source_preview.get("conflicts", [])),
        "counts": dict(domain_result.get("counts", source_preview.get("counts", {}))),
        "domain_payload": domain_payload,
        "domain_report": domain_report,
        "domain_result": {
            "status": "completed",
            "idempotent": bool(domain_result.get("idempotent", False)),
            "payload": domain_payload,
        },
    }
