from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from pathlib import Path

from pm_agent.contract_coverage import read_model, service
from pm_agent.database import repository
from pm_agent.database.bootstrap import main as init_db
from pm_agent.use_cases.hiref_management import HirefManagementService


def _package(
    *,
    package_id: str = "package-contract-coverage-r1",
    stfte_has_contract: bool = True,
) -> dict:
    current_hiref_id = "HIREF-001" if stfte_has_contract else None
    hiref_end_date = "2026-12-31" if stfte_has_contract else None
    return {
        "dataset_marker": "WORKBOOK_ONBOARDING_V1",
        "package_id": package_id,
        "schema_version": service.PACKAGE_SCHEMA_VERSION,
        "generated_at": "2026-08-15T00:00:00+00:00",
        "source_id": "source-workbook-contract-coverage",
        "publication_scope": {
            "scope_key": "workbook-contract-coverage",
            "as_of_date": "2026-08-15",
        },
        "manifest": {
            "member_ids": ["WD100001", "WD100002"],
            "stfte_member_ids": ["WD100001"],
            "ltfte_member_ids": ["WD100002"],
            "contract_member_ids": ["WD100001"] if stfte_has_contract else [],
            "unknown_resource_type_member_ids": [],
        },
        "members": [
            {
                "member_id": "WD100001",
                "display_name": "Alex Example",
                "status": "active",
                "resource_type": "STFTE",
                "current_hiref_id": current_hiref_id,
                "hiref_end_date": hiref_end_date,
            },
            {
                "member_id": "WD100002",
                "display_name": "Blair Example",
                "status": "active",
                "resource_type": "LTFTE",
                "current_hiref_id": None,
                "hiref_end_date": None,
            },
        ],
    }


