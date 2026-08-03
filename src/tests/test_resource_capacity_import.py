from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from pm_agent.database.bootstrap import main as init_db
from pm_agent.resource_intelligence import repository as capacity_repository
from pm_agent.resource_intelligence.read_model import get_effective_capacity
from pm_agent.resource_intelligence.service import confirm_import, preview_import
from pm_agent.workforce_planning_import.service import (
    confirm_import as confirm_workforce,
    preview_import as preview_workforce,
)

ROOT = Path(__file__).resolve().parents[1]
WORKFORCE_SAMPLE = ROOT / "sample-data/json/workforce_planning_import.sample.json"
CAPACITY_SAMPLE = ROOT / "sample-data/json/resource_capacity_import.sample.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _business_key_capacity_package() -> dict:
    package = _load(CAPACITY_SAMPLE)
    package["dataset_marker"] = "WORKBOOK_ONBOARDING_V1"
    package["package_id"] = "package-workbook-fy26-q4-capacity"
    package["source_id"] = "source-workbook-team-project-capacity"
    package["idempotency_key"] = "resource-capacity-workbook-fy26-q4-capacity"
    package["plan_version_id"] = "plan-workbook-fy26-q4-baseline"
    member_map = {
        "member-synthetic-001": "WD100001",
        "member-synthetic-002": "WD100002",
        "member-synthetic-003": "WD100003",
    }
    for item in package["manifest"]["member_periods"]:
        item["member_id"] = member_map[item["member_id"]]
    for item in package["manifest"]["coverage_keys"]:
        item["member_id"] = member_map[item["member_id"]]
    for index, item in enumerate(package["observations"], start=1):
        item["member_id"] = member_map[item["member_id"]]
        item["source_reference"] = f"workbook-capacity-row-{index:03d}"
    return package


def _business_key_workforce_package() -> dict:
    package = _load(WORKFORCE_SAMPLE)
    package["dataset_marker"] = "WORKBOOK_ONBOARDING_V1"
    package["package_id"] = "package-workbook-fy26-q4-baseline"
    package["source_id"] = "source-workbook-team-project-capacity"
    member_map = {
        "member-synthetic-001": {
            "member_id": "WD100001",
            "display_name": "Sample Member One",
            "role": "Delivery Manager",
            "level": "8",
            "resource_type": "LTFTE",
        },
        "member-synthetic-002": {
            "member_id": "WD100002",
            "display_name": "Sample Member Two",
            "role": "Engineer",
            "level": "7",
            "resource_type": "STFTE",
            "current_hiref_id": "H99881",
            "hiref_end_date": "2026-12-31",
        },
        "member-synthetic-003": {
            "member_id": "WD100003",
            "display_name": "Sample Member Three",
            "role": "Analyst",
            "level": "6",
            "resource_type": "LTFTE",
        },
    }
    project_map = {
        "project-synthetic-atlas": {
            "project_id": "RP-PROJ-001",
            "display_name": "Project Atlas Example",
            "status": "active",
            "priority": 2,
            "start_date": "2026-01-01",
            "target_end": "2026-12-31",
        },
        "project-synthetic-beacon": {
            "project_id": "RP-PROJ-002",
            "display_name": "Project Beacon Example",
            "status": "planning",
            "priority": 3,
            "start_date": None,
            "target_end": "2026-12-31",
        },
    }
    plan_id = "plan-workbook-fy26-q4-baseline"
    for item in package["members"]:
        mapped = member_map[item["member_id"]]
        item.update(mapped)
    for item in package["projects"]:
        mapped = project_map[item["project_id"]]
        item.update(mapped)
    package["plan_versions"][0]["plan_version_id"] = plan_id
    package["plan_versions"][0]["version_name"] = "FY26 Q4 Baseline"
    package["plan_versions"][0]["as_of_date"] = None
    package["manifest"]["member_ids"] = [
        mapped["member_id"] for mapped in member_map.values()
    ]
    package["manifest"]["project_ids"] = [
        mapped["project_id"] for mapped in project_map.values()
    ]
    package["manifest"]["plan_version_ids"] = [plan_id]
    member_ids = {key: value["member_id"] for key, value in member_map.items()}
    project_ids = {key: value["project_id"] for key, value in project_map.items()}
    for item in package["manifest"]["workforce_periods"]:
        item["member_id"] = member_ids[item["member_id"]]
    for item in package["manifest"]["allocation_keys"]:
        item["member_id"] = member_ids[item["member_id"]]
        item["project_id"] = project_ids[item["project_id"]]
        item["plan_version_id"] = plan_id
    for item in package["monthly_allocations"]:
        item["member_id"] = member_ids[item["member_id"]]
        item["project_id"] = project_ids[item["project_id"]]
        item["plan_version_id"] = plan_id
    return package


