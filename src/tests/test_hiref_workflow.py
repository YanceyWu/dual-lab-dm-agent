from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pytest
from typer.testing import CliRunner

from pm_agent.cli import app as app_module
from contract_coverage_test_helpers import publish_contract_coverage_from_legacy
from current_state_staffing_test_helpers import publish_current_state_staffing_from_legacy
from pm_agent.database.bootstrap import main as init_db
from pm_agent.dashboard import server as dashboard_server
from pm_agent.rules.hiref import project_alignment_status
from pm_agent.use_cases import hiref_management_service


def _seed_hiref_scenario(db_path: Path) -> None:
    init_db(quiet=True)

    today = date.today()
    plan_version_id = "baseline-2026"

    con = sqlite3.connect(db_path)
    con.execute("PRAGMA foreign_keys = ON")
    try:
        con.execute(
            """
            INSERT INTO plan_versions
                (plan_version_id, version_name, scenario_type, version_status)
            VALUES
                (?, 'Baseline 2026', 'baseline', 'active')
            """,
            [plan_version_id],
        )
        con.executemany(
            """
            INSERT INTO projects
                (id, name, jira_key, status, priority)
            VALUES (?, ?, ?, 'active', 1)
            """,
            [
                ("project-atlas-990001", "Project Atlas", "990001"),
                ("project-beacon-990002", "Project Beacon", "990002"),
                ("project-cedar-990003", "Project Cedar", "990003"),
            ],
        )
        con.executemany(
            """
            INSERT INTO employees
                (id, wd_id, name, level, status, resource_type, current_hiref, next_hiref, billing_end_date)
            VALUES (?, ?, ?, 'mid', 'active', ?, ?, ?, ?)
            """,
            [
                ("990101", "990101", "Alex Example", "STFTE", "HIREF-ATLAS-001", "", (today + timedelta(days=30)).isoformat()),
                ("990102", "990102", "Blair Example", "STFTE", "HIREF-CEDAR-001", "HIREF-CEDAR-NEXT", (today + timedelta(days=50)).isoformat()),
                ("990103", "990103", "Casey Example", "STFTE", "", "", ""),
            ],
        )
        con.executemany(
            """
            INSERT INTO assignments
                (employee_id, project_id, allocation, status)
            VALUES (?, ?, ?, 'active')
            """,
            [
                ("990101", "project-beacon-990002", 0.5),
                ("990102", "project-cedar-990003", 0.8),
            ],
        )
        con.executemany(
            """
            INSERT INTO hiref
                (id, project, request_type, start_date, end_date, notes)
            VALUES (?, ?, 'extend', ?, ?, '')
            """,
            [
                (
                    "HIREF-ATLAS-001",
                    "Project Atlas (990001)",
                    (today - timedelta(days=300)).isoformat(),
                    (today + timedelta(days=30)).isoformat(),
                ),
                (
                    "HIREF-CEDAR-001",
                    "Project Cedar (990003)",
                    (today - timedelta(days=200)).isoformat(),
                    (today + timedelta(days=50)).isoformat(),
                ),
                (
                    "HIREF-CEDAR-NEXT",
                    "Project Cedar (990003)",
                    (today + timedelta(days=51)).isoformat(),
                    (today + timedelta(days=365)).isoformat(),
                ),
                (
                    "HIREF-FREE-001",
                    "Project Beacon (990002)",
                    (today - timedelta(days=30)).isoformat(),
                    (today + timedelta(days=120)).isoformat(),
                ),
            ],
        )
        con.execute(
            """
            INSERT INTO staffing_placeholders
                (placeholder_id, display_name, source_system, hiref_id, status, notes)
            VALUES
                ('placeholder-qabi', 'To Be Hired', 'resource_portal', 'HIREF-OPEN-001', 'planned', 'Open contractor demand')
            """
        )
        con.execute(
            """
            INSERT INTO placeholder_monthly_allocations
                (placeholder_id, project_id, year, month, allocation, plan_version_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                "placeholder-qabi",
                "project-beacon-990002",
                (today + timedelta(days=31)).year,
                (today + timedelta(days=31)).month,
                0.5,
                plan_version_id,
            ],
        )
        con.commit()
    finally:
        con.close()
    publish_contract_coverage_from_legacy(
        db_path,
        package_id="package-hiref-contract-coverage-r1",
    )
    publish_current_state_staffing_from_legacy(
        db_path,
        package_id="package-hiref-current-state-r1",
    )


def test_hiref_management_service_surfaces_expiry_slot_and_placeholder_risks(
    isolated_db: Path,
) -> None:
    _seed_hiref_scenario(isolated_db)

    summary = hiref_management_service.summary(days=90)
    assert summary.success is True
    assert summary.data["freshness"]["state"] == "partial"
    assert summary.data["summary"] == {
        "active_stfte": None,
        "review_window_days": 90,
        "missing_current_hiref": None,
        "expiring_without_next": None,
        "expiring_with_next": None,
        "project_mismatches": None,
        "free_slots": None,
        "assigned_slots": None,
        "reserved_slots": None,
        "open_placeholders": 1,
        "unregistered_placeholder_slots": 1,
    }

    review_rows = hiref_management_service.review(days=90).data["rows"]
    alex = next(row for row in review_rows if row["name"] == "Alex Example")
    assert alex["project_alignment_status"] == "mismatch"
    assert alex["urgency"] == "critical"

    missing = next(row for row in review_rows if row["name"] == "Casey Example")
    assert missing["current_hiref_missing"] is True
    assert missing["urgency"] == "critical"

    slots = hiref_management_service.slots(free_only=True).data["rows"]
    assert slots == []
    all_slots = hiref_management_service.slots(free_only=False).data["rows"]
    free_slot = next(row for row in all_slots if row["id"] == "HIREF-FREE-001")
    assert free_slot["occupancy_status"] == "unknown"

    placeholders = hiref_management_service.placeholders().data["rows"]
    assert len(placeholders) == 1
    assert placeholders[0]["slot_registered"] is False
    assert placeholders[0]["project_display"] == "Project Beacon"


def test_hiref_cli_commands_render_with_seeded_data(isolated_db: Path) -> None:
    _seed_hiref_scenario(isolated_db)
    runner = CliRunner()

    summary_result = runner.invoke(app_module.app, ["hiref", "summary", "--days", "90"])
    assert summary_result.exit_code == 0, summary_result.output
    assert "HIREF Summary" in summary_result.output
    assert "缺少当前HIREF" in summary_result.output

    review_result = runner.invoke(app_module.app, ["hiref", "review", "--days", "90"])
    assert review_result.exit_code == 0, review_result.output
    assert "Actionable: 2" in review_result.output

    placeholder_result = runner.invoke(app_module.app, ["hiref", "placeholders"])
    assert placeholder_result.exit_code == 0, placeholder_result.output
    assert "To Be Hired" in placeholder_result.output


def test_hiref_dashboard_api_exposes_next_hiref_and_mismatch_context(
    isolated_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_hiref_scenario(isolated_db)
    monkeypatch.setattr(dashboard_server, "DB", str(isolated_db))

    client = dashboard_server.app.test_client()
    response = client.get("/api/hiref")

    assert response.status_code == 200
    assert response.headers["X-DM-Interface-Contract"] == "legacy-result-projection"
    payload = response.get_json()
    assert payload["contract_coverage_freshness_state"] == "partial"
    assert payload["next_covered_count"] is None
    assert payload["mismatch_count"] is None

    atlas_slot = next(item for item in payload["all_hiref"] if item["id"] == "HIREF-ATLAS-001")
    assert atlas_slot["project_alignment_status"] == "mismatch"
    assert atlas_slot["actual_project_display"] == "Project Beacon"

    cedar_slot = next(item for item in payload["all_hiref"] if item["id"] == "HIREF-CEDAR-001")
    assert cedar_slot["has_next_hiref"] is True
    assert cedar_slot["assigned_next_hiref"] == "HIREF-CEDAR-NEXT"
    assert cedar_slot["assigned_next_hiref_end_date"] is not None

    blair = next(item for item in payload["expiring_staff"] if item["name"] == "Blair Example")
    assert blair["next_hiref"] == "HIREF-CEDAR-NEXT"
    assert blair["project_alignment_status"] == "aligned"

    alex = next(item for item in payload["expiring_staff"] if item["name"] == "Alex Example")
    assert alex["project_alignment_status"] == "mismatch"


def test_hiref_summary_keeps_missing_contract_publication_explicit(
    isolated_db: Path,
) -> None:
    init_db(quiet=True)
    today = date.today()
    with sqlite3.connect(isolated_db) as con:
        con.execute(
            """
            INSERT INTO employees
                (id, wd_id, name, level, status, resource_type, current_hiref, billing_end_date)
            VALUES
                ('990301', '990301', 'Jordan Example', 'mid', 'active', 'STFTE', 'HIREF-UNKNOWN-001', ?)
            """,
            [(today + timedelta(days=30)).isoformat()],
        )
        con.execute(
            """
            INSERT INTO hiref
                (id, project, request_type, start_date, end_date, notes)
            VALUES
                ('HIREF-UNKNOWN-001', 'Project Unknown (990301)', 'extend', ?, ?, '')
            """,
            [
                (today - timedelta(days=60)).isoformat(),
                (today + timedelta(days=30)).isoformat(),
            ],
        )
        con.commit()

    summary = hiref_management_service.summary(days=90)
    assert summary.success is True
    assert summary.data["freshness"]["state"] == "unknown"
    assert summary.data["summary"]["active_stfte"] is None
    assert summary.data["summary"]["missing_current_hiref"] is None
    assert summary.data["summary"]["free_slots"] is None


def test_hiref_project_aliases_treat_related_project_name_as_aligned() -> None:
    assert project_alignment_status(
        "Project Cedar Delivery (990003)",
        actual_project_names=["Cedar Delivery Stream"],
        actual_project_ids=["project-cedar-stream-990003"],
        alias_groups=[{"project-cedar-delivery", "cedar-delivery-stream"}],
    ) == "aligned"
