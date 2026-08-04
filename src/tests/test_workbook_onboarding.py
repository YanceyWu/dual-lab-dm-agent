from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from openpyxl import Workbook

from pm_agent.database import repository as legacy_repository
from pm_agent.database.bootstrap import main as init_db
from pm_agent.resource_intelligence.read_model import get_effective_capacity
from pm_agent.workbook_onboarding.parser import (
    EXPECTED_HEADERS,
    WorkbookParseError,
    parse_workbook,
)
from pm_agent.workbook_onboarding.service import (
    import_workbook,
    preview_workbook_import,
)
from pm_agent.workbook_onboarding import service as workbook_service
from pm_agent.workbook_onboarding.repository import (
    advance_profile_revision,
    resolve_plan_identity,
)
from pm_agent.workbook_onboarding.validator import validate_workbook
from pm_agent.workforce_planning_import import repository as workforce_repository


def _write_workbook(
    path: Path,
    *,
    setup_rows: list[list[object]],
    member_rows: list[list[object]],
    project_rows: list[list[object]],
    allocation_rows: list[list[object]],
    capacity_rows: list[list[object]],
    sheet_names: tuple[str, str, str, str, str] = (
        "Setup",
        "Members",
        "Projects",
        "Allocations",
        "Capacity",
    ),
) -> Path:
    workbook = Workbook()
    first = workbook.active
    first.title = sheet_names[0]
    for title in sheet_names[1:]:
        workbook.create_sheet(title)
    rows_by_sheet = {
        "Setup": setup_rows,
        "Members": member_rows,
        "Projects": project_rows,
        "Allocations": allocation_rows,
        "Capacity": capacity_rows,
    }
    for name, worksheet in zip(sheet_names, workbook.worksheets, strict=True):
        worksheet.append(EXPECTED_HEADERS[name if name in EXPECTED_HEADERS else "Capacity"])
        for row in rows_by_sheet.get(name, []):
            worksheet.append(row)
    workbook.save(path)
    return path


def _baseline_workbook(
    path: Path,
    *,
    allocation_value: float = 0.5,
    include_capacity: bool = False,
    capacity_rows: list[list[object]] | None = None,
    members: list[list[object]] | None = None,
    projects: list[list[object]] | None = None,
    allocations: list[list[object]] | None = None,
    start_month: str = "2026-09",
    end_month: str = "2026-09",
) -> Path:
    return _write_workbook(
        path,
        setup_rows=[["FY26 Q4 Baseline", "2026-08-15", start_month, end_month]],
        member_rows=members
        or [
            [
                "WD100001",
                "Alex Example",
                "LTFTE",
                "active",
                None,
                None,
                "Engineer",
                7,
                "2026-09-01",
                None,
            ]
        ],
        project_rows=projects
        or [["RP-PROJ-001", "Project Atlas", "active", 2, "2026-09-01", "2026-12-31"]],
        allocation_rows=allocations
        or [["WD100001", "RP-PROJ-001", "2026-09", allocation_value]],
        capacity_rows=(
            capacity_rows
            if capacity_rows is not None
            else ([["WD100001", "2026-09", 0.0, 0.0, 0.0]] if include_capacity else [])
        ),
    )


def _confirm_staffing_adjustment(
    *,
    project_id: str,
    member_id: str,
    plan_version_id: str,
    month: str,
    allocation: float,
) -> None:
    proposal_id = "proposal-workbook-adjustment-001"
    token = "token-workbook-adjustment-001"
    legacy_repository.create_staffing_proposal(
        {
            "proposal_id": proposal_id,
            "expires_at": (
                datetime.now(timezone.utc) + timedelta(days=1)
            ).isoformat(timespec="seconds"),
            "confirmation_token": token,
            "request": {
                "project_id": project_id,
                "start_period": month,
                "role": "Engineer",
            },
            "evidence": {},
            "proposal": {
                "plan_version_id": plan_version_id,
                "periods": [{"year": int(month[:4]), "month": int(month[5:7])}],
                "selections": [{"member_id": member_id, "allocation": allocation}],
                "candidates": [],
            },
        }
    )
    result = legacy_repository.confirm_staffing_proposal(
        proposal_id,
        token,
        {
            "plan_version_id": plan_version_id,
            "periods": [{"year": int(month[:4]), "month": int(month[5:7])}],
            "selections": [{"member_id": member_id, "allocation": allocation}],
            "candidates": [],
        },
    )
    assert result["status"] == "confirmed"