def _bootstrap_dependencies(db_path: Path, *, inactive_second: bool = False) -> None:
    init_db(quiet=True)
    package = _load(WORKFORCE_SAMPLE)
    if inactive_second:
        package["members"][1]["status"] = "inactive"
    preview = preview_workforce(package, db_path=db_path)
    confirm_workforce(preview["session_id"], db_path=db_path)


def _replacement(package: dict, *, version: int = 2) -> dict:
    result = deepcopy(package)
    result["package_id"] = f"package-synthetic-resource-capacity-{version:03d}"
    result["idempotency_key"] = f"resource-capacity-synthetic-{version:03d}"
    for observation in result["observations"]:
        observation["source_observation_version"] = version
    return result


def test_clean_bootstrap_composes_only_dedicated_capacity_schema(isolated_db: Path) -> None:
    init_db(quiet=True)
    init_db(quiet=True)
    with sqlite3.connect(isolated_db) as database:
        tables = {row[0] for row in database.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
    assert {
        "resource_capacity_import_sessions", "resource_capacity_import_attempts",
        "resource_capacity_import_runs", "resource_capacity_publications",
        "resource_capacity_manifest_coverage", "resource_capacity_observations",
        "resource_capacity_derivations",
    } <= tables


def test_preview_confirm_derives_capacity_and_preserves_explicit_zero(isolated_db: Path) -> None:
    _bootstrap_dependencies(isolated_db)
    preview = preview_import(_load(CAPACITY_SAMPLE), db_path=isolated_db)
    assert preview["status"] == "previewed"
    assert preview["confirmation_required"] is True
    assert preview["counts"] == {
        "member_periods": 3, "coverage_keys": 9, "observations": 9,
        "explicit_zero_observations": 6,
    }
    result = confirm_import(preview["session_id"], db_path=isolated_db)
    assert result["report"]["coverage"]["state"] == "complete"
    assert result["report"]["coverage"]["explicit_zero_count"] == 6
    capacity = get_effective_capacity(
        "member-synthetic-001", 2026, 8, "plan-synthetic-baseline-001",
        db_path=isolated_db,
    )
    assert capacity["state"] == "known"
    assert capacity["non_project_fraction"] == 0.0
    assert capacity["non_project_deduction"] == 0.3
    assert capacity["effective_capacity"] == 0.7
    assert capacity["available_capacity"] == 0.2
    assert capacity["total_commitment"] == 0.8
    assert capacity["overload_amount"] == 0.0
    assert capacity["overload_state"] == "clear"


def test_overload_thresholds_are_deterministic(isolated_db: Path) -> None:
    _bootstrap_dependencies(isolated_db)
    package = _load(CAPACITY_SAMPLE)
    # Member 001 effective capacity 0.4 against allocation 0.5 => amber at 0.10.
    package["observations"][1]["fraction"] = 0.5
    # Member 002 effective capacity 0.7 against allocation 0.0 => clear.
    package["observations"][4]["fraction"] = 0.3
    preview = preview_import(package, db_path=isolated_db)
    confirm_import(preview["session_id"], db_path=isolated_db)
    amber = get_effective_capacity(
        "member-synthetic-001", 2026, 8, "plan-synthetic-baseline-001", db_path=isolated_db
    )
    assert amber["overload_amount"] == 0.1
    assert amber["overload_state"] == "amber"

    # A higher complete publication changes member 001 to red, atomically.
    next_package = _replacement(package)
    next_package["observations"][1]["fraction"] = 0.6
    next_preview = preview_import(next_package, db_path=isolated_db)
    confirm_import(next_preview["session_id"], db_path=isolated_db)
    red = get_effective_capacity(
        "member-synthetic-001", 2026, 8, "plan-synthetic-baseline-001", db_path=isolated_db
    )
    assert red["overload_amount"] == 0.2
    assert red["overload_state"] == "red"


def test_stale_and_inactive_evidence_never_produce_available_capacity(isolated_db: Path) -> None:
    _bootstrap_dependencies(isolated_db, inactive_second=True)
    package = _load(CAPACITY_SAMPLE)
    for observation in package["observations"][:3]:
        observation["observed_at"] = "2026-06-01T00:00:00+00:00"
    preview = preview_import(package, db_path=isolated_db)
    confirm_import(preview["session_id"], db_path=isolated_db)
    stale = get_effective_capacity(
        "member-synthetic-001", 2026, 8, "plan-synthetic-baseline-001", db_path=isolated_db
    )
    inactive = get_effective_capacity(
        "member-synthetic-002", 2026, 8, "plan-synthetic-baseline-001", db_path=isolated_db
    )
    assert (stale["state"], stale["effective_capacity"], stale["available_capacity"]) == (
        "stale", None, None
    )
    assert (inactive["state"], inactive["base_capacity"], inactive["available_capacity"]) == (
        "unknown", None, None
    )


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (lambda p: p["observations"].pop(), "RESOURCE_CAPACITY_OBSERVATION_COVERAGE_INCOMPLETE"),
        (lambda p: p["manifest"]["coverage_keys"].pop(), "RESOURCE_CAPACITY_COVERAGE_INCOMPLETE"),
        (lambda p: p["observations"][0].update(month=13), "RESOURCE_CAPACITY_PERIOD_INVALID"),
        (lambda p: p["observations"][0].update(fraction=1.1), "RESOURCE_CAPACITY_FRACTION_RANGE_INVALID"),
        (lambda p: p["observations"][0].update(commitment_kind=["leave"]), "RESOURCE_CAPACITY_COMMITMENT_KIND_INVALID"),
        (lambda p: p["observations"][0].update(authoritative_source_id="source-synthetic-bau"), "RESOURCE_CAPACITY_SOURCE_AUTHORITY_INVALID"),
        (lambda p: p["observations"][0].update(observed_at="2026-08-02T00:00:00+00:00"), "RESOURCE_CAPACITY_OBSERVATION_IN_FUTURE"),
    ],
)
def test_invalid_package_fails_before_session_creation(isolated_db: Path, mutate, code: str) -> None:
    _bootstrap_dependencies(isolated_db)
    package = _load(CAPACITY_SAMPLE)
    mutate(package)
    with pytest.raises(ValueError, match=code):
        preview_import(package, db_path=isolated_db)
    with sqlite3.connect(isolated_db) as database:
        assert database.execute(
            "SELECT COUNT(*) FROM resource_capacity_import_sessions"
        ).fetchone()[0] == 0


