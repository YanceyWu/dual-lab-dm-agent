"""Source-type registry for structured data onboarding."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

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

_REGISTRY = {WORKBOOK_SOURCE_TYPE: WORKBOOK_HANDLER}


def get_handler(source_type: str) -> SourceTypeHandler:
    handler = _REGISTRY.get(source_type)
    if handler is None:
        raise ValueError("DATA_ONBOARDING_SOURCE_TYPE_UNSUPPORTED")
    return handler


def list_source_types() -> list[str]:
    return sorted(_REGISTRY)