def test_parse_workbook_rejects_invalid_sheet_contract(tmp_path: Path) -> None:
    workbook_path = _write_workbook(
        tmp_path / "bad-sheets.xlsx",
        setup_rows=[["FY26 Q4 Baseline", "2026-08-15", "2026-09", "2026-09"]],
        member_rows=[],
        project_rows=[],
        allocation_rows=[],
        capacity_rows=[],
        sheet_names=("Setup", "Members", "Projects", "Allocations", "CapacityX"),
    )
    with pytest.raises(WorkbookParseError, match="WORKBOOK_SHEETS_INVALID"):
        parse_workbook(workbook_path)


def test_validate_workbook_blocks_stfte_without_hiref_fields(tmp_path: Path) -> None:
    workbook_path = _write_workbook(
        tmp_path / "invalid-member.xlsx",
        setup_rows=[["FY26 Q4 Baseline", "2026-08-15", "2026-09", "2026-09"]],
        member_rows=[
            [
                "WD100001",
                "Alex Example",
                "STFTE",
                "active",
                None,
                None,
                "Engineer",
                7,
                "2026-09-01",
                None,
            ]
        ],
        project_rows=[["RP-PROJ-001", "Project Atlas", "active", 2, "2026-09-01", "2026-12-31"]],
        allocation_rows=[["WD100001", "RP-PROJ-001", "2026-09", 0.5]],
        capacity_rows=[],
    )
    result = validate_workbook(parse_workbook(workbook_path))
    assert result.workbook is None
    assert "WORKBOOK_MEMBER_STFTE_HIREF_REQUIRED" in [
        item.code for item in result.blockers
    ]


def test_parse_workbook_rejects_extra_columns(tmp_path: Path) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Setup"
    worksheet.append(EXPECTED_HEADERS["Setup"] + ["extra_column"])
    worksheet.append(["FY26 Q4 Baseline", "2026-08-15", "2026-09", "2026-09", "ignored"])
    for name in ("Members", "Projects", "Allocations", "Capacity"):
        tab = workbook.create_sheet(name)
        tab.append(EXPECTED_HEADERS[name])
    workbook_path = tmp_path / "extra-columns.xlsx"
    workbook.save(workbook_path)
    with pytest.raises(WorkbookParseError, match="WORKBOOK_HEADERS_INVALID:Setup"):
        parse_workbook(workbook_path)


def test_validate_workbook_blocks_partial_month_member_effective_dates(
    tmp_path: Path,
) -> None:
    workbook_path = _write_workbook(
        tmp_path / "partial-month.xlsx",
        setup_rows=[["FY26 Q4 Baseline", "2026-08-15", "2026-09", "2026-09"]],
        member_rows=[
            [
                "WD100001",
                "Alex Example",
                "LTFTE",
                "active",
                None,
                None,
                "Engineer",
                7,
                "2026-09-15",
                None,
            ]
        ],
        project_rows=[["RP-PROJ-001", "Project Atlas", "active", 2, "2026-09-01", "2026-12-31"]],
        allocation_rows=[["WD100001", "RP-PROJ-001", "2026-09", 0.5]],
        capacity_rows=[],
    )
    result = validate_workbook(parse_workbook(workbook_path))
    assert "WORKBOOK_MEMBER_EFFECTIVE_START_NOT_MONTH_BOUNDARY" in [
        item.code for item in result.blockers
    ]


