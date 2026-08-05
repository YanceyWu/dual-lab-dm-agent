"""Adapter from workbook-native validated data to contract-coverage packages."""

from __future__ import annotations

from typing import Any

from pm_agent.contract_coverage.service import PACKAGE_SCHEMA_VERSION
from pm_agent.rules.identity import slugify_text
from pm_agent.workbook_onboarding.models import ValidatedWorkbook

DATASET_MARKER = "WORKBOOK_ONBOARDING_V1"
SOURCE_ID = "source-workbook-contract-coverage"
SCOPE_KEY = "workbook-contract-coverage"


def build_contract_coverage_package(
    workbook: ValidatedWorkbook,
    *,
    version_name: str,
    as_of_date: str,
    revision: int,
) -> dict[str, Any]:
    package_slug = slugify_text(version_name) or "baseline"
    members = [
        {
            "member_id": member.member_key,
            "display_name": member.display_name,
            "status": member.status,
            "resource_type": member.fte_type or "",
            "current_hiref_id": member.current_hiref_id,
            "hiref_end_date": member.hiref_end_date,
        }
        for member in workbook.members
    ]
    member_ids = sorted(member["member_id"] for member in members)
    stfte_member_ids = sorted(
        member["member_id"] for member in members if member["resource_type"] == "STFTE"
    )
    ltfte_member_ids = sorted(
        member["member_id"] for member in members if member["resource_type"] == "LTFTE"
    )
    contract_member_ids = sorted(
        member["member_id"]
        for member in members
        if member["current_hiref_id"] and member["hiref_end_date"]
    )
    unknown_resource_type_member_ids = sorted(
        member["member_id"] for member in members if member["resource_type"] == ""
    )
    return {
        "dataset_marker": DATASET_MARKER,
        "package_id": f"package-workbook-contract-coverage-{package_slug}-r{revision}",
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "generated_at": f"{as_of_date}T00:00:00+00:00",
        "source_id": SOURCE_ID,
        "publication_scope": {
            "scope_key": SCOPE_KEY,
            "as_of_date": as_of_date,
        },
        "manifest": {
            "member_ids": member_ids,
            "stfte_member_ids": stfte_member_ids,
            "ltfte_member_ids": ltfte_member_ids,
            "contract_member_ids": contract_member_ids,
            "unknown_resource_type_member_ids": unknown_resource_type_member_ids,
        },
        "members": members,
    }
