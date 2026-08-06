from __future__ import annotations

from pathlib import Path

from pm_agent.sample_data.demo_publications import (
    publish_contract_coverage_from_legacy_snapshot,
)


def publish_contract_coverage_from_legacy(
    db_path: Path,
    *,
    package_id: str = "package-test-contract-coverage-r1",
) -> dict:
    return publish_contract_coverage_from_legacy_snapshot(
        db_path,
        package_id=package_id,
        dataset_marker="TEST_CONTRACT_COVERAGE",
        source_id="source-test-contract-coverage",
        scope_key="test-contract-coverage",
        as_of_date="2026-08-15",
    )