def test_preview_workbook_expands_sparse_allocations_and_skips_empty_capacity(
    isolated_db: Path, tmp_path: Path
) -> None:
    init_db(quiet=True)
    workbook_path = _write_workbook(
        tmp_path / "sparse.xlsx",
        setup_rows=[["FY26 Q4 Baseline", "2026-08-15", "2026-09", "2026-10"]],
        member_rows=[
            ["WD100001", "Alex Example", "LTFTE", "active", None, None, "Engineer", 7, "2026-09-01", None],
            ["WD100002", "Blair Example", "LTFTE", "active", None, None, "Engineer", 7, "2026-09-01", None],
        ],
        project_rows=[
            ["RP-PROJ-001", "Project Atlas", "active", 2, "2026-09-01", "2026-12-31"],
            ["RP-PROJ-002", "Project Beacon", "planning", 3, None, "2026-12-31"],
        ],
        allocation_rows=[["WD100001", "RP-PROJ-001", "2026-09", 0.5]],
        capacity_rows=[],
    )
    preview = preview_workbook_import(workbook_path, db_path=isolated_db)
    assert preview["status"] == "previewed"
    assert preview["capacity_package"] is None
    assert preview["counts"]["expanded_allocation_records"] == 8
    allocation_map = {
        (
            row["member_id"],
            row["project_id"],
            row["year"],
            row["month"],
        ): row["allocation"]
        for row in preview["workforce_package"]["monthly_allocations"]
    }
    assert allocation_map[("WD100001", "RP-PROJ-001", 2026, 9)] == 0.5
    assert allocation_map[("WD100002", "RP-PROJ-002", 2026, 10)] == 0.0


def test_import_workbook_preserves_explicit_zero_and_missing_capacity_unknown(
    isolated_db: Path, tmp_path: Path
) -> None:
    init_db(quiet=True)
    workbook_path = _write_workbook(
        tmp_path / "capacity.xlsx",
        setup_rows=[["FY26 Q4 Baseline", "2026-08-15", "2026-09", "2026-09"]],
        member_rows=[
            ["WD100001", "Alex Example", "LTFTE", "active", None, None, "Engineer", 7, "2026-09-01", None],
            ["WD100002", "Blair Example", "LTFTE", "active", None, None, "Engineer", 7, "2026-09-01", None],
        ],
        project_rows=[["RP-PROJ-001", "Project Atlas", "active", 2, "2026-09-01", "2026-12-31"]],
        allocation_rows=[
            ["WD100001", "RP-PROJ-001", "2026-09", 0.5],
            ["WD100002", "RP-PROJ-001", "2026-09", 0.2],
        ],
        capacity_rows=[["WD100001", "2026-09", 0.0, 0.0, 0.0]],
    )
    result = import_workbook(workbook_path, db_path=isolated_db)
    plan_version_id = result["plan_version"]["plan_version_id"]
    assert result["status"] == "completed"
    assert result["capacity_result"]["report"]["coverage"]["explicit_zero_count"] == 3

    known = get_effective_capacity(
        "WD100001", 2026, 9, plan_version_id, db_path=isolated_db
    )
    missing = get_effective_capacity(
        "WD100002", 2026, 9, plan_version_id, db_path=isolated_db
    )
    assert known["state"] == "known"
    assert known["effective_capacity"] == 1.0
    assert known["available_capacity"] == 0.5
    assert missing["state"] == "unknown"


