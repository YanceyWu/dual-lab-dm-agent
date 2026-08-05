"""Source-type registry for structured data onboarding."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from pm_agent.data_onboarding import domain_json_source
from pm_agent.data_onboarding import registry_csv_source
from pm_agent.data_onboarding.models import DomainLinkRecord, SourceProfileRecord, SourceProfileUpsert
from pm_agent.data_onboarding.workbook_contract import WORKBOOK_SOURCE_TYPE
from pm_agent.data_onboarding import workbook_source


@dataclass(frozen=True)
class SourceTypeHandler:
    source_type: str
    validate_profile: Callable[[SourceProfileUpsert], SourceProfileUpsert]
    profile_metadata: Callable[[SourceProfileRecord], dict[str, Any]]
    build_source_identity: Callable[[SourceProfileRecord], dict[str, Any]]
    preview: Callable[..., dict[str, Any]]
    confirm: Callable[..., dict[str, Any]]
    planned_operations: Callable[[dict[str, Any]], list[dict[str, Any]]]
    coverage_summary: Callable[[dict[str, Any]], dict[str, Any]]
    publication_links: Callable[[dict[str, Any]], list[DomainLinkRecord]]
    release_run: Callable[..., None]


WORKBOOK_HANDLER = SourceTypeHandler(
    source_type=WORKBOOK_SOURCE_TYPE,
    validate_profile=workbook_source.validate_profile,
    profile_metadata=workbook_source.profile_metadata,
    build_source_identity=workbook_source.build_source_identity,
    preview=workbook_source.preview,
    confirm=workbook_source.confirm,
    planned_operations=workbook_source.planned_operations,
    coverage_summary=workbook_source.coverage_summary,
    publication_links=workbook_source.publication_links,
    release_run=workbook_source.release_run,
)

def _json_handler(
    definition: domain_json_source.JsonDomainSourceDefinition,
) -> SourceTypeHandler:
    return SourceTypeHandler(
        source_type=definition.source_type,
        validate_profile=lambda profile: domain_json_source.validate_profile(
            definition, profile
        ),
        profile_metadata=lambda profile: domain_json_source.profile_metadata(
            definition, profile
        ),
        build_source_identity=lambda profile: domain_json_source.build_source_identity(
            definition, profile
        ),
        preview=lambda profile, *, run_id, db_path=None: domain_json_source.preview(
            definition,
            profile,
            db_path=db_path,
        ),
        confirm=lambda profile, source_preview, *, db_path=None: domain_json_source.confirm(
            definition,
            profile,
            source_preview,
            db_path=db_path,
        ),
        planned_operations=lambda source_preview: domain_json_source.planned_operations(
            definition,
            source_preview,
        ),
        coverage_summary=lambda source_preview: domain_json_source.coverage_summary(
            definition,
            source_preview,
        ),
        publication_links=lambda source_result: domain_json_source.publication_links(
            definition,
            source_result,
        ),
        release_run=lambda run_id, *, db_path=None: domain_json_source.release_run(
            definition,
            run_id,
            db_path=db_path,
        ),
    )


def _csv_handler(
    definition: registry_csv_source.CsvRegistrySourceDefinition,
) -> SourceTypeHandler:
    return SourceTypeHandler(
        source_type=definition.source_type,
        validate_profile=lambda profile: registry_csv_source.validate_profile(
            definition, profile
        ),
        profile_metadata=lambda profile: registry_csv_source.profile_metadata(
            definition, profile
        ),
        build_source_identity=lambda profile: registry_csv_source.build_source_identity(
            definition, profile
        ),
        preview=lambda profile, *, run_id, db_path=None: registry_csv_source.preview(
            definition,
            profile,
            run_id=run_id,
            db_path=db_path,
        ),
        confirm=lambda profile, source_preview, *, db_path=None: registry_csv_source.confirm(
            definition,
            profile,
            source_preview,
            db_path=db_path,
        ),
        planned_operations=lambda source_preview: registry_csv_source.planned_operations(
            definition,
            source_preview,
        ),
        coverage_summary=lambda source_preview: registry_csv_source.coverage_summary(
            definition,
            source_preview,
        ),
        publication_links=lambda source_result: registry_csv_source.publication_links(
            definition,
            source_result,
        ),
        release_run=lambda run_id, *, db_path=None: registry_csv_source.release_run(
            definition,
            run_id,
            db_path=db_path,
        ),
    )


_REGISTRY = {
    WORKBOOK_SOURCE_TYPE: WORKBOOK_HANDLER,
    domain_json_source.WORKFORCE_PLANNING_JSON_SOURCE_TYPE: _json_handler(
        domain_json_source.WORKFORCE_PLANNING_JSON_DEFINITION
    ),
    domain_json_source.RESOURCE_CAPACITY_JSON_SOURCE_TYPE: _json_handler(
        domain_json_source.RESOURCE_CAPACITY_JSON_DEFINITION
    ),
    domain_json_source.MILESTONE_JSON_SOURCE_TYPE: _json_handler(
        domain_json_source.MILESTONE_JSON_DEFINITION
    ),
    domain_json_source.PROJECT_HEALTH_REIMPORT_JSON_SOURCE_TYPE: _json_handler(
        domain_json_source.PROJECT_HEALTH_REIMPORT_JSON_DEFINITION
    ),
    registry_csv_source.JIRA_BOARD_REGISTRY_SOURCE_TYPE: _csv_handler(
        registry_csv_source.JIRA_BOARD_REGISTRY_DEFINITION
    ),
    registry_csv_source.CONFLUENCE_PAGE_REGISTRY_SOURCE_TYPE: _csv_handler(
        registry_csv_source.CONFLUENCE_PAGE_REGISTRY_DEFINITION
    ),
}


def get_handler(source_type: str) -> SourceTypeHandler:
    handler = _REGISTRY.get(source_type)
    if handler is None:
        raise ValueError("DATA_ONBOARDING_SOURCE_TYPE_UNSUPPORTED")
    return handler


def list_source_types() -> list[str]:
    return sorted(_REGISTRY)