def test_identical_replay_is_idempotent_and_same_package_conflict_preserves_current(isolated_db: Path) -> None:
    _bootstrap_dependencies(isolated_db)
    package = _load(CAPACITY_SAMPLE)
    first = preview_import(package, db_path=isolated_db)
    first_result = confirm_import(first["session_id"], db_path=isolated_db)
    replay = preview_import(package, db_path=isolated_db)
    assert replay["status"] == "already_completed"
    assert confirm_import(replay["session_id"], db_path=isolated_db)["idempotent"] is True
    conflict = deepcopy(package)
    conflict["observations"][0]["fraction"] = 0.2
    rejected = preview_import(conflict, db_path=isolated_db)
    assert rejected["failure_code"] == "RESOURCE_CAPACITY_PACKAGE_REPLAY_CONFLICT"
    with sqlite3.connect(isolated_db) as database:
        current = database.execute(
            "SELECT publication_id FROM resource_capacity_publications WHERE is_current=1"
        ).fetchone()[0]
        assert database.execute(
            "SELECT COUNT(*) FROM resource_capacity_import_attempts"
        ).fetchone()[0] == 1
    assert current == first_result["report"]["publication_id"]


def test_same_or_lower_source_version_cannot_replace_current(isolated_db: Path) -> None:
    _bootstrap_dependencies(isolated_db)
    package = _load(CAPACITY_SAMPLE)
    first = preview_import(package, db_path=isolated_db)
    confirm_import(first["session_id"], db_path=isolated_db)
    same_version = _replacement(package)
    for observation in same_version["observations"]:
        observation["source_observation_version"] = 1
    rejected = preview_import(same_version, db_path=isolated_db)
    assert rejected["failure_code"] == "RESOURCE_CAPACITY_OBSERVATION_VERSION_CONFLICT"


def test_reused_idempotency_key_with_different_package_is_rejected(isolated_db: Path) -> None:
    _bootstrap_dependencies(isolated_db)
    package = _load(CAPACITY_SAMPLE)
    first = preview_import(package, db_path=isolated_db)
    confirm_import(first["session_id"], db_path=isolated_db)
    replacement = _replacement(package)
    replacement["idempotency_key"] = package["idempotency_key"]
    rejected = preview_import(replacement, db_path=isolated_db)
    assert rejected["failure_code"] == "RESOURCE_CAPACITY_IDEMPOTENCY_KEY_CONFLICT"