def test_import_workbook_rejects_when_workforce_preview_rejects(
    isolated_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    init_db(quiet=True)
    monkeypatch.setattr(
        workbook_service,
        "_build_candidate",
        lambda *args, **kwargs: {
            "status": "previewed",
            "workbook_path": "test.xlsx",
            "blockers": [],
            "warnings": [],
            "conflicts": [],
            "plan_version": {
                "plan_version_id": "plan-workbook-test",
                "version_name": "FY26 Q4 Baseline",
            },
            "revision": 1,
            "counts": {},
            "workforce_package": {},
            "capacity_package": None,
        },
    )
    monkeypatch.setattr(
        workbook_service,
        "preview_workforce_import",
        lambda *args, **kwargs: {
            "status": "rejected",
            "failure_code": "WORKFORCE_PLANNING_PACKAGE_REPLAY_CONFLICT",
        },
    )
    result = import_workbook("test.xlsx", db_path=isolated_db)
    assert result["status"] == "rejected"
    assert result["workforce_result"]["status"] == "rejected"
    assert result["capacity_result"] is None


def test_import_workbook_rejection_restores_revision_and_releases_reservation(
    isolated_db: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    init_db(quiet=True)
    workbook_path = _baseline_workbook(tmp_path / "rejected-import.xlsx")
    monkeypatch.setattr(
        workbook_service,
        "preview_workforce_import",
        lambda *args, **kwargs: {
            "status": "rejected",
            "failure_code": "WORKFORCE_PLANNING_PACKAGE_REPLAY_CONFLICT",
        },
    )

    result = import_workbook(workbook_path, db_path=isolated_db)
    assert result["status"] == "rejected"
    assert result["revision"] == 1

    with sqlite3.connect(isolated_db) as connection:
        revision = connection.execute(
            "SELECT current_revision FROM onboarding_profiles WHERE profile_key='default'"
        ).fetchone()
        reservations = connection.execute(
            """
            SELECT status
            FROM data_onboarding_plan_reservations
            WHERE requested_name='FY26 Q4 Baseline'
            """
        ).fetchall()
    assert revision == (0,)
    assert reservations == [("released",)]


def test_confirm_workbook_candidate_reuses_retryable_workforce_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = {
        "status": "previewed",
        "workbook_path": "test.xlsx",
        "blockers": [],
        "warnings": [],
        "conflicts": [],
        "plan_version": {
            "plan_version_id": "plan-workbook-test",
            "version_name": "FY26 Q4 Baseline",
        },
        "revision": 1,
        "counts": {},
        "workforce_package": {},
        "capacity_package": None,
    }
    monkeypatch.setattr(
        workbook_service,
        "preview_workforce_import",
        lambda *args, **kwargs: {
            "status": "retryable",
            "session_id": "workforce-session-1",
        },
    )
    monkeypatch.setattr(
        workbook_service,
        "confirm_workforce_import",
        lambda session_id, **kwargs: {
            "status": "completed",
            "session_id": session_id,
            "idempotent": False,
            "report": {"publication_id": "workforce-publication-1"},
        },
    )
    result = workbook_service.confirm_workbook_candidate(candidate)
    assert result["status"] == "completed"
    assert result["workforce_result"]["session_id"] == "workforce-session-1"
    assert result["workforce_result"]["report"]["publication_id"] == (
        "workforce-publication-1"
    )


def test_confirm_workbook_candidate_accepts_already_completed_workforce_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = {
        "status": "previewed",
        "workbook_path": "test.xlsx",
        "blockers": [],
        "warnings": [],
        "conflicts": [],
        "plan_version": {
            "plan_version_id": "plan-workbook-test",
            "version_name": "FY26 Q4 Baseline",
        },
        "revision": 1,
        "counts": {},
        "workforce_package": {},
        "capacity_package": None,
    }
    monkeypatch.setattr(
        workbook_service,
        "preview_workforce_import",
        lambda *args, **kwargs: {
            "status": "already_completed",
            "session_id": "workforce-session-1",
            "report": {"publication_id": "workforce-publication-1"},
        },
    )
    result = workbook_service.confirm_workbook_candidate(candidate)
    assert result["status"] == "completed"
    assert result["workforce_result"] == {
        "status": "completed",
        "session_id": "workforce-session-1",
        "idempotent": True,
        "report": {"publication_id": "workforce-publication-1"},
    }


def test_advance_profile_revision_serializes_concurrent_claims(isolated_db: Path) -> None:
    init_db(quiet=True)
    barrier = threading.Barrier(2)
    results: list[tuple[str, int]] = []
    errors: list[BaseException] = []

    def worker() -> None:
        try:
            barrier.wait()
            results.append(
                (
                    "ok",
                    advance_profile_revision(profile_key="default", db_path=isolated_db),
                )
            )
        except BaseException as exc:  # pragma: no cover - failure path assertion below
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert sorted(revision for _, revision in results) == [1, 2]


def test_resolve_plan_identity_serializes_concurrent_reservations(
    isolated_db: Path,
) -> None:
    init_db(quiet=True)
    barrier = threading.Barrier(2)
    results: list[dict[str, str]] = []
    errors: list[BaseException] = []

    def worker(profile_key: str, run_id: str) -> None:
        try:
            barrier.wait()
            results.append(
                resolve_plan_identity(
                    "FY26 Q4 Baseline",
                    profile_key=profile_key,
                    run_id=run_id,
                    db_path=isolated_db,
                )
            )
        except BaseException as exc:  # pragma: no cover - failure path assertion below
            errors.append(exc)

    threads = [
        threading.Thread(target=worker, args=("profile-a", "run-a")),
        threading.Thread(target=worker, args=("profile-b", "run-b")),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert {item["version_name"] for item in results} == {
        "FY26 Q4 Baseline",
        "FY26 Q4 Baseline-v2",
    }
    assert {item["plan_version_id"] for item in results} == {
        "plan-workbook-fy26-q4-baseline",
        "plan-workbook-fy26-q4-baseline-v2",
    }
    with sqlite3.connect(isolated_db) as connection:
        reservations = connection.execute(
            """
            SELECT run_id, version_name, plan_version_id, status
            FROM data_onboarding_plan_reservations
            ORDER BY run_id
            """
        ).fetchall()
    assert len(reservations) == 2
    assert set(reservations).issubset(
        {
        ("run-a", "FY26 Q4 Baseline", "plan-workbook-fy26-q4-baseline", "reserved"),
        ("run-a", "FY26 Q4 Baseline-v2", "plan-workbook-fy26-q4-baseline-v2", "reserved"),
        ("run-b", "FY26 Q4 Baseline", "plan-workbook-fy26-q4-baseline", "reserved"),
        ("run-b", "FY26 Q4 Baseline-v2", "plan-workbook-fy26-q4-baseline-v2", "reserved"),
        }
    )


def test_reimport_deduplicates_plan_version_name_and_replaces_current_baseline(
    isolated_db: Path, tmp_path: Path
) -> None:
    init_db(quiet=True)
    first_path = _baseline_workbook(tmp_path / "first.xlsx")
    first = import_workbook(first_path, db_path=isolated_db)
    second_path = _baseline_workbook(tmp_path / "second.xlsx")
    second = import_workbook(second_path, db_path=isolated_db)

    assert first["status"] == "completed"
    assert second["status"] == "completed"
    assert first["plan_version"]["version_name"] == "FY26 Q4 Baseline"
    assert second["plan_version"]["version_name"] == "FY26 Q4 Baseline-v2"

    current = workforce_repository.current_publication(db_path=isolated_db)
    package = json.loads(current["package_json"])
    assert package["plan_versions"][0]["version_name"] == "FY26 Q4 Baseline-v2"

    with sqlite3.connect(isolated_db) as connection:
        statuses = dict(
            connection.execute(
                "SELECT version_name, version_status FROM plan_versions"
            ).fetchall()
        )
    assert statuses == {
        "FY26 Q4 Baseline": "archived",
        "FY26 Q4 Baseline-v2": "active",
    }


def test_workbook_preview_blocks_unabsorbed_confirmed_adjustment_and_allows_absorbed(
    isolated_db: Path, tmp_path: Path
) -> None:
    init_db(quiet=True)
    baseline_path = _baseline_workbook(tmp_path / "baseline.xlsx", allocation_value=0.5)
    baseline = import_workbook(baseline_path, db_path=isolated_db)
    assert baseline["status"] == "completed"
    current_plan_id = baseline["plan_version"]["plan_version_id"]

    _confirm_staffing_adjustment(
        project_id="RP-PROJ-001",
        member_id="WD100001",
        plan_version_id=current_plan_id,
        month="2026-09",
        allocation=0.1,
    )

    conflicting = preview_workbook_import(
        _baseline_workbook(tmp_path / "conflict.xlsx", allocation_value=0.5),
        db_path=isolated_db,
    )
    absorbed = preview_workbook_import(
        _baseline_workbook(tmp_path / "absorbed.xlsx", allocation_value=0.6),
        db_path=isolated_db,
    )

    assert conflicting["status"] == "rejected"
    assert len(conflicting["conflicts"]) == 1
    assert conflicting["conflicts"][0]["member_id"] == "WD100001"
    assert conflicting["conflicts"][0]["project_id"] == "RP-PROJ-001"
    assert conflicting["conflicts"][0]["plan_version_id"] == current_plan_id
    assert conflicting["conflicts"][0]["baseline_allocation"] == 0.5
    assert conflicting["conflicts"][0]["effective_allocation"] == 0.6
    assert conflicting["conflicts"][0]["candidate_allocation"] == 0.5
    assert (
        conflicting["conflicts"][0]["conflict_code"]
        == "WORKBOOK_ONBOARDING_CONFIRMED_ADJUSTMENT_CONFLICT"
    )
    assert absorbed["status"] == "previewed"
    assert absorbed["conflicts"] == []
