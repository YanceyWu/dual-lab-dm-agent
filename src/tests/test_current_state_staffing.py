from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from pm_agent.current_state_staffing import read_model, service
from pm_agent.database.bootstrap import main as init_db


def _package(*, package_id: str = "package-current-state-r1", allocation: float = 0.6) -> dict:
    assignments = []
    if allocation > 0:
        assignments.append(
            {
                "member_id": "WD100001",
                "project_id": "RP-PROJ-001",
                "allocation": allocation,
            }
        )
    return {
        "dataset_marker": "WORKBOOK_ONBOARDING_V1",
        "package_id": package_id,
        "schema_version": service.PACKAGE_SCHEMA_VERSION,
        "generated_at": "2026-08-15T00:00:00+00:00",
        "source_id": "source-workbook-current-state-staffing",
        "publication_scope": {
            "scope_key": "workbook-current-state-staffing",
            "as_of_date": "2026-08-15",
            "effective_year": 2026,
            "effective_month": 9,
        },
        "manifest": {
            "member_ids": ["WD100001", "WD100002"],
            "project_ids": ["RP-PROJ-001"],
            "assignment_keys": [
                {
                    "member_id": item["member_id"],
                    "project_id": item["project_id"],
                }
                for item in assignments
            ],
        },
        "members": [
            {
                "member_id": "WD100001",
                "display_name": "Alex Example",
                "status": "active",
                "role": "Engineer",
                "level": "7",
                "resource_type": "LTFTE",
                "current_hiref_id": None,
                "hiref_end_date": None,
            },
            {
                "member_id": "WD100002",
                "display_name": "Blair Example",
                "status": "active",
                "role": "Engineer",
                "level": "7",
                "resource_type": "LTFTE",
                "current_hiref_id": None,
                "hiref_end_date": None,
            },
        ],
        "projects": [
            {
                "project_id": "RP-PROJ-001",
                "display_name": "Project Atlas",
                "status": "active",
                "priority": 2,
            }
        ],
        "assignments": assignments,
    }


def test_current_state_staffing_preview_rejects_same_package_id_with_different_payload(
    isolated_db: Path,
) -> None:
    init_db(quiet=True)

    first = service.preview_import(_package(allocation=0.6), db_path=isolated_db)
    conflicting = service.preview_import(_package(allocation=0.4), db_path=isolated_db)

    assert first["status"] == "previewed"
    assert conflicting["status"] == "rejected"
    assert conflicting["failure_code"] == "CURRENT_STATE_STAFFING_PACKAGE_REPLAY_CONFLICT"


def test_current_state_staffing_confirm_is_idempotent_and_publishes_once(
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
            "SELECT COUNT(*) FROM current_state_staffing_publications"
        ).fetchone()[0]
    assert publication_count == 1


def test_current_state_staffing_read_contract_reports_unavailable_unknown_then_known(
    isolated_db: Path,
    tmp_path: Path,
) -> None:
    uninitialized_db = tmp_path / "uninitialized.sqlite3"

    unavailable = read_model.current_publication_state(db_path=uninitialized_db)
    unavailable_freshness = read_model.current_publication_freshness(
        db_path=uninitialized_db
    )
    assert unavailable["state"] == "unavailable"
    assert unavailable["state_reason"] == "current_state_staffing_schema_missing"
    assert unavailable_freshness["state"] == "unavailable"

    init_db(quiet=True)

    unknown = read_model.current_publication_state(db_path=isolated_db)
    unknown_freshness = read_model.current_publication_freshness(db_path=isolated_db)
    assert unknown["state"] == "unknown"
    assert unknown["state_reason"] == "current_state_staffing_publication_not_found"
    assert unknown_freshness["state"] == "unknown"

    preview = service.preview_import(_package(), db_path=isolated_db)
    service.confirm_import(preview["session_id"], db_path=isolated_db)

    known = read_model.current_publication_state(db_path=isolated_db)
    fresh = read_model.current_publication_freshness(db_path=isolated_db)
    snapshot = read_model.current_staffing_snapshot(db_path=isolated_db)
    member = read_model.member_load_snapshot("WD100001", db_path=isolated_db)
    unassigned = read_model.member_load_snapshot("WD100002", db_path=isolated_db)
    project = read_model.project_team_snapshot("RP-PROJ-001", db_path=isolated_db)

    assert known["state"] == "known"
    assert fresh["state"] == "fresh"
    assert snapshot["state"] == "known"
    assert snapshot["freshness_state"] == "fresh"
    assert [item["member_id"] for item in snapshot["members"]] == ["WD100001", "WD100002"]
    assert snapshot["projects"][0]["project_id"] == "RP-PROJ-001"
    assert member["state"] == "known"
    assert member["freshness_state"] == "fresh"
    assert member["current_load"] == 0.6
    assert member["active_project_count"] == 1
    assert unassigned["state"] == "known"
    assert unassigned["current_load"] == 0.0
    assert unassigned["assignment_state"] == "unassigned"
    assert project["state"] == "known"
    assert project["freshness_state"] == "fresh"
    assert project["assignment_state"] == "assigned"
    assert project["assignments"][0]["member_id"] == "WD100001"