def _seed_legacy_hiref_state(db_path: Path) -> None:
    init_db(quiet=True)
    today = date.today()
    with sqlite3.connect(db_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executemany(
            """
            INSERT INTO employees
                (id, wd_id, name, level, status, resource_type, current_hiref, next_hiref, billing_end_date)
            VALUES (?, ?, ?, 'mid', 'active', ?, ?, ?, ?)
            """,
            [
                (
                    "990101",
                    "990101",
                    "Alex Example",
                    "STFTE",
                    "HIREF-ATLAS-001",
                    "",
                    (today + timedelta(days=30)).isoformat(),
                ),
                (
                    "990102",
                    "990102",
                    "Blair Example",
                    "STFTE",
                    "",
                    "",
                    "",
                ),
            ],
        )
        connection.execute(
            """
            INSERT INTO projects
                (id, name, jira_key, status, priority)
            VALUES
                ('project-atlas-990001', 'Project Atlas', '990001', 'active', 1)
            """
        )
        connection.execute(
            """
            INSERT INTO assignments
                (employee_id, project_id, allocation, status)
            VALUES
                ('990101', 'project-atlas-990001', 0.5, 'active')
            """
        )
        connection.execute(
            """
            INSERT INTO hiref
                (id, project, request_type, start_date, end_date, notes)
            VALUES
                (?, 'Project Atlas (990001)', 'extend', ?, ?, '')
            """,
            [
                "HIREF-ATLAS-001",
                (today - timedelta(days=120)).isoformat(),
                (today + timedelta(days=30)).isoformat(),
            ],
        )
        connection.commit()


def test_contract_coverage_preview_rejects_same_package_id_with_different_payload(
    isolated_db: Path,
) -> None:
    init_db(quiet=True)

    first = service.preview_import(_package(stfte_has_contract=True), db_path=isolated_db)
    conflicting = service.preview_import(_package(stfte_has_contract=False), db_path=isolated_db)

    assert first["status"] == "previewed"
    assert conflicting["status"] == "rejected"
    assert conflicting["failure_code"] == "CONTRACT_COVERAGE_PACKAGE_REPLAY_CONFLICT"


def test_contract_coverage_confirm_is_idempotent_and_publishes_once(
    isolated_db: Path,
) -> None:
    init_db(quiet=True)

    preview = service.preview_import(_package(), db_path=isolated_db)
    confirmed = service.confirm_import(preview["session_id"], db_path=isolated_db)
    repeated = service.confirm_import(preview["session_id"], db_path=isolated_db)

    assert confirmed["status"] == "completed"
    assert repeated["status"] == "completed"
    assert repeated["idempotent"] is True
    assert repeated["report"]["publication_id"] == confirmed["report"]["publication_id"]

    with sqlite3.connect(isolated_db) as connection:
        publication_count = connection.execute(
            "SELECT COUNT(*) FROM contract_coverage_publications"
        ).fetchone()[0]
    assert publication_count == 1


def test_contract_coverage_read_contract_reports_unavailable_unknown_then_known(
    isolated_db: Path,
    tmp_path: Path,
) -> None:
    uninitialized_db = tmp_path / "uninitialized.sqlite3"

    unavailable = read_model.current_publication_state(db_path=uninitialized_db)
    unavailable_freshness = read_model.current_publication_freshness(
        db_path=uninitialized_db
    )
    assert unavailable["state"] == "unavailable"
    assert unavailable["state_reason"] == "contract_coverage_schema_missing"
    assert unavailable_freshness["state"] == "unavailable"

    init_db(quiet=True)

    unknown = read_model.current_publication_state(db_path=isolated_db)
    unknown_freshness = read_model.current_publication_freshness(db_path=isolated_db)
    assert unknown["state"] == "unknown"
    assert unknown["state_reason"] == "contract_coverage_publication_not_found"
    assert unknown_freshness["state"] == "unknown"

    preview = service.preview_import(_package(), db_path=isolated_db)
    service.confirm_import(preview["session_id"], db_path=isolated_db)

    known = read_model.current_publication_state(db_path=isolated_db)
    fresh = read_model.current_publication_freshness(db_path=isolated_db)
    snapshot = read_model.contract_coverage_snapshot(db_path=isolated_db)
    member = read_model.member_contract_snapshot("WD100001", db_path=isolated_db)

    assert known["state"] == "known"
    assert fresh["state"] == "fresh"
    assert snapshot["state"] == "known"
    assert snapshot["freshness_state"] == "fresh"
    assert snapshot["summary"] == {
        "members": 2,
        "active_members": 2,
        "inactive_members": 0,
        "stfte_members": 1,
        "ltfte_members": 1,
        "contract_members": 1,
        "uncovered_stfte_members": 0,
        "unknown_resource_type_members": 0,
    }
    assert snapshot["members"][0]["contract_fact_state"] == "covered"
    assert snapshot["members"][1]["contract_fact_state"] == "not_required"
    assert member["state"] == "known"
    assert member["freshness_state"] == "fresh"
    assert member["member"]["current_hiref_id"] == "HIREF-001"


def test_contract_coverage_freshness_reports_stale_and_partial_states(
    isolated_db: Path,
) -> None:
    init_db(quiet=True)
    preview = service.preview_import(_package(), db_path=isolated_db)
    service.confirm_import(preview["session_id"], db_path=isolated_db)

    with sqlite3.connect(isolated_db) as connection:
        connection.execute(
            """
            UPDATE contract_coverage_publications
            SET published_at = '2000-01-01T00:00:00+00:00'
            WHERE is_current = 1
            """
        )
        connection.commit()
    stale = read_model.current_publication_freshness(db_path=isolated_db)
    assert stale["state"] == "stale"

    preview_partial = service.preview_import(
        _package(package_id="package-contract-coverage-r2", stfte_has_contract=False),
        db_path=isolated_db,
    )
    service.confirm_import(preview_partial["session_id"], db_path=isolated_db)
    partial = read_model.current_publication_freshness(db_path=isolated_db)
    assert partial["state"] == "partial"
    assert partial["coverage"]["member_contract_state"] == "partial"
    assert partial["coverage"]["missing_record_count"] == 1


def test_contract_coverage_publication_becomes_primary_for_hiref_member_reads(
    isolated_db: Path,
) -> None:
    _seed_legacy_hiref_state(isolated_db)

    preview = service.preview_import(
        {
            **_package(package_id="package-contract-coverage-legacy-r1"),
            "members": [
                {
                    "member_id": "990101",
                    "display_name": "Alex Example",
                    "status": "active",
                    "resource_type": "STFTE",
                    "current_hiref_id": None,
                    "hiref_end_date": None,
                },
                {
                    "member_id": "990102",
                    "display_name": "Blair Example",
                    "status": "active",
                    "resource_type": "LTFTE",
                    "current_hiref_id": None,
                    "hiref_end_date": None,
                },
            ],
            "manifest": {
                "member_ids": ["990101", "990102"],
                "stfte_member_ids": ["990101"],
                "ltfte_member_ids": ["990102"],
                "contract_member_ids": [],
                "unknown_resource_type_member_ids": [],
            },
        },
        db_path=isolated_db,
    )
    service.confirm_import(preview["session_id"], db_path=isolated_db)

    member = repository.get_member("990101")
    assert member is not None
    assert member["contract_coverage_state"] == "known"
    assert member["current_hiref"] == ""
    assert member["billing_end_date"] == ""

    review = HirefManagementService().review(days=90)
    assert review.success is True
    alex = next(row for row in review.data["rows"] if row["employee_id"] == "990101")
    assert alex["current_hiref_missing"] is True
    assert alex["contract_coverage_freshness_state"] == "partial"