def test_confirmation_rejects_dependency_change_after_preview(isolated_db: Path) -> None:
    _bootstrap_dependencies(isolated_db)
    preview = preview_import(_load(CAPACITY_SAMPLE), db_path=isolated_db)
    with sqlite3.connect(isolated_db) as database:
        database.execute(
            """UPDATE monthly_allocations SET allocation=0.6
               WHERE employee_id='member-synthetic-001'"""
        )
    with pytest.raises(ValueError, match="RESOURCE_CAPACITY_PREVIEW_BINDING_CHANGED"):
        confirm_import(preview["session_id"], db_path=isolated_db)
    with sqlite3.connect(isolated_db) as database:
        assert database.execute(
            "SELECT COUNT(*) FROM resource_capacity_publications"
        ).fetchone()[0] == 0
        attempt = database.execute(
            "SELECT status,failure_code FROM resource_capacity_import_attempts"
        ).fetchone()
    assert attempt == ("failed", "RESOURCE_CAPACITY_PREVIEW_BINDING_CHANGED")


def test_failed_replacement_rolls_back_current_publication_and_is_audited(
    isolated_db: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _bootstrap_dependencies(isolated_db)
    package = _load(CAPACITY_SAMPLE)
    first = preview_import(package, db_path=isolated_db)
    first_result = confirm_import(first["session_id"], db_path=isolated_db)
    replacement = _replacement(package)
    second = preview_import(replacement, db_path=isolated_db)
    monkeypatch.setattr(capacity_repository, "_integrity_report", lambda _db: {
        "sqlite_integrity": "failed", "foreign_key_violations": 1, "state": "failed"
    })
    with pytest.raises(RuntimeError, match="RESOURCE_CAPACITY_INTEGRITY_FAILED"):
        confirm_import(second["session_id"], db_path=isolated_db)
    with sqlite3.connect(isolated_db) as database:
        current = database.execute(
            "SELECT publication_id FROM resource_capacity_publications WHERE is_current=1"
        ).fetchone()[0]
        attempt = database.execute(
            """SELECT status,failure_code FROM resource_capacity_import_attempts
               WHERE session_id=?""",
            [second["session_id"]],
        ).fetchone()
    assert current == first_result["report"]["publication_id"]
    assert attempt == ("failed", "RESOURCE_CAPACITY_INTEGRITY_FAILED")


def test_reader_returns_explicit_unknown_before_capacity_publication(isolated_db: Path) -> None:
    _bootstrap_dependencies(isolated_db)
    result = get_effective_capacity(
        "member-synthetic-001", 2026, 8, "plan-synthetic-baseline-001", db_path=isolated_db
    )
    assert result["state"] == "unknown"
    assert result["available_capacity"] is None


def test_preview_confirm_accepts_business_keys_and_non_synthetic_source_references(
    isolated_db: Path,
) -> None:
    init_db(quiet=True)
    workforce_preview = preview_workforce(_business_key_workforce_package(), db_path=isolated_db)
    confirm_workforce(workforce_preview["session_id"], db_path=isolated_db)

    preview = preview_import(_business_key_capacity_package(), db_path=isolated_db)
    result = confirm_import(preview["session_id"], db_path=isolated_db)

    assert result["status"] == "completed"
    capacity = get_effective_capacity(
        "WD100001", 2026, 8, "plan-workbook-fy26-q4-baseline", db_path=isolated_db
    )
    assert capacity["state"] == "known"
    assert capacity["evidence"]["commitment_observation_fingerprints"]


def test_non_interactive_command_requires_dry_run_or_explicit_confirmation(isolated_db: Path) -> None:
    _bootstrap_dependencies(isolated_db)
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT)
    environment["DATABASE_PATH"] = str(isolated_db)
    command = [sys.executable, str(ROOT / "scripts/import_resource_capacity.py"),
               "--file", str(CAPACITY_SAMPLE)]
    missing = subprocess.run(command, cwd=ROOT, env=environment, capture_output=True, text=True)
    assert missing.returncode == 2
    assert "--dry-run | --confirm" in missing.stderr
    dry_run = subprocess.run([*command, "--dry-run"], cwd=ROOT, env=environment,
                             capture_output=True, text=True, check=True)
    assert json.loads(dry_run.stdout)["status"] == "previewed"
    confirmed = subprocess.run([*command, "--confirm"], cwd=ROOT, env=environment,
                               capture_output=True, text=True, check=True)
    assert json.loads(confirmed.stdout)["status"] == "completed"
