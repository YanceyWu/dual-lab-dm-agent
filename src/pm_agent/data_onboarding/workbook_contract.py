"""Shared workbook-onboarding framework constants."""

from __future__ import annotations

WORKBOOK_SOURCE_TYPE = "workbook"
WORKBOOK_MAPPING_PRESET_ID = "team-project-capacity-workbook-v1"
WORKBOOK_PLAN_NAMING_POLICY = "workbook_setup_name_with_auto_suffix"
WORKBOOK_MEMBER_KEY_TYPE = "workday_id"
WORKBOOK_PROJECT_KEY_TYPE = "resource_portal_project_id"
WORKBOOK_BASELINE_SOURCE = "workbook"
WORKBOOK_ADJUSTMENT_SOURCE = "copilot"
WORKBOOK_CONFLICT_POLICY = "copilot_wins_workbook_blocked"
WORKBOOK_DEFAULT_PROFILE_ID = "onboarding-profile-default"
WORKBOOK_DEFAULT_PROFILE_KEY = "default"
WORKBOOK_DEFAULT_DISPLAY_NAME = "Default workbook onboarding"
WORKBOOK_DEFAULT_SOURCE_OPTIONS = {
    "required_sheets": ["Setup", "Members", "Projects", "Allocations", "Capacity"],
    "capacity_row_coverage_policy": "missing_row_means_unknown",
}
