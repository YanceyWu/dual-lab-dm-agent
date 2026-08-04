"""Typed models for structured data onboarding."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

ProfileStatus = Literal["active", "inactive"]


@dataclass(frozen=True)
class SourceProfileUpsert:
    profile_id: str
    profile_key: str
    display_name: str
    source_type: str
    source_locator: str
    mapping_preset_id: str
    member_key_type: str
    project_key_type: str
    baseline_source: str
    adjustment_source: str
    conflict_policy: str
    plan_naming_policy: str
    source_options: dict[str, Any]
    status: ProfileStatus


@dataclass(frozen=True)
class SourceProfileRecord(SourceProfileUpsert):
    current_revision: int
    last_successful_run_id: str
    last_successful_run_at: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class DomainLinkRecord:
    capability_key: str
    status: str
    domain_session_id: str
    domain_publication_id: str
    domain_plan_version_id: str
    details: dict[str, Any]
