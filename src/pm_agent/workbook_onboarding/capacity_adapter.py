"""Adapter from workbook-native validated data to resource capacity packages."""

from __future__ import annotations

from typing import Any

from pm_agent.rules.identity import slugify_text
from pm_agent.workbook_onboarding.models import ValidatedWorkbook

DATASET_MARKER = "WORKBOOK_ONBOARDING_V1"
SOURCE_ID = "source-workbook-team-project-capacity"
COMMITMENT_SOURCE_IDS = {
    "leave": "source-workbook-capacity-leave",
    "bau": "source-workbook-capacity-bau",
    "non_project": "source-workbook-capacity-non-project",
}


def build_capacity_package(
    workbook: ValidatedWorkbook,
    *,
    plan_version_id: str,
    version_name: str,
    assessment_time: str,
    revision: int,
) -> dict[str, Any] | None:
    if not workbook.capacity_rows:
        return None
    package_slug = slugify_text(version_name) or "baseline"
    member_periods = [
        {"member_id": row.member_key, "year": row.year, "month": row.month_number}
        for row in workbook.capacity_rows
    ]
    coverage_keys = []
    observations = []
    for row in workbook.capacity_rows:
        for commitment_kind, fraction in (
            ("leave", row.leave_fraction),
            ("bau", row.bau_fraction),
            ("non_project", row.non_project_fraction),
        ):
            coverage_keys.append(
                {
                    "member_id": row.member_key,
                    "year": row.year,
                    "month": row.month_number,
                    "commitment_kind": commitment_kind,
                }
            )
            observations.append(
                {
                    "member_id": row.member_key,
                    "year": row.year,
                    "month": row.month_number,
                    "commitment_kind": commitment_kind,
                    "fraction": fraction,
                    "value_state": "known",
                    "authoritative_source_id": COMMITMENT_SOURCE_IDS[commitment_kind],
                    "source_reference": f"workbook-capacity-row-{row.row_number}",
                    "observed_at": assessment_time,
                    "rule_version": "workbook-capacity-observation-v1",
                    "source_observation_version": revision,
                }
            )
    return {
        "dataset_marker": DATASET_MARKER,
        "package_id": f"package-workbook-capacity-{package_slug}-r{revision}",
        "schema_version": "resource-capacity-import-v1",
        "generated_at": assessment_time,
        "source_id": SOURCE_ID,
        "idempotency_key": f"resource-capacity-workbook-{package_slug}-r{revision}",
        "plan_version_id": plan_version_id,
        "assessment_time": assessment_time,
        "manifest": {
            "member_periods": member_periods,
            "commitment_kinds": ["leave", "bau", "non_project"],
            "coverage_keys": coverage_keys,
        },
        "observations": observations,
    }