def test_current_state_staffing_freshness_reports_stale_and_partial_states(
    isolated_db: Path,
) -> None:
    init_db(quiet=True)
    preview = service.preview_import(_package(), db_path=isolated_db)
    service.confirm_import(preview["session_id"], db_path=isolated_db)

    with sqlite3.connect(isolated_db) as connection:
        connection.execute(
            """
            UPDATE current_state_staffing_publications
            SET published_at = '2000-01-01T00:00:00+00:00'
            WHERE is_current = 1
            """
        )
        connection.commit()
    stale = read_model.current_publication_freshness(db_path=isolated_db)
    assert stale["state"] == "stale"

    with sqlite3.connect(isolated_db) as connection:
        report = connection.execute(
            """
            SELECT report_json
            FROM current_state_staffing_publications
            WHERE is_current = 1
            LIMIT 1
            """
        ).fetchone()[0]
        parsed = json.loads(report)
        parsed["coverage"]["assignment_manifest_state"] = "partial"
        parsed["coverage"]["missing_record_count"] = 1
        connection.execute(
            """
            UPDATE current_state_staffing_publications
            SET report_json = ?
            WHERE is_current = 1
            """,
            [json.dumps(parsed)],
        )
        connection.commit()
    partial = read_model.current_publication_freshness(db_path=isolated_db)
    assert partial["state"] == "partial"


def test_legacy_member_and_project_views_are_derived_from_current_publication(
    isolated_db: Path,
) -> None:
    init_db(quiet=True)
    with sqlite3.connect(isolated_db) as connection:
        connection.execute(
            """
            INSERT INTO employees
                (id, wd_id, name, team, max_parallel, status, skills)
            VALUES
                ('employee-1', 'WD100001', 'Legacy Alex', 'Platform', 5, 'active', '{"python": 0.9}')
            """
        )
        connection.execute(
            """
            INSERT INTO projects
                (id, name, jira_key, target_end, status, priority)
            VALUES
                ('RP-PROJ-001', 'Legacy Project Atlas', 'ATLAS', '2026-12-31', 'active', 2)
            """
        )
        connection.execute(
            """
            INSERT INTO assignments
                (employee_id, project_id, role, allocation, start_date, status)
            VALUES
                ('employee-1', 'RP-PROJ-001', 'legacy', 0.1, '2026-08-01', 'active')
            """
        )
        connection.commit()

    preview = service.preview_import(_package(allocation=0.6), db_path=isolated_db)
    service.confirm_import(preview["session_id"], db_path=isolated_db)

    with sqlite3.connect(isolated_db) as connection:
        member_row = connection.execute(
            """
            SELECT id, name, team, max_parallel, current_load, active_projects
            FROM v_member_load
            WHERE id = 'WD100001'
            """
        ).fetchone()
        project_row = connection.execute(
            """
            SELECT project_id, project_name, jira_key, target_end, member_id, member_name, allocation
            FROM v_project_team
            WHERE project_id = 'RP-PROJ-001'
            """
        ).fetchone()

    assert member_row == ("WD100001", "Alex Example", "Platform", 5, 0.6, 1)
    assert project_row == (
        "RP-PROJ-001",
        "Project Atlas",
        "ATLAS",
        "2026-12-31",
        "WD100001",
        "Alex Example",
        0.6,
    )


def test_current_state_publication_freshness_is_decoupled_from_legacy_source_sla(
    isolated_db: Path,
) -> None:
    init_db(quiet=True)
    preview = service.preview_import(_package(), db_path=isolated_db)
    service.confirm_import(preview["session_id"], db_path=isolated_db)

    with sqlite3.connect(isolated_db) as connection:
        connection.execute(
            """
            UPDATE current_state_staffing_publications
            SET published_at = '2026-08-04T00:00:00+00:00'
            WHERE is_current = 1
            """
        )
        connection.execute(
            """
            UPDATE data_sources
            SET refresh_sla_hours = 1
            WHERE id = 'import-resource-portal'
            """
        )
        connection.commit()

    freshness = read_model.current_publication_freshness(db_path=isolated_db)

    assert freshness["source_id"] == "current-state-staffing-publication"
    assert freshness["refresh_sla_hours"] == 720.0
    assert freshness["state"] == "fresh"
