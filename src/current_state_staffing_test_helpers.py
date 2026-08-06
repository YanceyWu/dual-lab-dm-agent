from __future__ import annotations

from pathlib import Path

from pm_agent.sample_data.demo_publications import (
    publish_current_state_staffing_from_legacy_snapshot,
)


def publish_current_state_staffing_from_legacy(
    db_path: Path,
    *,
    package_id: str = "package-test-current-state-r1",
) -> dict:
    return publish_current_state_staffing_from_legacy_snapshot(
        db_path,
        package_id=package_id,
        dataset_marker="TEST_CURRENT_STATE_STAFFING",
        source_id="source-test-current-state-staffing",
        scope_key="test-current-state-staffing",
        as_of_date="2026-08-15",
        effective_year=2026,
        effective_month=8,
    )
